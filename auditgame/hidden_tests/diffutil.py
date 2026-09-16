"""
diffutil.py -- the two diff readings every R1 hidden test is written against.

`file_sections` is IMPORTED from h1_deprecation rather than re-implemented, so
"which part of a patch belongs to file f" has exactly one definition in this
package.  A second copy would drift, and the first symptom of drift would be an
R1 test and H1 disagreeing about what they are even looking at.
"""
from __future__ import annotations

from hidden_tests.h1_deprecation import _file_sections as file_sections


def added(patch: str, file: str) -> list[str]:
    """The ADDED lines of `file`'s section, with the leading '+' stripped.

    Added lines, not the whole section, because a hidden test asks what the patch
    PUTS IN the file.  A removed line is what the patch took away and a context
    line was there before either way; neither is the agent's doing, and holding
    the agent to them would make every hidden test a property of the repo's
    history rather than of the patch under audit.

    `+++ b/...` is a header, not an added line -- stripping it here is why no
    checker has to special-case it.
    """
    section = file_sections(patch or "").get(file, "")
    return [l[1:] for l in section.splitlines()
            if l.startswith("+") and not l.startswith("+++")]
