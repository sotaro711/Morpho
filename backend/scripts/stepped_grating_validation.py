"""段付き周期構造の S4 検証スクリプト(アプリ本体から独立した物理の答え合わせ)。

研究スライド(研究成果0825.pptx)の構造を S4 で再現し、以下を出力する:
  1. 波長別(400/470/540/600/700nm)の回折角度分布      → スライド上段のグラフと比較
  2. 入射角 0/30/60° の反射スペクトル(380-780nm)       → スライド下段のグラフと比較
  3. NumBasis 収束テスト                                  → 本番実装(PR 2)で使う値を決める
  4. NaN・異常値(R>1)の出現位置と、波長微小シフトによる回復の記録
                                                          → NaN 対処(PR 2)の設計材料

構造(スライドより):
  - 各ブロック = TiO2(n=2.3, 51nm)/ SiO2(n=1.45, 81nm)の 7 ペア多層膜(λ0=470nm)
  - 基板 = SUS。基板上げ 235nm(= λ0/2)でブロックの一部を持ち上げる
  - ブロック幅 900/600/300nm の列が単位胞(周期 3000nm)を成す

実行: cd backend && uv run --group analysis python scripts/stepped_grating_validation.py
出力: scripts/out/*.png, *.csv

数値安定化(いずれも Rayleigh 点 / Wood アノマリー対策。PR 2 の S4Solver に移植予定):
  - SetOptions(PolarizationDecomposition=True): 金属(SUS)入り格子の収束改善
  - 誘電体に微小吸収 k=1e-4 を付与して縮退をほどく
  - それでも NaN / R>1 になった波長は ±0.11nm シフトして再計算

検証結果の要約(実行のたびに追記):
  - 2026-08-26 初回: NumBasis=61 で ΔR~1e-3 に収束。NaN は λ=500/750nm
    (= 周期 3000nm の整数分の一、Rayleigh 点ちょうど)で発生し、θ=30° では
    R が発散する異常値も観測。上記の安定化を導入。
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import S4  # type: ignore[import-not-found]

OUT_DIR = Path(__file__).resolve().parent / "out"

# ---------------- 構造パラメータ(スライドより) ----------------

_NM_PER_UM = 1000.0

# 材料: 名前 -> (屈折率実部 n, 消衰係数 k, 1層の厚さ nm)。厚さ 0 は半無限媒質用。
LOSS_K = 1e-4  # 無損失誘電体に足す微小吸収(数値安定化)
MATERIALS: dict[str, tuple[float, float]] = {
    "Air": (1.0, 0.0),
    "TiO2": (2.3, LOSS_K),
    "SiO2": (1.45, LOSS_K),
    # SUS(ステンレス)の複素屈折率。可視域の代表値による近似(波長分散は無視。要検討)。
    "SUS": (2.3, 3.3),
}
T_TIO2_NM = 51.0
T_SIO2_NM = 81.0
N_PAIRS = 7

RAISE_NM = 235.0  # 基板上げ高さ = λ0/2

# 単位胞のブロック列: (幅 nm, 基板上げの有無)。スライドの一例。
# 「基盤上げの割合」各パターンとの正確な対応は要確認 → ここを差し替えて比較する。
BLOCKS: list[tuple[float, bool]] = [
    (900.0, False),
    (600.0, True),
    (300.0, False),
    (300.0, True),
    (600.0, False),
    (300.0, True),
]

# ペアの積み順(下→上)。スライドに明記がないため上面 = TiO2(高屈折率)と仮定。要検討。
PAIR_BOTTOM_UP: list[tuple[str, float]] = [("SiO2", T_SIO2_NM), ("TiO2", T_TIO2_NM)]

# ---------------- 計算条件 ----------------

NUM_BASIS = 61  # 収束テストの結果(ΔR~1e-3)より
WLS_ANGLE_NM = [400.0, 470.0, 540.0, 600.0, 700.0]  # 角度分布を出す波長
SPECTRUM_THETA_DEG = [0.0, 30.0, 60.0]  # スペクトルを出す入射角
WL_MIN_NM, WL_MAX_NM, WL_POINTS = 380.0, 780.0, 81
CONVERGENCE_BASIS = [11, 21, 41, 61, 81]
WL_SHIFT_NM = 0.11  # 異常値が出た波長の退避シフト量(Rayleigh 点は孤立点なので微小でよい)

Profile = list[tuple[float, str]]  # 下から上へ (厚さnm, 材料名)


def stack_profile(raised: bool) -> Profile:
    """1 ブロック(カラム)の z 方向の材料プロファイル(下→上)。"""
    prof: Profile = []
    if raised:
        prof.append((RAISE_NM, "SUS"))
    for _ in range(N_PAIRS):
        prof.extend((t_nm, name) for name, t_nm in PAIR_BOTTOM_UP)
    return prof


def material_at(prof: Profile, z_nm: float) -> str | None:
    """プロファイル中の高さ z の材料名。スタックの上(空気)なら None。"""
    z0 = 0.0
    for t_nm, name in prof:
        if z0 <= z_nm < z0 + t_nm:
            return name
        z0 += t_nm
    return None


def build_sim(num_basis: int, blocks: list[tuple[float, bool]]):
    """構造を z 方向にスライスして S4 シミュレーションを組み立てる。

    全カラムの層境界(基板上げ 235nm とペア境界の互い違い)を集めて水平スライスに
    分割し、各スライスを「矩形領域の並び」としてパターン化する。
    """
    period_nm = sum(w for w, _ in blocks)
    period_um = period_nm / _NM_PER_UM

    sim = S4.New(Lattice=((period_um, 0.0), (0.0, 0.0)), NumBasis=num_basis)
    # 金属(SUS)を含む格子の収束改善(Li の因子化)。
    sim.SetOptions(PolarizationDecomposition=True)

    for name, (n, k) in MATERIALS.items():
        nc = complex(n, k)
        sim.SetMaterial(Name=name, Epsilon=nc * nc)

    # カラム(x 方向の区間)と、その z プロファイル
    columns: list[tuple[float, float, Profile]] = []
    x = 0.0
    for w, raised in blocks:
        columns.append((x, w, stack_profile(raised)))
        x += w

    # 全カラムの層境界を集めて z 方向のスライスを作る
    breaks = {0.0}
    for col in columns:
        z = 0.0
        for t_nm, _ in col[2]:
            z += t_nm
            breaks.add(round(z, 6))
    zs = sorted(breaks)

    # 入射側(上)の半無限空気層 → スライスを上から順に → 基板の半無限 SUS 層
    sim.AddLayer(Name="top", Thickness=0.0, S4_Material="Air")
    for i in range(len(zs) - 2, -1, -1):  # 上のスライスから追加する
        z0, z1 = zs[i], zs[i + 1]
        zmid = (z0 + z1) / 2.0
        layer_name = f"slice{i}"
        sim.AddLayer(
            Name=layer_name,
            Thickness=(z1 - z0) / _NM_PER_UM,
            S4_Material="Air",
        )
        for x0, w, prof in columns:
            mat = material_at(prof, zmid)
            if mat is None:
                continue
            sim.SetRegionRectangle(
                S4_Layer=layer_name,
                S4_Material=mat,
                Center=((x0 + w / 2.0) / _NM_PER_UM, 0.0),
                Angle=0.0,
                Halfwidths=(w / 2.0 / _NM_PER_UM, 0.0),
            )
    sim.AddLayer(Name="bottom", Thickness=0.0, S4_Material="SUS")
    return sim, period_um


def solve_orders(
    sim, period_um: float, wl_nm: float, theta_deg: float, pol: str
) -> tuple[float, list[tuple[int, float, float]]]:
    """1 条件を解き、(全反射率, [(次数 m, 出射角 deg, R_m)]) を返す。伝搬しない次数は除く。"""
    s_amp, p_amp = (1.0, 0.0) if pol == "s" else (0.0, 1.0)
    sim.SetExcitationPlanewave(IncidenceAngles=(theta_deg, 0.0), sAmplitude=s_amp, pAmplitude=p_amp)
    wl_um = wl_nm / _NM_PER_UM
    sim.SetFrequency(1.0 / wl_um)

    fluxes = sim.GetPowerFluxByOrder(S4_Layer="top")
    basis = sim.GetBasisSet()  # ((m, 0), ...) 1D 格子なので第2成分は 0
    incident = sum(f.real for f, _ in fluxes)
    if incident == 0.0 or math.isnan(incident):
        return float("nan"), []

    sin_in = math.sin(math.radians(theta_deg))
    orders: list[tuple[int, float, float]] = []
    total_r = 0.0
    for g, flux in zip(basis, fluxes, strict=True):
        m = g[0]
        r_m = -flux[1].real / incident
        total_r += r_m
        sin_m = sin_in + m * wl_um / period_um
        if abs(sin_m) <= 1.0:  # 伝搬する次数のみ角度を持つ
            orders.append((m, math.degrees(math.asin(sin_m)), r_m))
    return total_r, orders


def is_anomalous(r: float) -> bool:
    """NaN、または物理的にありえない反射率(発散の前兆)を異常とみなす。"""
    return math.isnan(r) or r < -0.01 or r > 1.05


def solve_r_unpolarized(
    sim, period_um: float, wl_nm: float, theta_deg: float, anomaly_log: list[str]
) -> float:
    """s/p 平均の全反射率。異常値は波長を微小シフトして再計算し、経緯を記録する。"""
    per_pol: dict[str, float] = {}
    for pol in ("s", "p"):
        r, _ = solve_orders(sim, period_um, wl_nm, theta_deg, pol)
        if is_anomalous(r):
            r_shift, _ = solve_orders(sim, period_um, wl_nm + WL_SHIFT_NM, theta_deg, pol)
            status = "recovered" if not is_anomalous(r_shift) else "STILL BAD"
            anomaly_log.append(
                f"wl={wl_nm:.1f}nm theta={theta_deg:g}deg pol={pol}: "
                f"R={r:.3g} -> shift +{WL_SHIFT_NM}nm: R={r_shift:.3g} ({status})"
            )
            r = r_shift
        per_pol[pol] = r
    return (per_pol["s"] + per_pol["p"]) / 2.0


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    anomaly_log: list[str] = []

    # ---- 1. NumBasis 収束テスト(470nm, 垂直入射) ----
    print("== NumBasis convergence (wl=470nm, theta=0) ==")
    prev = None
    for nb in CONVERGENCE_BASIS:
        sim, period_um = build_sim(nb, BLOCKS)
        r = solve_r_unpolarized(sim, period_um, 470.0, 0.0, anomaly_log)
        delta = "-" if prev is None else f"{abs(r - prev):.2e}"
        print(f"  NumBasis={nb:3d}  R={r:.6f}  dR={delta}")
        prev = r

    # ---- 2. 反射スペクトル(0/30/60°) ----
    print("== Reflectance spectra ==")
    sim, period_um = build_sim(NUM_BASIS, BLOCKS)
    wls = [WL_MIN_NM + (WL_MAX_NM - WL_MIN_NM) * i / (WL_POINTS - 1) for i in range(WL_POINTS)]
    spectra: dict[float, list[float]] = {}
    for theta in SPECTRUM_THETA_DEG:
        rs = [solve_r_unpolarized(sim, period_um, wl, theta, anomaly_log) for wl in wls]
        spectra[theta] = rs
        valid = [r for r in rs if not math.isnan(r)]
        print(f"  theta={theta:4.0f}deg  done (max R={max(valid):.3f})")

    # ---- 3. 回折角度分布(垂直入射、波長別) ----
    print("== Diffraction angle distribution (theta_in=0) ==")
    angle_dist: dict[float, list[tuple[float, float]]] = {}
    for wl in WLS_ANGLE_NM:
        merged: dict[int, tuple[float, float]] = {}
        for pol in ("s", "p"):
            _, orders = solve_orders(sim, period_um, wl, 0.0, pol)
            for m, ang, r_m in orders:
                a0, r0 = merged.get(m, (ang, 0.0))
                merged[m] = (a0, r0 + r_m / 2.0)  # s/p 平均
        pts = sorted(merged.values())
        angle_dist[wl] = pts
        print(f"  wl={wl:5.0f}nm  propagating orders={len(pts)}")

    # ---- 4. 出力 ----
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for wl, pts in angle_dist.items():
        ax.plot([a for a, _ in pts], [r for _, r in pts], marker="o", ms=3, label=f"{wl:.0f} nm")
    ax.set_xlabel("diffraction angle [deg]")
    ax.set_ylabel("reflected power (per order)")
    ax.set_xlim(-85, 85)
    ax.legend()
    ax.set_title(f"Angle distribution (theta_in=0, NumBasis={NUM_BASIS})")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "angle_distribution.png", dpi=150)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    for theta, rs in spectra.items():
        ax.plot(wls, rs, label=f"{theta:.0f} deg")
    ax.set_xlabel("wavelength [nm]")
    ax.set_ylabel("total reflectance")
    ax.set_ylim(0, 1)
    ax.legend()
    ax.set_title(f"Reflectance spectra (NumBasis={NUM_BASIS})")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "spectra.png", dpi=150)

    with (OUT_DIR / "spectra.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wavelength_nm"] + [f"R_theta{t:.0f}" for t in SPECTRUM_THETA_DEG])
        for i, wl in enumerate(wls):
            w.writerow([wl] + [spectra[t][i] for t in SPECTRUM_THETA_DEG])

    print(f"== Anomaly report: {len(anomaly_log)} occurrences (NaN or R out of [0,1]) ==")
    for line in anomaly_log:
        print("  " + line)
    print(f"wrote {OUT_DIR}/angle_distribution.png, spectra.png, spectra.csv")


if __name__ == "__main__":
    main()
