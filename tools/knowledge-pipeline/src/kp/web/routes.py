from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any

import markdown as md_lib
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from kp.events import EventStore, ItemArchived, ItemUnarchived
from kp.web._data import load_memos, short_id

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _get_store() -> EventStore:
    return EventStore()


def _filter_memos(
    memos: list[dict[str, Any]],
    *,
    source: str | None,
    has_speakers: str | None,
    archived: str | None,
    state: str | None,
) -> list[dict[str, Any]]:
    result = memos
    if source:
        result = [m for m in result if m["source"] == source]
    if has_speakers:
        hs = has_speakers.strip()
        if hs.endswith("+"):
            try:
                min_count = int(hs[:-1])
            except ValueError:
                min_count = 1
            result = [m for m in result if len(m["speakers"]) >= min_count]
        else:
            try:
                exact = int(hs)
                result = [m for m in result if len(m["speakers"]) == exact]
            except ValueError:
                pass
    if archived == "all":
        pass  # no archive filter
    elif archived:  # any truthy non-"all" value -> archived only
        result = [m for m in result if m.get("archived")]
    else:
        result = [m for m in result if not m.get("archived")]
    if state:
        s = state.strip().lower()
        if s == "ingested_only":
            result = [m for m in result if m["pipeline_state"] in ("ingested", "normalized")]
        elif s == "transcribed_unanalyzed":
            result = [m for m in result if m["pipeline_state"] in ("transcribed", "diarized")]
        elif s == "analyzed":
            result = [m for m in result if m["pipeline_state"] == "analyzed"]
        elif s == "multi_speaker":
            result = [m for m in result if len(m["speakers"]) >= 2]
        elif s == "has_polished":
            result = [m for m in result if m.get("polished_md_path")]
        elif s == "has_macwhisper":
            result = [m for m in result if m.get("macwhisper_vtt_path")]
    return result


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    source: str | None = None,
    has_speakers: str | None = None,
    archived: str | None = None,
    state: str | None = None,
) -> HTMLResponse:
    store = _get_store()
    try:
        memos = load_memos(store)
        memos = _filter_memos(
            memos,
            source=source,
            has_speakers=has_speakers,
            archived=archived,
            state=state,
        )
    finally:
        store.close()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "memos": memos,
            "filter_source": source or "",
            "filter_has_speakers": has_speakers or "",
            "filter_archived": archived,
            "filter_state": state or "",
        },
    )


@router.get("/memo/{content_hash}", response_class=HTMLResponse)
async def memo_detail(request: Request, content_hash: str) -> HTMLResponse:
    store = _get_store()
    try:
        all_memos = load_memos(store)
    finally:
        store.close()

    if content_hash.startswith("kp-"):
        memo: dict[str, Any] | None = next(
            (m for m in all_memos if m["short_id"] == content_hash), None
        )
    else:
        memo: dict[str, Any] | None = next(
            (m for m in all_memos if m["content_hash"] == content_hash), None
        )
    if memo is None:
        return HTMLResponse("<h1>Memo not found</h1>", status_code=404)

    side_html: str | None = None
    side_label: str | None = None
    polished_path = memo.get("polished_md_path")
    vtt_path = memo.get("macwhisper_vtt_path")
    if polished_path and Path(polished_path).exists():
        raw_md = Path(polished_path).read_text(encoding="utf-8")
        side_html = md_lib.markdown(raw_md, extensions=["nl2br", "fenced_code"])
        side_label = "Polished Notes"
    elif vtt_path and Path(vtt_path).exists():
        side_html = Path(vtt_path).read_text(encoding="utf-8")
        side_label = "VTT Transcript"

    has_audio = bool(memo.get("audio_path") and Path(memo["audio_path"]).exists())
    parent_dir = str(Path(memo["audio_path"]).parent) if memo.get("audio_path") else None

    return templates.TemplateResponse(
        request,
        "memo.html",
        {
            "memo": memo,
            "side_html": side_html,
            "side_label": side_label,
            "has_audio": has_audio,
            "parent_dir": parent_dir,
        },
    )


@router.post("/memo/{content_hash}/archive")
async def memo_archive_toggle(content_hash: str, action: str = Form(default="toggle")) -> RedirectResponse:
    """Archive or unarchive a memo. action=archive|unarchive|toggle."""
    store = _get_store()
    try:
        # Resolve short_id form
        if content_hash.startswith("kp-"):
            memos = load_memos(store)
            m = next((mm for mm in memos if mm["short_id"] == content_hash), None)
            if m is None:
                raise HTTPException(404, "Memo not found")
            ch = m["content_hash"]
            source = m["source"]
            currently_archived = m["archived"]
        else:
            # Look up source + current state from a single load
            memos = load_memos(store)
            m = next((mm for mm in memos if mm["content_hash"] == content_hash), None)
            if m is None:
                raise HTTPException(404, "Memo not found")
            ch = content_hash
            source = m["source"]
            currently_archived = m["archived"]

        if action == "archive" or (action == "toggle" and not currently_archived):
            store.append(ItemArchived(source=source, content_hash=ch, data={}))
        elif action == "unarchive" or (action == "toggle" and currently_archived):
            store.append(ItemUnarchived(source=source, content_hash=ch, data={}))
    finally:
        store.close()

    return RedirectResponse(url=f"/memo/{ch}", status_code=303)


@router.get("/audio/{content_hash}")
async def memo_audio(content_hash: str) -> FileResponse:
    """Stream the audio file for a memo. Reads ItemNormalized.data.path."""
    store = _get_store()
    try:
        memos = load_memos(store)
    finally:
        store.close()

    if content_hash.startswith("kp-"):
        memo = next((m for m in memos if m["short_id"] == content_hash), None)
    else:
        memo = next((m for m in memos if m["content_hash"] == content_hash), None)
    if memo is None:
        raise HTTPException(status_code=404, detail="Memo not found")
    audio = memo.get("audio_path")
    if not audio:
        raise HTTPException(status_code=404, detail="No audio path recorded")
    p = Path(audio)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Audio file missing: {p}")
    media_type, _ = mimetypes.guess_type(str(p))
    return FileResponse(str(p), media_type=media_type or "audio/mp4")


@router.get("/status", response_class=HTMLResponse)
async def status(request: Request) -> HTMLResponse:
    store = _get_store()
    try:
        rows = list(store.all())
    finally:
        store.close()
    # Aggregate counts per (event_type, source)
    by_type: dict[str, int] = {}
    by_source: dict[str, dict[str, int]] = {}
    hashes_by_stage: dict[str, set[str]] = {}
    total_cost = 0.0
    for r in rows:
        et = r["event_type"]
        src = r["source"]
        ch = r["content_hash"]
        by_type[et] = by_type.get(et, 0) + 1
        by_source.setdefault(src, {})[et] = by_source.setdefault(src, {}).get(et, 0) + 1
        hashes_by_stage.setdefault(et, set()).add(ch)
        if et == "AnalysisCompleted":
            import json as _j

            try:
                d = _j.loads(r["data_json"]) if r.get("data_json") else {}
                total_cost += float(d.get("cost_usd") or 0.0)
            except Exception:
                pass
    # Per-stage totals (unique items reaching each stage)
    stages = [
        "ItemIngested",
        "ItemNormalized",
        "ItemTranscribed",
        "SpeakerDiarized",
        "AnalysisCompleted",
    ]
    stage_counts = {s: len(hashes_by_stage.get(s, set())) for s in stages}
    total_items = stage_counts.get("ItemIngested", 0)
    # Recent 30 events newest-first
    rows_desc = sorted(rows, key=lambda x: x.get("id", 0), reverse=True)[:30]
    recent = [
        {
            "id": r.get("id"),
            "ts": r.get("timestamp", ""),
            "event_type": r["event_type"],
            "source": r["source"],
            "short_id": short_id(r["content_hash"]),
        }
        for r in rows_desc
    ]
    return templates.TemplateResponse(
        request,
        "status.html",
        {
            "by_type": by_type,
            "by_source": by_source,
            "stage_counts": stage_counts,
            "total_items": total_items,
            "total_cost": round(total_cost, 6),
            "recent": recent,
        },
    )


@router.get("/api/memos.json")
async def api_memos() -> JSONResponse:
    store = _get_store()
    try:
        memos = load_memos(store)
        memos = _filter_memos(memos, source=None, has_speakers=None, archived="all", state=None)
    finally:
        store.close()
    # strip large internal fields not useful for the JSON API consumers
    slim = []
    for m in memos:
        copy = dict(m)
        copy.pop("all_events", None)
        copy.pop("diarized_segments", None)
        slim.append(copy)
    return JSONResponse(content=slim)
