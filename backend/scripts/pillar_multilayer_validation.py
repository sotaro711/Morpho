"""角柱の段差の上に成膜した多層膜（3 次元段差付き多層膜）の S4 検証スクリプト。

研究スライド「3 次元段差付き多層膜の解析」の構造を本番の S4Solver で再現し、以下を出力する:
  1. 入射角 0/30/60° の反射スペクトル（380-780nm、無偏光 = s, p の平均）を
     「0 次光のみ」「すべての光」「単純多層膜（段差なし）」の 3 並びで描く → スライドのグラフと比較
  2. NumBasis 収束表（470/600nm、垂直入射、s 偏光）

構造（スライドより。上げ高さと基板はスライドに無いので 2 次元の段差構造と同じ値を仮置き）:
  - 正方格子、周期 600nm。300nm 角の角柱（基板上げ 235nm = λ0/2）の上に
    TiO2(n=2.3, 51nm) / SiO2(n=1.45, 81nm) の 7.5 ペア（両端が TiO2）を成膜
  - 基板 = SUS（n=2.3+3.3i。可視域の代表値で分散は無視）
  - フロントの lib/lattice3d.ts と同じ水平スライス法: 角柱の列と平らな列の層境界を集めて
    z 方向に分割し、各スライスは平らな列の材料を背景に、角柱の列の材料を矩形領域で重ねる

実行: cd backend && uv run --group analysis python scripts/pillar_multilayer_validation.py \
      [conv|spec] [basis]（省略時は conv、基底 81）
出力: scripts/out/pillar_spectra_b{basis}.png, .csv

検証結果の要約（実行のたびに追記）:
  - 2026-10-26 収束表（470/600nm, θ=0, s, PolarizationDecomposition=False, 33 層）:
      基底 49/81/121 で R0(470)=0.736/0.727/0.728、R(600)=0.154/0.152/0.153。
      1 波長あたり 0.6/2.5/8 秒（基底 169/225 は 22/63 秒）。
    基板を SUS n=1.71+2.88i にした試行では基底 49〜225 で 0.732/0.728/0.724/0.716/0.717 と
    基底 169 以上で変化なし。同じ試行で PolarizationDecomposition=True にすると
    0.673/0.688/0.685/0.688（基底 81〜225）で、無効時と 0.03 の差が残る。因子化の違いによる
    不確かさとして ±0.03 程度を見込む。本番は球配列の検証に合わせて無効のまま。
  - 2026-10-26 スペクトル（基板 SUS n=1.71+2.88i、基底 81、41 波長 × 3 角度 × 2 偏光で約 12 分）:
      0 次のみ θ=0°: 400-480nm に R≈0.7-0.87 の山、500nm 以降は 0.1-0.25。
      30°/60° は 0.2-0.45 と低く、短波長側に寄る。すべての光は 0 次より 0.05-0.4 高い
      （高次回折へ散った分）。単純多層膜は 400-520nm で R≈1 のストップバンド。
    スライドの 3 グラフ（0 次光のみ / すべての光 / 単純多層膜）と形が一致する。
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from s4web.domain.entities.layer import Layer, RectRegion
from s4web.domain.entities.material import Material
from s4web.domain.entities.simulation import Polarization, SimulationCondition
from s4web.infrastructure.solvers.s4_solver import S4Solver

OUT_DIR = Path(__file__).resolve().parent / "out"

AIR = Material(1.0)
TIO2 = Material(2.3)
SIO2 = Material(1.45)
SUS = Material(2.3, 3.3)

PERIOD_NM = 600.0
PILLAR_NM = 300.0
RAISE_NM = 235.0
# 下（基板側）から上へ。両端が TiO2 の 7.5 ペア。
FILMS: list[tuple[Material, float]] = ([(TIO2, 51.0), (SIO2, 81.0)] * 7 + [(TIO2, 51.0)])[::-1]


def profile(raised: bool) -> list[tuple[Material, float]]:
    return ([(SUS, RAISE_NM)] if raised else []) + FILMS


def material_at(prof: list[tuple[Material, float]], z: float) -> Material | None:
    z0 = 0.0
    for material, thickness in prof:
        if z0 <= z < z0 + thickness:
            return material
        z0 += thickness
    return None


def pillar_layers(stepped: bool = True) -> list[Layer]:
    """角柱の列と平らな列の層境界で z 方向に分割し、各スライスを 1 層にする。"""
    raised, flat = profile(True), profile(False)
    columns = [raised, flat] if stepped else [flat]
    breaks = {0.0}
    for prof in columns:
        z = 0.0
        for _, thickness in prof:
            z += thickness
            breaks.add(round(z, 6))
    zs = sorted(breaks)
    layers = [Layer("air", 0, AIR)]
    for i in range(len(zs) - 2, -1, -1):
        z_mid = (zs[i] + zs[i + 1]) / 2
        background = material_at(flat, z_mid) or AIR
        regions: tuple[RectRegion, ...] = ()
        if stepped:
            top = material_at(raised, z_mid) or AIR
            if top is not background:
                regions = (RectRegion(top, PERIOD_NM / 2, PERIOD_NM / 2, PILLAR_NM, PILLAR_NM),)
        layers.append(Layer(f"slice{i}", zs[i + 1] - zs[i], background, regions))
    layers.append(Layer("sub", 0, SUS))
    return layers


def condition(
    wls: list[float], num_basis: int, theta: float, pol: Polarization, stepped: bool = True
) -> SimulationCondition:
    return SimulationCondition(
        wl_min_nm=min(wls),
        wl_max_nm=max(wls),
        wl_points=len(wls),
        theta_deg=theta,
        polarization=pol,
        layers=tuple(pillar_layers(stepped)),
        period_nm=PERIOD_NM if stepped else None,
        period_y_nm=PERIOD_NM if stepped else None,
        num_basis=num_basis if stepped else 1,
        explicit_wavelengths_nm=tuple(wls),
    )


def convergence(solver: S4Solver) -> None:
    print(f"layers: {len(pillar_layers())}")
    for num_basis in (49, 81, 121, 169):
        start = time.time()
        spectrum = solver.solve(condition([470.0, 600.0], num_basis, 0.0, Polarization.S))
        assert spectrum.reflectance_total is not None
        print(
            f"basis {num_basis}: R0={[round(r, 4) for r in spectrum.reflectance]} "
            f"Rtot={[round(r, 4) for r in spectrum.reflectance_total]} "
            f"{(time.time() - start) / 2:.1f}s/wl"
        )


def spectra(solver: S4Solver, num_basis: int) -> None:
    wls = [float(w) for w in range(380, 781, 10)]
    thetas = (0.0, 30.0, 60.0)
    # キー: (角度, 量) → 無偏光の反射率。量は zeroth / total / flat（段差なし）。
    results: dict[tuple[float, str], list[float]] = {}
    for theta in thetas:
        start = time.time()
        acc: dict[str, list[float]] = {
            "zeroth": [0.0] * len(wls),
            "total": [0.0] * len(wls),
            "flat": [0.0] * len(wls),
        }
        for pol in (Polarization.S, Polarization.P):
            stepped = solver.solve(condition(wls, num_basis, theta, pol))
            flat = solver.solve(condition(wls, num_basis, theta, pol, stepped=False))
            assert stepped.reflectance_total is not None
            for i in range(len(wls)):
                acc["zeroth"][i] += stepped.reflectance[i] / 2
                acc["total"][i] += stepped.reflectance_total[i] / 2
                acc["flat"][i] += flat.reflectance[i] / 2
        for key, values in acc.items():
            results[(theta, key)] = values
        print(f"theta {theta}: {time.time() - start:.0f}s", flush=True)

    OUT_DIR.mkdir(exist_ok=True)
    csv_path = OUT_DIR / f"pillar_spectra_b{num_basis}.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        keys = sorted(results)
        writer.writerow(["wl_nm", *(f"{int(theta)}deg_{key}" for theta, key in keys)])
        for i, wl in enumerate(wls):
            writer.writerow([wl, *(f"{results[k][i]:.4f}" for k in keys)])

    fig, axes = plt.subplots(1, 3, figsize=(15, 4), sharey=True)
    titles = {"zeroth": "zeroth order only", "total": "all orders", "flat": "plain multilayer"}
    for ax, key in zip(axes, ("zeroth", "total", "flat"), strict=True):
        for theta, color in zip(thetas, ("k", "tab:blue", "tab:orange"), strict=True):
            ax.plot(wls, results[(theta, key)], color=color, label=f"{int(theta)} deg")
        ax.set_title(titles[key])
        ax.set_xlabel("wavelength [nm]")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("R (unpolarized)")
    axes[0].legend()
    fig.tight_layout()
    png_path = OUT_DIR / f"pillar_spectra_b{num_basis}.png"
    fig.savefig(png_path, dpi=110)
    print(f"wrote {csv_path} and {png_path}")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "conv"
    num_basis = int(sys.argv[2]) if len(sys.argv) > 2 else 81
    solver = S4Solver()
    if mode == "conv":
        convergence(solver)
    else:
        spectra(solver, num_basis)


if __name__ == "__main__":
    main()
