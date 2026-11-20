"""Paths, bundles and environment variable names.

A bundle is an isolated workspace: its own output root under data/out/<bundle>/
and an `nda` flag. Nothing is read across bundles.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Output roots are relative to the repository root (commands run from there).
OUT_ROOT = Path("data") / "out"
ES_INPUT_ROOT = Path("data") / "es"

BUNDLE_ENV = "NIGHTDESK_BUNDLE"
DEFAULT_BUNDLE = "practice"
PUBLIC_DEMO_BUNDLE = "demo"
PUBLIC_DEMO_MANIFEST = Path("mappings/demo.yaml")
PUBLIC_DEMO_ENV = "NIGHTDESK_PUBLIC_DEMO"

# Service credential variable names (values are never read or stored here).
CREDENTIAL_ENV_VARS = (
    "MISTRAL_API_KEY",
    "NS_API_KEY",
    "SWISS_OTD_TOKEN",
    "DB_CLIENT_ID",
    "DB_API_KEY",
    "TRAIN_ARCHIVE_TOKEN",
)

# What each source needs before it can be fetched. Used by `nightdesk doctor`
# and shown by the setup instructions; never a place where a value is stored.
#   (label, variable names, what you can do once they are set)
SOURCES = (
    ("Infrabel punctuality (Belgium)", (), "Public CC0 monthly file. No key: works as-is."),
    ("NS maintenance (Netherlands)", ("NS_API_KEY",),
     "Dutch engineering works. Free key from the NS developer portal."),
    ("Rijden de Treinen archive (Netherlands)", (),
     "Saved archive reports. Fetch them yourself; no key needed here."),
    ("DB station boards (Germany)", ("DB_CLIENT_ID", "DB_API_KEY"),
     "German station departures and arrivals. Free OpenBoards plan on the DB API Marketplace."),
    ("Swiss SIRI (Switzerland)", ("SWISS_OTD_TOKEN",),
     "Planned Swiss disruptions. Free token from opentransportdata.swiss."),
    ("Train Archive", ("TRAIN_ARCHIVE_TOKEN",),
     "Daily archive trips by train number."),
    ("Mistral (optional drafting)", ("MISTRAL_API_KEY",),
     "Draft work fields from a notice. Off unless you also consent per case folder."),
)


def env_file_path():
    """Where keys are read from. Point NIGHTDESK_ENV_FILE elsewhere to use another file."""
    return os.environ.get("NIGHTDESK_ENV_FILE") or ".env"


def machine_env_file_path():
    """One key file shared by every project on this machine."""
    override = os.environ.get("NIGHTDESK_MACHINE_ENV_FILE")
    if override is not None:
        return Path(override)
    return Path.home() / ".agents" / "secrets" / "nightdesk.env"


def env_file_paths():
    """Key files, in load order: the project's own file first, then the machine file.

    A value already set wins, so a real environment variable beats both files and
    a project .env beats the machine file.
    """
    return [Path(env_file_path()), machine_env_file_path()]


def load_all_env_files():
    """Load every key file in order. Returns {path: [names loaded]}."""
    return {path: load_env_file(path) for path in env_file_paths()}


def load_env_file(path=".env"):
    """Load KEY=VALUE lines from a local .env file into os.environ.

    Real environment variables always win, so exporting a key still overrides the
    file. Returns the names that were loaded. Values are never printed.
    """
    file = Path(path)
    if not file.is_file():
        return []
    loaded = []
    for raw in file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip()
        if name.startswith("export "):
            name = name[len("export "):].strip()
        value = value.strip().strip('"').strip("'")
        if not name or not value or name in os.environ:
            continue
        os.environ[name] = value
        loaded.append(name)
    return loaded


def save_env_values(path, values):
    """Write NAME=value pairs into a key file, keeping comments and existing lines.

    The file is created readable only by its owner (mode 600). Empty values remove
    the value but keep the line, so the next reader sees "not set" rather than an error.
    """
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    lines = file.read_text(encoding="utf-8").splitlines() if file.is_file() else []
    seen = set()
    for index, raw in enumerate(lines):
        name = raw.partition("=")[0].strip()
        if name.startswith("export "):
            name = name[len("export "):].strip()
        if name in values and raw.lstrip()[:1] != "#":
            lines[index] = f"{name}={values[name]}"
            seen.add(name)
    for name, value in values.items():
        if name not in seen:
            lines.append(f"{name}={value}")
    file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(file, 0o600)
    return file


KEYCHAIN_SERVICE = "nightdesk"
KEYCHAIN_ENV = "NIGHTDESK_KEYCHAIN"


def keychain_value(name):
    """Read a credential from the macOS Keychain. Returns None when unavailable.

    Lookup is by service "nightdesk" and account = the variable name, so a key is
    stored once per machine and never written to a file or printed. Set
    NIGHTDESK_KEYCHAIN=off to ignore the Keychain (the test suite does this, so a
    developer's own keys never change what a test sees).
    """
    if sys.platform != "darwin" or os.environ.get(KEYCHAIN_ENV, "").lower() == "off":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", name, "-w"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def keychain_store(name, value):
    """Save one credential in the macOS Keychain, replacing any earlier value."""
    subprocess.run(
        ["security", "add-generic-password", "-U", "-s", KEYCHAIN_SERVICE, "-a", name, "-w", value],
        capture_output=True, text=True, timeout=10, check=True,
    )


def credential_value(name):
    """The credential from the environment or the Keychain. Never printed by callers."""
    value = os.environ.get(name)
    if value:
        return value
    return keychain_value(name)


def credential_present(name):
    """True when a credential holds a plausible value, in the environment or the Keychain."""
    value = credential_value(name)
    return bool(value) and all(33 <= ord(char) <= 126 for char in value)

# Fixed bundles. `es` is always nda=True.
FIXED_BUNDLES: dict[str, bool] = {
    "practice": False,
    "es": True,
    PUBLIC_DEMO_BUNDLE: False,
}

TEST_BUNDLE_RE = re.compile(r"test-[a-z0-9][a-z0-9-]{0,47}")

# Technical parser limits, not assertions about operational data values.
MAX_NUMBER_TEXT = 1024
MAX_NUMBER_EXPONENT = 1000

# Canonical vocabulary; unmapped values retain raw evidence and become unknown.
WORK_EFFECTS = ("TOTALSPERRUNG", "FAHRZEITVERLAENGERUNG", "ABWEICHUNG_VOM_FPL", "GGL_MIT_ZS_6",
                "GGL_MIT_ZS_8", "SONSTIGES", "closure", "restricted", "other", "unknown")
RECURRENCES = ("periodical", "continuous", "unknown")
EVENT_KINDS = ("arrival", "departure", "pass", "handover", "unknown")
# Technical plausibility guard: a decade-old work start is not silently accepted.
# Configurable review guard, not an asserted railway planning horizon.
WORK_YEAR_BEFORE_CAPTURE = 5
WORK_YEAR_AFTER_CAPTURE = 10

STATION_AREA_LINE_PREFIXES = ("0/",)
# September 2026 Infrabel monthly data also identifies 454/455 as EURSLEEPER.
# An actual dated schedule and a reviewed station match are still required.
ES_ROUTE = re.compile(r"ES[- ]?(400|401|452|453|454|455|474|475)")
# Byte hashes of the reviewed mappings. Keep older reviewed versions here when replacing a mapping.
INFRABEL_MAPPING_HASHES = {
    "infrabel_d1": "f8bb79a17cf5e1215c3f4190d7ea4b13bc4807eca934eea84341cd1ecb0abbb8",
    "infrabel_punctuality": "c0fb042027fa32df52532cdee9e0980456f86c7ea3c3313f6216c5ce235599ce",
}
DATASET_ASSUMPTIONS = {
    "infrabel_punctuality": ["Times assumed Europe/Brussels; upstream timezone on clock-change nights is not verified."],
    "infrabel_d1": [
        "Times assumed Europe/Brussels; upstream timezone on clock-change nights is not verified.",
        "D-1 point labels are feed-local station names. PTCAR identity is unverified.",
    ],
}


def is_within(path: Path, root: Path) -> bool:
    """Containment by resolved path and filesystem identity (case aliases on macOS)."""
    path, root = path.resolve(), root.resolve()
    if path == root or root in path.parents:
        return True
    try:
        stat = root.stat()
    except FileNotFoundError:
        return False
    identity = (stat.st_dev, stat.st_ino)
    for ancestor in (path, *path.parents):
        try:
            stat = ancestor.stat()
        except FileNotFoundError:
            continue
        if (stat.st_dev, stat.st_ino) == identity:
            return True
    return False


class BundleError(ValueError):
    """Unknown bundle name or a path outside the bundle root."""


@dataclass(frozen=True)
class Bundle:
    name: str
    nda: bool
    root: Path

    def real_root(self) -> Path:
        """The bundle root with symlinks resolved; refused if the root itself is a symlink.

        A symlinked root could point into another bundle or outside data/out/.
        """
        if self.root.is_symlink():
            raise BundleError(f"bundle root {self.root} is a symlink")
        root = self.root.resolve()
        if root != self.root.parent.resolve() / self.name:
            raise BundleError(f"bundle root {self.root} does not resolve to itself")
        return root

    def resolve(self, path: str | os.PathLike[str]) -> Path:
        """Resolve `path` (following symlinks) and refuse it unless it lies inside this bundle's root."""
        root = self.real_root()
        target = Path(path).resolve()
        if not is_within(target, root):
            raise BundleError(f"path {path!s} is outside bundle root {self.root}")
        return target


def get_bundle(name: str, out_root: Path = OUT_ROOT) -> Bundle:
    """Return the named practice, demo, NDA or test bundle."""
    if name in FIXED_BUNDLES:
        nda = FIXED_BUNDLES[name]
    elif TEST_BUNDLE_RE.fullmatch(name):
        nda = False
    else:
        raise BundleError(
            f"unknown bundle {name!r}: use practice, demo, es or test-<slug> "
            f"matching {TEST_BUNDLE_RE.pattern}"
        )
    return Bundle(name=name, nda=nda, root=Path(out_root) / name)


def selected_bundle_name() -> str:
    """Bundle chosen by NIGHTDESK_BUNDLE, defaulting to practice."""
    return os.environ.get(BUNDLE_ENV) or DEFAULT_BUNDLE

# Technical bounds for a local archive, not claims about timetable duration.
MAX_GTFS_BYTES = 128 * 1024 * 1024
MAX_GTFS_HOURS = 240
MAX_GTFS_SERVICE_DAYS = 10000
MAX_GTFS_ROWS = 50000

# Text parser/request resource limits; no operational or prediction thresholds.
MAX_NOTICE_CHARS = 24000
MAX_MODEL_RESPONSE_BYTES = 256 * 1024
MISTRAL_HOST = 'api.mistral.ai'
MISTRAL_MODEL = 'mistral-small-latest'
MISTRAL_TIMEOUT_SECONDS = 30
MISTRAL_MAX_TOKENS = 3000
TEXT_INJECTION_MARKERS = ('ignore previous instructions', 'ignore all instructions', 'mark as safe',
                          '<|system|>', '<|assistant|>', '[inst]', '[/inst]', 'system:',
                          'developer:', 'assistant:', 'überschreibe die regeln', 'ignoriere vorherige anweisungen')
TEXT_MONTHS = {'january': 1, 'januar': 1, 'february': 2, 'februar': 2, 'march': 3, 'märz': 3,
               'april': 4, 'may': 5, 'mai': 5, 'june': 6, 'juni': 6, 'july': 7, 'juli': 7,
               'august': 8, 'september': 9, 'october': 10, 'oktober': 10, 'november': 11,
               'december': 12, 'dezember': 12}

TEXT_INJECTION_PATTERNS = (r"\b(?:ignore|disregard) (?:the )?(?:previous|prior|all) instructions\b",
                           r"\b(?:system|assistant|developer)\s*:", r"<\|", r"\[/?inst\]")
