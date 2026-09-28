from pathlib import Path

import pytest

from s4web.domain.services.optical_constants_file import parse_optical_constants

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_reads_a_completeease_export_as_is() -> None:
    # 見出し 2 行・タブ区切り・行末の余分なタブ・CRLF・末尾の空行をそのまま読める。
    material = parse_optical_constants((FIXTURES / "completeease_cauchy.txt").read_text())
    assert len(material.points) == 61
    assert material.wavelength_range_nm == (300, 900)
    first = material.points[0]
    assert (first.wavelength_nm, first.n, first.k) == (300, pytest.approx(2.533333), 0)


@pytest.mark.parametrize(
    "text",
    [
        "400 2.5 0.1\n500 2.4 0\n",
        "400,2.5,0.1\n500,2.4,0\n",
        "400;2.5;0.1\n500;2.4;0\n",
        "wl n k\n400\t2.5\t0.1\n500\t2.4\t0\n",
    ],
    ids=["spaces", "commas", "semicolons", "header"],
)
def test_accepts_common_separators_and_headers(text: str) -> None:
    material = parse_optical_constants(text)
    assert [(p.wavelength_nm, p.n, p.k) for p in material.points] == [
        (400, 2.5, 0.1),
        (500, 2.4, 0),
    ]


def test_missing_k_column_means_no_absorption() -> None:
    material = parse_optical_constants("400 2.5\n500 2.4\n")
    assert all(p.k == 0 for p in material.points)


def test_rows_are_sorted_by_wavelength() -> None:
    material = parse_optical_constants("500 2.4\n400 2.5\n")
    assert [p.wavelength_nm for p in material.points] == [400, 500]


@pytest.mark.parametrize(
    "text, message",
    [
        ("Optical Constants vs. eV\n3.1 2.5 0\n2.0 2.4 0\n", "単位が nm ではない"),
        ("0.4 2.5 0\n0.5 2.4 0\n", "単位が nm ではない"),
        ("400 2.5 0\n", "2 行以上"),
        ("just a header\n", "2 行以上"),
        ("400 2.5 0\n400 2.4 0\n", "同じ波長"),
        ("400 0 0\n500 2.4 0\n", "不正"),
        ("400 2.5 -0.1\n500 2.4 0\n", "不正"),
    ],
    ids=[
        "eV header",
        "micron values",
        "single row",
        "no data",
        "duplicate",
        "n zero",
        "k negative",
    ],
)
def test_rejects_unreadable_files_with_a_reason(text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_optical_constants(text)


def test_rejects_too_many_points() -> None:
    text = "".join(f"{300 + i * 0.1:.1f} 2.0 0\n" for i in range(5001))
    with pytest.raises(ValueError, match="点が多すぎます"):
        parse_optical_constants(text)
