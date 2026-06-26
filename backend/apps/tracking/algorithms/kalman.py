"""
Robust Adaptive Kalman Filter + RTS Smoother for GPS track cleaning.

ALGORITHM/kalman_filter.py 의 _rule_based_outlier_mask_track 과
_robust_adaptive_kf_rts_track 로직을 그대로 살려 모듈로 정리한 버전.
(원본 파일은 최상위 def 시그니처가 잘려 파이썬 파싱이 안 되어 재구성)

입력: lat, lon, t_sec (unix epoch sec), accuracy_m, speed_kmh (모두 numpy array)
출력: (filtered_lat, filtered_lon) numpy array
"""
import math
import numpy as np

EARTH_R = 6378137.0


def _haversine_m(lat1, lon1, lat2, lon2):
    lat1 = np.asarray(lat1, dtype=float)
    lon1 = np.asarray(lon1, dtype=float)
    lat2 = np.asarray(lat2, dtype=float)
    lon2 = np.asarray(lon2, dtype=float)
    with np.errstate(invalid='ignore'):
        p1 = np.deg2rad(lat1)
        p2 = np.deg2rad(lat2)
        dp = np.deg2rad(lat2 - lat1)
        dl = np.deg2rad(lon2 - lon1)
        a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
        a = np.clip(a, 0.0, 1.0)
        return 2 * EARTH_R * np.arcsin(np.sqrt(a))


def _latlon_to_local_m(lat, lon, lat0, lon0):
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    lat_rad = np.deg2rad(lat)
    lon_rad = np.deg2rad(lon)
    lat0_rad = math.radians(float(lat0))
    lon0_rad = math.radians(float(lon0))
    x = EARTH_R * (lon_rad - lon0_rad) * math.cos(lat0_rad)
    y = EARTH_R * (lat_rad - lat0_rad)
    return x, y


def _local_m_to_latlon(x, y, lat0, lon0):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    lat0_rad = math.radians(float(lat0))
    lon0_rad = math.radians(float(lon0))
    lat = np.rad2deg(y / EARTH_R + lat0_rad)
    lon = np.rad2deg(x / (EARTH_R * math.cos(lat0_rad)) + lon0_rad)
    return lat, lon


def _make_spd(M, jitter=1e-12, max_tries=5):
    M = 0.5 * (M + M.T)
    for i in range(max_tries):
        try:
            np.linalg.cholesky(M)
            return M
        except np.linalg.LinAlgError:
            M = M + (jitter * (10 ** i)) * np.eye(M.shape[0])
    vals, vecs = np.linalg.eigh(M)
    vals = np.clip(vals, jitter, None)
    return (vecs * vals) @ vecs.T


def _inv2x2(A):
    a, b = A[0, 0], A[0, 1]
    c, d = A[1, 0], A[1, 1]
    det = a * d - b * c
    if abs(det) < 1e-18 or not np.isfinite(det):
        return np.linalg.pinv(A)
    inv_det = 1.0 / det
    return np.array([[d, -b], [-c, a]], dtype=float) * inv_det


def _find_first_valid(lat, lon):
    mask = np.isfinite(lat) & np.isfinite(lon)
    if not np.any(mask):
        return None, None
    i = int(np.argmax(mask))
    return float(lat[i]), float(lon[i])


# ---------------------------------------------------------------------------
# 1) 규칙 기반 outlier mask
# ---------------------------------------------------------------------------
def rule_based_outlier_mask(lat, lon, t_sec, speed_kmh=None, acc_m=None,
                            v_max_kmh=180.0, v_soft_kmh=130.0, dt_small_s=10.0,
                            min_dist_m=30.0, acc_bad_m=60.0,
                            spike_skip_vmax_kmh=90.0, spike_dsmall_m=50.0,
                            passes=3):
    n = len(lat)
    lat0 = np.asarray(lat, dtype=float).copy()
    lon0 = np.asarray(lon, dtype=float).copy()
    t0 = np.asarray(t_sec, dtype=float).copy()

    v_dev = np.full(n, np.nan) if speed_kmh is None else np.asarray(speed_kmh, dtype=float) / 3.6
    acc = np.full(n, np.nan) if acc_m is None else np.asarray(acc_m, dtype=float)

    bad = np.zeros(n, dtype=bool)
    v_max = v_max_kmh / 3.6
    v_soft = v_soft_kmh / 3.6
    spike_vmax = spike_skip_vmax_kmh / 3.6

    for _ in range(max(1, int(passes))):
        latw = lat0.copy()
        lonw = lon0.copy()
        latw[bad] = np.nan
        lonw[bad] = np.nan

        lat_prev = np.roll(latw, 1); lon_prev = np.roll(lonw, 1); t_prev = np.roll(t0, 1)
        lat_prev[0] = np.nan; lon_prev[0] = np.nan; t_prev[0] = np.nan

        dt = t0 - t_prev
        dist = _haversine_m(lat_prev, lon_prev, latw, lonw)
        with np.errstate(invalid='ignore', divide='ignore'):
            speed = np.where(np.isfinite(dt) & (dt > 0), dist / dt, np.nan)

        seg_bad_hard = ((dt > 0) & np.isfinite(speed) & np.isfinite(dist) &
                        (dist >= min_dist_m) & (speed > v_max))
        seg_bad_soft = ((dt > 0) & (dt <= dt_small_s) & np.isfinite(speed) & np.isfinite(dist) &
                        (dist >= min_dist_m) & (speed > v_soft) &
                        ((np.isfinite(v_dev) & (v_dev < 10 / 3.6)) |
                         (np.isfinite(acc) & (acc >= acc_bad_m))))
        bad |= (seg_bad_hard | seg_bad_soft)

        lat_next = np.roll(latw, -1); lon_next = np.roll(lonw, -1); t_next = np.roll(t0, -1)
        lat_next[-1] = np.nan; lon_next[-1] = np.nan; t_next[-1] = np.nan

        dt2 = t_next - t0
        dist2 = _haversine_m(latw, lonw, lat_next, lon_next)
        with np.errstate(invalid='ignore', divide='ignore'):
            speed2 = np.where(np.isfinite(dt2) & (dt2 > 0), dist2 / dt2, np.nan)

        dt_skip = t_next - t_prev
        dist_skip = _haversine_m(lat_prev, lon_prev, lat_next, lon_next)
        with np.errstate(invalid='ignore', divide='ignore'):
            speed_skip = np.where(np.isfinite(dt_skip) & (dt_skip > 0), dist_skip / dt_skip, np.nan)

        spike = (np.isfinite(speed) & np.isfinite(speed2) & np.isfinite(speed_skip) &
                 (speed > v_max) & (speed2 > v_max) &
                 (speed_skip <= spike_vmax) & (dist_skip <= spike_dsmall_m))
        bad |= spike

    return bad


# ---------------------------------------------------------------------------
# 2) Robust Adaptive Kalman Filter + RTS Smoother
# ---------------------------------------------------------------------------
def robust_adaptive_kf_rts(lat, lon, t_sec, acc_m=None, speed_kmh=None,
                           bad_mask=None, nu=5.0, sigma_a=1.8,
                           meas_floor_m=3.0, meas_ceiling_m=100.0,
                           r_adapt_rate=0.01, q_adapt_rate=0.02,
                           max_dt=30.0, smoother=True):
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    t_sec = np.asarray(t_sec, dtype=float)
    n = len(lat)

    meas_ok = np.isfinite(lat) & np.isfinite(lon)
    if not np.any(meas_ok):
        return np.full(n, np.nan), np.full(n, np.nan)

    lat0, lon0 = _find_first_valid(lat, lon)
    x_meas = np.full(n, np.nan); y_meas = np.full(n, np.nan)
    xm, ym = _latlon_to_local_m(lat[meas_ok], lon[meas_ok], lat0, lon0)
    x_meas[meas_ok] = xm
    y_meas[meas_ok] = ym

    has_meas = np.isfinite(x_meas) & np.isfinite(y_meas)
    first_meas = int(np.argmax(has_meas))

    dt_raw = np.full(n, np.nan)
    dt_raw[1:] = t_sec[1:] - t_sec[:-1]
    pos = dt_raw[np.isfinite(dt_raw) & (dt_raw > 0)]
    dt_default = float(np.median(pos)) if len(pos) else 1.0
    dt_default = float(np.clip(dt_default, 0.1, max(0.1, max_dt)))

    if acc_m is not None:
        acc = np.asarray(acc_m, dtype=float)
        sigma_m = np.where(np.isfinite(acc) & (acc > 0), acc, meas_floor_m)
        sigma_m = np.clip(sigma_m, meas_floor_m, meas_ceiling_m)
    else:
        sigma_m = np.full(n, float(meas_floor_m))

    spd_mps = None
    if speed_kmh is not None:
        spd = np.asarray(speed_kmh, dtype=float)
        spd_mps = np.where(np.isfinite(spd), spd / 3.6, np.nan)

    if bad_mask is not None:
        bad_mask = np.asarray(bad_mask, dtype=bool)
        if bad_mask.shape[0] != n:
            bad_mask = None

    x_filt = np.full((n, 4), np.nan)
    P_filt = np.full((n, 4, 4), np.nan)
    x_pred = np.full((n, 4), np.nan)
    P_pred = np.full((n, 4, 4), np.nan)
    F_store = np.full((n, 4, 4), np.nan)
    I4 = np.eye(4)

    xk = np.array([x_meas[first_meas], y_meas[first_meas], 0.0, 0.0])
    p_pos = float(max(sigma_m[first_meas], meas_floor_m)) ** 2
    Pk = _make_spd(np.diag([p_pos, p_pos, 25.0 ** 2, 25.0 ** 2]))

    r_scale = q_scale = 1.0
    m_dim = 2.0
    good_acc_m = max(10.0, 2.0 * meas_floor_m)
    outlier_acc_m = min(meas_ceiling_m, max(60.0, 0.6 * meas_ceiling_m))
    nis_maneuver_thresh = 6.0
    max_fade_normal = 6.0
    max_fade_maneuver = 25.0
    zupt_speed_thresh = 0.7
    zupt_min_streak = 2
    zupt_streak = 0

    F_store[first_meas] = I4.copy()
    x_pred[first_meas] = xk; P_pred[first_meas] = Pk
    x_filt[first_meas] = xk; P_filt[first_meas] = Pk

    def _build_F_Q(dtk, q_var):
        dt2 = dtk * dtk; dt3 = dt2 * dtk
        F = np.array([[1, 0, dtk, 0], [0, 1, 0, dtk], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=float)
        Q = q_var * np.array([
            [dt3 / 3, 0, dt2 / 2, 0],
            [0, dt3 / 3, 0, dt2 / 2],
            [dt2 / 2, 0, dtk, 0],
            [0, dt2 / 2, 0, dtk],
        ], dtype=float)
        return F, Q

    def _kalman_update_pos(xp, Pp, z, R_eff):
        e = z - xp[:2]
        S = _make_spd(Pp[:2, :2] + R_eff)
        Sinv = _inv2x2(S)
        K = Pp[:, :2] @ Sinv
        x_new = xp + K @ e
        I_KH = I4.copy(); I_KH[:, :2] -= K
        P_new = _make_spd(I_KH @ Pp @ I_KH.T + K @ R_eff @ K.T)
        return x_new, P_new

    def _kalman_update_vel_zupt(xp, Pp, sigma_v):
        z = np.array([0.0, 0.0])
        e = z - xp[2:4]
        Rv = np.diag([sigma_v ** 2, sigma_v ** 2])
        Sv = _make_spd(Pp[2:4, 2:4] + Rv)
        Svinv = _inv2x2(Sv)
        K = Pp[:, 2:4] @ Svinv
        x_new = xp + K @ e
        I_KH = I4.copy(); I_KH[:, 2:4] -= K
        P_new = _make_spd(I_KH @ Pp @ I_KH.T + K @ Rv @ K.T)
        return x_new, P_new

    for k in range(first_meas + 1, n):
        dtk = float(dt_raw[k]) if (np.isfinite(dt_raw[k]) and dt_raw[k] > 0) else dt_default
        dtk = max(0.0, dtk)
        q_var = (sigma_a ** 2) * q_scale
        xkp, Pkp = xk.copy(), Pk.copy()
        F_total = I4.copy()
        rem = dtk

        if rem > 0:
            while rem > max_dt:
                F, Q = _build_F_Q(max_dt, q_var)
                xkp = F @ xkp; Pkp = _make_spd(F @ Pkp @ F.T + Q)
                F_total = F @ F_total
                rem -= max_dt
            if rem > 0:
                F, Q = _build_F_Q(rem, q_var)
                xkp = F @ xkp; Pkp = _make_spd(F @ Pkp @ F.T + Q)
                F_total = F @ F_total

        F_store[k] = F_total
        x_pred[k] = xkp; P_pred[k] = Pkp
        x_new, P_new = xkp, Pkp

        if has_meas[k]:
            z = np.array([x_meas[k], y_meas[k]])
            sig2 = float(sigma_m[k] ** 2)
            R_base = (sig2 * r_scale) * np.eye(2)
            R_base = np.diag(np.clip(np.diag(R_base),
                                     meas_floor_m ** 2, meas_ceiling_m ** 2))

            S_base = _make_spd(Pkp[:2, :2] + R_base)
            Sinv_base = _inv2x2(S_base)
            e_base = z - xkp[:2]
            NIS = float(e_base.T @ Sinv_base @ e_base)
            nis_per = float(NIS / m_dim)

            outlier_hint = False
            if bad_mask is not None and bool(bad_mask[k]):
                outlier_hint = True
            if sigma_m[k] >= outlier_acc_m:
                outlier_hint = True

            maneuver_hint = ((not outlier_hint) and
                             (sigma_m[k] <= good_acc_m) and
                             (nis_per > nis_maneuver_thresh))

            if outlier_hint:
                w = (nu + m_dim) / (nu + max(NIS, 1e-12))
                w = float(np.clip(w, 0.02, 5.0))
                R_eff = R_base / w
                if (w < 0.08) and (sigma_m[k] >= outlier_acc_m):
                    x_new, P_new = xkp, Pkp
                else:
                    x_new, P_new = _kalman_update_pos(xkp, Pkp, z, R_eff)
            else:
                R_eff = R_base
                fade = (float(np.clip(nis_per, 1.0, max_fade_maneuver))
                        if maneuver_hint else float(np.clip(nis_per, 1.0, max_fade_normal)))
                P_tmp = Pkp if fade <= 1.0 else _make_spd(Pkp * fade)
                x_new, P_new = _kalman_update_pos(xkp, P_tmp, z, R_eff)

            desired_r = 1.0 if maneuver_hint else float(np.clip(nis_per, 0.25, 16.0))
            rate_up = float(np.clip(r_adapt_rate, 0.0, 1.0))
            rate_down = float(np.clip(max(0.05, 5.0 * r_adapt_rate), 0.0, 0.2))
            log_r = math.log(max(r_scale, 1e-6))
            log_r = ((1 - rate_up) * log_r + rate_up * math.log(desired_r)
                     if desired_r > r_scale
                     else (1 - rate_down) * log_r + rate_down * math.log(desired_r))
            r_scale = float(np.clip(math.exp(log_r), 0.5, 50.0))
            if sigma_m[k] <= good_acc_m:
                r_scale = min(r_scale, 4.0)

            log_q = math.log(max(q_scale, 1e-6))
            if maneuver_hint:
                desired_q = float(np.clip(nis_per, 0.5, 20.0))
                q_rate = max(q_adapt_rate, 0.05)
                log_q = (1 - q_rate) * log_q + q_rate * math.log(desired_q)
            else:
                relax = min(q_adapt_rate, 0.02)
                log_q = (1 - relax) * log_q + relax * math.log(1.0)
            q_scale = float(np.clip(math.exp(log_q), 1e-3, 1e3))

        if spd_mps is not None and np.isfinite(spd_mps[k]):
            if spd_mps[k] <= zupt_speed_thresh:
                zupt_streak += 1
            else:
                zupt_streak = 0
            if zupt_streak >= zupt_min_streak:
                sigma_v = max(0.3, 0.5 * spd_mps[k] + 0.1)
                x_new, P_new = _kalman_update_vel_zupt(x_new, P_new, sigma_v)

        xk, Pk = x_new, P_new
        x_filt[k] = xk; P_filt[k] = Pk

    # RTS smoother
    x_sm = x_filt.copy()
    break_before = np.zeros(n, dtype=bool)
    break_before[:first_meas + 1] = True
    gap_break_s = max(2.0 * max_dt, 6.0 * dt_default, 60.0)
    missing_run = poor_run = 0

    for k in range(first_meas + 1, n):
        dtk = float(dt_raw[k]) if (np.isfinite(dt_raw[k]) and dt_raw[k] > 0) else dt_default
        if not has_meas[k]:
            missing_run += 1
        else:
            if missing_run >= 5:
                break_before[k] = True
            missing_run = 0
        poor_now = ((not has_meas[k]) or (sigma_m[k] >= outlier_acc_m) or
                    (bad_mask is not None and bool(bad_mask[k])))
        if poor_now:
            poor_run += 1
        else:
            if poor_run >= 8:
                break_before[k] = True
            poor_run = 0
        if dtk > gap_break_s:
            break_before[k] = True

    if smoother and n >= 2:
        for k in range(n - 2, first_meas - 1, -1):
            if break_before[k + 1]:
                continue
            Fk1 = F_store[k + 1]; Pp1 = P_pred[k + 1]; Pfk = P_filt[k]
            if (not np.isfinite(Fk1).all()) or (not np.isfinite(Pp1).all()) or (not np.isfinite(Pfk).all()):
                continue
            try:
                Ck = np.linalg.solve(Pp1.T, (Pfk @ Fk1.T).T).T
            except np.linalg.LinAlgError:
                Ck = (Pfk @ Fk1.T) @ np.linalg.pinv(Pp1)
            x_sm[k] = x_filt[k] + Ck @ (x_sm[k + 1] - x_pred[k + 1])

    # Filter / Smoother blend
    sigma_blend_lo = max(5.0, 1.5 * meas_floor_m)
    sigma_blend_hi = max(25.0, 0.6 * meas_ceiling_m)
    x_out = x_filt.copy()
    for k in range(first_meas, n):
        if not np.isfinite(x_filt[k]).all():
            continue
        if not has_meas[k]:
            alpha = 1.0
        else:
            s = float(sigma_m[k])
            alpha = (0.5 if sigma_blend_hi <= sigma_blend_lo
                     else float(np.clip((s - sigma_blend_lo) /
                                        (sigma_blend_hi - sigma_blend_lo), 0.0, 1.0)))
        if np.isfinite(x_sm[k]).all():
            x_out[k] = (1.0 - alpha) * x_filt[k] + alpha * x_sm[k]

    lat_out, lon_out = _local_m_to_latlon(x_out[:, 0], x_out[:, 1], lat0, lon0)
    lat_out[:first_meas] = np.nan
    lon_out[:first_meas] = np.nan
    return lat_out, lon_out


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def smooth_gps_track(lat, lon, t_sec, accuracy_m=None, speed_kmh=None):
    """
    규칙 기반 outlier 제거 → Robust adaptive KF + RTS smoother.
    반환: (filtered_lat, filtered_lon) — 원본과 같은 길이, NaN 일 수 있음.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    t_sec = np.asarray(t_sec, dtype=float)

    bad = rule_based_outlier_mask(
        lat, lon, t_sec, speed_kmh=speed_kmh, acc_m=accuracy_m,
    )
    lat_in = lat.copy()
    lon_in = lon.copy()
    if accuracy_m is not None:
        acc_in = np.asarray(accuracy_m, dtype=float).copy()
        acc_in[bad] = np.maximum(acc_in[bad], 200.0)
    else:
        acc_in = None
        lat_in[bad] = np.nan
        lon_in[bad] = np.nan

    return robust_adaptive_kf_rts(
        lat_in, lon_in, t_sec,
        acc_m=acc_in, speed_kmh=speed_kmh, bad_mask=bad,
    )
