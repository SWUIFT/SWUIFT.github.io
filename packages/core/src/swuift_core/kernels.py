from __future__ import annotations
import math
import os
import sys
from typing import TYPE_CHECKING
import numpy as np
if TYPE_CHECKING:
    pass
_KERNEL_BACKEND = os.environ.get('SWUIFT_APP_KERNEL_BACKEND', 'numba').strip().lower()
_NUMBA_CACHE = not getattr(sys, 'frozen', False)

def kernel_backend() -> str:
    return 'numba' if _use_numba() else 'python'

def _use_numba() -> bool:
    if _KERNEL_BACKEND == 'python':
        return False
    return _NUMBA_AVAILABLE

def _angle_deg_py(dx: int, dy: int) -> float:
    if dx == 0 and dy == 0:
        return -9999.0
    if dx < 0:
        ac = 180.0
    elif dy <= 0:
        ac = 0.0
    else:
        ac = 360.0
    if dx != 0:
        angle = -math.degrees(math.atan(float(dy) / float(dx)))
    elif dy > 0:
        angle = -90.0
    elif dy < 0:
        angle = 90.0
    else:
        angle = 0.0
    return angle + ac

def radiation_kernel_py(source_rows: np.ndarray, source_cols: np.ndarray, fire_vals: np.ndarray, wind_dirs: np.ndarray, rows: int, cols: int, grid_size: float, radtotal: np.ndarray, tmpr: np.ndarray, rad_rf: float, aes: float, emissivity: float, sconst: float) -> np.ndarray:
    pi = math.pi
    ambient_T4 = 293.15 ** 4
    n_sources = source_rows.shape[0]
    if n_sources == 0:
        return radtotal
    grid_size_f = float(grid_size)
    for s in range(n_sources):
        si = int(source_rows[s])
        sj = int(source_cols[s])
        temp_idx = int(fire_vals[s])
        if temp_idx < 1 or temp_idx > tmpr.shape[0]:
            if rad_rf != 1.0:
                radtotal *= rad_rf
            continue
        temp_K = float(tmpr[temp_idx - 1]) + 273.15
        radiant = emissivity * sconst * (temp_K ** 4 - ambient_T4)
        wd = float(wind_dirs[s])
        wd_lo = wd - 90.0
        wd_hi = wd + 90.0
        if rad_rf != 1.0:
            radtotal *= rad_rf
        for ii in range(rows):
            dy = ii - si
            for jj in range(cols):
                dx = jj - sj
                if dx == 0 and dy == 0:
                    continue
                rangle = _angle_deg_py(dx, dy)
                if rangle < wd_lo or rangle > wd_hi:
                    continue
                r2 = (grid_size_f * float(dx)) ** 2 + (grid_size_f * float(dy)) ** 2
                if r2 == 0.0:
                    continue
                val = aes / (pi * r2) * radiant
                if math.isnan(val) or math.isinf(val):
                    continue
                radtotal[ii, jj] += val
    return radtotal

def brand_transport_kernel_py(source_rows: np.ndarray, source_cols: np.ndarray, brand_counts: np.ndarray, rows: int, cols: int, grid_size: float, wind_s_2d: np.ndarray, wind_d_2d: np.ndarray, fb_wind_coef: float, fb_wind_sd: float, fb_wind_sd_transverse: float, min_count: int, rng: np.random.RandomState) -> np.ndarray:
    deg2rad = math.pi / 180.0
    grid_size_f = float(grid_size)
    out_idx = []
    out_counts = []
    for s in range(source_rows.shape[0]):
        si = int(source_rows[s])
        sj = int(source_cols[s])
        nb = int(brand_counts[s])
        if nb <= 0:
            continue
        ws = float(wind_s_2d[si, sj])
        wdeg = float(wind_d_2d[si, sj])
        wd_sin = math.sin(wdeg * deg2rad)
        wd_cos = math.cos(wdeg * deg2rad)
        mu_ln = math.log(fb_wind_coef * ws) if ws > 0 else -30.0
        forward_normals = rng.randn(nb)
        lateral_normals = rng.randn(nb)
        source_counts: dict[int, int] = {}
        for b in range(nb):
            dforward = math.exp(mu_ln + fb_wind_sd * forward_normals[b])
            dlateral = fb_wind_sd_transverse * lateral_normals[b]
            dispy = -dforward * wd_sin + dlateral * wd_cos
            dispx = dforward * wd_cos + dlateral * wd_sin
            s_dispy = 1.0 if dispy > 0 else -1.0 if dispy < 0 else 0.0
            s_dispx = 1.0 if dispx > 0 else -1.0 if dispx < 0 else 0.0
            ynum = int(dispy / grid_size_f + s_dispy)
            xnum = int(dispx / grid_size_f + s_dispx)
            dy = ynum + si
            dx = xnum + sj
            if dy < 0 or dy >= rows or dx < 0 or (dx >= cols):
                continue
            ind = dy * cols + dx
            source_counts[ind] = source_counts.get(ind, 0) + 1
        for ind in sorted(source_counts):
            count = source_counts[ind]
            if count >= min_count:
                out_idx.append(ind)
                out_counts.append(count)
    if not out_idx:
        return np.empty((0, 2), dtype=np.int64)
    out = np.empty((len(out_idx), 2), dtype=np.int64)
    out[:, 0] = np.asarray(out_idx, dtype=np.int64)
    out[:, 1] = np.asarray(out_counts, dtype=np.int64)
    return out

def max_brands_in_circle_py(points: np.ndarray, radius: float) -> int:
    n = points.shape[0]
    if n == 0:
        return 0
    r2 = radius * radius
    best = 0
    for i in range(n):
        xi = points[i, 0]
        yi = points[i, 1]
        cnt = 0
        for j in range(n):
            dx = points[j, 0] - xi
            dy = points[j, 1] - yi
            if dx * dx + dy * dy <= r2:
                cnt += 1
        if cnt > best:
            best = cnt
    return best
_NUMBA_AVAILABLE = False
try:
    import numba

    @numba.njit(cache=_NUMBA_CACHE)
    def _angle_deg_numba(dx: int, dy: int) -> float:
        if dx == 0 and dy == 0:
            return -9999.0
        if dx < 0:
            ac = 180.0
        elif dy <= 0:
            ac = 0.0
        else:
            ac = 360.0
        if dx != 0:
            angle = -math.degrees(math.atan(float(dy) / float(dx)))
        elif dy > 0:
            angle = -90.0
        elif dy < 0:
            angle = 90.0
        else:
            angle = 0.0
        return angle + ac

    @numba.njit(cache=_NUMBA_CACHE)
    def radiation_kernel_numba(source_rows: np.ndarray, source_cols: np.ndarray, fire_vals: np.ndarray, wind_dirs: np.ndarray, rows: int, cols: int, grid_size: float, radtotal: np.ndarray, tmpr: np.ndarray, rad_rf: float, aes: float, emissivity: float, sconst: float) -> np.ndarray:
        pi = math.pi
        ambient_T4 = 293.15 ** 4
        n_sources = source_rows.shape[0]
        if n_sources == 0:
            return radtotal
        grid_size_f = float(grid_size)
        for s in range(n_sources):
            si = int(source_rows[s])
            sj = int(source_cols[s])
            temp_idx = int(fire_vals[s])
            if temp_idx < 1 or temp_idx > tmpr.shape[0]:
                if rad_rf != 1.0:
                    radtotal *= rad_rf
                continue
            temp_K = float(tmpr[temp_idx - 1]) + 273.15
            radiant = emissivity * sconst * (temp_K ** 4 - ambient_T4)
            wd = float(wind_dirs[s])
            wd_lo = wd - 90.0
            wd_hi = wd + 90.0
            if rad_rf != 1.0:
                radtotal *= rad_rf
            for ii in range(rows):
                dy = ii - si
                for jj in range(cols):
                    dx = jj - sj
                    if dx == 0 and dy == 0:
                        continue
                    rangle = _angle_deg_numba(dx, dy)
                    if rangle < wd_lo or rangle > wd_hi:
                        continue
                    r2 = (grid_size_f * float(dx)) ** 2 + (grid_size_f * float(dy)) ** 2
                    if r2 == 0.0:
                        continue
                    val = aes / (pi * r2) * radiant
                    if math.isnan(val) or math.isinf(val):
                        continue
                    radtotal[ii, jj] += val
        return radtotal

    @numba.njit(cache=_NUMBA_CACHE)
    def brand_transport_kernel_numba(source_rows: np.ndarray, source_cols: np.ndarray, brand_counts: np.ndarray, rows: int, cols: int, grid_size: float, wind_s_2d: np.ndarray, wind_d_2d: np.ndarray, fb_wind_coef: float, fb_wind_sd: float, fb_wind_sd_transverse: float, min_count: int, randn_vec: np.ndarray) -> np.ndarray:
        deg2rad = math.pi / 180.0
        grid_size_f = float(grid_size)
        max_out = 0
        for s in range(source_rows.shape[0]):
            nb_tmp = int(brand_counts[s])
            if nb_tmp > 0:
                max_out += nb_tmp
        out_indices = np.empty(max_out, dtype=np.int64)
        out_counts = np.empty(max_out, dtype=np.int64)
        out_n = 0
        rand_idx = 0
        for s in range(source_rows.shape[0]):
            si = int(source_rows[s])
            sj = int(source_cols[s])
            nb = int(brand_counts[s])
            if nb <= 0:
                continue
            deposit_indices = np.empty(nb, dtype=np.int64)
            deposit_n = 0
            ws = float(wind_s_2d[si, sj])
            wdeg = float(wind_d_2d[si, sj])
            wd_sin = math.sin(wdeg * deg2rad)
            wd_cos = math.cos(wdeg * deg2rad)
            mu_ln = math.log(fb_wind_coef * ws) if ws > 0 else -30.0
            for b in range(nb):
                dforward = math.exp(mu_ln + fb_wind_sd * randn_vec[rand_idx + b])
                dlateral = fb_wind_sd_transverse * randn_vec[rand_idx + nb + b]
                dispy = -dforward * wd_sin + dlateral * wd_cos
                dispx = dforward * wd_cos + dlateral * wd_sin
                s_dispy = 1.0 if dispy > 0 else -1.0 if dispy < 0 else 0.0
                s_dispx = 1.0 if dispx > 0 else -1.0 if dispx < 0 else 0.0
                ynum = int(dispy / grid_size_f + s_dispy)
                xnum = int(dispx / grid_size_f + s_dispx)
                dy = ynum + si
                dx = xnum + sj
                if dy < 0 or dy >= rows or dx < 0 or (dx >= cols):
                    continue
                deposit_indices[deposit_n] = dy * cols + dx
                deposit_n += 1
            rand_idx += 2 * nb
            if deposit_n == 0:
                continue
            sorted_deposits = np.sort(deposit_indices[:deposit_n])
            current = sorted_deposits[0]
            count = 1
            for k in range(1, deposit_n):
                ind = sorted_deposits[k]
                if ind == current:
                    count += 1
                else:
                    if count >= min_count:
                        out_indices[out_n] = current
                        out_counts[out_n] = count
                        out_n += 1
                    current = ind
                    count = 1
            if count >= min_count:
                out_indices[out_n] = current
                out_counts[out_n] = count
                out_n += 1
        if out_n == 0:
            return np.empty((0, 2), dtype=np.int64)
        out = np.empty((out_n, 2), dtype=np.int64)
        for k in range(out_n):
            out[k, 0] = out_indices[k]
            out[k, 1] = out_counts[k]
        return out

    @numba.njit(cache=_NUMBA_CACHE)
    def max_brands_in_circle_numba(points: np.ndarray, radius: float) -> int:
        n = points.shape[0]
        if n == 0:
            return 0
        r2 = radius * radius
        best = 0
        for i in range(n):
            xi = points[i, 0]
            yi = points[i, 1]
            cnt = 0
            for j in range(n):
                dx = points[j, 0] - xi
                dy = points[j, 1] - yi
                if dx * dx + dy * dy <= r2:
                    cnt += 1
            if cnt > best:
                best = cnt
        return best
    _NUMBA_AVAILABLE = True
except Exception:
    # Frozen apps can fail Numba initialization before the UI starts; use Python kernels instead.
    pass

def radiation_kernel(source_rows: np.ndarray, source_cols: np.ndarray, fire_vals: np.ndarray, wind_dirs: np.ndarray, rows: int, cols: int, grid_size: float, radtotal: np.ndarray, tmpr: np.ndarray, rad_rf: float, aes: float, emissivity: float, sconst: float) -> np.ndarray:
    if _use_numba():
        return radiation_kernel_numba(source_rows, source_cols, fire_vals, wind_dirs, rows, cols, grid_size, radtotal, tmpr, rad_rf, aes, emissivity, sconst)
    return radiation_kernel_py(source_rows, source_cols, fire_vals, wind_dirs, rows, cols, grid_size, radtotal, tmpr, rad_rf, aes, emissivity, sconst)

def brand_transport_kernel(source_rows: np.ndarray, source_cols: np.ndarray, brand_counts: np.ndarray, rows: int, cols: int, grid_size: float, wind_s_2d: np.ndarray, wind_d_2d: np.ndarray, fb_wind_coef: float, fb_wind_sd: float, fb_wind_sd_transverse: float, min_count: int, rng: np.random.RandomState) -> np.ndarray:
    if _use_numba():
        total_brands = int(np.sum(brand_counts))
        if total_brands <= 0:
            return np.empty((0, 2), dtype=np.int64)
        randn_vec = np.ascontiguousarray(rng.randn(total_brands * 2), dtype=np.float64)
        return brand_transport_kernel_numba(source_rows, source_cols, brand_counts, rows, cols, grid_size, wind_s_2d, wind_d_2d, fb_wind_coef, fb_wind_sd, fb_wind_sd_transverse, min_count, randn_vec)
    return brand_transport_kernel_py(source_rows, source_cols, brand_counts, rows, cols, grid_size, wind_s_2d, wind_d_2d, fb_wind_coef, fb_wind_sd, fb_wind_sd_transverse, min_count, rng)

def max_brands_in_circle(points: np.ndarray, radius: float) -> int:
    if points.size == 0:
        return 0
    pts = np.ascontiguousarray(points, dtype=np.float64)
    if _use_numba():
        return max_brands_in_circle_numba(pts, radius)
    return max_brands_in_circle_py(pts, radius)
