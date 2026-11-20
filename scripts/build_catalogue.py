"""Write data-catalogue.json: what was captured, and what may be published.

Metadata only. The catalogue names every capture held locally, with the hash,
size, source and licence that the capture itself recorded, so someone else can
reproduce a capture and prove they hold the same bytes. It never copies data.

A capture is marked redistributable only when its recorded licence says so.
Everything with an unclear licence is listed and left out of the repository:

    uv run python scripts/build_catalogue.py            # writes data-catalogue.json
    uv run python scripts/build_catalogue.py --print    # just show the summary
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_ROOT = ROOT / "data" / "out"
SNAPSHOT_ROOT = ROOT / "data" / "snapshots"
CATALOGUE = ROOT / "data-catalogue.json"

# A licence string that permits redistribution of the file itself.
REDISTRIBUTABLE = {"CC0", "CC BY 4.0", "CC BY-SA 4.0", "synthetic"}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_entry(folder: Path) -> dict:
    bundle = folder.parent.parent.name
    raw = json.loads((folder / "capture.json").read_text(encoding="utf-8"))
    origin = raw.get("_capture") or {}
    evidence = origin.get("evidence") or {}

    licence = evidence.get("licence")
    source_url = evidence.get("source_url")
    attribution = evidence.get("attribution")

    files = []
    for path in sorted(folder.iterdir()):
        if not path.is_file() or path.name == "capture.json":
            continue
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_of(path)})
        source_url = source_url or (evidence.get(path.stem) or {}).get("source_url")

    return {
        "bundle": bundle,
        "provider": folder.name.rsplit("-", 1)[0],
        "folder": folder.name,
        "captured_at": origin.get("captured_at"),
        "licence": licence or "UNKNOWN",
        "attribution": attribution,
        "source_url": source_url,
        "redistributable": (licence or "") in REDISTRIBUTABLE,
        "files": files,
    }


def snapshot_entry(folder: Path) -> dict:
    country = folder.parent.name
    files = []
    licence = "UNKNOWN"
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append({"name": str(path.relative_to(folder)), "bytes": path.stat().st_size,
                          "sha256": sha256_of(path)})
    manifest = folder / "manifest.json"
    if manifest.is_file():
        recorded = json.loads(manifest.read_text(encoding="utf-8"))
        licence = recorded.get("licence") or "UNKNOWN"
    return {
        "bundle": "data/snapshots",
        "provider": f"{country} snapshot",
        "folder": f"{country}/{folder.name}",
        "captured_at": None,
        "licence": licence,
        "attribution": None,
        "source_url": None,
        "redistributable": licence in REDISTRIBUTABLE,
        "files": files,
    }


def build() -> dict:
    entries = []
    if OUT_ROOT.is_dir():
        for folder in sorted(OUT_ROOT.glob("*/source-captures/*")):
            if (folder / "capture.json").is_file():
                entries.append(capture_entry(folder))
    if SNAPSHOT_ROOT.is_dir():
        for folder in sorted(p for p in SNAPSHOT_ROOT.glob("*/*") if p.is_dir()):
            entries.append(snapshot_entry(folder))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": ("Metadata only: no captured data is included. Reproduce a capture with the "
                 "nightdesk command for its provider and your own key, then compare the sha256. "
                 "Redistributable marks the files a licence permits publishing; example-data/ "
                 "holds those, everything else stays out of the repository."),
        "captures": entries,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print", dest="show", action="store_true", help="print a summary instead of writing")
    args = parser.parse_args(argv)

    catalogue = build()
    entries = catalogue["captures"]
    publishable = [e for e in entries if e["redistributable"]]
    if args.show:
        for entry in entries:
            mark = "publish" if entry["redistributable"] else "keep out"
            print(f"{mark:9} {entry['provider']:22} {entry['licence']:12} {entry['folder']}")
        print(f"\n{len(entries)} captures, {len(publishable)} redistributable")
        return 0

    CATALOGUE.write_text(json.dumps(catalogue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {CATALOGUE.relative_to(ROOT)}: {len(entries)} captures, "
          f"{len(publishable)} redistributable, {len(entries) - len(publishable)} kept local")
    return 0


if __name__ == "__main__":
    sys.exit(main())
