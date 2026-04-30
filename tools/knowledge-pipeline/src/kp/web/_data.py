from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from kp.events import EventStore


_PARAGRAPH_GAP_SECONDS = 1.5
_VOICE_MEMOS_RE = re.compile(r"^(\d{8})\s+(\d{6})")  # 20260214 143432
_ISO_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")     # 2025-10-26


def _date_from_title(title: str | None) -> str | None:
    """Extract YYYY-MM-DD from a title that encodes a recording date."""
    if not title:
        return None
    from datetime import datetime
    m = _VOICE_MEMOS_RE.match(title)
    if m:
        try:
            dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
            return dt.date().isoformat()
        except ValueError:
            pass
    m = _ISO_DATE_RE.search(title)
    if m:
        try:
            datetime.strptime(m.group(1), "%Y-%m-%d")
            return m.group(1)
        except ValueError:
            pass
    return None
_CROCKFORD = "0123456789abcdefghjkmnpqrstvwxyz"


def short_id(content_hash: str) -> str:
    """Crockford base32 of the first 40 bits of the content_hash, prefixed with 'kp-'."""
    if not content_hash:
        return "kp-?"
    n = int(content_hash[:10], 16)  # first 40 bits = first 10 hex chars
    out = []
    for _ in range(8):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "kp-" + "".join(reversed(out))


def format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    s = int(round(seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s // 3600}h{(s % 3600) // 60:02d}m"


def format_timestamp(seconds: float) -> str:
    s = int(seconds)
    if s < 3600:
        return f"{s // 60}:{s % 60:02d}"
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _empty_entry(content_hash: str, source: str) -> dict[str, Any]:
    return {
        "content_hash": content_hash,
        "short_id": short_id(content_hash),
        "source": source,
        "date": None,
        "title": None,
        "duration": None,
        "duration_label": "—",
        "speakers": [],
        "people": [],
        "topics": [],
        "summary": None,
        "memo_type": None,
        "action_items": [],
        "transcript_text": None,
        "diarized_segments": [],  # raw [{start,end,speaker_id,text}]
        "speaker_groups": [],     # chronological groups: [{speaker_id, start, end, paragraphs:[str], start_label}]
        "macwhisper_vtt_path": None,
        "polished_md_path": None,
        "audio_path": None,
        "all_events": [],
        "archived": False,
        "pipeline_state": "ingested",
        "_earliest_timestamp": None,
    }


def _build_speaker_groups(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group consecutive same-speaker segments; split into paragraphs on long pauses."""
    groups: list[dict[str, Any]] = []
    if not segments:
        return groups

    cur_spk: str | None = None
    cur_group: dict[str, Any] | None = None
    cur_para: list[str] = []
    last_end: float = 0.0

    def flush_para():
        nonlocal cur_para
        if cur_group is not None and cur_para:
            cur_group["paragraphs"].append(" ".join(p.strip() for p in cur_para if p.strip()))
            cur_para = []

    def flush_group():
        nonlocal cur_group
        flush_para()
        if cur_group is not None and cur_group["paragraphs"]:
            groups.append(cur_group)
        cur_group = None

    for seg in segments:
        spk = seg.get("speaker_id") or "SPEAKER_UNKNOWN"
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        if spk != cur_spk:
            flush_group()
            cur_spk = spk
            cur_group = {
                "speaker_id": spk,
                "start": start,
                "end": end,
                "start_label": format_timestamp(start),
                "paragraphs": [],
            }
            cur_para = [text]
        else:
            # same speaker; paragraph break on gap
            if start - last_end > _PARAGRAPH_GAP_SECONDS and cur_para:
                flush_para()
            cur_para.append(text)
            cur_group["end"] = end
        last_end = end

    flush_group()
    return groups


def load_memos(store: EventStore) -> list[dict[str, Any]]:
    """One-pass scan of all events, grouped by content_hash. Sorted by date desc."""
    data: dict[str, dict[str, Any]] = {}

    for row in store.all():
        et = row["event_type"]
        ch = row["content_hash"]
        source = row["source"]
        timestamp = row.get("timestamp", "")
        entry = data.setdefault(ch, _empty_entry(ch, source))

        if entry["_earliest_timestamp"] is None or timestamp < entry["_earliest_timestamp"]:
            entry["_earliest_timestamp"] = timestamp

        ev_data: dict[str, Any] = json.loads(row["data_json"]) if row.get("data_json") else {}
        metadata: dict[str, Any] = ev_data.get("metadata", {})

        # always keep raw event row for the detail-page expandable
        entry["all_events"].append({
            "id": row.get("id"),
            "timestamp": timestamp,
            "event_type": et,
            "data": ev_data,
        })

        if et == "ItemIngested":
            if not entry["macwhisper_vtt_path"] and metadata.get("macwhisper_vtt_path"):
                entry["macwhisper_vtt_path"] = metadata["macwhisper_vtt_path"]
            if not entry["polished_md_path"] and metadata.get("polished_md_path"):
                entry["polished_md_path"] = metadata["polished_md_path"]
            if not entry["title"] and metadata.get("filename"):
                entry["title"] = Path(metadata["filename"]).stem
            if not entry["date"] and metadata.get("recorded_at"):
                entry["date"] = metadata["recorded_at"][:10]
            if entry["source"] == "voice_memo" and not entry.get("_original_path") and ev_data.get("path"):
                entry["_original_path"] = ev_data["path"]

        elif et == "ItemNormalized":
            if not entry["macwhisper_vtt_path"] and metadata.get("macwhisper_vtt_path"):
                entry["macwhisper_vtt_path"] = metadata["macwhisper_vtt_path"]
            if not entry["polished_md_path"] and metadata.get("polished_md_path"):
                entry["polished_md_path"] = metadata["polished_md_path"]
            if not entry["date"] and metadata.get("date"):
                entry["date"] = metadata["date"]
            if not entry["date"] and metadata.get("recorded_at"):
                entry["date"] = metadata["recorded_at"][:10]
            if not entry["title"] and metadata.get("generated_title"):
                entry["title"] = metadata["generated_title"]
            if not entry["title"] and metadata.get("filename"):
                entry["title"] = Path(metadata["filename"]).stem
            # audio path comes from the post-conversion (or pass-through) path written by normalize
            # Only voice_memo has audio; polished_memo's path points at a .md file
            if entry["source"] == "voice_memo" and not entry["audio_path"] and ev_data.get("path"):
                entry["audio_path"] = ev_data["path"]

        elif et == "ItemTranscribed":
            if not entry["transcript_text"] and ev_data.get("text"):
                entry["transcript_text"] = ev_data["text"]
            if entry["duration"] is None and metadata.get("duration") is not None:
                entry["duration"] = float(metadata["duration"])

        elif et == "SpeakerDiarized":
            speakers = ev_data.get("speakers") or []
            if speakers:
                entry["speakers"] = speakers
            segments = ev_data.get("segments") or []
            if segments and not entry["diarized_segments"]:
                entry["diarized_segments"] = segments
                entry["speaker_groups"] = _build_speaker_groups(segments)

        elif et == "AnalysisCompleted":
            analysis: dict[str, Any] = ev_data.get("analysis") or {}
            if not entry["summary"] and analysis.get("summary"):
                entry["summary"] = analysis["summary"]
            if analysis.get("action_items"):
                entry["action_items"] = analysis["action_items"]
            if analysis.get("people"):
                entry["people"] = analysis["people"]
            if analysis.get("topics"):
                entry["topics"] = analysis["topics"]
            if not entry["memo_type"] and analysis.get("memo_type"):
                entry["memo_type"] = analysis["memo_type"]
            if not entry["speakers"] and analysis.get("speakers"):
                entry["speakers"] = analysis["speakers"]
            if not entry["title"] and analysis.get("summary"):
                entry["title"] = analysis["summary"][:60]

        elif et == "ItemArchived":
            entry["archived"] = True
        elif et == "ItemUnarchived":
            entry["archived"] = False

    # Pipeline state — highest stage reached
    def _compute_state(entry: dict) -> str:
        has_events_by_type = {ev["event_type"] for ev in entry["all_events"]}
        if "AnalysisCompleted" in has_events_by_type:
            return "analyzed"
        if "SpeakerDiarized" in has_events_by_type:
            return "diarized"
        if "ItemTranscribed" in has_events_by_type:
            return "transcribed"
        if "ItemNormalized" in has_events_by_type:
            return "normalized"
        return "ingested"

    for entry in data.values():
        entry["pipeline_state"] = _compute_state(entry)

    # Resolve fallbacks
    for entry in data.values():
        if not entry["date"]:
            # Try title (which holds original filename stem) for encoded date
            entry["date"] = _date_from_title(entry.get("title"))
        if not entry["date"]:
            # Try the audio file's mtime if we know its path (backfill for pre-recorded_at events).
            # Prefer the original ingest path (e.g. .qta) over audio_path (which is the
            # cache .m4a for converted files and would carry a today-ish mtime).
            candidates = [entry.get("_original_path"), entry.get("audio_path")]
            for ap in candidates:
                if not ap or re.search(r"/cache/audio/[0-9a-f]{60,}", ap):
                    continue
                try:
                    import os as _os
                    from datetime import datetime as _dt, timezone as _tz
                    mtime = _os.stat(ap).st_mtime
                    entry["date"] = _dt.fromtimestamp(mtime, tz=_tz.utc).date().isoformat()
                    break
                except OSError:
                    pass
        if not entry["date"] and entry["_earliest_timestamp"]:
            entry["date"] = entry["_earliest_timestamp"][:10]
        del entry["_earliest_timestamp"]
        entry.pop("_original_path", None)
        entry["duration_label"] = format_duration(entry["duration"])

    result = list(data.values())
    result.sort(key=lambda e: e["date"] or "", reverse=True)
    return result
