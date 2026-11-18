"""Fetch a bounded public Infrabel D-1 capture for confirmed local intake."""
from datetime import datetime, timezone
import hashlib
from http.client import HTTPSConnection, HTTPException
import json
from pathlib import Path
from tempfile import mkdtemp
from urllib.parse import quote, urlencode

from nightdesk.adapters.staging import stage_capture, write_raw
from nightdesk.intake.mapping import CaptureOrigin, write_private

HOST = "opendata.infrabel.be"
ENDPOINT = "/api/explore/v2.1/catalog/datasets/ruwe-gegevens-van-stiptheid-d-1/records"
WORKS_ENDPOINT = "/api/explore/v2.1/catalog/datasets/langetermijnplanning-tcr-spoornetwerk/exports/json"
OPERATOR = "EURSLEEPER"
PAGE_SIZE = 100
MAX_PAGES = 10
MAX_PAGE_BYTES = 2 * 1024 * 1024


def _read_page(path, *, limit=MAX_PAGE_BYTES):
    connection = HTTPSConnection(HOST, timeout=20)
    try:
        connection.request("GET", path, headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"infrabel_http_{response.status}")
        raw = response.read(limit + 1)
    except HTTPException:
        raise ValueError("infrabel_response_invalid") from None
    finally:
        connection.close()
    if len(raw) > limit:
        raise ValueError("infrabel_page_too_large")
    return raw


def fetch_d1(bundle):
    """Retain original pages and a replayable intake file beneath the bundle."""
    if bundle.nda:
        raise ValueError("infrabel_fetch_requires_public_practice_bundle")

    rows, pages = [], []
    expected_total = None
    for _ in range(MAX_PAGES):
        query = urlencode({
            "where": f'train_serv="{OPERATOR}"',
            "order_by": "datdep,train_no,planned_date_dep,planned_time_dep,ptcar_lg_nm_nl",
            "limit": PAGE_SIZE,
            "offset": len(rows),
        })
        path = f"{ENDPOINT}?{query}"
        raw = _read_page(path)
        fetched_at = datetime.now(timezone.utc).isoformat()
        try:
            page = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
            raise ValueError("infrabel_invalid_json") from None
        if not isinstance(page, dict):
            raise ValueError("infrabel_invalid_page")
        total, records = page.get("total_count"), page.get("results")
        if type(total) is not int or total < 0 or not isinstance(records, list) or len(records) > PAGE_SIZE:
            raise ValueError("infrabel_invalid_page")
        if expected_total is None:
            expected_total = total
        if total != expected_total or len(rows) + len(records) > total:
            raise ValueError("infrabel_page_count_changed")
        if total > PAGE_SIZE * MAX_PAGES:
            raise ValueError("infrabel_capture_limit")
        if not records and len(rows) < total:
            raise ValueError("infrabel_page_missing")

        url = f"https://{HOST}{path}"
        for row in records:
            if not isinstance(row, dict) or row.get("train_serv") != OPERATOR:
                raise ValueError("infrabel_unexpected_operator")
            point_name = row.get("ptcar_lg_nm_nl")
            # D-1 has names but no PTCAR number. Keep a feed-local label.
            point_label = quote(point_name, safe="") if isinstance(point_name, str) and point_name.strip() else None
            rows.append({**row, "d1_point_label": point_label, "d1_source_url": url, "d1_fetched_at": fetched_at})
        pages.append((raw, {"url": url, "fetched_at": fetched_at, "rows": len(records),
                            "sha256": hashlib.sha256(raw).hexdigest()}))
        if len(rows) == total:
            break
    else:
        raise ValueError("infrabel_capture_limit")

    root = bundle.resolve(bundle.root / "infrabel")
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(mkdtemp(prefix="d1-", dir=root))
    for index, (raw, metadata) in enumerate(pages, start=1):
        metadata["file"] = f"page-{index}.json"
        write_raw(folder / metadata["file"], raw)
    intake = folder / "capture.json"
    write_private(intake, json.dumps({"results": rows}, ensure_ascii=False, allow_nan=False) + "\n")
    capture_hash = hashlib.sha256(intake.read_bytes()).hexdigest()
    manifest = {"dataset": "infrabel_d1", "licence": "CC0", "complete": False,
                "operator": OPERATOR, "rows": len(rows), "capture_sha256": capture_hash,
                "pages": [metadata for _, metadata in pages]}
    write_private(folder / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    return {"capture": str(intake), "manifest": str(folder / "manifest.json"), "rows": len(rows)}


def fetch_works(bundle):
    if bundle.nda:
        raise ValueError("infrabel_fetch_requires_public_practice_bundle")
    path = f"{WORKS_ENDPOINT}?{urlencode({'order_by': 'id'})}"
    raw = _read_page(path, limit=64 * 1024 * 1024)
    rows = json.loads(raw)
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("infrabel_works_invalid_export")
    origin = CaptureOrigin(captured_at=datetime.now(timezone.utc), filter={"logically_deleted": "No"},
                           evidence={"source_url": f"https://{HOST}{path}",
                                     "source_file": "works.json", "source_sha256": hashlib.sha256(raw).hexdigest(),
                                     "coverage": "One long-term plan snapshot", "licence": "CC0"})
    normalized = [{**row, "nd_country": "BE"} for row in rows]
    return stage_capture(bundle, "infrabel-works", normalized, origin=origin,
                         raw_files=[("works.json", raw)])
