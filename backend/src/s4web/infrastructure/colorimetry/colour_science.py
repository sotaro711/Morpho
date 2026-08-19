"""colour-science を用いた ColorimetryPort の実装（infrastructure 層）。

参照プログラム（D65・CIE1931 2°・sRGB）と同じ手順で
反射スペクトルを sRGB 色に変換する。colour-science への依存はここだけ。
"""

from collections.abc import Sequence

import colour
import numpy as np

from s4web.domain.entities.color import ColorResult
from s4web.domain.ports.colorimetry_port import ColorimetryPort


class ColourScienceColorimetry(ColorimetryPort):
    def __init__(self) -> None:
        self._illuminant = colour.SDS_ILLUMINANTS["D65"]
        self._cmfs = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        self._wp = colour.CCS_ILLUMINANTS["CIE 1931 2 Degree Standard Observer"]["D65"]

    def reflectance_to_srgb(
        self,
        wavelengths_nm: Sequence[float],
        reflectance: Sequence[float],
    ) -> ColorResult:
        values = np.asarray(reflectance, dtype=float)
        # NaN を 0 埋めし、0..1 にクリップ（Rayleigh 点の欠損なども吸収）。
        values = np.nan_to_num(values, nan=0.0)
        values = np.clip(values, 0.0, 1.0)

        sd = colour.SpectralDistribution(dict(zip(wavelengths_nm, values, strict=True)))
        xyz = colour.sd_to_XYZ(sd, cmfs=self._cmfs, illuminant=self._illuminant)
        srgb = colour.XYZ_to_sRGB(xyz / 100.0, illuminant=self._wp, apply_cctf_encoding=True)
        srgb = np.clip(srgb, 0.0, 1.0)

        r, g, b = (int(round(float(c) * 255)) for c in srgb)
        return ColorResult(r=r, g=g, b=b)
