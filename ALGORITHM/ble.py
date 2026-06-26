# -*- coding: utf-8 -*-
"""
BLE 단일 파일 분석기 - 단계별 시간 추출
ble_cycle_detector.py를 복제하여 독립 실행 가능한 단일 코드
"""

import pandas as pd
import numpy as np
from scipy.signal import savgol_filter
from scipy.stats import norm
from scipy.ndimage import gaussian_filter1d
from typing import List, Tuple, Dict, Optional, Union
import pickle
import os
import sys

# ============================================
# 상수 정의
# ============================================
STATE_IN_VEHICLE = 0
STATE_SEARCHING = 1
STATE_DELIVERING = 2

STATE_NAMES = {
    STATE_IN_VEHICLE: "In Vehicle",
    STATE_SEARCHING: "Searching",
    STATE_DELIVERING: "Delivering"
}

STATE_MAP = {"In Vehicle": 0, "Searching": 1, "Delivering": 2}


# ============================================
# 유틸리티 함수
# ============================================

def segment_list(states: np.ndarray) -> List[Tuple[int, int, int]]:
    """상태 시퀀스를 세그먼트 리스트로 변환: [(state, start, end), ...]"""
    seg = []
    n = len(states)
    i = 0
    while i < n:
        s = i
        state_val = int(states[i])
        while i < n and states[i] == state_val:
            i += 1
        seg.append((state_val, s, i))
    return seg


def postprocess_min_duration(states: np.ndarray, min_len: int = 5) -> np.ndarray:
    """너무 짧은 세그먼트를 이웃 상태로 병합"""
    z = states.copy()
    segs = segment_list(z)
    for _, s, e in segs:
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
            left_len = 0
            i = s - 1
            while i >= 0 and z[i] == left:
                left_len += 1
                i -= 1
            right_len = 0
            i = e
            while i < len(z) and z[i] == right:
                right_len += 1
                i += 1
            z[s:e] = left if left_len >= right_len else right
    return z


def viterbi_log(log_emission: np.ndarray, log_trans: np.ndarray, log_start: np.ndarray) -> np.ndarray:
    """Viterbi 알고리즘 (log domain)"""
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


# ============================================
# 전처리 함수
# ============================================

def preprocess_data(
    csv_path_or_df: Union[str, pd.DataFrame],
    interp_limit: int = 5,
    fill_value: float = -100.0,
    smooth_win: int = 7,
) -> pd.DataFrame:
    """1Hz 데이터프레임 생성"""
    if isinstance(csv_path_or_df, str):
        df = pd.read_csv(csv_path_or_df)
    else:
        df = csv_path_or_df.copy()

    if "time" not in df.columns or "type" not in df.columns or "value" not in df.columns:
        raise ValueError("CSV에 time, type, value 컬럼이 필요합니다")

    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time")

    # RSSI 데이터 추출
    r = df[df["type"] == "rssi"][["time", "value"]].copy()
    r["value"] = pd.to_numeric(r["value"], errors="coerce")
    r = r.dropna(subset=["value"]).set_index("time")

    # 1초 리샘플링
    sec = r["value"].resample("1s").agg(["mean", "count"])
    rssi = sec["mean"]
    obs_count = sec["count"].fillna(0)

    # obs_code: 2=observed, 1=interpolated, 0=missing
    obs_code = pd.Series(np.where(obs_count > 0, 2, 0), index=sec.index)
    rssi_i = rssi.interpolate(limit=interp_limit)
    interpolated = rssi.isna() & rssi_i.notna()
    obs_code.loc[interpolated] = 1

    rssi_f = rssi_i.fillna(fill_value)

    # smooth, rolling_std
    smooth = rssi_f.rolling(smooth_win, center=False, min_periods=1).median()
    rolling_std = rssi_f.rolling(15, center=True, min_periods=1).std().fillna(3.0)

    # baseline 계산
    smooth_obs = smooth[obs_code > 0]
    baseline = float(np.percentile(smooth_obs.values, 90)) if len(smooth_obs) > 20 else float(np.percentile(smooth.values, 90))

    # smooth_rel
    smooth_rel = pd.Series(np.nan, index=smooth.index)
    observed_mask = obs_code > 0
    smooth_rel.loc[observed_mask] = smooth.loc[observed_mask] - baseline
    smooth_rel = smooth_rel.interpolate(limit=interp_limit).ffill().bfill()

    # Ground Truth (if exists)
    gt_1s = None
    if "event_from_timeline" in df.columns:
        gt = df[["time", "event_from_timeline"]].dropna(subset=["event_from_timeline"]).copy()
        gt = gt.sort_values("time").drop_duplicates("time").set_index("time")
        gt_state = gt["event_from_timeline"].map(STATE_MAP)
        gt_1s = gt_state.resample("1s").ffill()

    # 인덱스 정렬
    start = sec.index.min()
    end = sec.index.max()
    if gt_1s is not None:
        start = max(start, gt_1s.index.min())
        end = min(end, gt_1s.index.max())
    idx = pd.date_range(start=start, end=end, freq="1s")

    out = pd.DataFrame({
        "rssi": rssi_f.reindex(idx).fillna(fill_value),
        "smooth": smooth.reindex(idx).fillna(fill_value),
        "smooth_rel": smooth_rel.reindex(idx).fillna(0.0),
        "rolling_std": rolling_std.reindex(idx).fillna(3.0),
        "obs_code": obs_code.reindex(idx).fillna(0).astype(int),
    }, index=idx)

    if gt_1s is not None:
        out["gt"] = gt_1s.reindex(idx).ffill().astype(float)

    return out


# ============================================
# v8.2.5 모델 로더 및 전환점 탐지
# ============================================

_V825_MODEL_DATA = None

def load_v825_model():
    """v8.2.5 MSE-Calib 패턴 기반 모델 로드"""
    global _V825_MODEL_DATA
    if _V825_MODEL_DATA is not None:
        return _V825_MODEL_DATA

    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v825_model.pkl')
    if not os.path.exists(model_path):
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'v80_final_model.pkl')
        if not os.path.exists(model_path):
            return None

    try:
        with open(model_path, 'rb') as f:
            _V825_MODEL_DATA = pickle.load(f)
        return _V825_MODEL_DATA
    except Exception as e:
        print("[경고] v8.2.5 모델 로드 실패: %s" % e)
        return None


def extract_window_features_v80(rssi, center_idx, window_size=15):
    """v8.0 모델용 윈도우 특성 추출"""
    T = len(rssi)
    half_win = window_size // 2

    start_idx = max(0, center_idx - half_win)
    end_idx = min(T, center_idx + half_win + 1)

    window = rssi[start_idx:end_idx]
    if len(window) < 5:
        return None

    features = {}

    # 기본 통계
    features['win_mean'] = np.mean(window)
    features['win_std'] = np.std(window)
    features['win_min'] = np.min(window)
    features['win_max'] = np.max(window)
    features['win_range'] = features['win_max'] - features['win_min']
    features['win_median'] = np.median(window)

    # Percentiles
    features['win_p10'] = np.percentile(window, 10)
    features['win_p25'] = np.percentile(window, 25)
    features['win_p75'] = np.percentile(window, 75)
    features['win_p90'] = np.percentile(window, 90)
    features['win_iqr'] = features['win_p75'] - features['win_p25']

    # 변동성
    if len(window) >= 3:
        diff = np.diff(window)
        features['win_diff_mean'] = np.mean(diff)
        features['win_diff_std'] = np.std(diff)
        features['win_diff_abs_mean'] = np.mean(np.abs(diff))
        features['win_diff_abs_max'] = np.max(np.abs(diff))
        features['win_pos_diff_ratio'] = np.sum(diff > 0) / len(diff)
        features['win_neg_diff_ratio'] = np.sum(diff < 0) / len(diff)
    else:
        features['win_diff_mean'] = 0
        features['win_diff_std'] = 0
        features['win_diff_abs_mean'] = 0
        features['win_diff_abs_max'] = 0
        features['win_pos_diff_ratio'] = 0.5
        features['win_neg_diff_ratio'] = 0.5

    # 기울기
    if len(window) >= 3:
        x = np.arange(len(window))
        features['win_slope'] = np.polyfit(x, window, 1)[0]
    else:
        features['win_slope'] = 0

    # 윈도우 내 앞/뒤
    mid = len(window) // 2
    before_win = window[:mid] if mid > 0 else window
    after_win = window[mid:] if mid > 0 else window

    features['win_before_mean'] = np.mean(before_win)
    features['win_after_mean'] = np.mean(after_win)
    features['win_local_change'] = features['win_after_mean'] - features['win_before_mean']
    features['win_before_std'] = np.std(before_win) if len(before_win) > 1 else 0
    features['win_after_std'] = np.std(after_win) if len(after_win) > 1 else 0

    # 전체 대비
    global_mean = np.mean(rssi)
    global_std = np.std(rssi) + 1e-8
    global_min = np.min(rssi)
    global_max = np.max(rssi)
    global_range = global_max - global_min + 1e-8

    features['win_mean_zscore'] = (features['win_mean'] - global_mean) / global_std
    features['win_mean_normalized'] = (features['win_mean'] - global_min) / global_range

    start_mean = np.mean(rssi[:min(15, T//4)])
    end_mean = np.mean(rssi[-min(15, T//4):])
    features['win_vs_start'] = features['win_mean'] - start_mean
    features['win_vs_end'] = features['win_mean'] - end_mean

    # CV
    features['win_cv'] = features['win_std'] / (abs(features['win_mean']) + 1e-8)

    # Spike count
    if len(window) >= 3:
        diff = np.diff(window)
        threshold = np.std(rssi) * 0.5
        features['win_spike_count'] = np.sum(np.abs(diff) > threshold)
    else:
        features['win_spike_count'] = 0

    # Autocorr
    if len(window) >= 3:
        mean_centered = window - np.mean(window)
        if np.sum(mean_centered**2) > 0:
            autocorr = np.correlate(mean_centered, mean_centered, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            autocorr = autocorr / (autocorr[0] + 1e-8)
            features['win_autocorr_lag1'] = autocorr[1] if len(autocorr) > 1 else 0
        else:
            features['win_autocorr_lag1'] = 0
    else:
        features['win_autocorr_lag1'] = 0

    return features


def extract_cycle_features_v826(rssi, probs_smooth):
    """v8.2.6 calibrator용 cycle-level 특성 추출"""
    T = len(rssi)
    features = {}

    features['rssi_mean'] = np.mean(rssi)
    features['rssi_std'] = np.std(rssi) + 1e-8
    features['rssi_range'] = np.max(rssi) - np.min(rssi) + 1e-8

    start_mean = np.mean(rssi[:min(15, max(1, T//4))])
    end_mean = np.mean(rssi[-min(15, max(1, T//4)):])
    features['rssi_start_end_diff'] = start_mean - end_mean

    features['rssi_median'] = np.median(rssi)
    features['rssi_q25'] = np.percentile(rssi, 25)
    features['rssi_q75'] = np.percentile(rssi, 75)
    features['rssi_iqr'] = features['rssi_q75'] - features['rssi_q25']

    centered = rssi - features['rssi_mean']
    std = features['rssi_std']
    features['rssi_skew'] = np.mean((centered / std) ** 3) if std > 1e-6 else 0
    features['rssi_kurt'] = np.mean((centered / std) ** 4) - 3 if std > 1e-6 else 0

    features['prob_max'] = np.max(probs_smooth)
    features['prob_argmax'] = np.argmax(probs_smooth) / T
    features['prob_mean'] = np.mean(probs_smooth)
    features['prob_auc'] = np.sum(probs_smooth) / T

    gradient = np.gradient(probs_smooth)
    features['grad_max'] = np.max(gradient)
    features['grad_argmax'] = np.argmax(gradient) / T
    features['grad_mean'] = np.mean(gradient)
    features['grad_std'] = np.std(gradient)

    eps = 1e-8
    p = np.clip(probs_smooth, eps, 1 - eps)
    entropy = -p * np.log(p) - (1 - p) * np.log(1 - p)
    features['prob_entropy'] = np.mean(entropy)

    features['seq_length'] = T

    return features


def find_transition_changepoint_v826(probs_smooth, half_win=7):
    """v8.2.6 changepoint 기반 전환점 탐지"""
    T = len(probs_smooth)
    eps = 1e-8
    lo, hi = half_win, T - half_win - 1

    if lo >= hi:
        return T // 3

    log_1_minus_p = np.log(1 - probs_smooth + eps)
    log_p = np.log(probs_smooth + eps)

    prefix_sum = np.concatenate(([0.0], np.cumsum(log_1_minus_p)))
    suffix_sum = np.concatenate((np.cumsum(log_p[::-1])[::-1], [0.0]))

    scores = prefix_sum[:T] + suffix_sum[:T]
    valid_scores = scores[lo:hi+1]
    best_tau = lo + np.argmax(valid_scores)

    return int(best_tau)


def find_transition_with_v825(cycle_rssi: np.ndarray) -> Tuple[Optional[int], str]:
    """v8.2.5 패턴 기반 모델로 전환점 탐지"""
    model_data = load_v825_model()
    if model_data is None:
        return None, 'no_model'

    try:
        classifier = model_data.get('classifier')
        if classifier is None:
            classifier = model_data.get('model')
        if classifier is None:
            return None, 'no_classifier'

        feature_names = model_data['feature_names']
        version = model_data.get('version', 'v8.2.5_mse')

        T = len(cycle_rssi)
        probs = []

        for idx in range(T):
            features = extract_window_features_v80(cycle_rssi, idx)
            if features is None:
                probs.append(0.0)
                continue

            X = pd.DataFrame([[features.get(f, 0) for f in feature_names]], columns=feature_names)
            try:
                prob = classifier.predict_proba(X)[0][1]
            except:
                prob = 0.5
            probs.append(prob)

        probs = np.array(probs)
        probs_smooth = gaussian_filter1d(probs, sigma=3)

        half_win = model_data.get('window_size', 15) // 2
        pred_split_raw = find_transition_changepoint_v826(probs_smooth, half_win)

        if 'calibrator_weights' in model_data and 'calibrator_scaler' in model_data:
            calib_features = model_data.get('calibrator_feature_names', [])
            scaler = model_data['calibrator_scaler']
            w = model_data['calibrator_weights']

            cycle_feat = extract_cycle_features_v826(cycle_rssi, probs_smooth)
            X_calib = np.array([[cycle_feat.get(f, 0) for f in calib_features]])
            X_scaled = scaler.transform(X_calib)
            X_aug = np.hstack([X_scaled, np.ones((1, 1))])

            delta = (X_aug @ w)[0]
            pred_split = pred_split_raw - int(round(delta))
            pred_split = max(half_win, min(pred_split, T - half_win - 1))

            return int(pred_split), f'{version}_calib'
        else:
            pred_split = max(half_win, min(pred_split_raw, T - half_win - 1))
            return int(pred_split), f'{version}_raw'

    except Exception as e:
        print("[경고] v8.2.5 예측 실패: %s" % e)
        return None, 'error'


# ============================================
# In-Vehicle 탐지 (2-state HMM)
# ============================================

def detect_in_vehicle(data: pd.DataFrame) -> np.ndarray:
    """Enhanced 2-state HMM으로 IV vs OUT 분류"""
    rssi = data['rssi'].values
    obs_code = data['obs_code'].values

    if 'rolling_std' in data.columns:
        obs_std = data['rolling_std'].values
    else:
        obs_std = pd.Series(rssi).rolling(5, center=True, min_periods=1).std().fillna(3.0).values

    n = len(rssi)

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
    mu_cycle = (p25 + p10) / 2

    base_scale_iv = 5.5
    base_scale_cycle = 11
    std_weight = 0.15
    scale_iv_dyn = base_scale_iv + std_weight * obs_std
    scale_cycle_dyn = base_scale_cycle + std_weight * obs_std

    rssi_context = pd.Series(rssi).rolling(35, center=True, min_periods=1).mean().values

    log_p_iv_rssi = norm.logpdf(rssi, loc=mu_iv, scale=scale_iv_dyn)
    log_p_cycle_rssi = norm.logpdf(rssi, loc=mu_cycle, scale=scale_cycle_dyn)

    log_p_iv_ctx = norm.logpdf(rssi_context, loc=mu_iv, scale=scale_iv_dyn * 2.0)
    log_p_cycle_ctx = norm.logpdf(rssi_context, loc=mu_cycle, scale=scale_cycle_dyn * 2.0)

    log_p_iv = 0.45 * log_p_iv_rssi + 0.55 * log_p_iv_ctx
    log_p_cycle = 0.45 * log_p_cycle_rssi + 0.55 * log_p_cycle_ctx

    high_rssi_mask = rssi >= p77
    log_p_iv[high_rssi_mask] += 5.0
    log_p_cycle[high_rssi_mask] -= 10.0

    near_p77_mask = (rssi >= p77 - 5) & (rssi < p77)
    log_p_iv[near_p77_mask] += 2.0
    log_p_cycle[near_p77_mask] -= 3.0

    missing_mask = obs_code == 0
    log_p_iv[missing_mask] = log_p_iv[missing_mask] * 0.5
    log_p_cycle[missing_mask] = log_p_cycle[missing_mask] * 0.5

    LOG_FLOOR = -500.0
    log_p_iv = np.clip(log_p_iv, LOG_FLOOR, 0)
    log_p_cycle = np.clip(log_p_cycle, LOG_FLOOR, 0)

    log_em = np.column_stack([log_p_iv, log_p_cycle])

    A = np.array([
        [0.9995, 0.0005],
        [0.002, 0.998]
    ], dtype=float)

    logA = np.log(A)
    logpi = np.log(np.array([0.98, 0.02]))

    z = viterbi_log(log_em, logA, logpi)

    hmm_iv_high_regions = []
    segs = segment_list(z)
    for state_val, s, e in segs:
        if state_val == 0:
            seg_rssi = rssi[s:e]
            seg_len = e - s
            high_count = np.sum(seg_rssi >= p50)
            if high_count >= seg_len * 0.5 and high_count >= 5:
                hmm_iv_high_regions.append((s, e))

    z = postprocess_min_duration(z, min_len=22)

    segs = segment_list(z)
    for state_val, s, e in segs:
        if state_val == 1:
            seg_rssi = rssi[s:e]
            seg_mean = np.mean(seg_rssi)

            entry_idx = max(0, s - 10)
            exit_idx = min(n, e + 10)

            entry_rssi = np.mean(rssi[entry_idx:s]) if s > 0 else seg_mean
            exit_rssi = np.mean(rssi[e:exit_idx]) if e < n else seg_mean

            entry_drop = entry_rssi - seg_mean
            exit_rise = exit_rssi - seg_mean

            cond1 = (entry_drop < 10) and (exit_rise < 10)
            cond2 = seg_mean > -68
            cond3 = (seg_mean > -72) and (entry_drop < 22)

            if cond1 or cond2 or cond3:
                z[s:e] = 0

    z = postprocess_min_duration(z, min_len=22)

    for rs, re in hmm_iv_high_regions:
        z[rs:re] = 0

    segs = segment_list(z)
    for state_val, s, e in segs:
        if state_val == 1 and (e - s) >= 500:
            seg_rssi = rssi[s:e]
            seg_mean = np.mean(seg_rssi[seg_rssi < -50])

            high_threshold = seg_mean + 15
            high_mask = seg_rssi >= high_threshold

            i = 0
            while i < len(high_mask):
                if high_mask[i]:
                    j = i
                    while j < len(high_mask):
                        if high_mask[j]:
                            j += 1
                        elif j + 5 < len(high_mask) and np.any(high_mask[j:j+5]):
                            j += 1
                        else:
                            break
                    if j - i >= 20:
                        z[s+i:s+j] = 0
                    i = j
                else:
                    i += 1

    segs = segment_list(z)
    for state_val, s, e in segs:
        if state_val == 1 and (e - s) >= 100:
            seg_rssi = rssi[s:e]
            seg_len = len(seg_rssi)

            window = 25
            for ws in range(0, seg_len - window + 1):
                we = ws + window
                window_rssi = seg_rssi[ws:we]
                window_mean = np.mean(window_rssi)

                before_start = max(0, ws - 30)
                after_end = min(seg_len, we + 30)
                before_mean = np.mean(seg_rssi[before_start:ws]) if ws > 0 else window_mean
                after_mean = np.mean(seg_rssi[we:after_end]) if we < seg_len else window_mean
                surround_mean = (before_mean + after_mean) / 2

                if window_mean > surround_mean + 14:
                    actual_start = s + ws
                    actual_end = s + we

                    while actual_start > s and rssi[actual_start - 1] > surround_mean + 10:
                        actual_start -= 1
                    while actual_end < e and rssi[actual_end] > surround_mean + 10:
                        actual_end += 1

                    if actual_end - actual_start >= 20:
                        z[actual_start:actual_end] = 0

    segs = segment_list(z)
    for state_val, s, e in segs:
        if state_val == 0:
            seg_rssi = rssi[s:e]
            seg_len = e - s
            low_count = np.sum(seg_rssi <= p25)
            if low_count >= seg_len * 0.5:
                z[s:e] = 1

    return z


def get_cycle_segments(z: np.ndarray, min_len: int = 15) -> List[Tuple[int, int]]:
    """OUT(1) 구간 추출"""
    segs = []
    n = len(z)
    i = 0
    while i < n:
        if z[i] == 1:
            j = i
            while j < n and z[j] == 1:
                j += 1
            if (j - i) >= min_len:
                segs.append((i, j))
            i = j
        else:
            i += 1
    return segs


def compute_global_stats(data: pd.DataFrame) -> Dict:
    """전체 데이터에서 통계 계산"""
    rssi = data['rssi'].values
    obs_code = data['obs_code'].values

    observed = rssi[(obs_code >= 1) & (rssi > -99)]
    if len(observed) < 100:
        observed = rssi[rssi > -99]

    if len(observed) < 10:
        return {'p90': -50, 'p75': -55, 'p50': -65, 'p25': -80, 'p10': -90}

    return {
        'p90': float(np.percentile(observed, 90)),
        'p75': float(np.percentile(observed, 75)),
        'p50': float(np.percentile(observed, 50)),
        'p25': float(np.percentile(observed, 25)),
        'p10': float(np.percentile(observed, 10)),
    }


def validate_cycle_is_real(
    cycle_rssi: np.ndarray,
    cycle_obs_code: np.ndarray,
    global_stats: Dict,
    cycle_start_idx: int = 0,
    total_len: int = 0,
) -> Tuple[bool, str]:
    """사이클이 진짜 배송 사이클인지 검증"""
    T = len(cycle_rssi)
    if T < 15:
        return False, "too_short"
    return True, "valid"


# ============================================
# SR/DL 경계 탐지
# ============================================

def find_sr_dl_boundary(
    cycle_rssi: np.ndarray,
    min_sr: int = 3,
    min_dl: int = 3,
) -> int:
    """사이클 내 SR→DL 전환점 탐지 (휴리스틱)"""
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
    min_val = np.min(smoothed)
    min_idx = np.argmin(smoothed)
    drop_diff = sr_init - min_val

    if T < 50:
        expected_sr_ratio = 0.30
    elif T < 100:
        expected_sr_ratio = 0.22
    elif T < 200:
        expected_sr_ratio = 0.15
    else:
        expected_sr_ratio = 0.11
    expected_sr_len = max(min_sr, int(T * expected_sr_ratio))

    if drop_diff < 5:
        for t in range(max(min_sr, min_idx), T - min_dl):
            if smoothed[t] > min_val + 2:
                return t
        return max(min_sr, min(expected_sr_len, min_idx, T - min_dl))

    deriv = np.diff(smoothed)
    cliff_threshold = -max(4.0, drop_diff * 0.15)

    search_start = max(min_sr, expected_sr_len // 2)
    search_end = min(expected_sr_len + 5, min_idx, T - min_dl - 1)

    cliff_start = None
    for t in range(search_start, search_end):
        if t + 3 < T:
            avg_deriv = np.mean(deriv[t:t+3])
            if avg_deriv < cliff_threshold:
                persistence_win = min(8, T - t - min_dl)
                if persistence_win >= 4:
                    pre_level = np.mean(smoothed[max(0, t-4):t])
                    post_seg = smoothed[t+2:t+2+persistence_win]
                    if len(post_seg) > 0:
                        post_max = np.max(post_seg)
                        if post_max < pre_level - drop_diff * 0.25:
                            cliff_start = t
                            break

    if cliff_start is not None:
        return max(min_sr, cliff_start)

    threshold = sr_init - drop_diff * 0.35
    transition_idx = None
    search_start = max(min_sr, expected_sr_len * 2 // 3)
    search_end = min(expected_sr_len * 3, min_idx + 10, T - min_dl)

    for t in range(search_start, search_end):
        if smoothed[t] < threshold:
            persistence_win = min(6, T - t - min_dl)
            if persistence_win >= 3:
                post_seg = smoothed[t:t+persistence_win]
                if len(post_seg) > 0:
                    post_max = np.max(post_seg)
                    if post_max < threshold + drop_diff * 0.15:
                        transition_idx = t
                        break

    if transition_idx is not None:
        sr_len = transition_idx
    else:
        sr_len = expected_sr_len

    return max(min_sr, min(sr_len, T - min_dl))


# ============================================
# 메인 분석 함수
# ============================================

def get_state_times(csv_path: str) -> Tuple[int, int, int]:
    """
    BLE CSV 파일을 분석하여 상태별 시간(초)을 반환합니다.

    Args:
        csv_path: BLE CSV 파일 경로

    Returns:
        (in_vehicle_seconds, searching_seconds, delivering_seconds) 튜플
    """
    # 1. 데이터 전처리
    data = preprocess_data(csv_path)
    n = len(data)

    # 2. In-Vehicle 탐지
    iv_states = detect_in_vehicle(data)

    # 3. 사이클 세그먼트 추출
    global_stats = compute_global_stats(data)
    raw_cycle_segments = get_cycle_segments(iv_states, min_len=15)

    cycle_segments = []
    for start, end in raw_cycle_segments:
        cycle_rssi = data['rssi'].values[start:end]
        cycle_obs = data['obs_code'].values[start:end]
        is_valid, _ = validate_cycle_is_real(
            cycle_rssi, cycle_obs, global_stats,
            cycle_start_idx=start, total_len=n
        )
        if is_valid:
            cycle_segments.append((start, end))

    # 4. 각 사이클 SR/DL 경계 탐지
    states = np.full(n, STATE_IN_VEHICLE, dtype=int)

    for start, end in cycle_segments:
        cycle_rssi = data['rssi'].values[start:end]

        sr_len = None
        v825_result, _ = find_transition_with_v825(cycle_rssi)
        if v825_result is not None:
            sr_len = v825_result

        if sr_len is None:
            sr_len = find_sr_dl_boundary(cycle_rssi)

        states[start:start + sr_len] = STATE_SEARCHING
        states[start + sr_len:end] = STATE_DELIVERING

    # 5. 결과 계산
    total_iv = int(np.sum(states == STATE_IN_VEHICLE))
    total_sr = int(np.sum(states == STATE_SEARCHING))
    total_dl = int(np.sum(states == STATE_DELIVERING))

    return (total_iv, total_sr, total_dl)


def analyze_ble_file(csv_path: str) -> dict:
    """BLE CSV 파일을 분석하여 단계별 시간을 추출"""
    print("=" * 70)
    print(f"BLE 파일 분석: {os.path.basename(csv_path)}")
    print("=" * 70)

    # 1. 데이터 전처리
    print("\n[1단계] 데이터 전처리...")
    data = preprocess_data(csv_path)
    n = len(data)
    print(f"   - 총 데이터 길이: {n}초 ({n/60:.1f}분)")
    print(f"   - 시작 시간: {data.index[0]}")
    print(f"   - 종료 시간: {data.index[-1]}")

    rssi = data['rssi'].values
    obs_code = data['obs_code'].values
    observed = rssi[obs_code >= 1]

    print(f"   - RSSI 범위: {np.min(observed):.1f} ~ {np.max(observed):.1f} dB")
    print(f"   - RSSI 평균: {np.mean(observed):.1f} dB")
    print(f"   - 관측률: {np.mean(obs_code >= 1)*100:.1f}%")

    # 2. In-Vehicle 탐지
    print("\n[2단계] In-Vehicle 탐지 (HMM)...")
    iv_states = detect_in_vehicle(data)

    iv_count = np.sum(iv_states == 0)
    cycle_count = np.sum(iv_states == 1)
    print(f"   - In-Vehicle (0): {iv_count}초 ({iv_count/n*100:.1f}%)")
    print(f"   - 배송 사이클 (1): {cycle_count}초 ({cycle_count/n*100:.1f}%)")

    # 3. 사이클 세그먼트 추출
    print("\n[3단계] 사이클 세그먼트 추출...")
    global_stats = compute_global_stats(data)
    raw_cycle_segments = get_cycle_segments(iv_states, min_len=15)

    cycle_segments = []
    for start, end in raw_cycle_segments:
        cycle_rssi = data['rssi'].values[start:end]
        cycle_obs = data['obs_code'].values[start:end]
        is_valid, _ = validate_cycle_is_real(
            cycle_rssi, cycle_obs, global_stats,
            cycle_start_idx=start, total_len=n
        )
        if is_valid:
            cycle_segments.append((start, end))

    print(f"   - 원본 사이클 수: {len(raw_cycle_segments)}개")
    print(f"   - 유효 사이클 수: {len(cycle_segments)}개")

    # 4. 각 사이클 상세 분석
    print("\n[4단계] 사이클별 SR/DL 경계 탐지...")
    print("-" * 70)

    cycles = []
    states = np.full(n, STATE_IN_VEHICLE, dtype=int)

    for cycle_id, (start, end) in enumerate(cycle_segments):
        T = end - start
        cycle_rssi = data['rssi'].values[start:end]
        cycle_smooth = data['smooth'].values[start:end]
        cycle_obs = data['obs_code'].values[start:end]

        sr_len = None
        ml_mode = 'heuristic'

        v825_result, v825_mode = find_transition_with_v825(cycle_rssi)
        if v825_result is not None:
            sr_len = v825_result
            ml_mode = v825_mode

        if sr_len is None:
            sr_len = find_sr_dl_boundary(cycle_rssi)
            ml_mode = 'heuristic'

        dl_len = T - sr_len

        states[start:start + sr_len] = STATE_SEARCHING
        states[start + sr_len:end] = STATE_DELIVERING

        cycle_info = {
            'id': cycle_id + 1,
            'start_idx': start,
            'end_idx': end,
            'start_time': str(data.index[start]),
            'end_time': str(data.index[end-1]),
            'length': T,
            'sr_seconds': sr_len,
            'dl_seconds': dl_len,
            'sr_ratio': sr_len / T * 100,
            'mode': ml_mode,
            'rssi_mean': np.mean(cycle_rssi),
            'rssi_min': np.min(cycle_rssi),
            'rssi_max': np.max(cycle_rssi),
        }
        cycles.append(cycle_info)

        print(f"   사이클 {cycle_id+1:2d}: 시작={start:5d}, 길이={T:4d}초, "
              f"SR={sr_len:3d}초 ({sr_len/T*100:4.1f}%), DL={dl_len:3d}초 [{ml_mode}]")

    print("-" * 70)

    # 5. 전체 통계
    print("\n[5단계] 전체 결과 집계...")

    total_iv = int(np.sum(states == STATE_IN_VEHICLE))
    total_sr = int(np.sum(states == STATE_SEARCHING))
    total_dl = int(np.sum(states == STATE_DELIVERING))

    print(f"\n{'='*70}")
    print("최종 결과")
    print(f"{'='*70}")
    print(f"\n총 시간: {n}초 ({n/60:.1f}분)")
    print(f"\n상태별 시간:")
    print(f"   - In Vehicle:  {total_iv:5d}초 ({total_iv/60:6.1f}분) - {total_iv/n*100:5.1f}%")
    print(f"   - Searching:   {total_sr:5d}초 ({total_sr/60:6.1f}분) - {total_sr/n*100:5.1f}%")
    print(f"   - Delivering:  {total_dl:5d}초 ({total_dl/60:6.1f}분) - {total_dl/n*100:5.1f}%")

    print(f"\n사이클 통계:")
    print(f"   - 총 사이클 수: {len(cycles)}개")

    if cycles:
        avg_cycle_len = np.mean([c['length'] for c in cycles])
        avg_sr = np.mean([c['sr_seconds'] for c in cycles])
        avg_dl = np.mean([c['dl_seconds'] for c in cycles])

        print(f"   - 평균 사이클 길이: {avg_cycle_len:.1f}초")
        print(f"   - 평균 Searching: {avg_sr:.1f}초")
        print(f"   - 평균 Delivering: {avg_dl:.1f}초")

        lengths = [c['length'] for c in cycles]
        print(f"\n사이클 길이 분포:")
        print(f"   - 최소: {min(lengths)}초")
        print(f"   - 최대: {max(lengths)}초")
        print(f"   - 중앙값: {np.median(lengths):.0f}초")

    print(f"\n{'='*70}")

    return {
        'file': os.path.basename(csv_path),
        'total_seconds': n,
        'total_iv': total_iv,
        'total_sr': total_sr,
        'total_dl': total_dl,
        'num_cycles': len(cycles),
        'cycles': cycles,
        'data': data,
        'states': states,
    }


def print_cycle_details(result: dict):
    """사이클 상세 정보 출력"""
    print("\n" + "=" * 70)
    print("사이클 상세 정보")
    print("=" * 70)

    for c in result['cycles']:
        print(f"\n사이클 {c['id']}:")
        print(f"   시간: {c['start_time']} ~ {c['end_time']}")
        print(f"   인덱스: {c['start_idx']} ~ {c['end_idx']}")
        print(f"   길이: {c['length']}초 ({c['length']/60:.1f}분)")
        print(f"   Searching: {c['sr_seconds']}초 ({c['sr_ratio']:.1f}%)")
        print(f"   Delivering: {c['dl_seconds']}초 ({100-c['sr_ratio']:.1f}%)")
        print(f"   RSSI: 평균={c['rssi_mean']:.1f}dB, 범위={c['rssi_min']:.0f}~{c['rssi_max']:.0f}dB")
        print(f"   탐지 모드: {c['mode']}")


def export_timeline(result: dict, output_path: str = None):
    """타임라인 CSV 내보내기"""
    if output_path is None:
        base = os.path.splitext(os.path.basename(result['file']))[0]
        export_dir = os.environ.get("BLE_TIMELINE_EXPORT_DIR", "").strip()
        if export_dir:
            os.makedirs(export_dir, exist_ok=True)
            output_path = os.path.join(export_dir, f"{base}_timeline.csv")
        else:
            base = os.path.splitext(result['file'])[0]
            output_path = f"{base}_timeline.csv"

    data = result['data'].copy()
    data['predicted_state'] = result['states']
    data['state_name'] = [STATE_NAMES[s] for s in result['states']]

    data.to_csv(output_path, encoding="utf-8-sig")
    print(f"\n타임라인 저장: {output_path}")

    return output_path


if __name__ == "__main__":
    target_file = "ble_20260106_233313_691.csv"

    base_path = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_path, target_file)

    if not os.path.exists(csv_path):
        print(f"파일을 찾을 수 없습니다: {csv_path}")
        sys.exit(1)

    result = analyze_ble_file(csv_path)
    print_cycle_details(result)
    export_timeline(result)
