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
