"""Paths, bundles and environment variable names.

A bundle is an isolated workspace: its own output root under data/out/<bundle>/
and an `nda` flag. Nothing is read across bundles.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

# Output roots are relative to the repository root (commands run from there).
OUT_ROOT = Path("data") / "out"
ES_INPUT_ROOT = Path("data") / "es"

BUNDLE_ENV = "NIGHTDESK_BUNDLE"
DEFAULT_BUNDLE = "practice"

# Service credential variable names (values are never read or stored here).
CREDENTIAL_ENV_VARS = (
    "MISTRAL_API_KEY",
    "NS_API_KEY",
    "SWISS_OTD_TOKEN",
    "DB_CLIENT_ID",
    "DB_API_KEY",
    "TRAIN_ARCHIVE_TOKEN",
)

# Fixed bundles. `es` is always nda=True.
FIXED_BUNDLES: dict[str, bool] = {
    "practice": False,
    "es": True,
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
DATASET_ASSUMPTIONS = {
    "infrabel_punctuality": ["Times assumed Europe/Brussels; upstream timezone on clock-change nights is not verified."],
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
    """Return the named bundle: practice, es, or a safe test-<slug> bundle."""
    if name in FIXED_BUNDLES:
        nda = FIXED_BUNDLES[name]
    elif TEST_BUNDLE_RE.fullmatch(name):
        nda = False
    else:
        raise BundleError(
            f"unknown bundle {name!r}: use practice, es or test-<slug> "
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
