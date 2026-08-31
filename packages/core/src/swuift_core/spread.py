from __future__ import annotations
import atexit
import math
import multiprocessing as mp
import os
from concurrent.futures import ProcessPoolExecutor
from typing import Tuple
import numpy as np
from .config import SWUIFTConfig
from .kernels import brand_transport_kernel, max_brands_in_circle, radiation_kernel
_RADIATION_POOL: ProcessPoolExecutor | None = None
_RADIATION_POOL_WORKERS = 0

def _shutdown_radiation_pool() -> None:
    global _RADIATION_POOL, _RADIATION_POOL_WORKERS
    if _RADIATION_POOL is not None:
        _RADIATION_POOL.shutdown(wait=True)
        _RADIATION_POOL = None
        _RADIATION_POOL_WORKERS = 0
atexit.register(_shutdown_radiation_pool)

def _get_radiation_pool(workers: int) -> ProcessPoolExecutor:
    global _RADIATION_POOL, _RADIATION_POOL_WORKERS
    if _RADIATION_POOL is None or _RADIATION_POOL_WORKERS != workers:
        _shutdown_radiation_pool()
        start_method = 'fork' if 'fork' in mp.get_all_start_methods() else 'spawn'
        context = mp.get_context(start_method)
        _RADIATION_POOL = ProcessPoolExecutor(max_workers=workers, mp_context=context)
        _RADIATION_POOL_WORKERS = workers
    return _RADIATION_POOL

def _radiation_chunk_worker(args) -> np.ndarray:
    source_rows, source_cols, fire_vals, wind_dirs, rows, cols, grid_size, tmpr, rad_rf, aes, emissivity, sconst = args
    partial = np.zeros((rows, cols), dtype=np.float64)
    return radiation_kernel(source_rows, source_cols, fire_vals, wind_dirs, rows, cols, grid_size, partial, tmpr, rad_rf, aes, emissivity, sconst)

def brand_gen(cfg: SWUIFTConfig, rows: int, cols: int, binary_cover: np.ndarray, fire: np.ndarray, fstep: int, lstep: int, wind_s_2d: np.ndarray, wind_d_2d: np.ndarray, fb_veg_gen: int, fb_str_ig: int, veg_included: bool, tstep: int, domains_mat: np.ndarray, rng: np.random.RandomState) -> Tuple[np.ndarray, np.ndarray]:
    brand_gen_mat = np.zeros((rows, cols), dtype=np.float64)
    str_mask = (binary_cover > 0) & (fire >= fstep) & (fire <= lstep)
    if np.any(str_mask):
        ws_vals = wind_s_2d[str_mask]
        bg = np.round(306.77 * np.exp(0.1879 * ws_vals) * (cfg.grid_size * 2 * math.sqrt((cfg.grid_size / 2) ** 2 + 1)) / (lstep - fstep + 1))
        brand_gen_mat[str_mask] = bg
    if veg_included:
        veg_mask = (binary_cover < 0) & (fire >= 1) & (fire < 2) & (domains_mat != 9)
        brand_gen_mat[veg_mask] = fb_veg_gen
    nz = np.nonzero(brand_gen_mat)
    if nz[0].size == 0:
        empty = np.empty((2, 0), dtype=np.int64)
        return (empty, brand_gen_mat)
    source_rows = nz[0].astype(np.int64)
    source_cols = nz[1].astype(np.int64)
    nb_arr = brand_gen_mat[nz].astype(np.int64)
    deposits = brand_transport_kernel(source_rows, source_cols, nb_arr, rows, cols, cfg.grid_size, wind_s_2d, wind_d_2d, cfg.fb_wind_coef, cfg.fb_wind_sd, cfg.fb_wind_sd_transverse, fb_str_ig, rng)
    if deposits.shape[0] == 0:
        empty = np.empty((2, 0), dtype=np.int64)
        return (empty, brand_gen_mat)
    brands = deposits.T.copy()
    return (brands, brand_gen_mat)

def radiation_gen(cfg: SWUIFTConfig, rows: int, cols: int, binary_cover: np.ndarray, fire: np.ndarray, tmpr: np.ndarray, radtotal: np.ndarray, fstep: int, lstep: int, rad_rf: float, wind_d_2d: np.ndarray, aes: float, ee: float, er: float, sconst: float) -> np.ndarray:
    emissivity = 1.0 / (1.0 / ee + 1.0 / er - 1.0)
    source_mask = (binary_cover > 0) & (fire >= fstep) & (fire <= lstep)
    fire_int = fire.astype(np.int64)
    source_mask &= (fire_int >= 1) & (fire_int <= tmpr.shape[0])
    if not np.any(source_mask):
        return radtotal
    src = np.argwhere(source_mask)
    source_rows = np.ascontiguousarray(src[:, 0].astype(np.int64))
    source_cols = np.ascontiguousarray(src[:, 1].astype(np.int64))
    fire_vals = fire[source_mask].copy()
    wind_dirs = wind_d_2d[source_mask].copy()
    workers = int(os.environ.get('SWUIFT_APP_RADIATION_WORKERS', '1'))
    if rad_rf == 1.0 and workers > 1 and (source_rows.size >= workers):
        workers = min(workers, source_rows.size)
        chunks = [idx for idx in np.array_split(np.arange(source_rows.size), workers) if idx.size > 0]
        tasks = [(source_rows[idx], source_cols[idx], fire_vals[idx], wind_dirs[idx], rows, cols, float(cfg.grid_size), tmpr, rad_rf, aes, emissivity, sconst) for idx in chunks]
        pool = _get_radiation_pool(len(tasks))
        for partial in pool.map(_radiation_chunk_worker, tasks):
            radtotal += partial
        return radtotal
    radtotal = radiation_kernel(source_rows, source_cols, fire_vals, wind_dirs, rows, cols, float(cfg.grid_size), radtotal, tmpr, rad_rf, aes, emissivity, sconst)
    return radtotal

def radiation_ig(ignition: np.ndarray, binary_cover: np.ndarray, radtotal: np.ndarray, rad_energy_ig: float, criteria_rad: np.ndarray, limrad: float) -> np.ndarray:
    mask = (binary_cover > 0) & (ignition == 0) & (radtotal > rad_energy_ig) & (criteria_rad <= limrad)
    ignition[mask] = 1
    return ignition

def brand_ig(cfg: SWUIFTConfig, rows: int, cols: int, binary_cover: np.ndarray, ignition: np.ndarray, log_lines: list, brands: np.ndarray, fb_str_ig: int, fb_veg_ig: int, fb_dist_mu: float, fb_dist_sd: float, veg_included: bool, domains_mat: np.ndarray, criteria_spo: np.ndarray, limspo: float, rng: np.random.RandomState) -> np.ndarray:
    if brands.shape[1] == 0:
        return ignition
    brand_indices = brands[0, :].astype(np.intp)
    brand_counts = brands[1, :].astype(np.int64)
    total_counts = np.zeros(rows * cols, dtype=np.int64)
    np.add.at(total_counts, brand_indices, brand_counts)
    for i in range(rows):
        for j in range(cols):
            ind = i * cols + j
            total_here = int(total_counts[ind])
            if total_here == 0:
                continue
            if binary_cover[i, j] <= 0:
                continue
            log_lines.append(f'Number of brands land on the pixel({i + 1},{j + 1}): {total_here}')
            if ignition[i, j] != 0 or criteria_spo[i, j] > limspo or total_here < fb_str_ig:
                continue
            col_mask = brand_indices == ind
            counts_at_cell = brand_counts[col_mask]
            x_starts = rng.uniform(0, cfg.grid_size, size=int(col_mask.sum()))
            Xz_parts = []
            Yz_parts = []
            idx = 0
            for cnt in counts_at_cell:
                cnt_int = int(cnt)
                xs = x_starts[idx]
                xz = xs + rng.lognormal(fb_dist_mu, fb_dist_sd, size=cnt_int)
                yz = rng.uniform(0, 0.2, size=cnt_int)
                Xz_parts.append(xz)
                Yz_parts.append(yz)
                idx += 1
            Xz = np.concatenate(Xz_parts) if Xz_parts else np.empty(0)
            Yz = np.concatenate(Yz_parts) if Yz_parts else np.empty(0)
            mask1 = Yz < 0.1
            pts1 = np.column_stack((Xz[mask1], Yz[mask1])) if np.any(mask1) else np.empty((0, 2))
            max_brand_1 = max_brands_in_circle(pts1, radius=0.05)
            if max_brand_1 >= fb_str_ig:
                ignition[i, j] = 1
            mask2 = Yz >= 0.1
            if np.any(mask2):
                pts2 = pts1
                max_brand_2 = max_brands_in_circle(pts2, radius=0.05)
                if max_brand_2 >= fb_str_ig:
                    ignition[i, j] = 1
            else:
                max_brand_2 = 0
            max_brand = max(max_brand_1, max_brand_2)
            log_lines.append(f'Max number of brands in a Santamaria circle: {max_brand}')
    if veg_included:
        for i in range(rows):
            for j in range(cols):
                if binary_cover[i, j] >= 0:
                    continue
                if ignition[i, j] != 0:
                    continue
                if domains_mat[i, j] >= 8:
                    continue
                if int(total_counts[i * cols + j]) >= fb_veg_ig:
                    ignition[i, j] = 1
    return ignition
