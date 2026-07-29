from __future__ import annotations

import pytest

from mmp.codec import parse, serialize
from mmp.errors import ValidationError

SAMPLE = """\
MMP/1.0
!META topic=quantum_physics; lang=en; rev=1; entries=1; created=2026-01-08; updated=2026-07-29
!LEGEND
WPD=wave particle duality
!SRC
s1|Nielsen&Chuang|Quantum Computation and Quantum Information|2010|isbn:9781107002173
!INDEX
e1|F|WPD,double slit|double-slit interference changes under path measurement|s1
!FUTURE mode=test
opaque|extension|data
!BODY
@e1
def: WPD = matter shows wave and particle behavior
fact: measured path -> particle pattern
"""


def test_round_trip_preserves_unknown_sections() -> None:
    package = parse(SAMPLE)
    rendered = serialize(package)
    reparsed = parse(rendered)
    assert reparsed.legend["WPD"] == "wave particle duality"
    assert reparsed.unknown_sections == [
        ("!FUTURE mode=test", ["opaque|extension|data"])
    ]
    assert reparsed.bodies["e1"][1] == "fact: measured path -> particle pattern"


def test_rejects_non_ascii() -> None:
    with pytest.raises(ValidationError, match="ASCII"):
        parse(SAMPLE.replace("matter", "matiere\u0301"))


def test_rejects_wrong_section_order() -> None:
    broken = SAMPLE.replace("!LEGEND\nWPD=wave particle duality\n!SRC", "!SRC")
    with pytest.raises(ValidationError, match="missing required section"):
        parse(broken)
