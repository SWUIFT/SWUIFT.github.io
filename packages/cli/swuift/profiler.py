"""Per-timestep profiler for diagnosing simulation bottlenecks.

Wraps each phase of the simulation loop with high-resolution timers
and prints/logs an aggregated summary at the end.

Usage:
    python -m swuift.profiler /path/to/data [--max-steps 5]
"""

from __future__ import annotations

import math
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np

from .config import SWUIFTConfig
from .data_loader import SWUIFTData, load_all
from swuift_core.hardening import apply_hardening
from swuift_core.spread import brand_gen, brand_ig, radiation_gen, radiation_ig


class StepProfiler:
    """Accumulates per-phase timing across timesteps."""

    def __init__(self):
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self._t0 = 0.0
        self._current_phase = ""

    def start(self, phase: str):
        self._current_phase = phase
        self._t0 = time.perf_counter()

    def stop(self):
        elapsed = time.perf_counter() - self._t0
        self.timings[self._current_phase].append(elapsed)
        return elapsed

    def report(self, n_steps: int) -> str:
        lines = [
            "",
            "=" * 80,
            f"  PROFILER SUMMARY  ({n_steps} steps)",
            "=" * 80,
            f"  {'Phase':<35s} {'Total (s)':>10s} {'Mean (s)':>10s} "
            f"{'Max (s)':>10s} {'%':>7s}",
            "-" * 80,
        ]
        grand_total = sum(sum(v) for v in self.timings.values())
        for phase in self.timings:
            vals = self.timings[phase]
            total = sum(vals)
            mean = total / len(vals) if vals else 0
            mx = max(vals) if vals else 0
            pct = 100 * total / grand_total if grand_total > 0 else 0
            lines.append(
                f"  {phase:<35s} {total:>10.3f} {mean:>10.4f} {mx:>10.4f} {pct:>6.1f}%"
            )
        lines.append("-" * 80)
        lines.append(f"  {'TOTAL':<35s} {grand_total:>10.3f}")
        lines.append(f"  {'Per-step avg':<35s} {grand_total / n_steps:>10.3f}")
        lines.append("=" * 80)
        return "\n".join(lines)


def _time_vector(t_start, t_end, t_step_min):
    dt = timedelta(minutes=t_step_min)
    times = []
    t = t_start
    while t <= t_end:
        times.append(t)
        t += dt
    return times


def run_profiled(data_dir: str, max_steps: int = 5, preload_wind: bool = True):
    """Run a limited number of steps with detailed per-phase timing."""
    print(f"Loading data from {data_dir} ...")
    _defaults, data = load_all(data_dir, preload_wind=preload_wind)
    rows, cols = data.rows, data.cols
    print(f"  Grid: {rows} x {cols} = {rows * cols:,} cells")

    cfg = SWUIFTConfig(maxstep=max_steps)
    fstep, lstep = cfg.fstep, cfg.lstep
    print(f"  fstep={fstep}  lstep={lstep}")

    # ── hardening ──
    prof = StepProfiler()
    prof.start("hardening (one-time)")
    hard = apply_hardening(
        cfg, data.binary_cover, data.homes_mat,
        data.hardening_mat_rad, data.hardening_mat_spo,
        data.knownig_mat, data.lati, data.long,
    )
    t = prof.stop()
    print(f"  Hardening: {t:.3f}s")

    knownig_mat = hard.knownig_mat
    criteria_rad = hard.criteria_rad
    criteria_spo = hard.criteria_spo

    rng = np.random.RandomState(cfg.seed_spread)
    t_num_vec = _time_vector(cfg.t_start, cfg.t_end, cfg.t_step_min)
    maxstep = min(max_steps, len(t_num_vec))

    ignition = np.zeros((rows, cols))
    fire = np.zeros((rows, cols))
    radtotal = np.zeros((rows, cols))
    homes_positive = data.homes_mat > 0
    bc_positive = data.binary_cover > 0

    emissivity = 1.0 / (1.0 / cfg.ee + 1.0 / cfg.er - 1.0)

    print(f"\n  Running {maxstep} steps with profiling...\n")

    for tstep in range(1, maxstep + 1):
        print(f"--- Step {tstep} ---")

        # 1. increment
        prof.start("1_fire_increment")
        fire[fire > 0] += 1
        prof.stop()

        # 2. known ignitions
        prof.start("2_known_ignitions")
        ignition[(knownig_mat == tstep) & (data.domains_mat >= 8)] = 1
        prof.stop()

        # 3. full-house propagation
        prof.start("3_fullhouse_propagation")
        ind_mask = (ignition == 1) & bc_positive
        homes_ids = np.unique(data.homes_mat[ind_mask])
        homes_ids = homes_ids[homes_ids > 0]
        for hid in homes_ids:
            h_mask = data.homes_mat == hid
            if np.any(fire[h_mask] >= fstep):
                ignition[h_mask] = 1
        prof.stop()

        # 4. wind (clamp index if wind has fewer timesteps than simulation)
        prof.start("4_wind_load")
        wind_ix = min(tstep - 1, data.wind.n_timesteps - 1)
        wind_s_2d, wind_d_2d = data.wind.get_slice(wind_ix)
        prof.stop()

        # 5. brand gen
        prof.start("5_brand_gen")
        brands, brand_gen_mat = brand_gen(
            cfg, rows, cols,
            data.binary_cover, fire, fstep, lstep,
            wind_s_2d, wind_d_2d,
            cfg.fb_veg_gen, cfg.fb_str_ig,
            cfg.veg_included, tstep,
            data.domains_mat, rng,
        )
        t = prof.stop()
        n_src = int((brand_gen_mat > 0).sum())
        total_brands = int(brand_gen_mat.sum())
        print(f"  brand_gen: {t:.3f}s  sources={n_src}  total_brands={total_brands:,}  deposits={brands.shape[1]}")

        # 5.5 — diagnose r_max_cells
        prof.start("5.5_radiation_diagnostics")
        source_mask = (data.binary_cover > 0) & (fire >= fstep) & (fire <= lstep)
        n_rad_sources = int(source_mask.sum())
        r_max_cells_actual = 0
        if n_rad_sources > 0:
            fire_int = fire.astype(np.int64)
            source_mask &= (fire_int >= 1) & (fire_int <= cfg.tmpr.shape[0])
            fire_vals_src = fire[source_mask]
            fire_idx = fire_vals_src.astype(np.int64)
            temps_K = cfg.tmpr[fire_idx - 1] + 273.15
            ambient_T4 = 293.15 ** 4
            radiants = emissivity * cfg.sconst * (temps_K ** 4 - ambient_T4)
            radiant_max = float(radiants.max()) if len(radiants) > 0 else 0
            epsilon = 1.0
            if radiant_max > 0 and cfg.aes > 0:
                r_max_m = math.sqrt(cfg.aes * radiant_max / (math.pi * epsilon))
                r_max_cells_actual = int(math.ceil(r_max_m / cfg.grid_size))
                r_max_cells_actual = min(r_max_cells_actual, max(rows, cols))
            lut_size = (2 * r_max_cells_actual + 1) ** 2
            window_per_src = min((2 * r_max_cells_actual + 1), rows) * min((2 * r_max_cells_actual + 1), cols)
        else:
            lut_size = 0
            window_per_src = 0
            radiant_max = 0
        prof.stop()
        print(f"  radiation: n_sources={n_rad_sources}  r_max_cells={r_max_cells_actual}  "
              f"LUT_size={lut_size:,}  window_cells_per_src={window_per_src:,}  "
              f"total_inner_iters={n_rad_sources * window_per_src:,}  radiant_max={radiant_max:.1f}")

        # 6. radiation
        prof.start("6_radiation_gen")
        radtotal = radiation_gen(
            cfg, rows, cols,
            data.binary_cover, fire, cfg.tmpr, radtotal,
            fstep, lstep, cfg.rad_decay,
            wind_d_2d, cfg.aes, cfg.ee, cfg.er, cfg.sconst,
        )
        t = prof.stop()
        print(f"  radiation_gen: {t:.3f}s")

        # 7. radiation ignition
        prof.start("7_radiation_ig")
        ignition = radiation_ig(
            ignition, data.binary_cover, radtotal,
            cfg.rad_ig_thresh, criteria_rad, cfg.limrad,
        )
        prof.stop()

        # 8. brand ignition
        prof.start("8_brand_ig")
        brand_log: list[str] = []
        ignition = brand_ig(
            cfg, rows, cols,
            data.binary_cover, ignition,
            brand_log, brands,
            cfg.fb_str_ig, cfg.fb_veg_ig,
            cfg.fb_dist_mu, cfg.fb_dist_sd,
            cfg.veg_included, data.domains_mat,
            criteria_spo, cfg.limspo, rng,
        )
        t = prof.stop()
        print(f"  brand_ig: {t:.3f}s  deposits_checked={brands.shape[1]}  log_entries={len(brand_log)}")

        # 9. register fires
        prof.start("9_register_fires")
        new_fire_mask = (fire == 0) & (ignition == 1)
        fire[new_fire_mask] = 0.11
        prof.stop()

        # 10. snapshot (synchronous for profiling)
        prof.start("10_snapshot")
        from .plotting import save_snapshot
        prof_dir = "/tmp/swuift_prof" if os.path.exists("/tmp/swuift_prof") else "/dev/null"
        save_snapshot(
            rows, cols,
            data.binary_cover, ignition, fire,
            data.long, data.lati,
            t_num_vec[tstep - 1], tstep,
            fstep, lstep,
            data.water,
            prof_dir,
            dpi=72,
        )
        t = prof.stop()
        print(f"  snapshot: {t:.3f}s")

        # step total
        step_total = sum(
            prof.timings[k][-1] for k in prof.timings if len(prof.timings[k]) > 0
        )
        print(f"  STEP TOTAL: ~{sum(prof.timings[k][-1] for k in prof.timings if prof.timings[k]):.3f}s")

    print(prof.report(maxstep))
    data.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Profile SWUIFT timestep performance.")
    parser.add_argument("data_dir", help="Path to the data folder")
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--lazy-wind", action="store_true",
                        help="Use lazy HDF5 reads instead of preloading.")
    args = parser.parse_args()

    os.makedirs("/tmp/swuift_prof", exist_ok=True)
    run_profiled(args.data_dir, max_steps=args.max_steps, preload_wind=not args.lazy_wind)


if __name__ == "__main__":
    main()
