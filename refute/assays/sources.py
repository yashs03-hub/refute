"""Where calibration evidence comes from.

One interface, two backends, so the calibration run is the same code whether it
is replaying what has already been found or querying a live corpus:

    RecordedSource   replays `literature.py`. Needs no network or credential,
                     which is what makes the harness testable before the event.
    PaperclipSource  shells out to the `paperclip` CLI over ~11M full texts.

Why the indirection matters here specifically: a PubMed-only attempt failed not
because the corpus was too small but because it exposes abstracts. The
constants live in methods and troubleshooting sections. Swapping the source is
therefore the whole experiment, so it needs to be a swap and not a rewrite.

STATUS: `PaperclipSource` is written against the published CLI contract and has
never been run - no credential exists yet. Its command construction is unit
tested; its output parsing is not, and cannot be until a key is available. Any
failure on the day should be suspected here first.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol

from .evidence import CalibrationReport
from .literature import REPORTS


@dataclass(frozen=True)
class Hit:
    """One document returned by a source."""

    source: str          # DOI or identifier
    title: str
    snippet: str


class CalibrationSource(Protocol):
    name: str

    @property
    def available(self) -> bool: ...

    def why_unavailable(self) -> str: ...

    def search(self, query: str, limit: int = 10) -> list[Hit]: ...


class RecordedSource:
    """Replays findings already recorded in `literature.py`.

    Not a search engine - it cannot answer a query it has not seen. It exists so
    the harness, the CLI and the report arithmetic can all be exercised offline,
    and so the Paperclip run has a baseline to be compared against.
    """

    name = "recorded"

    @property
    def available(self) -> bool:
        return True

    def why_unavailable(self) -> str:
        return ""

    def search(self, query: str, limit: int = 10) -> list[Hit]:
        return []

    def report_for(self, key: str) -> CalibrationReport | None:
        return REPORTS.get(key)


class PaperclipSource:
    """Full-text search over Paperclip's corpus via its CLI.

    `search` is hybrid BM25 + vector. The CLI also exposes `grep` (regex across
    full texts) and `map` (parallel extraction across many papers), which are the
    tools that actually matter for failure constants - a rate is easier to find
    by its shape than by its topic. Those are deliberately not wrapped yet:
    wrapping an unverified contract twice is worse than wrapping it once.
    """

    name = "paperclip"

    def __init__(self, binary: str = "paperclip") -> None:
        self._binary = binary

    @property
    def available(self) -> bool:
        return not self.why_unavailable()

    def why_unavailable(self) -> str:
        if shutil.which(self._binary) is None:
            return (
                "paperclip CLI not on PATH - install with "
                "'curl -fsSL https://paperclip.gxl.ai/install.sh | bash'"
            )
        if not os.environ.get("PAPERCLIP_API_KEY"):
            # `paperclip login` writes ~/.paperclip/credentials.json instead.
            creds = os.path.expanduser("~/.paperclip/credentials.json")
            if not os.path.exists(creds):
                return (
                    "no credential - run 'paperclip login', or set "
                    "PAPERCLIP_API_KEY. Create it yourself; it is never written "
                    "for you."
                )
        return ""

    def command(self, query: str, limit: int = 10) -> list[str]:
        """Built separately from execution so it can be tested without a key."""
        return [self._binary, "search", query, "-n", str(limit), "--json"]

    def search(self, query: str, limit: int = 10) -> list[Hit]:
        if reason := self.why_unavailable():
            raise RuntimeError(f"paperclip unavailable: {reason}")
        proc = subprocess.run(
            self.command(query, limit), capture_output=True, text=True, timeout=120
        )
        if proc.returncode != 0:
            raise RuntimeError(f"paperclip failed: {proc.stderr.strip()[:300]}")
        return self.parse(proc.stdout)

    @staticmethod
    def parse(stdout: str) -> list[Hit]:
        """Tolerant of shape, because the exact schema is unverified.

        Accepts a bare list or a dict wrapping one under a plausible key, and
        skips records it cannot read rather than failing the whole run - losing
        one hit is recoverable, losing a batch mid-event is not.
        """
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            for key in ("results", "hits", "documents", "data"):
                if isinstance(data.get(key), list):
                    data = data[key]
                    break
            else:
                return []
        hits = []
        for row in data:
            if not isinstance(row, dict):
                continue
            hits.append(
                Hit(
                    source=str(row.get("doi") or row.get("id") or row.get("pmid") or ""),
                    title=str(row.get("title", "")),
                    snippet=str(
                        row.get("snippet") or row.get("text") or row.get("abstract") or ""
                    ),
                )
            )
        return hits


def get_source(name: str = "auto") -> CalibrationSource:
    """Pick a source. 'auto' prefers Paperclip and falls back to recorded."""
    if name == "paperclip":
        return PaperclipSource()
    if name == "recorded":
        return RecordedSource()
    if name == "auto":
        pc = PaperclipSource()
        return pc if pc.available else RecordedSource()
    raise ValueError(f"unknown source '{name}'. Known: paperclip, recorded, auto")
