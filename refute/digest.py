"""One digest algorithm for a requirement key list, with nothing behind it.

Three modules need to say which revision of a requirement set an answer is
total over, and each one arrived at its own copy of the same six lines:

* `requirements.requirement_version` hashes the keys a protocol declares. It is
  the definition - the registry owns the requirement list.
* `adapt._version_of` hashes the keys it was actually handed, deliberately
  rather than looking the protocol up: the version records which requirement
  set this answer is total over, so a caller that answered a doctored or stale
  list must produce a version that differs from the registry's. That skew is
  what `pipeline._version_warning` exists to surface, and reading the registry
  there would hide it.
* `handoff._version_of` does the same for a handoff, and could not import
  `requirements` at all, because importing it would pull `AssayProtocol` in
  behind it and that module deliberately knows nothing about protocols.

Every one of those reasons was sound, and none of them is a reason to have
three implementations of one contract. They have to agree exactly - a digest
that differs by a character makes the pipeline warn that a fresh answer is
stale - and agreement held only because two of the three were pinned by tests.

So the *algorithm* is here and the *key list* stays with the caller. That
division is the whole point: what was duplicated for a bad reason (the hash) is
shared, and what was duplicated for a good reason (each caller hashing what it
was actually given, never what the registry says) is preserved. Nothing here
takes a protocol, a resolution or a requirement - only strings - which is what
lets `handoff` import it without importing an assay.

This module imports `hashlib` and nothing else, and it must stay that way.
"""

from __future__ import annotations

import hashlib
from typing import Iterable

# Length of the digest. Twelve hex characters is ~48 bits, which is far more
# than the handful of requirement sets that will ever exist, and short enough to
# appear in a filename or a log line without wrapping.
VERSION_CHARS = 12

__all__ = ["VERSION_CHARS", "requirement_digest"]


def requirement_digest(keys: Iterable[str]) -> str:
    """A short stable identifier for a set of requirement keys.

    Over the keys only. Units and descriptions are prose about the same
    requirement, and rewording one should not invalidate every resolution set
    that answered it - whereas adding or removing a key genuinely does mean an
    old answer is no longer total over the new set.

    Sorted here rather than by the caller, so reordering declarations cannot
    change the version and no caller can forget. `requirements.tier1_needs`
    preserves declaration order for readability; the version deliberately does
    not depend on it.

    A `hashlib` digest and not Python's `hash()`, which is salted per process: a
    version that changed between two runs of the same code would mark every
    stored resolution set stale on a restart, which is worse than having no
    version at all because it would be discovered late and intermittently.
    `tests/test_requirements.py` runs a subprocess under a hostile
    PYTHONHASHSEED to keep that true.
    """
    joined = "\n".join(sorted(keys))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:VERSION_CHARS]
