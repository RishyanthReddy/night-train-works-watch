"""Run Phase 0's six acceptance steps through the installed CLI.

Default: isolated temporary workspace with synthetic fixtures only.
--workspace .: run in the repo and retain local exports under data/out/practice/.
The second pass uses macOS sandbox-exec to deny networking, with a loopback probe.
No source file, system networking setting or credential is changed.
"""

import argparse
import errno
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from nightdesk.config import CREDENTIAL_ENV_VARS, get_bundle
from nightdesk.intake.mapping import captures

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / ".venv/bin/nightdesk"
PYTHON = REPO / ".venv/bin/python"
DENY = ["/usr/bin/sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]


def run(workspace: Path):
    env = {k: v for k, v in os.environ.items() if k not in CREDENTIAL_ENV_VARS and k != "NIGHTDESK_BUNDLE"}
    assert not any(k in env for k in CREDENTIAL_ENV_VARS)
    outputs = []

    def command(args, *, denied=False, expected=0):
        cmd = (DENY if denied else []) + [str(CLI), *args]
        result = subprocess.run(cmd, cwd=workspace, env=env, text=True, capture_output=True)
        print("$ " + ("[network denied] " if denied else "") + "nightdesk " + " ".join(args))
        print(result.stdout, end="")
        print(result.stderr, end="")
        print(f"exit {result.returncode}")
        assert result.returncode == expected
        return result.stdout

    # A fresh test bundle guarantees a genuine pre-confirm refusal, even on repeat runs.
    refusal_bundle = "test-preconfirm-" + os.urandom(4).hex()
    command(["ingest", "tests/fixtures/admin/admin_v1.csv", "--mapping", "mappings/admin_v1.yaml", "--bundle", refusal_bundle], expected=1)
    for denied in (False, True):
        if denied:
            probe = subprocess.run(DENY + [str(PYTHON), "-I", "-c",
                'import socket; print(socket.socket().connect_ex(("127.0.0.1",9)))'],
                cwd=workspace, env=env, text=True, capture_output=True)
            print("Network-denial probe: exit", probe.returncode, "errno", probe.stdout.strip())
            assert probe.returncode == 0 and int(probe.stdout.strip()) in (errno.EPERM, errno.EACCES)
        calls = [
            ["sniff", "tests/fixtures/admin/admin_v1.csv"],
            ["mapping", "confirm", "mappings/admin_v1.yaml", "--bundle", "practice"],
            ["ingest", "tests/fixtures/admin/admin_v1.csv", "--mapping", "mappings/admin_v1.yaml", "--bundle", "practice"],
            ["ingest", "tests/fixtures/admin/admin_v2.csv", "--mapping", "mappings/admin_v1.yaml", "--bundle", "practice"],
            ["rejects", "--bundle", "practice"],
            ["compare", "tests/fixtures/admin/admin_v1.csv", "tests/fixtures/admin/admin_v2.csv", "--key", "record_id", "--bundle", "practice", "--out", "data/out/practice/"],
            ["mapping", "confirm", "mappings/admin_alt.yaml", "--bundle", "practice"],
            ["ingest", "tests/fixtures/admin/admin_alt.csv", "--mapping", "mappings/admin_alt.yaml", "--bundle", "practice"],
        ]
        outputs.append([command(args, denied=denied) for args in calls])
    assert outputs[0] == outputs[1], "CLI stdout differs between ordinary and network-denied runs"
    previous = Path.cwd()
    try:
        os.chdir(workspace)
        c = captures(get_bundle("practice"))
        by_file = {Path(x["metadata"]["path"]).name: x for x in c}
        a, alt = (by_file[f"admin_{name}.csv"]["rows"] for name in ("v1", "alt"))
        assert [(r.fields, r.extra, r.unresolved) for r in a] == [(r.fields, r.extra, r.unresolved) for r in alt]
        reports = list(Path("data/out/practice").glob("comparison-*.json"))
        assert reports
        report = json.loads(reports[-1].read_text())
        assert report["counts"] == {"changed": 2, "added": 1, "unchanged": 2, "only_in_old": 0}
        print("PASS: alternate YAML yields identical canonical fields/extra; provenance remains distinct.")
        print("PASS: all six acceptance steps; identical stdout with six credential variables unset and OS network denied.")

        # Exercise the other supported file formats through real subprocesses too.
        import yaml
        from openpyxl import Workbook
        formats = "test-formats-" + os.urandom(4).hex()
        folder = Path("data/out") / formats / "inputs"
        folder.mkdir(parents=True)
        common = {"version": 1, "dataset": "synthetic_formats", "licence": "synthetic", "record": "GenericRow",
                  "required": ["record_id", "duration_s"], "fields": {
                      "record_id": {"column": "id", "parse": "str"},
                      "duration_s": {"column": "seconds", "parse": "seconds"}}}
        j = folder / "synthetic.json"
        j.write_text(json.dumps({"items": [{"id": "syn-j", "seconds": 90, "nested": {"keep": [1, 2]}}]}))
        jm = folder / "json.yaml"
        jm.write_text(yaml.safe_dump(common | {"file": {"type": "json", "records_path": "items"}}))
        x = folder / "synthetic.xlsx"
        wb = Workbook()
        wb.active.append(["id", "seconds"])
        wb.active.append(["syn-x", 120])
        wb.save(x)
        xm = folder / "xlsx.yaml"
        xm.write_text(yaml.safe_dump(common | {"file": {"type": "xlsx"}}))
        for source, mapping in [(j, jm), (x, xm)]:
            command(["sniff", str(source)] + (["--records-path", "items"] if source == j else []), denied=True)
            command(["mapping", "confirm", str(mapping), "--bundle", formats], denied=True)
            command(["ingest", str(source), "--mapping", str(mapping), "--bundle", formats], denied=True)
        merged = folder / "merged.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.append(["Synthetic", None])
        ws.merge_cells("A1:B1")
        ws.append(["id", "seconds"])
        ws.append(["syn-flat", 30])
        wb.save(merged)
        command(["sniff", str(merged)], denied=True, expected=1)
        flat = folder / "flattened.csv"
        command(["flatten", str(merged), "--header-rows", "2", "--out", str(flat), "--bundle", formats], denied=True)
        flat_mapping = folder / "flattened.yaml"
        common["fields"]["record_id"]["column"] = "Synthetic_id"
        common["fields"]["duration_s"]["column"] = "Synthetic_seconds"
        flat_mapping.write_text(yaml.safe_dump(common | {"file": {"type": "csv"}}))
        command(["mapping", "confirm", str(flat_mapping), "--bundle", formats], denied=True)
        command(["ingest", str(flat), "--mapping", str(flat_mapping), "--bundle", formats], denied=True)
        assert sorted(r.fields["duration_s"] for c in captures(get_bundle(formats)) for r in c["rows"]) == [30, 90, 120]
        print("PASS: real JSON/XLSX sniff and ingest, plus merged-header refusal -> flatten -> ingest, with network denied.")
    finally:
        os.chdir(previous)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.workspace:
        run(args.workspace.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix="nightdesk-p0-") as tmp:
            workspace = Path(tmp)
            shutil.copytree(REPO / "tests/fixtures/admin", workspace / "tests/fixtures/admin")
            shutil.copytree(REPO / "mappings", workspace / "mappings")
            run(workspace)
