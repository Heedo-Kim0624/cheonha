"""
BLE RSSI 기반 3-State 분류기 (In Vehicle / Searching / Delivering).

ALGORITHM/ble.py 의 핵심:
- preprocess_data (1Hz 리샘플 · 보간 · smoothing)
- detect_in_vehicle (Enhanced 2-state HMM + Viterbi)
- find_sr_dl_boundary (SR→DL 전환점 휴리스틱)

v8.2.5 ML 모델(pickle) 로드는 sklearn 버전 의존성이 강해 서비스에선 제외,
heuristic 전환점 탐지만 사용.
"""
from typing import List, Tuple, Dict
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import norm


STATE_IV = 'IV'
STATE_SR = 'SR'
STATE_DL = 'DL'


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def _segment_list(states: np.ndarray) -> List[Tuple[int, int, int]]:
    seg = []
    n = len(states)
    i = 0
    while i < n:
        s = i
        val = int(states[i])
        while i < n and states[i] == val:
            i += 1
        seg.append((val, s, i))
    return seg


def _postprocess_min_duration(states: np.ndarray, min_len: int = 5) -> np.ndarray:
    z = states.copy()
    for _, s, e in _segment_list(z):
        if e - s >= min_len:
            continue
        left = z[s - 1] if s > 0 else None
        right = z[e] if e < len(z) else None
        if left is None and right is None:
            continue
        if left is None:
            z[s:e] = right
        elif right is None:
            z[s:e] = left
        else:
            ll = 0; i = s - 1
            while i >= 0 and z[i] == left:
                ll += 1; i -= 1
            rl = 0; i = e
            while i < len(z) and z[i] == right:
                rl += 1; i += 1
            z[s:e] = left if ll >= rl else right
    return z


def _viterbi_log(log_emission: np.ndarray,
                 log_trans: np.ndarray,
                 log_start: np.ndarray) -> np.ndarray:
    T, K = log_emission.shape
    dp = np.full((T, K), -np.inf)
    ptr = np.zeros((T, K), dtype=int)
    dp[0] = log_start + log_emission[0]
    for t in range(1, T):
        prev = dp[t - 1][:, None] + log_trans
        ptr[t] = np.argmax(prev, axis=0)
        dp[t] = prev[ptr[t], np.arange(K)] + log_emission[t]
    z = np.zeros(T, dtype=int)
    z[-1] = int(np.argmax(dp[-1]))
    for t in range(T - 2, -1, -1):
        z[t] = ptr[t + 1, z[t + 1]]
    return z


# ---------------------------------------------------------------------------
# 1Hz 리샘플링 + smoothing
# ---------------------------------------------------------------------------
def preprocess_ble(ble_time_rssi: pd.DataFrame,
                   interp_limit: int = 5,
                   fill_value: float = -100.0,
                   smooth_win: int = 7) -> pd.DataFrame:
    """
    ble_time_rssi: DataFrame with columns [time, rssi]  (time 은 datetime, rssi 는 정수/NaN)
    반환: 1Hz 인덱스된 DataFrame(rssi, smooth, rolling_std, obs_code)
    """
    df = ble_time_rssi.copy()
    df['time'] = pd.to_datetime(df['time'])
    df = df.sort_values('time').dropna(subset=['rssi'])
    if df.empty:
        return pd.DataFrame(columns=['rssi', 'smooth', 'rolling_std', 'obs_code'])

    r = df.set_index('time')['rssi']
    sec = r.resample('1s').agg(['mean', 'count'])
    rssi = sec['mean']
    obs_count = sec['count'].fillna(0)

    obs_code = pd.Series(np.where(obs_count > 0, 2, 0), index=sec.index)
    rssi_i = rssi.interpolate(limit=interp_limit)
    interpolated = rssi.isna() & rssi_i.notna()
    obs_code.loc[interpolated] = 1
    rssi_f = rssi_i.fillna(fill_value)

    smooth = rssi_f.rolling(smooth_win, center=False, min_periods=1).median()
    rolling_std = rssi_f.rolling(15, center=True, min_periods=1).std().fillna(3.0)

    return pd.DataFrame({
        'rssi': rssi_f,
        'smooth': smooth,
        'rolling_std': rolling_std,
        'obs_code': obs_code.astype(int),
    })


# ---------------------------------------------------------------------------
# In-Vehicle 탐지 (2-state HMM)
# ---------------------------------------------------------------------------
def detect_in_vehicle(ble1hz: pd.DataFrame) -> np.ndarray:
    """
    ble1hz: preprocess_ble 결과 (rssi, smooth, rolling_std, obs_code).
    반환: z[] — 0(In Vehicle) / 1(Out-of-vehicle=Cycle) 배열
    """
    rssi = ble1hz['rssi'].values
    obs_code = ble1hz['obs_code'].values
    obs_std = ble1hz['rolling_std'].values
    n = len(rssi)
    if n < 10:
        return np.zeros(n, dtype=int)

    observed = rssi[(rssi > -99) & (obs_code >= 1)]
    if len(observed) < 10:
        observed = rssi[rssi > -99]
    if len(observed) < 10:
        observed = rssi

    p90 = np.percentile(observed, 90)
    p77 = np.percentile(observed, 77)
    p75 = np.percentile(observed, 75)
    p50 = np.percentile(observed, 50)
    p25 = np.percentile(observed, 25)
    p10 = np.percentile(observed, 10)

    mu_iv = (p90 + p75) / 2
    mu_cy = (p25 + p10) / 2
    scale_iv = 5.5 + 0.15 * obs_std
    scale_cy = 11 + 0.15 * obs_std

    context = pd.Series(rssi).rolling(35, center=True, min_periods=1).mean().values

    log_p_iv_rssi = norm.logpdf(rssi, loc=mu_iv, scale=scale_iv)
    log_p_cy_rssi = norm.logpdf(rssi, loc=mu_cy, scale=scale_cy)
    log_p_iv_ctx = norm.logpdf(context, loc=mu_iv, scale=scale_iv * 2.0)
    log_p_cy_ctx = norm.logpdf(context, loc=mu_cy, scale=scale_cy * 2.0)

    log_p_iv = 0.45 * log_p_iv_rssi + 0.55 * log_p_iv_ctx
    log_p_cy = 0.45 * log_p_cy_rssi + 0.55 * log_p_cy_ctx

    high_mask = rssi >= p77
    log_p_iv[high_mask] += 5.0
    log_p_cy[high_mask] -= 10.0

    near_mask = (rssi >= p77 - 5) & (rssi < p77)
    log_p_iv[near_mask] += 2.0
    log_p_cy[near_mask] -= 3.0

    miss = obs_code == 0
    log_p_iv[miss] *= 0.5
    log_p_cy[miss] *= 0.5

    log_p_iv = np.clip(log_p_iv, -500.0, 0)
    log_p_cy = np.clip(log_p_cy, -500.0, 0)

    log_em = np.column_stack([log_p_iv, log_p_cy])
    A = np.array([[0.9995, 0.0005], [0.002, 0.998]])
    z = _viterbi_log(log_em, np.log(A), np.log(np.array([0.98, 0.02])))

    # IV-high 보정
    iv_high_regions = []
    for val, s, e in _segment_list(z):
        if val == 0:
            seg = rssi[s:e]
            high_cnt = np.sum(seg >= p50)
            if high_cnt >= (e - s) * 0.5 and high_cnt >= 5:
                iv_high_regions.append((s, e))

    z = _postprocess_min_duration(z, min_len=22)

    # 짧고 얕은 이탈은 IV 로 환원
    for val, s, e in _segment_list(z):
        if val == 1:
            seg_mean = float(np.mean(rssi[s:e]))
            entry_rssi = float(np.mean(rssi[max(0, s - 10):s])) if s > 0 else seg_mean
            exit_rssi = float(np.mean(rssi[e:min(n, e + 10)])) if e < n else seg_mean
            entry_drop = entry_rssi - seg_mean
            exit_rise = exit_rssi - seg_mean
            if (entry_drop < 10 and exit_rise < 10) or \
               (seg_mean > -68) or \
               (seg_mean > -72 and entry_drop < 22):
                z[s:e] = 0

    z = _postprocess_min_duration(z, min_len=22)
    for rs, re_ in iv_high_regions:
        z[rs:re_] = 0

    # 긴 낮은 IV 는 cycle 로 재분류
    for val, s, e in _segment_list(z):
        if val == 0:
            seg = rssi[s:e]
            low_cnt = np.sum(seg <= p25)
            if low_cnt >= (e - s) * 0.5:
                z[s:e] = 1

    return z


# ---------------------------------------------------------------------------
# SR → DL 경계 (heuristic)
# ---------------------------------------------------------------------------
def find_sr_dl_boundary(cycle_rssi: np.ndarray,
                        min_sr: int = 3, min_dl: int = 3) -> int:
    T = len(cycle_rssi)
    if T < min_sr + min_dl:
        return min_sr

    if T >= 7:
        win_len = min(11, T if T % 2 == 1 else T - 1)
        smoothed = savgol_filter(cycle_rssi, win_len, min(2, win_len - 1))
    else:
        smoothed = cycle_rssi.copy()

    init_window = min(20, T)
    sr_init = float(np.percentile(smoothed[:init_window], 80))
    min_val = float(np.min(smoothed))
    min_idx = int(np.argmin(smoothed))
    drop_diff = sr_init - min_val

    if T < 50:
        expected = 0.30
    elif T < 100:
        expected = 0.22
    elif T < 200:
        expected = 0.15
    else:
        expected = 0.11
    expected_sr_len = max(min_sr, int(T * expected))

    if drop_diff < 5:
        for t in range(max(min_sr, min_idx), T - min_dl):
            if smoothed[t] > min_val + 2:
                return t
        return max(min_sr, min(expected_sr_len, min_idx, T - min_dl))

    deriv = np.diff(smoothed)
    cliff_threshold = -max(4.0, drop_diff * 0.15)

    search_s = max(min_sr, expected_sr_len // 2)
    search_e = min(expected_sr_len + 5, min_idx, T - min_dl - 1)

    cliff = None
    for t in range(search_s, max(search_s + 1, search_e)):
        if t + 3 < T:
            if np.mean(deriv[t:t + 3]) < cliff_threshold:
                persistence = min(8, T - t - min_dl)
                if persistence >= 4:
                    pre = float(np.mean(smoothed[max(0, t - 4):t]))
                    post = smoothed[t + 2:t + 2 + persistence]
                    if len(post) and np.max(post) < pre - drop_diff * 0.25:
                        cliff = t
                        break
    if cliff is not None:
        return max(min_sr, cliff)

    threshold = sr_init - drop_diff * 0.35
    search_s = max(min_sr, expected_sr_len * 2 // 3)
    search_e = min(expected_sr_len * 3, min_idx + 10, T - min_dl)
    tr = None
    for t in range(search_s, max(search_s + 1, search_e)):
        if smoothed[t] < threshold:
            persistence = min(6, T - t - min_dl)
            if persistence >= 3:
                post = smoothed[t:t + persistence]
                if len(post) and np.max(post) < threshold + drop_diff * 0.15:
                    tr = t
                    break

    sr_len = tr if tr is not None else expected_sr_len
    return max(min_sr, min(sr_len, T - min_dl))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def classify_three_states(ble_time_rssi: pd.DataFrame) -> pd.DataFrame:
    """
    BLE 시계열(time, rssi)을 입력받아 1Hz 기준 3-state 를 분류한다.

    반환: 1Hz DataFrame[index=time, state ('IV'/'SR'/'DL'), cycle_id (0 or ≥1)]
    """
    pre = preprocess_ble(ble_time_rssi)
    if pre.empty:
        return pd.DataFrame(columns=['state', 'cycle_id'])

    z = detect_in_vehicle(pre)
    states = np.array([STATE_IV] * len(z), dtype=object)
    cycle_ids = np.zeros(len(z), dtype=int)

    cycle_no = 0
    for val, s, e in _segment_list(z):
        if val == 0:
            continue  # In Vehicle
        cycle_no += 1
        cycle_ids[s:e] = cycle_no
        cycle_rssi = pre['smooth'].values[s:e]
        sr_len = find_sr_dl_boundary(cycle_rssi)
        states[s:s + sr_len] = STATE_SR
        states[s + sr_len:e] = STATE_DL

    out = pd.DataFrame({
        'state': states,
        'cycle_id': cycle_ids,
    }, index=pre.index)
    return out
