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

STATUS - CORRECTED 2026-08-16
-----------------------------
This block used to read: *"`PaperclipSource` is written against the published
CLI contract and has never been run - no credential exists yet. Its command
construction is unit tested; its output parsing is not, and cannot be until a
key is available."* Every clause of that is now false. It is quoted rather than
deleted because the way it turned out false is the useful part: the published
contract was wrong in three places, and nothing but running it would have found
them.

What is true instead, verified 2026-08-16: the CLI is installed, the credential
resolves, `available` returns True, and a live search returns hits. Output
parsing is tested against captured real CLI output - see `REAL_SEARCH_OUTPUT` in
`tests/test_calibration_harness.py` - and specifically not against the JSON
shape the contract implied, because that shape does not exist. The three
divergences are recorded in the comment above `DEFAULT_SOURCES`.

The warning it carried still applies, narrowed: suspect this file first when a
live run misbehaves, because it is the one place a text format from someone
else's tool is being read.

WHAT AVAILABILITY IS NOT
------------------------
A working source is not a calibration. `refute calibrate` still replays
`literature.py` and says so in its own header; live evidence comes from
`refute search`. Do not read "paperclip: available" as "the constants were
found".
"""

from __future__ import annotations

import os
import re
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

    # Verified against the live CLI on 2026-08-15. Three things the original
    # contract got wrong, all found in the first ten minutes of having a key:
    #
    #   1. `search` REQUIRES -s/--source and errors without it.
    #   2. `--json` is accepted and silently IGNORED - the output is human text.
    #   3. `map`, which the plan assumed would do the extraction, is gated to
    #      GXL testers and returns an error on this account. `grep` is not, and
    #      is the better tool anyway: a failure rate is easier to find by its
    #      shape than by its topic.
    DEFAULT_SOURCES = "pmc,biorxiv,medrxiv"

    # `  1. Title` starts an entry; `PMC123 · PMC · 2024-01-01` identifies it.
    _ENTRY_RE = re.compile(r"^\s{0,4}(\d+)\.\s+(.*)$")
    _IDENT_RE = re.compile(r"^\s+(\S+)\s+·\s+(\S+)\s+·\s+(\d{4}-\d{2}-\d{2})\s*$")
    _HEADER_RE = re.compile(r"^Found\s+(\d+)\s+paper", re.MULTILINE)

    def command(self, query: str, limit: int = 10, sources: str | None = None) -> list[str]:
        """Built separately from execution so it can be tested without a key."""
        return [
            self._binary, "search",
            "-s", sources or self.DEFAULT_SOURCES,
            query, "-n", str(limit),
        ]

    def grep_command(
        self, pattern: str, from_id: str, context: int = 1, ignore_case: bool = True
    ) -> list[str]:
        """Regex across full texts, scoped to a saved result set.

        This is where the failure constants actually are. `search` ranks whole
        papers by topic; a mortality rate or a delamination percentage is a
        SHAPE inside a methods section, and grep is the tool for a shape.
        """
        cmd = [self._binary, "grep", "--from", from_id, "-C", str(context)]
        if ignore_case:
            cmd.append("-i")
        cmd.append(pattern)
        return cmd

    def search(self, query: str, limit: int = 10) -> list[Hit]:
        if reason := self.why_unavailable():
            raise RuntimeError(f"paperclip unavailable: {reason}")
        proc = subprocess.run(
            self.command(query, limit), capture_output=True, text=True, timeout=300
        )
        if proc.returncode != 0:
            raise RuntimeError(f"paperclip failed: {proc.stderr.strip()[:300]}")
        return self.parse(proc.stdout)

    @staticmethod
    def result_id(stdout: str) -> str | None:
        """The `[s_1a2b3c]` handle, needed to chain grep onto a search."""
        m = re.search(r"\[(s_[0-9a-f]+)\]", stdout)
        return m.group(1) if m else None

    @classmethod
    def parse(cls, stdout: str) -> list[Hit]:
        """Parse the CLI's human output. RAISES if it cannot.

        Deliberately NOT tolerant. The previous version returned [] on anything
        it could not read, which meant a changed output format was indistinguish-
        able from "the literature contains nothing" - and "the literature
        contains nothing" is this project's headline finding. A parser that can
        silently manufacture that result is a parser that can invalidate the
        whole claim. Zero hits must be something the CLI *said*, not something a
        try/except produced.
        """
        text = stdout.strip()
        if not text:
            raise ValueError("paperclip returned no output at all")

        header = cls._HEADER_RE.search(text)
        if header is None:
            # Legitimate empty results, stated by the tool.
            if "No matches" in text or "No papers" in text or "Found 0" in text:
                return []
            raise ValueError(
                "could not parse paperclip output - the CLI contract has "
                f"changed. First 200 chars:\n{text[:200]}"
            )

        claimed = int(header.group(1))
        hits: list[Hit] = []
        pending: list[str] = []          # lines of the current entry

        def flush() -> None:
            if not pending:
                return
            ident, url, snippet, title_parts = "", "", "", []
            for line in pending:
                if m := cls._IDENT_RE.match(line):
                    ident = m.group(1)
                elif line.strip().startswith("http"):
                    url = line.strip()
                elif line.strip().startswith('"'):
                    snippet = line.strip().strip('"')
                elif not ident:
                    # Everything before the identifier line is title or authors;
                    # titles wrap across lines in this output, so keep them all
                    # and drop the last (the author list).
                    title_parts.append(line.strip())
            if title_parts:
                title_parts = title_parts[:-1] or title_parts
            if ident or url:
                hits.append(
                    Hit(
                        source=ident or url,
                        title=" ".join(p for p in title_parts if p),
                        snippet=snippet,
                    )
                )
            pending.clear()

        for line in text.splitlines():
            if cls._ENTRY_RE.match(line) and not line.strip().startswith("http"):
                flush()
                pending.append(cls._ENTRY_RE.match(line).group(2))
            elif pending:
                if line.strip().startswith("[") or not line.strip():
                    continue
                pending.append(line)
        flush()

        if claimed and not hits:
            raise ValueError(
                f"paperclip said it found {claimed} papers but none could be "
                "parsed - the output format has changed"
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
