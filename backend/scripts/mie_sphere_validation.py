"""Si 球の単層配列(Mie 共鳴)の S4 検証スクリプト(アプリ本体から独立した物理の答え合わせ)。

研究スライド「Si粒子単層配置(Mie共鳴)による青色発色」の構造を S4 で再現し、以下を出力する:
  1. 入射角 0/30° × s/p 偏光の反射スペクトル(380-780nm)  → スライド右側のグラフと比較
  2. スライス数 × NumBasis の収束表(470nm, 垂直入射)        → 本番実装の既定値を決める
  3. NaN・異常値(R>1)の出現記録

構造(スライドより):
  - 正方格子、周期 160nm。Si 球(直径 120nm、n=4.0+0.072i)が基板の上に載る(粒子間隔 40nm)
  - 基板の屈折率はスライドに無いので n=1.5(樹脂)と仮置き。要確認
  - スライド側は FEM(球をそのまま扱う)。S4 では球を z 方向に N 枚に輪切りし、
    各スライスを「厚さ D/N、中心に半径 r(z) の円領域」を持つ層で近似する(階段近似)。
    円の Fourier 係数は S4 が解析的に持つので、面内方向は離散化しない。

スライドの読み取り値(目視):
  s 偏光 θ=0°: R≈0.78(380-450nm)→ 0.5(480nm)→ 0.1(560nm)→ ≈0(600nm 以降)
  p 偏光 θ=30°: 380nm で 0.42 から立ち上がり 460nm で 0.73、以降は θ=0° とほぼ同じ

実行: cd backend && uv run --group analysis python scripts/mie_sphere_validation.py [slices] [basis]
      (省略時は NUM_SLICES / NUM_BASIS。収束表は引数によらず固定の組み合わせで出す)
出力: scripts/out/sphere_spectra_s{slices}_b{basis}.png, .csv, sphere_convergence.csv

Fourier 因子化の選択(段差格子の検証とは逆の結論):
  段差格子(金属 SUS 入り)では PolarizationDecomposition=True(Li の因子化)が収束に必要
  だったが、誘電体の円領域ではこれを有効にすると収束が著しく遅い(470nm, 8 スライスで
  基底 121→289 で R=0.30→0.38 と上がり続ける)。無効なら基底 81 で 3 桁目まで収束する
  (0.503→0.505)。PolarizationBasis=Normal/Jones、SubpixelSmoothing も差がなく、
  LanczosSmoothing は R=0.09 と大きく外れる。本番の S4Solver はパターン時に一律で
  True にしているので、材料や形状で切り替えられるようにする必要がある。

検証結果の要約(実行のたびに追記):
  - 2026-10-25 収束表(470nm, θ=0, s, PolarizationDecomposition=False):
      slices=8:  基底 49/81/121/169/225 で R=0.493/0.503/0.504/0.504/0.505(基底 81 で収束)
      slices=16: 0.523/0.539/0.549/0.554/0.558(基底 225 でもわずかに上昇)
      slices=32: 0.529/0.548/0.560(基底 121)
    スライスを増やすと上下端の薄い円(半径が小さい)の表現に高次の基底が要り、
    収束が遅くなる。1 波長あたり: 基底 81/121/169 × 16 スライスで 1.4/4.3/12 秒
    (基底数のほぼ 3 乗、スライス数に比例)。
  - 2026-10-25 スペクトル(16 スライス, 基底 81, 41 波長 × 4 条件で約 4.5 分):
      s θ=0°:  R=0.79(380)→0.82(420)→0.65(460)→0.42(480)→0.10(520)→0.02(580 以降)
      s θ=30°: 440-460nm に肩(0.76→0.55)。p θ=30°: 0.43(380)→0.74(440)、以降は θ=0° と同じ
    いずれもスライドの形・値とよく一致(基板 n=1.5 の仮置きで問題なさそう)。
    基底 169 との差は全波長で ≤0.016(470nm: 0.539 vs 0.554)。NaN・異常値なし。
    → 本番の既定値候補: 16 スライス・基底 81。表示用に 41 波長なら 1 条件 1 分強。
"""

from __future__ import annotations

import csv
import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import S4  # type: ignore[import-not-found]

OUT_DIR = Path(__file__).resolve().parent / "out"

# ---------------- 構造パラメータ(スライドより) ----------------

_NM_PER_UM = 1000.0

# 材料: 名前 -> (屈折率実部 n, 消衰係数 k)
MATERIALS: dict[str, tuple[float, float]] = {
    "Air": (1.0, 0.0),
    "Si": (4.0, 0.072),
    "Substrate": (1.5, 0.0),  # スライドに記載なし。樹脂と仮置き
}
PERIOD_NM = 160.0
DIAMETER_NM = 120.0

# ---------------- 計算条件 ----------------

NUM_SLICES = 16
NUM_BASIS = 81
SPECTRUM_THETA_DEG = [0.0, 30.0]
WL_MIN_NM, WL_MAX_NM, WL_POINTS = 380.0, 780.0, 41
CONVERGENCE_SLICES = [8, 16, 32]
CONVERGENCE_BASIS = [49, 81, 121, 169]
# Li の因子化を有効にした場合の参考値(収束の遅さを記録するため)
CONVERGENCE_BASIS_POLDECOMP = [81, 169]


def sphere_slices(diameter_nm: float, num_slices: int) -> list[tuple[float, float]]:
    """球を等厚の輪切りにし、上から順に (厚さ nm, 円の半径 nm) を返す。

    半径はスライス中央の高さで評価する。上端・下端のスライスは中央でも半径が
    0 にならないので、全スライスが円領域を持つ。
    """
    radius = diameter_nm / 2.0
    h = diameter_nm / num_slices
    slices: list[tuple[float, float]] = []
    for i in range(num_slices):
        z_mid = diameter_nm - (i + 0.5) * h  # 球の底を z=0 として上から
        r = math.sqrt(max(radius**2 - (z_mid - radius) ** 2, 0.0))
        slices.append((h, r))
    return slices


def build_sim(num_basis: int, num_slices: int, polarization_decomposition: bool = False):
    """球を輪切りにして S4 シミュレーションを組み立てる。"""
    period_um = PERIOD_NM / _NM_PER_UM
    sim = S4.New(Lattice=((period_um, 0.0), (0.0, period_um)), NumBasis=num_basis)
    # Li の因子化は誘電体の円領域では収束を悪くする(モジュール docstring 参照)。
    sim.SetOptions(PolarizationDecomposition=polarization_decomposition)

    for name, (n, k) in MATERIALS.items():
        nc = complex(n, k)
        sim.SetMaterial(Name=name, Epsilon=nc * nc)

    sim.AddLayer(Name="top", Thickness=0.0, S4_Material="Air")
    for i, (h_nm, r_nm) in enumerate(sphere_slices(DIAMETER_NM, num_slices)):
        layer_name = f"slice{i}"
        sim.AddLayer(Name=layer_name, Thickness=h_nm / _NM_PER_UM, S4_Material="Air")
        sim.SetRegionCircle(
            S4_Layer=layer_name,
            S4_Material="Si",
            Center=(period_um / 2.0, period_um / 2.0),
            Radius=r_nm / _NM_PER_UM,
        )
    sim.AddLayer(Name="bottom", Thickness=0.0, S4_Material="Substrate")
    return sim


def solve_r(sim, wl_nm: float, theta_deg: float, pol: str) -> float:
    """1 条件の全反射率(全次数の合計)。"""
    s_amp, p_amp = (1.0, 0.0) if pol == "s" else (0.0, 1.0)
    sim.SetExcitationPlanewave(IncidenceAngles=(theta_deg, 0.0), sAmplitude=s_amp, pAmplitude=p_amp)
    sim.SetFrequency(_NM_PER_UM / wl_nm)
    fluxes = sim.GetPowerFluxByOrder(S4_Layer="top")
    incident = sum(f.real for f, _ in fluxes)
    if incident == 0.0 or math.isnan(incident):
        return float("nan")
    return sum(-b.real for _, b in fluxes) / incident


def is_anomalous(r: float) -> bool:
    return math.isnan(r) or r < -0.01 or r > 1.05


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    anomaly_log: list[str] = []
    num_slices = int(sys.argv[1]) if len(sys.argv) > 1 else NUM_SLICES
    num_basis = int(sys.argv[2]) if len(sys.argv) > 2 else NUM_BASIS

    # ---- 1. 収束表(470nm, 垂直入射, s 偏光) ----
    # 周期 160nm は可視域の波長より短いので Rayleigh 点は範囲外(空気側 160nm、θ=30° で 240nm)。
    print("== Convergence (wl=470nm, theta=0, s-pol): R and seconds per solve ==")
    conv_rows: list[list[float | int]] = []
    header = "slices\\basis " + "".join(f"{nb:>16d}" for nb in CONVERGENCE_BASIS)
    print("  " + header)
    for ns in CONVERGENCE_SLICES:
        cells: list[str] = []
        row: list[float | int] = [ns]
        for nb in CONVERGENCE_BASIS:
            sim = build_sim(nb, ns)
            t0 = time.perf_counter()
            r = solve_r(sim, 470.0, 0.0, "s")
            dt = time.perf_counter() - t0
            cells.append(f"{r:.4f} ({dt:5.2f}s)")
            row.extend([r, dt])
        conv_rows.append(row)
        print(f"  {ns:>12d} " + "".join(f"{c:>16s}" for c in cells))
    with (OUT_DIR / "sphere_convergence.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["slices"] + [f"R_nb{nb},sec_nb{nb}" for nb in CONVERGENCE_BASIS])
        w.writerows(conv_rows)
    print("  (reference) PolarizationDecomposition=True, slices=8:")
    for nb in CONVERGENCE_BASIS_POLDECOMP:
        sim = build_sim(nb, 8, polarization_decomposition=True)
        print(f"    NumBasis={nb:3d}  R={solve_r(sim, 470.0, 0.0, 's'):.4f}")

    # ---- 2. 反射スペクトル(0/30°, s/p) ----
    print(f"== Reflectance spectra (slices={num_slices}, NumBasis={num_basis}) ==")
    sim = build_sim(num_basis, num_slices)
    wls = [WL_MIN_NM + (WL_MAX_NM - WL_MIN_NM) * i / (WL_POINTS - 1) for i in range(WL_POINTS)]
    spectra: dict[tuple[str, float], list[float]] = {}
    for pol in ("s", "p"):
        for theta in SPECTRUM_THETA_DEG:
            t0 = time.perf_counter()
            rs: list[float] = []
            for wl in wls:
                r = solve_r(sim, wl, theta, pol)
                if is_anomalous(r):
                    anomaly_log.append(f"wl={wl:.1f}nm theta={theta:g}deg pol={pol}: R={r:.3g}")
                rs.append(r)
            spectra[(pol, theta)] = rs
            r470 = rs[min(range(len(wls)), key=lambda i: abs(wls[i] - 470.0))]
            print(
                f"  pol={pol} theta={theta:4.0f}deg  R(470nm)={r470:.3f}  "
                f"max R={max(rs):.3f}  ({time.perf_counter() - t0:.1f}s)"
            )

    # ---- 3. 出力 ----
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, pol in zip(axes, ("s", "p"), strict=True):
        for theta in SPECTRUM_THETA_DEG:
            ax.plot(wls, spectra[(pol, theta)], label=f"θ={theta:.0f}°")
        ax.set_xlabel("wavelength [nm]")
        ax.set_ylim(0, 1)
        ax.set_title(f"{pol}-pol (slices={num_slices}, NumBasis={num_basis})")
        ax.legend()
    axes[0].set_ylabel("total reflectance")
    fig.tight_layout()
    stem = f"sphere_spectra_s{num_slices}_b{num_basis}"
    fig.savefig(OUT_DIR / f"{stem}.png", dpi=150)

    with (OUT_DIR / f"{stem}.csv").open("w", newline="") as f:
        w = csv.writer(f)
        keys = list(spectra)
        w.writerow(["wavelength_nm"] + [f"R_{pol}_theta{t:.0f}" for pol, t in keys])
        for i, wl in enumerate(wls):
            w.writerow([wl] + [spectra[k][i] for k in keys])

    print(f"== Anomaly report: {len(anomaly_log)} occurrences (NaN or R out of [0,1]) ==")
    for line in anomaly_log:
        print("  " + line)
    print(f"wrote {OUT_DIR}/{stem}.png, {stem}.csv, sphere_convergence.csv")


if __name__ == "__main__":
    main()
