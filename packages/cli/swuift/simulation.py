"""Main SWUIFT simulation loop — optimized.

Key optimizations over the base PROTOTYPE:
- Precomputed static masks and home-to-pixel lookup tables
- Incremental set-based home tracking (replaces np.unique scans)
- Vectorized zvector updates
- Threaded I/O for CSV dumps and frame rendering
- Configurable dump interval (skip per-step CSV by default)
"""

from __future__ import annotations

import csv
import json
import os
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Callable, Dict, Set, Tuple

import numpy as np
from swuift_core.hardening import apply_hardening_profile
from swuift_core.spread import brand_gen, brand_ig, radiation_gen, radiation_ig

from .config import SWUIFTConfig
from .data_loader import SWUIFTData
from .plotting import (
    assemble_video,
    build_plt_mat,
    plot_pixel_ignitions,
    plot_structure_ignitions,
    save_snapshot,
)
from .timezones import (
    format_local_time,
    localized_timestamp,
    utc_to_local,
)


class SimulationCancelledError(Exception):
    """Raised when an application callback cancels a running simulation."""


def _time_vector(t_start: datetime, t_end: datetime, t_step_min: float):
    dt = timedelta(minutes=t_step_min)
    times = []
    t = t_start
    while t <= t_end:
        times.append(t)
        t += dt
    return times


def _write_log(msg: str):
    print(msg, end="")


def _progress_bar(step: int, total: int, width: int = 32) -> str:
    if total <= 0:
        return "[" + ("-" * width) + "]"
    filled = int(round(width * step / total))
    filled = max(0, min(width, filled))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + "]"


def _summarize_brand_log(brand_log: list[str]) -> tuple[int, int]:
    deposits_logged = 0
    max_circle = 0
    prefix = "Max number of brands in a Santamaria circle:"
    for line in brand_log:
        if line.startswith("Number of brands land on the pixel"):
            deposits_logged += 1
            continue
        if line.startswith(prefix):
            raw = line.split(":", 1)[1].strip()
            try:
                max_circle = max(max_circle, int(raw))
            except ValueError:
                pass
    return deposits_logged, max_circle


def _render_step_window(
    *,
    tstep: int,
    maxstep: int,
    sim_time: datetime,
    display_timezone: str,
    ig_known_step: int,
    ig_dev_step: int,
    ig_rad_step: int,
    ig_brand_step: int,
    str_pixels_ignited: int,
    structures_ignited: int,
    step_brands_on_structures: int,
    brands_on_structures_cumsum: int,
    deposits_logged: int,
    max_santamaria_circle: int,
) -> None:
    pct = 100.0 * tstep / maxstep if maxstep else 0.0
    bar = _progress_bar(tstep, maxstep)
    lines = [
        "+" + ("-" * 86) + "+",
        f"| Progress {bar} {tstep:>3}/{maxstep:<3} ({pct:6.2f}%)",
        f"| Time      {format_local_time(sim_time, display_timezone)}",
        (
            "| Ignitions  "
            f"known:+{ig_known_step}  dev:+{ig_dev_step}  rad:+{ig_rad_step}  "
            f"brand:+{ig_brand_step}"
        ),
        f"| Structures pixels:{str_pixels_ignited}  homes:{structures_ignited}",
        (
            "| Brands    "
            f"step:{step_brands_on_structures}  cumulative:{brands_on_structures_cumsum}  "
            f"deposits:{deposits_logged}  max_circle:{max_santamaria_circle}"
        ),
        "+" + ("-" * 86) + "+",
    ]
    for line in lines:
        _write_log(line + "\n")


def _build_home_pixel_index(
    homes_mat: np.ndarray,
) -> Tuple[Dict[int, np.ndarray], Dict[int, np.ndarray]]:
    """Build home_id -> (row_indices, col_indices) lookup.

    Returns (home_id_to_rows, home_id_to_cols) dicts.
    """
    mask = homes_mat > 0
    flat = homes_mat[mask].astype(np.intp)
    rows_idx, cols_idx = np.where(mask)

    home_id_to_rows: Dict[int, list] = defaultdict(list)
    home_id_to_cols: Dict[int, list] = defaultdict(list)
    for k in range(len(flat)):
        hid = int(flat[k])
        home_id_to_rows[hid].append(rows_idx[k])
        home_id_to_cols[hid].append(cols_idx[k])

    home_rows = {hid: np.array(v, dtype=np.intp) for hid, v in home_id_to_rows.items()}
    home_cols = {hid: np.array(v, dtype=np.intp) for hid, v in home_id_to_cols.items()}
    return home_rows, home_cols


def _dump_step_binary(step_dir: str, fire, ignition, radtotal, out_fire, zvector):
    """Save per-step arrays as .npy (much faster than np.savetxt)."""
    os.makedirs(step_dir, exist_ok=True)
    np.save(os.path.join(step_dir, "fire.npy"), fire)
    np.save(os.path.join(step_dir, "ignition.npy"), ignition)
    np.save(os.path.join(step_dir, "radtotal.npy"), radtotal)
    np.save(os.path.join(step_dir, "out_fire.npy"), out_fire)
    np.save(os.path.join(step_dir, "zvector.npy"), zvector)


def _dump_step_csv(step_dir: str, fire, ignition, radtotal, out_fire, zvector):
    """Save per-step arrays as .csv for backward compatibility."""
    os.makedirs(step_dir, exist_ok=True)
    np.savetxt(os.path.join(step_dir, "fire.csv"), fire, delimiter=",")
    np.savetxt(os.path.join(step_dir, "ignition.csv"), ignition, delimiter=",")
    np.savetxt(os.path.join(step_dir, "radtotal.csv"), radtotal, delimiter=",")
    np.savetxt(os.path.join(step_dir, "out_fire.csv"), out_fire, delimiter=",")
    np.savetxt(os.path.join(step_dir, "zvector.csv"), zvector, delimiter=",")


def _make_spread_rng(cfg: SWUIFTConfig) -> tuple[np.random.RandomState, int]:
    """Create an auditable RNG while preserving seeded/unseeded scenario policy."""
    if cfg.rng_profile == "matlab_unseeded":
        effective_seed = int(np.random.SeedSequence().generate_state(1, dtype=np.uint32)[0])
        return np.random.RandomState(effective_seed), effective_seed
    if cfg.rng_profile != "seeded":
        raise ValueError(f"Unknown RNG profile: {cfg.rng_profile!r}")
    if cfg.seed_spread is None:
        raise ValueError("Seeded RNG profile requires seed_spread.")
    return np.random.RandomState(cfg.seed_spread), int(cfg.seed_spread)


def _radiation_summary(radtotal: np.ndarray, structure_mask: np.ndarray) -> dict[str, float]:
    values = np.asarray(radtotal[structure_mask], dtype=np.float64)
    if values.size == 0:
        return {
            "rad_structure_mean": 0.0,
            "rad_structure_max": 0.0,
            "rad_structure_p50": 0.0,
            "rad_structure_p95": 0.0,
            "rad_structure_p99": 0.0,
        }
    return {
        "rad_structure_mean": float(np.mean(values)),
        "rad_structure_max": float(np.max(values)),
        "rad_structure_p50": float(np.quantile(values, 0.50)),
        "rad_structure_p95": float(np.quantile(values, 0.95)),
        "rad_structure_p99": float(np.quantile(values, 0.99)),
    }


def run_simulation(
    cfg: SWUIFTConfig,
    data: SWUIFTData,
    output_dir: str,
    frame_dpi: int,
    dump_every: int,
    dump_csv: bool = False,
    out_frames: bool = True,
    out_video: bool = True,
    out_gif: bool = True,
    out_ig_plots: bool = True,
    out_fire_csv: bool = True,
    out_buildings_csv: bool = True,
    out_rad_steps: bool = False,
    out_spo_steps: bool = False,
    emit_metrics: bool = True,
    emit_frame_state: bool = True,
    checkpoint_every: int = 0,
    forensic_full: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
    cancellation_callback: Callable[[], bool] | None = None,
    phase_callback: Callable[[str], None] | None = None,
    display_timezone: str = "UTC",
) -> dict:
    """Execute the full SWUIFT simulation with all optimizations.

    Parameters
    ----------
    dump_every : int
        Save per-step state every N steps.  0 = never (default).
    dump_csv : bool
        If True, dump as CSV; otherwise use fast .npy binary format.
    """

    # ── hardening ──────────────────────────────────────────────────────────
    hard = apply_hardening_profile(
        cfg,
        data.binary_cover,
        data.homes_mat,
        data.hardening_mat_rad,
        data.hardening_mat_spo,
        data.knownig_mat,
        data.lati,
        data.long,
    )
    knownig_mat = hard.knownig_mat
    criteria_rad = hard.criteria_rad
    criteria_spo = hard.criteria_spo

    # ── zvector ────────────────────────────────────────────────────────────
    n_homes = int(data.homes_mat.max())
    zvector = np.zeros((n_homes, 5))
    zvector[:, 0] = np.arange(1, n_homes + 1)

    # ── RNG for spread ────────────────────────────────────────────────────
    rng, effective_spread_seed = _make_spread_rng(cfg)

    # ── time vector and maxstep (from config: maxstep if set, else derived from t_start..t_end) ──
    t_num_vec = _time_vector(cfg.t_start, cfg.t_end, cfg.t_step_min)
    if cfg.maxstep is not None:
        maxstep = min(cfg.maxstep, len(t_num_vec))
        t_num_vec = t_num_vec[:maxstep]
    else:
        maxstep = len(t_num_vec)

    fstep = cfg.fstep
    lstep = cfg.lstep

    # ── state matrices ────────────────────────────────────────────────────
    rows, cols = data.rows, data.cols
    ignition = np.zeros((rows, cols))
    fire = np.zeros((rows, cols))
    radtotal = np.zeros((rows, cols))
    out_fire = np.zeros((rows, cols))

    ig_known = np.zeros(maxstep)
    ig_dev = np.zeros(maxstep)
    ig_rad = np.zeros(maxstep)
    ig_brand = np.zeros(maxstep)
    ig_total = np.zeros(maxstep)

    house_ig_known = np.zeros(maxstep)
    house_ig_rad = np.zeros(maxstep)
    house_ig_brand = np.zeros(maxstep)
    house_ig_total = np.zeros(maxstep)

    # Cumulative ember statistics on structures (all statuses)
    brands_on_structures_cumsum = 0
    step_metrics: list[dict] = []

    # ── precomputed static masks (Tier 3a) ────────────────────────────────
    homes_positive = data.homes_mat > 0
    bc_positive = data.binary_cover > 0

    # ── home-to-pixel lookup (Tier 3b/3d) ─────────────────────────────────
    home_rows, home_cols = _build_home_pixel_index(data.homes_mat)

    # ── incremental home tracking (Tier 3b) ───────────────────────────────
    ignited_homes: Set[int] = set()
    str_pixels_ignited: int = 0

    # ── output dirs (single frames dir; MATLAB-style video/GIF retired) ───
    frames_dir = os.path.join(output_dir, "frames")
    timesteps_dir = os.path.join(output_dir, "timesteps")
    if out_frames:
        os.makedirs(frames_dir, exist_ok=True)
    if dump_every > 0 or out_rad_steps or out_spo_steps:
        os.makedirs(timesteps_dir, exist_ok=True)
    checkpoints_dir = os.path.join(output_dir, "checkpoints")
    frame_state_dir = os.path.join(output_dir, "normalized_frame_state")
    if checkpoint_every > 0 or forensic_full:
        os.makedirs(checkpoints_dir, exist_ok=True)
    if emit_frame_state:
        os.makedirs(frame_state_dir, exist_ok=True)

    # ── I/O pools ──────────────────────────────────────────────────────────
    # ProcessPoolExecutor for matplotlib rendering (CPU-bound, GIL-free)
    render_pool = ProcessPoolExecutor(max_workers=2)
    # ThreadPoolExecutor for file writes (I/O-bound)
    io_pool = ThreadPoolExecutor(max_workers=2)
    render_futures: list = []
    io_futures: list = []

    wall_start = time.time()
    _write_log(f"Spread loop begins at: {datetime.now()}\n")
    _write_log("################################\n")
    _write_log(f"grid cell size = {cfg.grid_size} m\n")
    _write_log(f"simulation timezone = {display_timezone}\n")
    _write_log(f"start time = {format_local_time(cfg.t_start, display_timezone)}\n")
    _write_log(f"end time = {format_local_time(cfg.t_end, display_timezone)}\n")
    _write_log(f"time step = {cfg.t_step_min} minutes\n")
    _write_log(f"Fully developed phase between steps {fstep} and {lstep}\n")
    _write_log(f"threshold for ignition due to radiation = {cfg.rad_ig_thresh}\n")
    _write_log(f"emissivity receiving = {cfg.er}\n")
    _write_log(f"emissivity emitting = {cfg.ee}\n")
    _write_log(f"area for radiating surface = {cfg.aes} m2\n")
    _write_log(f"radiation reduction factor = {cfg.rad_decay}\n")
    _write_log(f"mass of each firebrand = {cfg.fb_mass} g\n")
    _write_log(f"brands for Santamaria condition = {cfg.fb_str_ig}\n")
    _write_log(f"brands for igniting vegetation = {cfg.fb_veg_ig}\n")
    _write_log(f"brands generated from vegetation = {cfg.fb_veg_gen}\n")
    _write_log("################################\n\n")

    # ── main loop ─────────────────────────────────────────────────────────
    for tstep in range(1, maxstep + 1):
        if cancellation_callback is not None and cancellation_callback():
            render_pool.shutdown(wait=False, cancel_futures=True)
            io_pool.shutdown(wait=False, cancel_futures=True)
            raise SimulationCancelledError("Simulation cancelled.")
        step_wall_start = time.perf_counter()
        sim_time = t_num_vec[tstep - 1]

        # 1. increment burning stages
        fire[fire > 0] += 1

        # 2. known ignitions from wildfire (only outside urban domain)
        ignition[(knownig_mat == tstep) & (data.domains_mat >= 8)] = 1

        # track known ignitions — incremental
        ig_known_mask = (
            homes_positive & (knownig_mat == tstep) & (data.domains_mat >= 8)
        )
        ig_known[tstep - 1] = ignition[ig_known_mask].sum()
        if np.any(ig_known_mask):
            new_known_ids = set(data.homes_mat[ig_known_mask & homes_positive].astype(int))
            new_known_ids.discard(0)
            house_ig_known[tstep - 1] = len(new_known_ids)

        str_pixels_ignited = int(ignition[homes_positive].sum())
        _update_ignited_homes(ignited_homes, ignition, homes_positive, data.homes_mat)
        house_ig_tmp = len(ignited_homes)

        # 3. full-house propagation via lookup (Tier 3d)
        ind_mask = (ignition == 1) & bc_positive
        active_home_ids = set(data.homes_mat[ind_mask].astype(int))
        active_home_ids.discard(0)
        for hid in active_home_ids:
            if hid not in home_rows:
                continue
            hr = home_rows[hid]
            hc = home_cols[hid]
            if np.any(fire[hr, hc] >= fstep):
                ignition[hr, hc] = 1

        new_str_pix = int(ignition[homes_positive].sum())
        ig_dev[tstep - 1] = new_str_pix - str_pixels_ignited
        str_pixels_ignited = new_str_pix
        # 4. load wind slice (clamp index if wind has fewer timesteps than simulation)
        wind_ix = min(tstep - 1, data.wind.n_timesteps - 1)
        wind_s_2d, wind_d_2d = data.wind.get_slice(wind_ix)

        # 5. brand generation & transport
        brands, brand_gen_mat = brand_gen(
            cfg, rows, cols,
            data.binary_cover, fire,
            fstep, lstep,
            wind_s_2d, wind_d_2d,
            cfg.fb_veg_gen, cfg.fb_str_ig,
            cfg.veg_included, tstep,
            data.domains_mat, rng,
        )
        # 5b. ember statistics on structures (all statuses)
        step_brands_on_structures = 0
        if brands.shape[1] > 0:
            brand_indices = brands[0, :].astype(np.intp)
            brand_counts = brands[1, :].astype(np.int64)
            total_counts = np.zeros(rows * cols, dtype=np.int64)
            np.add.at(total_counts, brand_indices, brand_counts)
            total_counts_2d = total_counts.reshape(rows, cols)
            step_brands_on_structures = int(
                total_counts_2d[data.binary_cover > 0].sum()
            )
        brands_on_structures_cumsum += step_brands_on_structures
        # 6. radiation
        radtotal = radiation_gen(
            cfg, rows, cols,
            data.binary_cover, fire, cfg.tmpr, radtotal,
            fstep, lstep, cfg.rad_decay,
            wind_d_2d, cfg.aes, cfg.ee, cfg.er, cfg.sconst,
        )
        # 7. radiation ignition
        ig_before_rad = str_pixels_ignited
        homes_before_rad = len(ignited_homes)
        ignition = radiation_ig(
            ignition, data.binary_cover, radtotal,
            cfg.rad_ig_thresh, criteria_rad, cfg.limrad,
        )

        # vectorized zvector update for radiation (Tier 3c)
        _update_zvector_radiation(
            ignition, ig_before_rad, homes_positive, bc_positive,
            data.homes_mat, zvector, tstep, home_rows, home_cols,
            ignited_homes,
        )

        str_pixels_ignited = int(ignition[homes_positive].sum())
        _update_ignited_homes(ignited_homes, ignition, homes_positive, data.homes_mat)
        ig_rad[tstep - 1] = str_pixels_ignited - ig_before_rad
        house_ig_rad[tstep - 1] = len(ignited_homes) - homes_before_rad
        house_ig_tmp = len(ignited_homes)
        # 8. brand ignition
        ig_before_brand = str_pixels_ignited
        homes_before_brand = len(ignited_homes)
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
        # vectorized zvector update for branding (Tier 3c)
        _update_zvector_branding(
            ignition, ig_before_brand, homes_positive, bc_positive,
            data.homes_mat, zvector, tstep, home_rows, home_cols,
            ignited_homes,
        )

        str_pixels_ignited = int(ignition[homes_positive].sum())
        _update_ignited_homes(ignited_homes, ignition, homes_positive, data.homes_mat)
        ig_brand[tstep - 1] = str_pixels_ignited - ig_before_brand
        house_ig_brand[tstep - 1] = len(ignited_homes) - homes_before_brand
        house_ig_tmp = len(ignited_homes)
        deposits_logged, max_santamaria_circle = _summarize_brand_log(brand_log)
        _render_step_window(
            tstep=tstep,
            maxstep=maxstep,
            sim_time=sim_time,
            display_timezone=display_timezone,
            ig_known_step=int(ig_known[tstep - 1]),
            ig_dev_step=int(ig_dev[tstep - 1]),
            ig_rad_step=int(ig_rad[tstep - 1]),
            ig_brand_step=int(ig_brand[tstep - 1]),
            str_pixels_ignited=str_pixels_ignited,
            structures_ignited=house_ig_tmp,
            step_brands_on_structures=step_brands_on_structures,
            brands_on_structures_cumsum=brands_on_structures_cumsum,
            deposits_logged=deposits_logged,
            max_santamaria_circle=max_santamaria_circle,
        )

        # 9. register new fires
        new_fire_mask = (fire == 0) & (ignition == 1)
        fire[new_fire_mask] = 0.11

        ig_total[tstep - 1] = ignition[homes_positive].sum()
        house_ig_total[tstep - 1] = len(ignited_homes)

        # 10. track earliest fire time (minutes since sim start, from config time step)
        newly_on_fire = (fire != 0) & (out_fire == 0)
        out_fire[newly_on_fire] = (tstep - 1) * cfg.t_step_min

        frame_state = build_plt_mat(
            rows, cols, data.binary_cover, ignition, fire,
            fstep, lstep, data.water,
        ).astype(np.int16, copy=False)
        if emit_frame_state:
            np.save(
                os.path.join(frame_state_dir, f"state_{tstep:04d}.npy"),
                frame_state,
            )

        category_values, category_counts = np.unique(frame_state, return_counts=True)
        categories = {
            f"state_{int(value)}_cells": int(count)
            for value, count in zip(category_values, category_counts)
        }
        timestamp = localized_timestamp(sim_time, display_timezone)
        metric = {
            "tstep": tstep,
            "sim_time": sim_time.isoformat(sep=" "),
            "sim_time_utc": timestamp["utc"],
            "sim_time_local": timestamp["local"],
            "sim_time_timezone": timestamp["timezone"],
            "sim_time_offset": timestamp["offset"],
            "elapsed_minutes": float((tstep - 1) * cfg.t_step_min),
            "progress_fraction": float(tstep / maxstep),
            "ig_known": int(ig_known[tstep - 1]),
            "ig_dev": int(ig_dev[tstep - 1]),
            "ig_rad": int(ig_rad[tstep - 1]),
            "ig_brand": int(ig_brand[tstep - 1]),
            "ig_total": int(ig_total[tstep - 1]),
            "house_ig_known": int(house_ig_known[tstep - 1]),
            "house_ig_rad": int(house_ig_rad[tstep - 1]),
            "house_ig_brand": int(house_ig_brand[tstep - 1]),
            "house_ig_total": int(house_ig_total[tstep - 1]),
            "active_fire_cells": int(np.count_nonzero(fire > 0)),
            "fully_developed_structure_cells": int(
                np.count_nonzero((data.binary_cover > 0) & (fire >= fstep) & (fire <= lstep))
            ),
            "burned_structure_cells": int(
                np.count_nonzero((data.binary_cover > 0) & (fire > lstep))
            ),
            "burned_vegetation_cells": int(
                np.count_nonzero((data.binary_cover < 0) & (fire > 1))
            ),
            "brand_generated_total": int(np.sum(brand_gen_mat)),
            "brand_destination_cells": int(brands.shape[1]),
            "brand_deposited_total": int(np.sum(brands[1, :])) if brands.shape[1] else 0,
            "brands_on_structures_step": int(step_brands_on_structures),
            "brands_on_structures_cumulative": int(brands_on_structures_cumsum),
            "brand_deposits_logged": int(deposits_logged),
            "max_santamaria_circle": int(max_santamaria_circle),
            "fire_age_max": float(np.max(fire)) if fire.size else 0.0,
            "wind_speed_min": float(np.min(wind_s_2d)),
            "wind_speed_max": float(np.max(wind_s_2d)),
            "wind_speed_mean": float(np.mean(wind_s_2d)),
            "wind_speed_std_population": float(np.std(wind_s_2d)),
            "wind_direction_min": float(np.min(wind_d_2d)),
            "wind_direction_max": float(np.max(wind_d_2d)),
            "wind_direction_mean": float(np.mean(wind_d_2d)),
            "wind_direction_std_population": float(np.std(wind_d_2d)),
            "hardening_rad_pass_cells": int(np.count_nonzero(criteria_rad <= cfg.limrad)),
            "hardening_spo_pass_cells": int(np.count_nonzero(criteria_spo <= cfg.limspo)),
            **_radiation_summary(radtotal, bc_positive),
            **categories,
        }
        metric["step_wall_seconds"] = float(time.perf_counter() - step_wall_start)
        step_metrics.append(metric)

        if out_frames:
            ign_copy = ignition.copy()
            fire_copy = fire.copy()
            snap_args = (
                rows, cols,
                data.binary_cover, ign_copy, fire_copy,
                data.long, data.lati,
                sim_time, tstep,
                fstep, lstep,
                data.water,
                frames_dir,
                frame_dpi,
                display_timezone,
            )
            render_futures.append(render_pool.submit(save_snapshot, *snap_args))

        if out_rad_steps:
            io_pool.submit(
                np.savetxt,
                os.path.join(timesteps_dir, f"rad_{tstep:06d}.csv"),
                radtotal.copy(),
                delimiter=",",
            )
        if out_spo_steps:
            io_pool.submit(
                np.savetxt,
                os.path.join(timesteps_dir, f"spo_{tstep:06d}.csv"),
                brand_gen_mat.copy(),
                delimiter=",",
            )

        # 12. per-step dump (threaded, configurable interval)
        if dump_every > 0 and tstep % dump_every == 0:
            step_dir = os.path.join(timesteps_dir, f"t{tstep:06d}")
            dumper = _dump_step_csv if dump_csv else _dump_step_binary
            io_futures.append(io_pool.submit(
                dumper, step_dir,
                fire.copy(), ignition.copy(),
                radtotal.copy(), out_fire.copy(), zvector.copy(),
            ))

        checkpoint_due = forensic_full or tstep == maxstep or (
            checkpoint_every > 0 and (tstep % checkpoint_every == 0 or tstep == maxstep)
        )
        if checkpoint_due:
            step_dir = os.path.join(checkpoints_dir, f"t{tstep:06d}")
            io_futures.append(io_pool.submit(
                _dump_step_binary, step_dir,
                fire.copy(), ignition.copy(), radtotal.copy(), out_fire.copy(), zvector.copy(),
            ))
        if progress_callback is not None:
            progress_callback(tstep, maxstep)

    # ── wait for all I/O and rendering to complete ──────────────────────────
    for fut in render_futures:
        fut.result()
    render_pool.shutdown(wait=True)
    for fut in io_futures:
        fut.result()
    io_pool.shutdown(wait=True)

    # ── post-loop: clean out_fire ──────────────────────────────────────────
    out_fire[(out_fire == 0) & (knownig_mat == 0)] = np.nan

    wall_end = time.time()
    runtime_min = (wall_end - wall_start) / 60
    _write_log("\n################################\n")
    _write_log(f"Runtime: {runtime_min:.1f} minutes.\n")
    _write_log(f"rad_ig_thresh: {cfg.rad_ig_thresh}\n")
    _write_log(f"brand_wind_coef: {cfg.brand_wind_coef}\n")
    _write_log(f"brand_wind_sd: {cfg.brand_wind_sd}\n")
    _write_log(f"brand_wind_sd_lat: {cfg.brand_wind_sd_lat}\n")
    _write_log(f"fb_mass: {cfg.fb_mass}\n")
    _write_log(f"fb_dist_mu: {cfg.fb_dist_mu}\n")
    _write_log(f"fb_dist_sd: {cfg.fb_dist_sd}\n")

    # ── video / GIF (single output; MATLAB-style retired) ──────────────────
    if out_frames and (out_video or out_gif):
        if phase_callback is not None:
            phase_callback("Generating video")
        print("Assembling requested video assets …")
        assemble_video(frames_dir, output_dir, tag="", make_mp4=out_video, make_gif=out_gif)

    # ── summary plots ─────────────────────────────────────────────────────
    step_size = max(1, maxstep // 6)
    tick_positions = list(range(1, maxstep + 1, step_size))
    time_labels = [
        utc_to_local(t_num_vec[k - 1], display_timezone).strftime("%H:%M %Z")
        for k in tick_positions
    ]

    if out_ig_plots:
        plot_pixel_ignitions(
            output_dir, maxstep, time_labels, tick_positions,
            ig_known, ig_dev, ig_rad, ig_brand, ig_total,
        )
        plot_structure_ignitions(
            output_dir, maxstep, time_labels, tick_positions,
            house_ig_known, house_ig_rad, house_ig_brand, house_ig_total,
        )

    # ── CSV exports ───────────────────────────────────────────────────────
    if out_fire_csv:
        np.savetxt(os.path.join(output_dir, "fire_prog.csv"), out_fire, delimiter=",")
    if out_buildings_csv:
        np.savetxt(os.path.join(output_dir, "zvector.csv"), zvector, delimiter=",")

    if emit_metrics and step_metrics:
        metrics_path = os.path.join(output_dir, "metrics_per_step.json")
        with open(metrics_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "schema_version": 1,
                    "scenario": getattr(cfg, "scenario_id", None),
                    "display_timezone": display_timezone,
                    "effective_spread_seed": effective_spread_seed,
                    "steps": step_metrics,
                },
                handle,
                indent=2,
            )
        fieldnames = sorted({key for row in step_metrics for key in row})
        with open(os.path.join(output_dir, "metrics_per_step.csv"), "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(step_metrics)

    print(f"Simulation complete.  Outputs in {output_dir}")
    return {
        "effective_spread_seed": effective_spread_seed,
        "rng_profile": cfg.rng_profile,
        "hardening_profile": cfg.hardening_profile,
        "metric_steps": len(step_metrics),
    }


# ── helper: incremental home set update ──────────────────────────────────

def _update_ignited_homes(
    ignited_homes: Set[int],
    ignition: np.ndarray,
    homes_positive: np.ndarray,
    homes_mat: np.ndarray,
) -> None:
    """Add newly-ignited home IDs to the set."""
    ign_mask = (ignition == 1) & homes_positive
    if not np.any(ign_mask):
        return
    hids = np.unique(homes_mat[ign_mask].astype(int))
    for hid in hids:
        if hid > 0:
            ignited_homes.add(hid)


# ── helper: vectorized zvector updates ───────────────────────────────────

def _update_zvector_radiation(
    ignition: np.ndarray,
    ig_before: int,
    homes_positive: np.ndarray,
    bc_positive: np.ndarray,
    homes_mat: np.ndarray,
    zvector: np.ndarray,
    tstep: int,
    home_rows: dict,
    home_cols: dict,
    ignited_homes: Set[int],
) -> None:
    """Update zvector for radiation-caused ignitions."""
    new_pix = int(ignition[homes_positive].sum())
    if new_pix <= ig_before:
        return
    new_mask = (ignition == 1) & bc_positive & homes_positive
    hids = np.unique(homes_mat[new_mask].astype(int))
    for hid in hids:
        if hid > 0 and hid not in ignited_homes:
            if zvector[hid - 1, 1] == 0:
                zvector[hid - 1, 1] = 1
                zvector[hid - 1, 2] = 1
                zvector[hid - 1, 4] = tstep


def _update_zvector_branding(
    ignition: np.ndarray,
    ig_before: int,
    homes_positive: np.ndarray,
    bc_positive: np.ndarray,
    homes_mat: np.ndarray,
    zvector: np.ndarray,
    tstep: int,
    home_rows: dict,
    home_cols: dict,
    ignited_homes: Set[int],
) -> None:
    """Update zvector for brand-caused ignitions."""
    new_pix = int(ignition[homes_positive].sum())
    if new_pix <= ig_before:
        return
    new_mask = (ignition == 1) & bc_positive & homes_positive
    hids = np.unique(homes_mat[new_mask].astype(int))
    for hid in hids:
        if hid > 0 and hid not in ignited_homes:
            if zvector[hid - 1, 1] == 0:
                zvector[hid - 1, 1] = 1
                zvector[hid - 1, 3] = 1
                zvector[hid - 1, 4] = tstep


