"""Stage a provider response for the confirmed, offline intake path."""

import json
import os
from pathlib import Path
import shutil
from tempfile import mkdtemp

from nightdesk.intake.mapping import CaptureOrigin, write_private
from nightdesk.config import PUBLIC_DEMO_BUNDLE


def write_raw(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def stage_capture(bundle, provider, rows, *, origin: CaptureOrigin, raw_files=()):
    if bundle.nda or bundle.name == PUBLIC_DEMO_BUNDLE:
        raise ValueError("provider_capture_requires_practice_bundle")
    root = bundle.resolve(bundle.root / "source-captures")
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(mkdtemp(prefix=f"{provider}-", dir=root))
    intake = folder / "capture.json"
    try:
        for local_name, data in raw_files:
            if Path(local_name).name != local_name or local_name == "capture.json":
                raise ValueError("invalid_raw_capture_file_name")
            write_raw(folder / local_name, data)
        write_private(intake, json.dumps({"_capture": origin.model_dump(mode="json"), "results": rows},
                                        ensure_ascii=False, allow_nan=False) + "\n")
    except BaseException:
        shutil.rmtree(folder)
        raise
    return {"capture": str(intake), "rows": len(rows)}
