from __future__ import annotations

import csv
import datetime as dt
import json
import math
from bisect import bisect_right
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG_PATH = ROOT / "00_admin" / "rqi_dii_rules_v1_config.json"
DISCLOSURE_CSV = ROOT / "02_manual_coding" / "rqi_dii_pilot_coding_v1.csv"
PANEL_CSV = ROOT / "04_processed_data" / "minimum_viable_panel_v1.csv"
MARKET_CSV = ROOT / "03_market_data" / "price_supply_panel_raw_v1.csv"
STRESS_CSV = ROOT / "02_manual_coding" / "stress_regime_calendar_v1.csv"
EVENT_WINDOW_CSV = ROOT / "05_analysis" / "event_study_results_v1" / "event_window_panel_v1.csv"
EVENT_CLASS_CSV = ROOT / "02_manual_coding" / "event_classification_table_v1.csv"

OUT_DIR = ROOT / "05_analysis" / "robustness_results_v1"
RQI_SENSITIVITY_CSV = OUT_DIR / "rqi_weight_sensitivity_v1.csv"
BASELINE_COEF_CSV = OUT_DIR / "baseline_robustness_coefficients_v1.csv"
BASELINE_SUMMARY_CSV = OUT_DIR / "baseline_robustness_summary_v1.csv"
EVENT_EFFECTS_CSV = OUT_DIR / "event_window_robustness_effects_v1.csv"
EVENT_SUMMARY_CSV = OUT_DIR / "event_window_robustness_summary_v1.csv"
MARKET_FLAGS_CSV = OUT_DIR / "market_abnormal_price_flags_v1.csv"
MARKET_SUMMARY_CSV = OUT_DIR / "market_abnormal_price_summary_v1.csv"
STRESS_SENSITIVITY_CSV = OUT_DIR / "stress_calendar_sensitivity_v1.csv"
LOG_MD = ROOT / "99_logs" / "robustness_run_log_20260522.md"
MEMO_MD = ROOT / "06_outputs" / "P1E_ROBUSTNESS_MEMO_20260522.md"
PROGRESS_MD = ROOT / "06_outputs" / "P1_PHASE_E_PROGRESS_20260522.md"

ACCESS_DATE = "2026-05-22"
HAC_LAGS = 7


def load_rule_config() -> dict[str, Any]:
    with RULE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


RULE_CONFIG = load_rule_config()
RULE_VERSION = RULE_CONFIG.get("rule_version", "RQI_DII_v1.0")
RULE_STATUS = RULE_CONFIG.get("rule_status", "frozen_confirmed_by_researcher")
PROVISIONAL_REASON = "robustness_pilot_pending_multi_issuer_source_expansion"


def parse_date(value: Any) -> dt.date | None:
    if value is None or pd.isna(value) or value == "":
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def to_float(value: Any) -> float:
    if value is None or pd.isna(value) or value == "":
        return np.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return np.nan


def fmt_num(value: Any, digits: int = 4) -> str:
    if value is None or pd.isna(value):
        return ""
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.{digits}f}"


def rqi_profiles() -> list[dict[str, Any]]:
    profiles = [
        {
            "profile": RULE_CONFIG.get("rqi_weight_profile", "primary_path_b"),
            **RULE_CONFIG["rqi_weights_primary"],
            "profile_role": "primary",
        }
    ]
    for item in RULE_CONFIG.get("rqi_robustness_weights", []):
        profiles.append({**item, "profile_role": "robustness"})
    return profiles


def compute_rqi(row: pd.Series, weights: dict[str, Any]) -> float:
    total = to_float(row.get("total_reserve_assets_usd"))
    if pd.isna(total) or total <= 0:
        return np.nan
    treasury = to_float(row.get("treasury_securities_usd"))
    repo = to_float(row.get("treasury_repo_usd"))
    reserve_cash = to_float(row.get("reserve_fund_cash_usd"))
    bank_cash = to_float(row.get("bank_cash_usd"))
    treasury = 0.0 if pd.isna(treasury) else treasury
    repo = 0.0 if pd.isna(repo) else repo
    reserve_cash = 0.0 if pd.isna(reserve_cash) else reserve_cash
    bank_cash = 0.0 if pd.isna(bank_cash) else bank_cash
    observed = treasury + repo + reserve_cash + bank_cash
    if observed > total * 1.05:
        return np.nan
    other = max(total - observed, 0.0)
    numerator = (
        float(weights["treasury_securities"]) * treasury
        + float(weights["treasury_repo"]) * repo
        + float(weights["reserve_fund_cash"]) * reserve_cash
        + float(weights["bank_cash"]) * bank_cash
        + float(weights["other_residual"]) * other
    )
    return numerator / total


def build_rqi_sensitivity(disclosures: pd.DataFrame) -> pd.DataFrame:
    rows = []
    profiles = rqi_profiles()
    primary_profile = profiles[0]["profile"]
    for _, row in disclosures.iterrows():
        result: dict[str, Any] = {
            "event_id": row.get("event_id", ""),
            "stablecoin": row.get("stablecoin", ""),
            "report_date": row.get("latest_report_date", ""),
            "publication_date": row.get("publication_date", ""),
            "manual_review_required": row.get("manual_review_required", ""),
            "asset_extraction_confidence": row.get("asset_extraction_confidence", ""),
            "rule_version": RULE_VERSION,
            "rule_status": RULE_STATUS,
        }
        for profile in profiles:
            name = profile["profile"]
            result[f"rqi_{name}"] = compute_rqi(row, profile)
        primary_value = result.get(f"rqi_{primary_profile}")
        for profile in profiles[1:]:
            name = profile["profile"]
            value = result.get(f"rqi_{name}")
            result[f"delta_{name}_minus_{primary_profile}"] = (
                value - primary_value
                if not pd.isna(value) and not pd.isna(primary_value)
                else np.nan
            )
        rows.append(result)
    out = pd.DataFrame(rows)
    out.to_csv(RQI_SENSITIVITY_CSV, index=False)
    return out


def attach_rqi_variants(panel: pd.DataFrame, rqi_sensitivity: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    panel["date_obj"] = panel["date"].apply(parse_date)
    rqi_sensitivity = rqi_sensitivity.copy()
    rqi_sensitivity["publication_date_obj"] = rqi_sensitivity["publication_date"].apply(parse_date)
    events = rqi_sensitivity[rqi_sensitivity["publication_date_obj"].notna()].sort_values("publication_date_obj")
    event_dates = list(events["publication_date_obj"])
    profiles = [profile["profile"] for profile in rqi_profiles()]
    for profile in profiles:
        panel[f"rqi_{profile}_asof"] = np.nan

    for idx, row in panel.iterrows():
        day = row["date_obj"]
        if day is None:
            continue
        event_idx = bisect_right(event_dates, day) - 1
        if event_idx < 0:
            continue
        event = events.iloc[event_idx]
        for profile in profiles:
            panel.at[idx, f"rqi_{profile}_asof"] = event.get(f"rqi_{profile}", np.nan)
    return panel


def prepare_panel(panel: pd.DataFrame) -> pd.DataFrame:
    df = panel.copy()
    df["date_obj"] = pd.to_datetime(df["date"])
    numeric_cols = [
        "price_usd",
        "peg_dev",
        "abs_peg_dev",
        "tail_depeg_50bp",
        "tail_depeg_100bp",
        "downside_depeg_50bp",
        "downside_depeg_100bp",
        "premium_50bp",
        "circulating_face_usd",
        "market_cap_usd_est",
        "market_stress_flag",
        "days_since_disclosure",
        "stale_disclosure_45d",
        "report_to_publication_lag_days",
        "pilot_dii_asof",
        "disclosure_manual_review_required_asof",
    ]
    numeric_cols.extend([f"rqi_{profile['profile']}_asof" for profile in rqi_profiles()])
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    first_date = df["date_obj"].min()
    df["trend_years"] = (df["date_obj"] - first_date).dt.days / 365.25
    df["abs_peg_dev_bps"] = df["abs_peg_dev"] * 10000
    df["tail_depeg_50bp_pct"] = df["tail_depeg_50bp"] * 100
    df["downside_depeg_50bp_pct"] = df["downside_depeg_50bp"] * 100
    df["dii_10pp"] = df["pilot_dii_asof"] * 10
    df["days_since_disclosure_30d"] = df["days_since_disclosure"] / 30
    df["log_supply"] = np.log(df["circulating_face_usd"])
    df["manual_review_asof"] = df["disclosure_manual_review_required_asof"].fillna(0)
    return df


def clean_design(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    cols = [y_col] + x_cols
    data = df[["date", *cols]].replace([np.inf, -np.inf], np.nan).dropna(subset=cols).copy()
    kept_x = []
    for col in x_cols:
        values = data[col].to_numpy(dtype=float)
        if len(values) and np.nanstd(values) >= 1e-12:
            kept_x.append(col)
    y = data[y_col].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(data)), *[data[col].to_numpy(dtype=float) for col in kept_x]]) if len(data) else np.empty((0, 1))
    return data, y, X, ["Intercept", *kept_x]


def hac_covariance(X: np.ndarray, residuals: np.ndarray, lags: int) -> np.ndarray:
    n, k = X.shape
    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((k, k))
    for t in range(n):
        xt = X[t : t + 1].T
        meat += residuals[t] ** 2 * (xt @ xt.T)
    max_lag = min(lags, n - 1)
    for lag in range(1, max_lag + 1):
        weight = 1 - lag / (max_lag + 1)
        for t in range(lag, n):
            xt = X[t : t + 1].T
            xlag = X[t - lag : t - lag + 1].T
            meat += weight * residuals[t] * residuals[t - lag] * (xt @ xlag.T + xlag @ xt.T)
    return xtx_inv @ meat @ xtx_inv


def ols_hac(
    df: pd.DataFrame,
    model_run_id: str,
    family: str,
    sample_id: str,
    rqi_profile: str,
    y_col: str,
    x_cols: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data, y, X, names = clean_design(df, y_col, x_cols)
    n, k = X.shape
    base_summary = {
        "model_run_id": model_run_id,
        "model_family": family,
        "sample_id": sample_id,
        "rqi_profile": rqi_profile,
        "outcome": y_col,
        "n": n,
        "k": k,
        "rule_version": RULE_VERSION,
        "rule_status": RULE_STATUS,
        "provisional_flag": 1,
        "provisional_reason": PROVISIONAL_REASON,
    }
    if n <= k + 5 or k <= 1:
        return [], {**base_summary, "status": "skipped_insufficient_rows_or_variation"}
    beta = np.linalg.pinv(X.T @ X) @ X.T @ y
    fitted = X @ beta
    residuals = y - fitted
    sse = float(np.sum(residuals**2))
    tss = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - sse / tss if tss > 0 else np.nan
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k) if n > k and not np.isnan(r2) else np.nan
    cov = hac_covariance(X, residuals, HAC_LAGS)
    se = np.sqrt(np.clip(np.diag(cov), 0, np.inf))
    df_resid = max(n - k, 1)

    coef_rows = []
    for name, b, s in zip(names, beta, se):
        t_stat = b / s if s > 0 else np.nan
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df_resid)) if not np.isnan(t_stat) else np.nan
        coef_rows.append(
            {
                **base_summary,
                "term": name,
                "coef": b,
                "hac_se_lag7": s,
                "t_stat": t_stat,
                "p_value": p_value,
                "r2": r2,
                "adj_r2": adj_r2,
                "status": "estimated",
            }
        )
    return coef_rows, {
        **base_summary,
        "start_date": data["date"].iloc[0],
        "end_date": data["date"].iloc[-1],
        "y_mean": float(np.mean(y)),
        "y_sd": float(np.std(y, ddof=1)),
        "r2": r2,
        "adj_r2": adj_r2,
        "status": "estimated",
    }


def sample_frame(df: pd.DataFrame, sample_id: str) -> pd.DataFrame:
    if sample_id == "all_rows_with_variant":
        return df.copy()
    if sample_id == "rqi_available":
        return df.copy()
    if sample_id == "manual_review_free":
        return df[df["manual_review_asof"] == 0].copy()
    if sample_id == "non_stress_rows":
        return df[df["market_stress_flag"] == 0].copy()
    if sample_id == "stress_rows_diagnostic":
        return df[df["market_stress_flag"] == 1].copy()
    if sample_id == "exclude_100bp_tail_days":
        return df[df["tail_depeg_100bp"] != 1].copy()
    raise ValueError(f"Unknown sample: {sample_id}")


def run_baseline_robustness(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    coef_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    sample_ids = [
        "all_rows_with_variant",
        "rqi_available",
        "manual_review_free",
        "non_stress_rows",
        "stress_rows_diagnostic",
        "exclude_100bp_tail_days",
    ]
    model_families = [
        ("absdev_rqi_dii", "abs_peg_dev_bps", "standard"),
        ("tail50_rqi_dii_lpm", "tail_depeg_50bp_pct", "standard"),
        ("absdev_stress_interaction", "abs_peg_dev_bps", "stress_interaction"),
    ]
    for profile in rqi_profiles():
        profile_name = profile["profile"]
        rqi_col = f"rqi_{profile_name}_asof"
        rqi_10pp = f"rqi_{profile_name}_10pp"
        panel[rqi_10pp] = panel[rqi_col] * 10
        panel[f"stress_x_{profile_name}_10pp"] = panel["market_stress_flag"] * panel[rqi_10pp]
        panel["stress_x_dii_10pp"] = panel["market_stress_flag"] * panel["dii_10pp"]
        for sample_id in sample_ids:
            sample = sample_frame(panel, sample_id)
            for family, outcome, kind in model_families:
                if kind == "standard":
                    x_cols = [
                        rqi_10pp,
                        "dii_10pp",
                        "days_since_disclosure_30d",
                        "stale_disclosure_45d",
                        "market_stress_flag",
                        "log_supply",
                        "trend_years",
                    ]
                else:
                    x_cols = [
                        rqi_10pp,
                        "dii_10pp",
                        "market_stress_flag",
                        f"stress_x_{profile_name}_10pp",
                        "stress_x_dii_10pp",
                        "days_since_disclosure_30d",
                        "stale_disclosure_45d",
                        "log_supply",
                        "trend_years",
                    ]
                model_run_id = f"{family}__{profile_name}__{sample_id}"
                coefs, summary = ols_hac(sample, model_run_id, family, sample_id, profile_name, outcome, x_cols)
                coef_rows.extend(coefs)
                summary_rows.append(summary)
    coef_df = pd.DataFrame(coef_rows)
    summary_df = pd.DataFrame(summary_rows)
    coef_df.to_csv(BASELINE_COEF_CSV, index=False)
    summary_df.to_csv(BASELINE_SUMMARY_CSV, index=False)
    return coef_df, summary_df


def mean_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else np.nan


def max_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.max()) if len(values) else np.nan


def run_event_window_robustness() -> tuple[pd.DataFrame, pd.DataFrame]:
    window_panel = pd.read_csv(EVENT_WINDOW_CSV)
    event_class = pd.read_csv(EVENT_CLASS_CSV)
    primary_windows = [int(x) for x in RULE_CONFIG.get("event_study", {}).get("primary_windows_days", [3, 7])]
    robustness_windows = [int(x) for x in RULE_CONFIG.get("event_study", {}).get("robustness_windows_days", [14])]
    windows = sorted(set(primary_windows + robustness_windows))
    event_meta = event_class.set_index("event_id").to_dict("index")
    rows = []
    for event_id, event_rows in window_panel.groupby("event_id"):
        event_rows = event_rows.copy()
        meta = event_meta.get(event_id, {})
        event_day = event_rows[event_rows["relative_day"] == 0]
        for window in windows:
            pre = event_rows[(event_rows["relative_day"] >= -window) & (event_rows["relative_day"] <= -1)]
            post = event_rows[(event_rows["relative_day"] >= 0) & (event_rows["relative_day"] <= window)]
            pre_abs = mean_or_nan(pre["abs_peg_dev_bps"])
            post_abs = mean_or_nan(post["abs_peg_dev_bps"])
            pre_tail50 = mean_or_nan(pre["tail_depeg_50bp"])
            post_tail50 = mean_or_nan(post["tail_depeg_50bp"])
            rows.append(
                {
                    "event_id": event_id,
                    "event_date": meta.get("event_date", ""),
                    "window_days": window,
                    "window_role": "primary" if window in primary_windows else "robustness",
                    "pre_n": len(pre),
                    "post_n": len(post),
                    "pre_mean_abs_peg_dev_bps": pre_abs,
                    "post_mean_abs_peg_dev_bps": post_abs,
                    "delta_post_minus_pre_abs_peg_dev_bps": post_abs - pre_abs if not pd.isna(pre_abs) and not pd.isna(post_abs) else np.nan,
                    "event_day_abs_peg_dev_bps": mean_or_nan(event_day["abs_peg_dev_bps"]),
                    "max_post_abs_peg_dev_bps": max_or_nan(post["abs_peg_dev_bps"]),
                    "pre_tail50_rate": pre_tail50,
                    "post_tail50_rate": post_tail50,
                    "delta_post_minus_pre_tail50_rate": post_tail50 - pre_tail50 if not pd.isna(pre_tail50) and not pd.isna(post_tail50) else np.nan,
                    "event_has_rqi": meta.get("has_rqi", ""),
                    "event_has_dii": meta.get("has_dii", ""),
                    "event_manual_review_required": meta.get("manual_review_required", ""),
                    "event_stress_regime_disclosure": meta.get("stress_regime_disclosure", ""),
                    "overlap_risk_7d_window": meta.get("overlap_risk_7d_window", ""),
                    "overlap_risk_14d_window": meta.get("overlap_risk_14d_window", ""),
                    "classification_status": meta.get("classification_status", ""),
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    effects = pd.DataFrame(rows)
    effects.to_csv(EVENT_EFFECTS_CSV, index=False)

    groups = {
        "all_events": effects,
        "no_overlap_14d": effects[effects["overlap_risk_14d_window"].astype(str) != "1"],
        "events_with_rqi": effects[effects["event_has_rqi"].astype(str) == "1"],
        "manual_review_free_events": effects[effects["event_manual_review_required"].astype(str) == "0"],
        "manual_review_required_events": effects[effects["event_manual_review_required"].astype(str) == "1"],
        "banking_stress_disclosure_events": effects[effects["event_stress_regime_disclosure"] == "banking_stress"],
        "normal_disclosure_events": effects[effects["event_stress_regime_disclosure"] == "normal"],
    }
    summary_rows = []
    for group_name, data in groups.items():
        for window in windows:
            subset = data[data["window_days"] == window]
            summary_rows.append(
                {
                    "group": group_name,
                    "window_days": window,
                    "window_role": "primary" if window in primary_windows else "robustness",
                    "events": subset["event_id"].nunique(),
                    "mean_pre_abs_peg_dev_bps": mean_or_nan(subset["pre_mean_abs_peg_dev_bps"]),
                    "mean_post_abs_peg_dev_bps": mean_or_nan(subset["post_mean_abs_peg_dev_bps"]),
                    "mean_delta_abs_peg_dev_bps": mean_or_nan(subset["delta_post_minus_pre_abs_peg_dev_bps"]),
                    "median_delta_abs_peg_dev_bps": float(pd.to_numeric(subset["delta_post_minus_pre_abs_peg_dev_bps"], errors="coerce").median()) if len(subset) else np.nan,
                    "max_event_day_abs_peg_dev_bps": max_or_nan(subset["event_day_abs_peg_dev_bps"]),
                    "mean_delta_tail50_rate": mean_or_nan(subset["delta_post_minus_pre_tail50_rate"]),
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(EVENT_SUMMARY_CSV, index=False)
    return effects, summary


def run_market_abnormal_price_qc() -> tuple[pd.DataFrame, pd.DataFrame]:
    market = pd.read_csv(MARKET_CSV)
    for col in ["price_usd", "abs_peg_dev", "circulating_face_usd", "tail_depeg_50bp", "tail_depeg_100bp"]:
        market[col] = pd.to_numeric(market[col], errors="coerce")
    med_supply = (
        market[market["circulating_face_usd"] > 0]
        .groupby("stablecoin")["circulating_face_usd"]
        .median()
        .to_dict()
    )
    market["supply_median_by_coin"] = market["stablecoin"].map(med_supply)
    market["low_supply_lifecycle_flag"] = (
        (market["circulating_face_usd"] > 0)
        & (market["supply_median_by_coin"] > 0)
        & (market["circulating_face_usd"] < market["supply_median_by_coin"] * 0.05)
    ).astype(int)
    market["abnormal_price_50bp_flag"] = (market["abs_peg_dev"] >= 0.005).astype(int)
    market["abnormal_price_100bp_flag"] = (market["abs_peg_dev"] >= 0.01).astype(int)
    market["manual_market_review_flag"] = (
        (market["abnormal_price_100bp_flag"] == 1)
        | ((market["stablecoin"].isin(["BUSD", "TUSD"])) & (market["abnormal_price_50bp_flag"] == 1))
        | (market["low_supply_lifecycle_flag"] == 1)
    ).astype(int)
    flagged = market[market["manual_market_review_flag"] == 1].copy()
    keep_cols = [
        "date",
        "stablecoin",
        "issuer",
        "price_usd",
        "abs_peg_dev",
        "tail_depeg_50bp",
        "tail_depeg_100bp",
        "circulating_face_usd",
        "supply_median_by_coin",
        "abnormal_price_50bp_flag",
        "abnormal_price_100bp_flag",
        "low_supply_lifecycle_flag",
        "manual_market_review_flag",
        "market_stress_flag",
        "market_stress_types",
        "rule_version",
        "rule_status",
    ]
    flagged[keep_cols].to_csv(MARKET_FLAGS_CSV, index=False)

    summaries = []
    for stablecoin, subset in market.groupby("stablecoin"):
        valid_abs = pd.to_numeric(subset["abs_peg_dev"], errors="coerce").dropna()
        summaries.append(
            {
                "stablecoin": stablecoin,
                "rows": len(subset),
                "tail_50bp_days": int((subset["abnormal_price_50bp_flag"] == 1).sum()),
                "tail_100bp_days": int((subset["abnormal_price_100bp_flag"] == 1).sum()),
                "manual_market_review_rows": int((subset["manual_market_review_flag"] == 1).sum()),
                "low_supply_lifecycle_rows": int((subset["low_supply_lifecycle_flag"] == 1).sum()),
                "max_abs_peg_dev": float(valid_abs.max()) if len(valid_abs) else np.nan,
                "median_supply_proxy": med_supply.get(stablecoin, np.nan),
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "provisional_flag": 1,
                "provisional_reason": "market_abnormal_price_qc_pending",
            }
        )
    summary = pd.DataFrame(summaries)
    summary.to_csv(MARKET_SUMMARY_CSV, index=False)
    return flagged, summary


def stress_variant_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date_only"] = pd.to_datetime(out["date"]).dt.date
    out["stress_current_flag"] = pd.to_numeric(out["market_stress_flag"], errors="coerce").fillna(0)
    out["stress_svb_only_flag"] = out["date_only"].between(dt.date(2023, 3, 10), dt.date(2023, 3, 20)).astype(int)
    stress_calendar = pd.read_csv(STRESS_CSV)
    anchor_dates = []
    for _, row in stress_calendar.iterrows():
        affected = str(row.get("affected_stablecoins", ""))
        if "ALL" in affected or "USDC" in affected:
            start = parse_date(row.get("start_date", ""))
            if start:
                anchor_dates.append(start)
    short_days = set()
    for anchor in anchor_dates:
        for offset in range(-3, 4):
            short_days.add(anchor + dt.timedelta(days=offset))
    out["stress_short_anchor_flag"] = out["date_only"].isin(short_days).astype(int)
    return out


def run_stress_sensitivity(panel: pd.DataFrame) -> pd.DataFrame:
    base = stress_variant_flags(panel)
    primary_profile = rqi_profiles()[0]["profile"]
    rqi_col = f"rqi_{primary_profile}_asof"
    rows = []
    for variant_id, flag_col in [
        ("current_provisional_windows", "stress_current_flag"),
        ("svb_only_banking_stress", "stress_svb_only_flag"),
        ("short_anchor_windows", "stress_short_anchor_flag"),
    ]:
        sample = base.copy()
        sample["market_stress_flag_variant"] = sample[flag_col]
        sample[f"stress_x_{primary_profile}_10pp_variant"] = sample["market_stress_flag_variant"] * (sample[rqi_col] * 10)
        sample["stress_x_dii_10pp_variant"] = sample["market_stress_flag_variant"] * sample["dii_10pp"]
        x_cols = [
            f"rqi_{primary_profile}_10pp",
            "dii_10pp",
            "market_stress_flag_variant",
            f"stress_x_{primary_profile}_10pp_variant",
            "stress_x_dii_10pp_variant",
            "days_since_disclosure_30d",
            "stale_disclosure_45d",
            "log_supply",
            "trend_years",
        ]
        sample[f"rqi_{primary_profile}_10pp"] = sample[rqi_col] * 10
        coefs, summary = ols_hac(
            sample,
            f"stress_calendar__{variant_id}",
            "stress_calendar_sensitivity",
            "all_rows_with_variant",
            primary_profile,
            "abs_peg_dev_bps",
            x_cols,
        )
        for row in coefs:
            row["stress_variant"] = variant_id
            rows.append(row)
        if not coefs:
            rows.append({**summary, "stress_variant": variant_id, "term": "", "coef": np.nan, "hac_se_lag7": np.nan, "p_value": np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(STRESS_SENSITIVITY_CSV, index=False)
    return out


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int | None = None) -> str:
    data = df[cols].copy()
    if max_rows is not None:
        data = data.head(max_rows)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in data.iterrows():
        values = []
        for col in cols:
            value = row.get(col, "")
            if isinstance(value, float) or isinstance(value, np.floating):
                values.append(fmt_num(value, 4))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_reports(
    rqi_sensitivity: pd.DataFrame,
    baseline_coefs: pd.DataFrame,
    baseline_summary: pd.DataFrame,
    event_summary: pd.DataFrame,
    market_summary: pd.DataFrame,
    stress_sensitivity: pd.DataFrame,
) -> None:
    primary_profile = rqi_profiles()[0]["profile"]
    rqi_cols = [f"rqi_{profile['profile']}" for profile in rqi_profiles()]
    rqi_available = int(rqi_sensitivity[f"rqi_{primary_profile}"].notna().sum())

    key_coef_terms = baseline_coefs[
        (baseline_coefs["model_family"] == "absdev_rqi_dii")
        & (baseline_coefs["sample_id"].isin(["all_rows_with_variant", "manual_review_free", "non_stress_rows", "exclude_100bp_tail_days"]))
        & (baseline_coefs["term"].str.contains("_10pp", na=False))
        & (baseline_coefs["rqi_profile"].isin([primary_profile, "bank_cash_070", "bank_cash_090", "repo_090"]))
    ][["rqi_profile", "sample_id", "term", "coef", "hac_se_lag7", "p_value", "n"]].copy()

    event_key = event_summary[
        (event_summary["group"].isin(["all_events", "no_overlap_14d", "manual_review_free_events"]))
        & (event_summary["window_days"].isin([3, 7, 14]))
    ][["group", "window_days", "events", "mean_delta_abs_peg_dev_bps", "mean_delta_tail50_rate"]].copy()

    stress_key = stress_sensitivity[
        stress_sensitivity["term"].isin(["market_stress_flag_variant", f"stress_x_{primary_profile}_10pp_variant", "stress_x_dii_10pp_variant"])
    ][["stress_variant", "term", "coef", "hac_se_lag7", "p_value", "n"]].copy()

    LOG_MD.write_text(
        "\n".join(
            [
                "# Robustness Run Log",
                "",
                f"Date: {ACCESS_DATE}",
                "",
                f"Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`)",
                "",
                "## Inputs",
                "",
                f"- Disclosure coding: `{DISCLOSURE_CSV.relative_to(ROOT)}`",
                f"- Minimum viable panel: `{PANEL_CSV.relative_to(ROOT)}`",
                f"- Market panel: `{MARKET_CSV.relative_to(ROOT)}`",
                f"- Event-window panel: `{EVENT_WINDOW_CSV.relative_to(ROOT)}`",
                "",
                "## Outputs",
                "",
                f"- `{RQI_SENSITIVITY_CSV.relative_to(ROOT)}`",
                f"- `{BASELINE_COEF_CSV.relative_to(ROOT)}`",
                f"- `{BASELINE_SUMMARY_CSV.relative_to(ROOT)}`",
                f"- `{EVENT_EFFECTS_CSV.relative_to(ROOT)}`",
                f"- `{EVENT_SUMMARY_CSV.relative_to(ROOT)}`",
                f"- `{MARKET_FLAGS_CSV.relative_to(ROOT)}`",
                f"- `{MARKET_SUMMARY_CSV.relative_to(ROOT)}`",
                f"- `{STRESS_SENSITIVITY_CSV.relative_to(ROOT)}`",
                "",
                "## Run Counts",
                "",
                f"- RQI profiles tested: {len(rqi_profiles())}",
                f"- Disclosure rows with primary RQI: {rqi_available}",
                f"- Baseline robustness model runs: {len(baseline_summary)}",
                f"- Estimated coefficient rows: {len(baseline_coefs)}",
                f"- Event-window summary rows: {len(event_summary)}",
                f"- Market manual-review flag rows: {int(market_summary['manual_market_review_rows'].sum())}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    memo = [
        "# P1-E Robustness Pilot Memo",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        "## Purpose",
        "",
        f"This memo reports the first robustness execution under `{RULE_VERSION}`. It is a pilot robustness package, not final empirical evidence.",
        "",
        "## RQI Weight Sensitivity",
        "",
        f"RQI sensitivity was computed for {len(rqi_profiles())} profiles. Primary RQI is available for {rqi_available} of {len(rqi_sensitivity)} disclosure rows.",
        "",
        md_table(rqi_sensitivity[["event_id", *rqi_cols]].dropna(subset=[f"rqi_{primary_profile}"]).head(8), ["event_id", *rqi_cols]),
        "",
        "## Baseline Robustness Key Coefficients",
        "",
        md_table(key_coef_terms, ["rqi_profile", "sample_id", "term", "coef", "hac_se_lag7", "p_value", "n"], max_rows=32),
        "",
        "## Event-Window Robustness",
        "",
        md_table(event_key, ["group", "window_days", "events", "mean_delta_abs_peg_dev_bps", "mean_delta_tail50_rate"]),
        "",
        "## Market Abnormal-Price QC",
        "",
        md_table(market_summary, ["stablecoin", "tail_50bp_days", "tail_100bp_days", "manual_market_review_rows", "low_supply_lifecycle_rows", "max_abs_peg_dev"]),
        "",
        "## Stress-Calendar Sensitivity",
        "",
        md_table(stress_key, ["stress_variant", "term", "coef", "hac_se_lag7", "p_value", "n"], max_rows=18),
        "",
        "## Technical Interpretation",
        "",
        "The robustness package confirms that the pipeline can rerun systematically across RQI weights, sample filters, event windows, abnormal-price flags, and stress-window variants. These outputs should be read as design diagnostics. They are not sufficient for final claims because the sample is still USDC-centered for disclosure-linked models and because ad hoc/multi-issuer event coverage is not complete.",
        "",
        "## Next Step",
        "",
        "The next stage should expand disclosure/event coverage beyond USDC and convert the robustness results into a claim-safe pilot empirical memo.",
    ]
    MEMO_MD.write_text("\n".join(memo) + "\n", encoding="utf-8")

    progress = [
        "# P1-E 阶段进展报告：Robustness Execution",
        "",
        f"日期：{ACCESS_DATE}",
        "",
        "## 阶段结论",
        "",
        f"P1-E 已完成第一轮冻结规则下的稳健性执行。所有输出均标记为 `{RULE_VERSION}`，并继续保留 pilot/provisional 边界。",
        "",
        "## 已保存输出",
        "",
        f"- `{RQI_SENSITIVITY_CSV.relative_to(ROOT)}`",
        f"- `{BASELINE_COEF_CSV.relative_to(ROOT)}`",
        f"- `{BASELINE_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_EFFECTS_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{MARKET_FLAGS_CSV.relative_to(ROOT)}`",
        f"- `{MARKET_SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{STRESS_SENSITIVITY_CSV.relative_to(ROOT)}`",
        f"- `{LOG_MD.relative_to(ROOT)}`",
        f"- `{MEMO_MD.relative_to(ROOT)}`",
        f"- `{PROGRESS_MD.relative_to(ROOT)}`",
        "",
        "## 核查结果",
        "",
        f"- RQI 权重 profiles：{len(rqi_profiles())}。",
        f"- primary RQI 可用 disclosure rows：{rqi_available} / {len(rqi_sensitivity)}。",
        f"- baseline robustness model runs：{len(baseline_summary)}。",
        f"- estimated coefficient rows：{len(baseline_coefs)}。",
        f"- event-window summary rows：{len(event_summary)}。",
        f"- market manual-review flag rows：{int(market_summary['manual_market_review_rows'].sum())}。",
        "",
        "## 方法解释边界",
        "",
        "本阶段证明稳健性管线可以系统运行，但尚不能形成最终实证结论。当前结果主要用于判断模型是否对权重、窗口、样本、压力期和市场异常处理高度敏感。",
        "",
        "## 下一步计划",
        "",
        "1. P1-F：扩展 USDT、Paxos/BUSD/PYUSD、TUSD 的 disclosure/event index。",
        "2. P1-G：生成 pilot empirical memo v1，将 baseline、event-study、robustness 合并为可写作但不过度解释的阶段性证据。",
        "3. 建立 source verification queue，处理 auditor/provider、April 2023 USDC reserve table、weekly disclosure event layer。",
    ]
    PROGRESS_MD.write_text("\n".join(progress) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    disclosures = pd.read_csv(DISCLOSURE_CSV)
    panel = pd.read_csv(PANEL_CSV)

    rqi_sensitivity = build_rqi_sensitivity(disclosures)
    panel_with_rqi = attach_rqi_variants(panel, rqi_sensitivity)
    prepared_panel = prepare_panel(panel_with_rqi)
    baseline_coefs, baseline_summary = run_baseline_robustness(prepared_panel)
    _, event_summary = run_event_window_robustness()
    _, market_summary = run_market_abnormal_price_qc()
    stress_sensitivity = run_stress_sensitivity(prepared_panel)

    write_reports(
        rqi_sensitivity,
        baseline_coefs,
        baseline_summary,
        event_summary,
        market_summary,
        stress_sensitivity,
    )


if __name__ == "__main__":
    main()
