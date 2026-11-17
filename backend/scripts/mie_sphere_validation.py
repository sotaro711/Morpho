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


_NM_PER_UM = 1000.0

MATERIALS: dict[str, tuple[float, float]] = {
    "Air": (1.0, 0.0),
    "Si": (4.0, 0.072),
    "Substrate": (1.5, 0.0),
}
PERIOD_NM = 160.0
DIAMETER_NM = 120.0


NUM_SLICES = 16
NUM_BASIS = 81
SPECTRUM_THETA_DEG = [0.0, 30.0]
WL_MIN_NM, WL_MAX_NM, WL_POINTS = 380.0, 780.0, 41
CONVERGENCE_SLICES = [8, 16, 32]
CONVERGENCE_BASIS = [49, 81, 121, 169]
CONVERGENCE_BASIS_POLDECOMP = [81, 169]


def sphere_slices(diameter_nm: float, num_slices: int) -> list[tuple[float, float]]:
    radius = diameter_nm / 2.0
    h = diameter_nm / num_slices
    slices: list[tuple[float, float]] = []
    for i in range(num_slices):
        z_mid = diameter_nm - (i + 0.5) * h
        r = math.sqrt(max(radius**2 - (z_mid - radius) ** 2, 0.0))
        slices.append((h, r))
    return slices


def build_sim(num_basis: int, num_slices: int, polarization_decomposition: bool = False):
    period_um = PERIOD_NM / _NM_PER_UM
    sim = S4.New(Lattice=((period_um, 0.0), (0.0, period_um)), NumBasis=num_basis)
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
