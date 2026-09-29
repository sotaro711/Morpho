"""光学定数のテキストファイルを読んで DispersiveMaterial にする。

想定する形式は 1 行 1 波長の「波長(nm) n k」。エリプソメータの解析ソフト
（J.A. Woollam CompleteEASE など）の書き出しをそのまま読めるようにする:
見出し行、タブ区切り、行末の余分なタブ、CRLF、末尾の空行。

エラー文言は登録画面にそのまま出すので日本語にしている。
"""

import re
from math import isfinite

from s4web.domain.entities.material import (
    MAX_DISPERSION_POINTS,
    DispersionPoint,
    DispersiveMaterial,
)

_SEPARATOR = re.compile(r"[\s,;]+")
# 見出しに nm 以外の単位が書かれていれば、数値の大きさを見る前に拒否する。
_NON_NM_UNIT = re.compile(r"\b(eV|µm|um|micron|microns|cm-1|Å|angstrom)\b", re.IGNORECASE)
# 可視域の nm なら数百になる。最大波長がこれ未満なら μm や eV のデータと判断する。
_MIN_PLAUSIBLE_NM = 100.0


def parse_optical_constants(text: str) -> DispersiveMaterial:
    """ファイルの内容を材料にする。読めない内容は理由を書いた ValueError。"""
    points: list[DispersionPoint] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        # 行頭・行末の区切り文字も落とす（行末の余分なタブやカンマで空の列ができないように）。
        stripped = line.strip(" \t\r,;")
        if not stripped:
            continue
        fields = _SEPARATOR.split(stripped)
        try:
            wavelength_nm, n = float(fields[0]), float(fields[1])
        except IndexError, ValueError:
            if _NON_NM_UNIT.search(line):
                raise ValueError(
                    "波長の単位が nm ではないようです。nm に変換したファイルを使ってください"
                ) from None
            continue  # 見出しなど、数値でない行は読み飛ばす
        # 小数点がカンマの「1,52」は 2 列に割れて n=1, k=52 と誤読されるので、列が多い行は拒否する。
        if len(fields) > 3:
            raise ValueError(f"{line_no} 行目の列が多すぎます（波長 nm、n、k の 3 列まで）")
        try:
            k = float(fields[2]) if len(fields) > 2 else 0.0
        except ValueError:
            raise ValueError(f"{line_no} 行目の k が数値ではありません") from None
        if not all(map(isfinite, (wavelength_nm, n, k))) or wavelength_nm <= 0 or n <= 0 or k < 0:
            raise ValueError(f"{line_no} 行目の値が不正です（波長と n は正の数、k は 0 以上）")
        points.append(DispersionPoint(wavelength_nm, n, k))

    if len(points) < 2:
        raise ValueError("数値の行が 2 行以上必要です（1 列目: 波長 nm、2 列目: n、3 列目: k）")
    if len(points) > MAX_DISPERSION_POINTS:
        raise ValueError(f"点が多すぎます（{len(points)} 点。上限は {MAX_DISPERSION_POINTS} 点）")

    points.sort(key=lambda p: p.wavelength_nm)
    if points[-1].wavelength_nm < _MIN_PLAUSIBLE_NM:
        raise ValueError(
            "波長の単位が nm ではないようです（最大でも "
            f"{points[-1].wavelength_nm:g}）。nm に変換したファイルを使ってください"
        )
    for prev, nxt in zip(points, points[1:], strict=False):
        if nxt.wavelength_nm == prev.wavelength_nm:
            raise ValueError(f"同じ波長 {prev.wavelength_nm:g} nm の行が複数あります")
    return DispersiveMaterial(tuple(points))
