# Parallelism Feasibility — 2026-04-30

## Verdict: MPS_FIRST

**Summary**: MPS is available on this machine (Apple Silicon). Memory is critically constrained
(~147 MB free, system already deep in compressor at ~27 GB compressed into 6 GB). SQLite is in
`delete` mode — not WAL — so multiple writers would cause SQLITE_BUSY serialization. Single-process
with MPS will outperform any parallel CPU sharding scheme.

---

## Hardware
- **RAM**: 16 GB total (`hw.memsize: 17179869184`)
- **CPU cores (logical/physical)**: 10 / 10 (Apple Silicon M-series, no hyperthreading)
- **MPS available**: **yes** (`torch.backends.mps.is_available() = True`)

---

## RAM Headroom Analysis

From `vm_stat` (page size = 16 KB):

| Metric | Pages | Bytes |
|---|---|---|
| Free | 8,993 | ~147 MB |
| Active | 201,022 | ~3.1 GB |
| Inactive (reclaimable) | 195,680 | ~3.1 GB |
| Wired | 218,726 | ~3.4 GB |
| In compressor (compressed data) | 1,750,732 | ~27 GB of data → 6.3 GB compressed |

**Total estimated in use**: ~15.9 GB of 16 GB.

The compressor holding 27 GB of logical data (compressed to 6 GB) is a strong signal the system
is already at memory capacity. The OS is actively swapping/compressing to maintain headroom.

**Parallel headroom assessment:**
- pyannote model: ~2 GB per process
- whisperx ASR (base): ~150 MB; (large-v2): ~3 GB
- 2 parallel processes minimum cost: ~4 GB (just for pyannote) + ASR copies
- Available before swap: ~147 MB free + up to ~3.1 GB inactive reclaim = ~3.2 GB theoretical max
- **Conclusion**: 2 parallel processes fit only with base-sized ASR models and aggressive reclamation.
  Any larger model configuration will immediately swap-thrash, making parallelism slower than serial.

---

## SQLite
- **journal_mode**: `delete` (confirmed: `PRAGMA journal_mode` → `delete`)
- **WAL mode**: NOT enabled
- **Contention risk**: **HIGH**

In `delete` mode, SQLite uses an exclusive write lock on the entire database file for the duration
of each write transaction. Multiple concurrent `kp run` writers will:
1. Hit `SQLITE_BUSY` on every write collision
2. Retry with backoff (default SQLite busy_timeout behavior)
3. Serialize all writes — effectively single-threaded DB throughput anyway

The ingest-heavy phase (embedding writes, event inserts) is particularly exposed. The
transcribe/diarize-heavy phase does fewer DB writes but longer per-file wall-clock time, so
contention would occur in bursts at the end of each file's pipeline stage.

**Even if WAL were enabled**, the CPU and RAM constraints make parallelism unattractive here.

---

## Model Load Cost

From `whisperx_backend.py`:
- `WhisperXBackend` lazy-loads `_asr` (whisperx model) and `_diar` (pyannote `DiarizationPipeline`)
- No model caching or sharing across processes — each `kp run` subprocess gets its own copies
- `DiarizationPipeline` from pyannote-audio loads ~2 GB of speaker diarization model weights
- Each `kp run` also loads `whisperx.load_align_model` per file (alignment model, ~500 MB)

| Resource | 1 process | 2 processes | 3 processes |
|---|---|---|---|
| pyannote RAM | ~2 GB | ~4 GB | ~6 GB |
| Fits in available RAM | marginal | **no** | **no** |

**2 parallel processes will not fit without severe swap thrashing.**

---

## CPU Saturation Analysis

- 10 physical cores, Apple Silicon (efficiency + performance cores)
- Diarization via pyannote runs on CPU (until D1 MPS fix lands)
- whisperx transcription + alignment: CPU-bound or MPS-accelerated
- 2-3 parallel diarization jobs would saturate all P-cores, leaving no headroom for:
  - macOS scheduling overhead
  - DB writes
  - The alignment + speaker assignment steps that interleave with diarization

With MPS available and Worker C's fix in place:
- GPU inference via MPS offloads the model compute from CPU entirely
- P-cores stay available for audio loading, alignment CPU steps, DB writes
- Single-process wall time with MPS likely < parallel CPU wall time × N

---

## Recommendation for Worker A

**Wait for Worker C's D1 MPS fix to merge, then run single-process:**

```bash
kp run \
  --source voice_memo \
  --path '/path/to/VOICE MEMO DUMP' \
  --stages transcribe,diarize,analyze,embed \
  --no-dry-run
```

Once D1 lands and `device` defaults to or accepts `mps`, the MPS-accelerated single process will:
- Use GPU for model inference (free from CPU contention)
- Avoid model double-load RAM pressure
- Avoid SQLite delete-mode write serialization errors
- Process files sequentially without memory thrashing

**Do NOT shard into parallel `kp run` invocations on this machine.**

---

## Rationale

Three independent blockers each individually rule out parallelism:

1. **RAM**: System is at ~99% capacity. Loading 2× pyannote models would require ~4 GB, which is
   beyond available headroom without severe swap. Swap on M-series flash is fast but adds 2-10×
   latency per page fault under load — eliminating any throughput gain from parallelism.

2. **SQLite delete mode**: Not WAL. Multiple concurrent writers = exclusive locks + SQLITE_BUSY
   retries. The pipeline cannot safely run N writers against the same `events.db` without enabling
   WAL mode first (`PRAGMA journal_mode=WAL`). Even then, RAM is the binding constraint.

3. **MPS available**: The entire premise of parallelism was "MPS not available, CPU only, so spread
   across cores." MPS IS available. Single-process MPS diarization will be faster than parallel
   CPU diarization on this 16 GB machine.

**MPS_FIRST is the correct verdict.**
