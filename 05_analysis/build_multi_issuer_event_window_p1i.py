from __future__ import annotations

import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG_PATH = ROOT / "00_admin" / "rqi_dii_rules_v1_config.json"
TASK_BACKLOG_CSV = ROOT / "00_admin" / "TASK_BACKLOG.csv"

EVENT_INDEX_CSV = ROOT / "02_manual_coding" / "multi_issuer_disclosure_event_index_v1.csv"
EPISODE_OVERRIDES_CSV = ROOT / "02_manual_coding" / "analytic_event_episode_overrides_p1j_v1.csv"
MARKET_CSV = ROOT / "03_market_data" / "price_supply_panel_raw_v1.csv"

OUT_DIR = ROOT / "05_analysis" / "multi_issuer_event_window_results_v1"
EVENT_UNITS_CSV = OUT_DIR / "multi_issuer_event_units_v1.csv"
WINDOW_PANEL_CSV = OUT_DIR / "multi_issuer_event_window_panel_v1.csv"
EVENT_EFFECTS_CSV = OUT_DIR / "multi_issuer_event_level_effects_v1.csv"
EVENT_TIME_CSV = OUT_DIR / "multi_issuer_event_time_average_v1.csv"
SUMMARY_CSV = OUT_DIR / "multi_issuer_event_summary_v1.csv"
COMPARISON_CSV = OUT_DIR / "multi_issuer_comparison_matrix_v1.csv"

MEMO_MD = ROOT / "06_outputs" / "P1I_MULTI_ISSUER_EVENT_WINDOW_MEMO_20260522.md"
PROGRESS_MD = ROOT / "06_outputs" / "P1_PHASE_I_PROGRESS_20260522.md"
STATUS_MD = ROOT / "00_admin" / "PROJECT_STATUS_UPDATE_MULTI_ISSUER_EVENT_WINDOW_20260522.md"
LOG_MD = ROOT / "99_logs" / "multi_issuer_event_window_log_20260522.md"

ACCESS_DATE = "2026-05-22"


def load_rule_config() -> dict[str, Any]:
    with RULE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


RULE_CONFIG = load_rule_config()
RULE_VERSION = RULE_CONFIG.get("rule_version", "RQI_DII_v1.0")
RULE_STATUS = RULE_CONFIG.get("rule_status", "frozen_confirmed_by_researcher")
EVENT_STUDY_CONFIG = RULE_CONFIG.get("event_study", {})
PRIMARY_WINDOWS = [int(x) for x in EVENT_STUDY_CONFIG.get("primary_windows_days", [3, 7])]
ROBUSTNESS_WINDOWS = [int(x) for x in EVENT_STUDY_CONFIG.get("robustness_windows_days", [14])]
WINDOWS = sorted(set([*PRIMARY_WINDOWS, *ROBUSTNESS_WINDOWS]))
WINDOW_MAX = max(WINDOWS)
PROVISIONAL_REASON = "multi_issuer_ready_event_extension_source_verification_pending"


def parse_date(value: Any) -> dt.date | None:
    if pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def numeric_flag(value: Any) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip().lower()
    if text in {"1", "yes", "true", "y"}:
        return 1
    return 0


def priority_rank(value: Any) -> int:
    text = str(value).strip().upper()
    if text.startswith("P") and text[1:].isdigit():
        return int(text[1:])
    return 9


def join_unique(values: pd.Series, sep: str = "; ") -> str:
    items = []
    for value in values:
        if pd.isna(value) or str(value).strip() == "":
            continue
        text = str(value).strip()
        if text not in items:
            items.append(text)
    return sep.join(items)


def mean_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else np.nan


def median_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.median()) if len(values) else np.nan


def max_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.max()) if len(values) else np.nan


def fmt(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def md_table(df: pd.DataFrame, cols: list[str], max_rows: int | None = None) -> str:
    if df.empty:
        return "_No rows available._"
    data = df[cols].copy()
    if max_rows:
        data = data.head(max_rows)
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for _, row in data.iterrows():
        values = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                values.append(fmt(value, 4))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows([{name: row.get(name, "") for name in fieldnames} for row in rows])


def load_market() -> pd.DataFrame:
    df = pd.read_csv(MARKET_CSV)
    df["date_obj"] = pd.to_datetime(df["date"]).dt.date
    for col in [
        "price_usd",
        "peg_dev",
        "abs_peg_dev",
        "tail_depeg_50bp",
        "tail_depeg_100bp",
        "downside_depeg_50bp",
        "premium_50bp",
        "circulating_face_usd",
        "market_stress_flag",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["peg_dev_bps"] = df["peg_dev"] * 10000
    df["abs_peg_dev_bps"] = df["abs_peg_dev"] * 10000

    by_date = df.groupby("date_obj").agg(
        date_abs_sum=("abs_peg_dev_bps", "sum"),
        date_peg_sum=("peg_dev_bps", "sum"),
        date_tail50_sum=("tail_depeg_50bp", "sum"),
        date_count=("stablecoin", "count"),
    )
    df = df.merge(by_date, left_on="date_obj", right_index=True, how="left")
    peer_count = (df["date_count"] - 1).replace(0, np.nan)
    df["peer_mean_abs_peg_dev_bps"] = (df["date_abs_sum"] - df["abs_peg_dev_bps"]) / peer_count
    df["peer_mean_peg_dev_bps"] = (df["date_peg_sum"] - df["peg_dev_bps"]) / peer_count
    df["peer_tail50_rate"] = (df["date_tail50_sum"] - df["tail_depeg_50bp"]) / peer_count
    df["peer_adjusted_abs_peg_dev_bps"] = df["abs_peg_dev_bps"] - df["peer_mean_abs_peg_dev_bps"]
    df["peer_adjusted_peg_dev_bps"] = df["peg_dev_bps"] - df["peer_mean_peg_dev_bps"]
    return df


def load_ready_events() -> pd.DataFrame:
    df = pd.read_csv(EVENT_INDEX_CSV)
    df["event_study_ready_flag"] = df["event_study_ready"].apply(numeric_flag)
    df["event_date_obj"] = df["event_date"].apply(parse_date)
    ready = df[(df["event_study_ready_flag"] == 1) & df["event_date_obj"].notna()].copy()
    for col in ["scheduled_flag", "ad_hoc_flag", "manual_review_required"]:
        ready[f"{col}_num"] = ready[col].apply(numeric_flag)
    ready["priority_rank"] = ready["priority"].apply(priority_rank)
    ready["event_unit_key"] = ready.apply(
        lambda row: row["linked_event_group"]
        if not pd.isna(row.get("linked_event_group")) and str(row.get("linked_event_group")).strip()
        else row["event_id"],
        axis=1,
    )
    ready["episode_override_applied"] = 0
    ready["canonical_event_date_basis_effective"] = ready.get("event_date_basis", "")
    ready["episode_merge_rule"] = ""
    ready["episode_body_inclusion_status"] = ""
    ready["episode_override_rationale"] = ""

    overrides = load_episode_overrides()
    if not overrides.empty:
        override_cols = [
            "event_id",
            "analytic_event_unit_id",
            "canonical_event_date",
            "canonical_event_date_basis",
            "episode_merge_rule",
            "body_inclusion_status",
            "rationale",
        ]
        ready = ready.merge(overrides[override_cols], on="event_id", how="left")
        override_mask = ready["analytic_event_unit_id"].notna()
        ready.loc[override_mask, "event_unit_key"] = ready.loc[override_mask, "analytic_event_unit_id"]
        ready.loc[override_mask, "event_date_obj"] = ready.loc[override_mask, "canonical_event_date"].apply(parse_date)
        ready.loc[override_mask, "episode_override_applied"] = 1
        ready.loc[override_mask, "canonical_event_date_basis_effective"] = ready.loc[override_mask, "canonical_event_date_basis"]
        ready.loc[override_mask, "episode_body_inclusion_status"] = ready.loc[override_mask, "body_inclusion_status"]
        ready.loc[override_mask, "episode_override_rationale"] = ready.loc[override_mask, "rationale"]
        ready["episode_merge_rule"] = ready["episode_merge_rule_y"].fillna(ready["episode_merge_rule_x"])
        ready = ready.drop(columns=["episode_merge_rule_x", "episode_merge_rule_y"])
    return ready


def load_episode_overrides() -> pd.DataFrame:
    if not EPISODE_OVERRIDES_CSV.exists():
        return pd.DataFrame()
    return pd.read_csv(EPISODE_OVERRIDES_CSV)


def build_event_units(ready: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = ready.groupby(["stablecoin", "event_unit_key", "event_date_obj"], dropna=False)
    for (stablecoin, unit_key, event_date), group in grouped:
        scheduled = int(group["scheduled_flag_num"].max())
        ad_hoc = int(group["ad_hoc_flag_num"].max())
        event_class = "mixed"
        if ad_hoc and not scheduled:
            event_class = "ad_hoc"
        elif scheduled and not ad_hoc:
            event_class = "scheduled"

        event_date_rows = market[(market["stablecoin"] == stablecoin) & (market["date_obj"] == event_date)]
        market_row = event_date_rows.iloc[0] if len(event_date_rows) else None
        rows.append(
            {
                "event_unit_id": str(unit_key),
                "stablecoin": stablecoin,
                "issuer": join_unique(group["issuer"]),
                "event_date": event_date.isoformat(),
                "record_count": len(group),
                "event_ids": join_unique(group["event_id"]),
                "event_families": join_unique(group["event_family"]),
                "document_families": join_unique(group["document_family"]),
                "event_types": join_unique(group["event_type"]),
                "source_statuses": join_unique(group["source_status"]),
                "source_urls": join_unique(group["source_url"]),
                "scheduled_flag": scheduled,
                "ad_hoc_flag": ad_hoc,
                "event_class": event_class,
                "issuer_scope": "USDC" if stablecoin == "USDC" else "non_USDC",
                "stress_regime": join_unique(group["stress_regime"]),
                "manual_review_required": int(group["manual_review_required_num"].max()),
                "min_priority": f"P{int(group['priority_rank'].min())}" if len(group) else "",
                "source_record_count": len([x for x in group["source_url"] if not pd.isna(x) and str(x).strip()]),
                "has_rqi": int(group["rqi_available"].apply(numeric_flag).max()) if "rqi_available" in group else 0,
                "has_dii": int(group["dii_available"].apply(numeric_flag).max()) if "dii_available" in group else 0,
                "event_day_price_usd": "" if market_row is None else market_row["price_usd"],
                "event_day_abs_peg_dev_bps": "" if market_row is None else market_row["abs_peg_dev_bps"],
                "event_day_peer_adjusted_abs_peg_dev_bps": "" if market_row is None else market_row["peer_adjusted_abs_peg_dev_bps"],
                "market_stress_on_event_date": "" if market_row is None else int(market_row["market_stress_flag"]),
                "market_stress_types_on_event_date": "" if market_row is None else market_row["market_stress_types"],
                "episode_override_applied": int(group["episode_override_applied"].max()),
                "canonical_event_date_basis": join_unique(group["canonical_event_date_basis_effective"]),
                "episode_merge_rules": join_unique(group["episode_merge_rule"]),
                "episode_body_inclusion_status": join_unique(group["episode_body_inclusion_status"]),
                "episode_override_rationale": join_unique(group["episode_override_rationale"]),
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "provisional_flag": 1,
                "provisional_reason": PROVISIONAL_REASON,
            }
        )

    out = pd.DataFrame(rows).sort_values(["event_date", "stablecoin", "event_unit_id"]).reset_index(drop=True)
    out["event_date_obj"] = out["event_date"].apply(parse_date)
    out = add_overlap_flags(out)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.drop(columns=["event_date_obj"]).to_csv(EVENT_UNITS_CSV, index=False)
    return out


def add_overlap_flags(units: pd.DataFrame) -> pd.DataFrame:
    units = units.sort_values(["stablecoin", "event_date_obj", "event_unit_id"]).copy()
    prev_gaps = []
    next_gaps = []
    for _, row in units.iterrows():
        same = units[(units["stablecoin"] == row["stablecoin"]) & (units["event_unit_id"] != row["event_unit_id"])]
        before = same[same["event_date_obj"] < row["event_date_obj"]]["event_date_obj"]
        after = same[same["event_date_obj"] > row["event_date_obj"]]["event_date_obj"]
        prev_gaps.append("" if before.empty else (row["event_date_obj"] - before.max()).days)
        next_gaps.append("" if after.empty else (after.min() - row["event_date_obj"]).days)
    units["previous_event_gap_days"] = prev_gaps
    units["next_event_gap_days"] = next_gaps
    for window in [7, 14]:
        units[f"overlap_risk_{window}d_window"] = units.apply(
            lambda row: int(
                (str(row["previous_event_gap_days"]).isdigit() and int(row["previous_event_gap_days"]) <= 2 * window)
                or (str(row["next_event_gap_days"]).isdigit() and int(row["next_event_gap_days"]) <= 2 * window)
            ),
            axis=1,
        )
    return units


def build_window_panel(units: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    market_by_key = market.set_index(["stablecoin", "date_obj"])
    rows = []
    for _, event in units.iterrows():
        event_date = event["event_date_obj"]
        for rel_day in range(-WINDOW_MAX, WINDOW_MAX + 1):
            day = event_date + dt.timedelta(days=rel_day)
            key = (event["stablecoin"], day)
            if key not in market_by_key.index:
                continue
            m = market_by_key.loc[key]
            rows.append(
                {
                    "event_unit_id": event["event_unit_id"],
                    "stablecoin": event["stablecoin"],
                    "issuer_scope": event["issuer_scope"],
                    "event_class": event["event_class"],
                    "event_date": event["event_date"],
                    "date": day.isoformat(),
                    "relative_day": rel_day,
                    "record_count": event["record_count"],
                    "event_families": event["event_families"],
                    "manual_review_required": event["manual_review_required"],
                    "market_stress_on_event_date": event["market_stress_on_event_date"],
                    "market_stress_flag": m["market_stress_flag"],
                    "market_stress_types": m["market_stress_types"],
                    "overlap_risk_7d_window": event["overlap_risk_7d_window"],
                    "overlap_risk_14d_window": event["overlap_risk_14d_window"],
                    "episode_override_applied": event["episode_override_applied"],
                    "canonical_event_date_basis": event["canonical_event_date_basis"],
                    "episode_merge_rules": event["episode_merge_rules"],
                    "price_usd": m["price_usd"],
                    "peg_dev_bps": m["peg_dev_bps"],
                    "abs_peg_dev_bps": m["abs_peg_dev_bps"],
                    "peer_mean_abs_peg_dev_bps": m["peer_mean_abs_peg_dev_bps"],
                    "peer_adjusted_abs_peg_dev_bps": m["peer_adjusted_abs_peg_dev_bps"],
                    "peer_adjusted_peg_dev_bps": m["peer_adjusted_peg_dev_bps"],
                    "tail_depeg_50bp": m["tail_depeg_50bp"],
                    "tail_depeg_100bp": m["tail_depeg_100bp"],
                    "peer_tail50_rate": m["peer_tail50_rate"],
                    "circulating_face_usd": m["circulating_face_usd"],
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(WINDOW_PANEL_CSV, index=False)
    return out


def build_event_effects(window_panel: pd.DataFrame, units: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, event in units.iterrows():
        event_rows = window_panel[window_panel["event_unit_id"] == event["event_unit_id"]].copy()
        event_day = event_rows[event_rows["relative_day"] == 0]
        for window in WINDOWS:
            pre = event_rows[(event_rows["relative_day"] >= -window) & (event_rows["relative_day"] <= -1)]
            post = event_rows[(event_rows["relative_day"] >= 0) & (event_rows["relative_day"] <= window)]

            pre_abs = mean_or_nan(pre["abs_peg_dev_bps"])
            post_abs = mean_or_nan(post["abs_peg_dev_bps"])
            pre_adj_abs = mean_or_nan(pre["peer_adjusted_abs_peg_dev_bps"])
            post_adj_abs = mean_or_nan(post["peer_adjusted_abs_peg_dev_bps"])
            pre_signed = mean_or_nan(pre["peg_dev_bps"])
            post_signed = mean_or_nan(post["peg_dev_bps"])
            pre_tail50 = mean_or_nan(pre["tail_depeg_50bp"])
            post_tail50 = mean_or_nan(post["tail_depeg_50bp"])
            rows.append(
                {
                    "event_unit_id": event["event_unit_id"],
                    "stablecoin": event["stablecoin"],
                    "issuer_scope": event["issuer_scope"],
                    "event_class": event["event_class"],
                    "event_date": event["event_date"],
                    "event_families": event["event_families"],
                    "record_count": event["record_count"],
                    "manual_review_required": event["manual_review_required"],
                    "min_priority": event["min_priority"],
                    "market_stress_on_event_date": event["market_stress_on_event_date"],
                    "overlap_risk_7d_window": event["overlap_risk_7d_window"],
                    "overlap_risk_14d_window": event["overlap_risk_14d_window"],
                    "episode_override_applied": event["episode_override_applied"],
                    "canonical_event_date_basis": event["canonical_event_date_basis"],
                    "episode_merge_rules": event["episode_merge_rules"],
                    "window_days": window,
                    "pre_n": len(pre),
                    "post_n": len(post),
                    "expected_pre_n": window,
                    "expected_post_n": window + 1,
                    "complete_window": int(len(pre) == window and len(post) == window + 1),
                    "pre_mean_abs_peg_dev_bps": pre_abs,
                    "post_mean_abs_peg_dev_bps": post_abs,
                    "delta_post_minus_pre_abs_peg_dev_bps": post_abs - pre_abs if not pd.isna(pre_abs) and not pd.isna(post_abs) else np.nan,
                    "pre_mean_peer_adjusted_abs_peg_dev_bps": pre_adj_abs,
                    "post_mean_peer_adjusted_abs_peg_dev_bps": post_adj_abs,
                    "delta_post_minus_pre_peer_adjusted_abs_bps": post_adj_abs - pre_adj_abs if not pd.isna(pre_adj_abs) and not pd.isna(post_adj_abs) else np.nan,
                    "pre_mean_peg_dev_bps": pre_signed,
                    "post_mean_peg_dev_bps": post_signed,
                    "delta_post_minus_pre_peg_dev_bps": post_signed - pre_signed if not pd.isna(pre_signed) and not pd.isna(post_signed) else np.nan,
                    "event_day_abs_peg_dev_bps": mean_or_nan(event_day["abs_peg_dev_bps"]),
                    "event_day_peer_adjusted_abs_peg_dev_bps": mean_or_nan(event_day["peer_adjusted_abs_peg_dev_bps"]),
                    "max_post_abs_peg_dev_bps": max_or_nan(post["abs_peg_dev_bps"]),
                    "max_post_peer_adjusted_abs_peg_dev_bps": max_or_nan(post["peer_adjusted_abs_peg_dev_bps"]),
                    "pre_tail50_rate": pre_tail50,
                    "post_tail50_rate": post_tail50,
                    "delta_post_minus_pre_tail50_rate": post_tail50 - pre_tail50 if not pd.isna(pre_tail50) and not pd.isna(post_tail50) else np.nan,
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(EVENT_EFFECTS_CSV, index=False)
    return out


def build_event_time_average(window_panel: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        window_panel.groupby(["issuer_scope", "event_class", "relative_day"], as_index=False)
        .agg(
            n_event_units=("event_unit_id", "nunique"),
            n_rows=("event_unit_id", "count"),
            mean_abs_peg_dev_bps=("abs_peg_dev_bps", "mean"),
            median_abs_peg_dev_bps=("abs_peg_dev_bps", "median"),
            mean_peer_adjusted_abs_peg_dev_bps=("peer_adjusted_abs_peg_dev_bps", "mean"),
            mean_peg_dev_bps=("peg_dev_bps", "mean"),
            tail50_rate=("tail_depeg_50bp", "mean"),
            market_stress_share=("market_stress_flag", "mean"),
            manual_review_event_share=("manual_review_required", "mean"),
        )
        .sort_values(["issuer_scope", "event_class", "relative_day"])
    )
    grouped["rule_version"] = RULE_VERSION
    grouped["rule_status"] = RULE_STATUS
    grouped.to_csv(EVENT_TIME_CSV, index=False)
    return grouped


def summarize_group(event_effects: pd.DataFrame, group_name: str, subset: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for window in WINDOWS:
        data = subset[subset["window_days"] == window]
        rows.append(
            {
                "group": group_name,
                "window_days": window,
                "event_units": data["event_unit_id"].nunique(),
                "complete_window_units": int(pd.to_numeric(data["complete_window"], errors="coerce").sum()) if len(data) else 0,
                "manual_review_required_units": int(data[data["manual_review_required"] == 1]["event_unit_id"].nunique()) if len(data) else 0,
                "overlap_risk_7d_units": int(data[data["overlap_risk_7d_window"] == 1]["event_unit_id"].nunique()) if len(data) else 0,
                "mean_pre_abs_peg_dev_bps": mean_or_nan(data["pre_mean_abs_peg_dev_bps"]),
                "mean_post_abs_peg_dev_bps": mean_or_nan(data["post_mean_abs_peg_dev_bps"]),
                "mean_delta_abs_peg_dev_bps": mean_or_nan(data["delta_post_minus_pre_abs_peg_dev_bps"]),
                "median_delta_abs_peg_dev_bps": median_or_nan(data["delta_post_minus_pre_abs_peg_dev_bps"]),
                "mean_delta_peer_adjusted_abs_bps": mean_or_nan(data["delta_post_minus_pre_peer_adjusted_abs_bps"]),
                "median_delta_peer_adjusted_abs_bps": median_or_nan(data["delta_post_minus_pre_peer_adjusted_abs_bps"]),
                "max_event_day_abs_peg_dev_bps": max_or_nan(data["event_day_abs_peg_dev_bps"]),
                "max_post_abs_peg_dev_bps": max_or_nan(data["max_post_abs_peg_dev_bps"]),
                "mean_delta_tail50_rate": mean_or_nan(data["delta_post_minus_pre_tail50_rate"]),
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "provisional_flag": 1,
                "provisional_reason": PROVISIONAL_REASON,
            }
        )
    return rows


def build_summary(event_effects: pd.DataFrame) -> pd.DataFrame:
    groups: dict[str, pd.DataFrame] = {
        "all_ready_event_units": event_effects,
        "usdc_units": event_effects[event_effects["issuer_scope"] == "USDC"],
        "non_usdc_units": event_effects[event_effects["issuer_scope"] == "non_USDC"],
        "scheduled_units": event_effects[event_effects["event_class"] == "scheduled"],
        "ad_hoc_units": event_effects[event_effects["event_class"] == "ad_hoc"],
        "non_usdc_scheduled_units": event_effects[(event_effects["issuer_scope"] == "non_USDC") & (event_effects["event_class"] == "scheduled")],
        "non_usdc_ad_hoc_units": event_effects[(event_effects["issuer_scope"] == "non_USDC") & (event_effects["event_class"] == "ad_hoc")],
        "manual_review_required_units": event_effects[event_effects["manual_review_required"] == 1],
        "manual_review_free_units": event_effects[event_effects["manual_review_required"] == 0],
    }
    for stablecoin in sorted(event_effects["stablecoin"].dropna().unique()):
        groups[f"{stablecoin.lower()}_units"] = event_effects[event_effects["stablecoin"] == stablecoin]

    rows = []
    for name, subset in groups.items():
        rows.extend(summarize_group(event_effects, name, subset))
    out = pd.DataFrame(rows)
    out.to_csv(SUMMARY_CSV, index=False)
    return out


def build_comparison_matrix(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    comparisons = [
        ("non_usdc_vs_usdc", "non_usdc_units", "usdc_units"),
        ("ad_hoc_vs_scheduled", "ad_hoc_units", "scheduled_units"),
        ("non_usdc_ad_hoc_vs_non_usdc_scheduled", "non_usdc_ad_hoc_units", "non_usdc_scheduled_units"),
    ]
    for comparison_id, treated, reference in comparisons:
        for window in WINDOWS:
            a = summary[(summary["group"] == treated) & (summary["window_days"] == window)]
            b = summary[(summary["group"] == reference) & (summary["window_days"] == window)]
            if a.empty or b.empty:
                continue
            a_row = a.iloc[0]
            b_row = b.iloc[0]
            rows.append(
                {
                    "comparison_id": comparison_id,
                    "window_days": window,
                    "treated_group": treated,
                    "reference_group": reference,
                    "treated_event_units": a_row["event_units"],
                    "reference_event_units": b_row["event_units"],
                    "treated_mean_delta_abs_bps": a_row["mean_delta_abs_peg_dev_bps"],
                    "reference_mean_delta_abs_bps": b_row["mean_delta_abs_peg_dev_bps"],
                    "difference_in_mean_delta_abs_bps": a_row["mean_delta_abs_peg_dev_bps"] - b_row["mean_delta_abs_peg_dev_bps"],
                    "treated_mean_delta_peer_adjusted_abs_bps": a_row["mean_delta_peer_adjusted_abs_bps"],
                    "reference_mean_delta_peer_adjusted_abs_bps": b_row["mean_delta_peer_adjusted_abs_bps"],
                    "difference_in_mean_delta_peer_adjusted_abs_bps": a_row["mean_delta_peer_adjusted_abs_bps"] - b_row["mean_delta_peer_adjusted_abs_bps"],
                    "interpretation_status": "descriptive_only_small_sample_no_causal_claim",
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(COMPARISON_CSV, index=False)
    return out


def update_task_backlog() -> None:
    if not TASK_BACKLOG_CSV.exists():
        return
    with TASK_BACKLOG_CSV.open("r", newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []
    for row in rows:
        if row.get("task_id") == "T014":
            row["status"] = "in_progress"
            row["notes"] = "Multi-issuer ready events connected to descriptive event-window pilot in P1-I; source verification and final inclusion decision remain open"
        if row.get("task_id") == "T025":
            row["status"] = "done"
            row["notes"] = "Descriptive-only multi-issuer event-window extension generated for BUSD USDT USDP ready rows in P1-I"
    with TASK_BACKLOG_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(
    ready: pd.DataFrame,
    units: pd.DataFrame,
    window_panel: pd.DataFrame,
    effects: pd.DataFrame,
    summary: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    non_usdc_units = units[units["issuer_scope"] == "non_USDC"]
    collapsed_records = int(len(ready) - len(units))
    non_usdc_records = int(len(ready[ready["stablecoin"] != "USDC"]))
    manual_units = int(units["manual_review_required"].sum())
    override_records = int(pd.to_numeric(ready["episode_override_applied"], errors="coerce").sum()) if "episode_override_applied" in ready else 0
    override_units = int(pd.to_numeric(units["episode_override_applied"], errors="coerce").sum()) if "episode_override_applied" in units else 0
    usdt_overlap_units = int(units[(units["stablecoin"] == "USDT") & (units["overlap_risk_7d_window"] == 1)]["event_unit_id"].nunique())
    full_7_units = int(effects[(effects["window_days"] == 7) & (effects["complete_window"] == 1)]["event_unit_id"].nunique())

    summary_cols = [
        "group",
        "window_days",
        "event_units",
        "complete_window_units",
        "mean_delta_abs_peg_dev_bps",
        "mean_delta_peer_adjusted_abs_bps",
        "max_event_day_abs_peg_dev_bps",
    ]
    event_cols = [
        "event_unit_id",
        "stablecoin",
        "event_class",
        "event_date",
        "record_count",
        "manual_review_required",
        "event_day_abs_peg_dev_bps",
        "market_stress_on_event_date",
        "overlap_risk_7d_window",
        "episode_override_applied",
    ]
    comparison_cols = [
        "comparison_id",
        "window_days",
        "treated_event_units",
        "reference_event_units",
        "difference_in_mean_delta_abs_bps",
        "difference_in_mean_delta_peer_adjusted_abs_bps",
        "interpretation_status",
    ]

    memo = [
        "# P1-I Multi-Issuer Event-Window Pilot Memo",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        "## Purpose",
        "",
        "This memo extends the event-window machinery from the USDC-only pilot to all event-study-ready records in the multi-issuer index. The goal is to test whether BUSD, USDT, and USDP ready rows can be linked to the common market panel and summarized with the same event-date rule.",
        "",
        "## Method",
        "",
        f"- Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`).",
        "- Event date uses the frozen rule: `event_date`, derived from publication date where available.",
        "- Event-study-ready issuer records are collapsed into analytic event units by stablecoin, linked event group, and event date.",
        "- The BUSD issuer announcement and NYDFS regulatory record on 2023-02-13 are treated as one analytic event unit to avoid duplicate counting of the same shock.",
        f"- Episode overrides from `{EPISODE_OVERRIDES_CSV.relative_to(ROOT)}` are applied before event-unit construction.",
        "- The USDT Q1 2024 BDO PDF and official news release are treated as one analytic disclosure episode dated 2024-05-01, the public news-release date.",
        "- Windows are calendar-day windows around the event date: +/-3, +/-7, and +/-14.",
        "- Outcomes are own absolute peg deviation, signed peg deviation, tail de-peg indicators, and peer-adjusted absolute peg deviation.",
        "- Peer-adjusted absolute peg deviation subtracts the same-day mean absolute peg deviation of the other stablecoins in the market panel.",
        "",
        "## Coverage",
        "",
        f"- Ready event records loaded: {len(ready)}.",
        f"- Analytic event units after same-date group collapsing: {len(units)}.",
        f"- Collapsed duplicate/source-companion records: {collapsed_records}.",
        f"- Episode-override records applied: {override_records}.",
        f"- Episode-override analytic units: {override_units}.",
        f"- Non-USDC ready records: {non_usdc_records}.",
        f"- Non-USDC analytic event units: {len(non_usdc_units)}.",
        f"- Event-window panel rows: {len(window_panel)}.",
        f"- Event-level effect rows: {len(effects)}.",
        f"- Analytic event units requiring manual/source review: {manual_units}.",
        f"- Units with complete +/-7 measurement windows: {full_7_units}.",
        f"- USDT units with +/-7 overlap risk: {usdt_overlap_units}.",
        "",
        "## Analytic Event Units",
        "",
        md_table(units.drop(columns=["event_date_obj"], errors="ignore"), event_cols),
        "",
        "## Summary Diagnostics",
        "",
        md_table(summary[summary["window_days"].isin(PRIMARY_WINDOWS)], summary_cols, max_rows=24),
        "",
        "## Descriptive Comparison Matrix",
        "",
        md_table(comparison[comparison["window_days"].isin(PRIMARY_WINDOWS)], comparison_cols),
        "",
        "## Interpretation Boundary",
        "",
        "The P1-I outputs support a cross-issuer descriptive extension and identify where non-USDC event windows are usable. They do not support final causal inference, because non-USDC event-unit counts remain small, most non-USDC units still require source verification, and several disclosure events occur during broad market or issuer-specific stress periods.",
        "",
        "## Research Contribution Added by P1-I",
        "",
        "P1-I converts the earlier multi-issuer source index into empirical event-window evidence. The contribution is methodological and diagnostic: the project now has a reproducible bridge from source-level issuer events to cross-issuer market outcomes, plus a peer-adjusted outcome that separates issuer-specific peg movement from market-wide de-peg pressure.",
        "",
        "## Next Research Step",
        "",
        "The next high-value step is P1-H/P2-E: resolve high-priority source verification for BUSD and USDT, then decide whether non-USDC event windows belong in the primary analysis or a sensitivity table.",
    ]
    MEMO_MD.write_text("\n".join(memo) + "\n", encoding="utf-8")

    progress = [
        "# P1-I 阶段进展报告：Multi-Issuer Event-Window Pilot",
        "",
        f"日期：{ACCESS_DATE}",
        "",
        "## 阶段结论",
        "",
        "P1-I 已完成跨发行人事件窗口扩展。当前项目不再只有 USDC scheduled-disclosure event study，而是已经把 BUSD、USDT、USDP 的 event-study-ready 事件连接到统一市场面板，并生成描述性 pre/post 与 peer-adjusted 结果。",
        "",
        "P1-J 更新：USDT Q1 2024 PDF 与官方新闻已通过 episode override 合并为一个 analytic disclosure episode，避免重复计数。",
        "",
        "## 已保存输出",
        "",
        f"- `{EVENT_UNITS_CSV.relative_to(ROOT)}`",
        f"- `{WINDOW_PANEL_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_EFFECTS_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_TIME_CSV.relative_to(ROOT)}`",
        f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{COMPARISON_CSV.relative_to(ROOT)}`",
        f"- `{MEMO_MD.relative_to(ROOT)}`",
        f"- `{STATUS_MD.relative_to(ROOT)}`",
        f"- `{LOG_MD.relative_to(ROOT)}`",
        f"- `{PROGRESS_MD.relative_to(ROOT)}`",
        "",
        "## 核查计数",
        "",
        f"- event-study-ready records：{len(ready)}。",
        f"- analytic event units：{len(units)}。",
        f"- episode-override records：{override_records}。",
        f"- episode-override units：{override_units}。",
        f"- non-USDC event units：{len(non_usdc_units)}。",
        f"- window panel rows：{len(window_panel)}。",
        f"- event-level effects rows：{len(effects)}。",
        f"- summary rows：{len(summary)}。",
        f"- comparison rows：{len(comparison)}。",
        "",
        "## 下一步计划",
        "",
        "1. P1-H：优先复核 BUSD wind-down 与 USDT Q1 2024 source records。",
        "2. P2-E：生成 researcher-reviewed source verification triage，辅助人工快速关闭 P0/P1 队列。",
        "3. P2-D：把 P1-I 的结果整合入正式论文结果段，明确正文/附录边界。",
        "4. 若 source verification 关闭，可进一步尝试 pooled descriptive regression 或 matched-event appendix。",
    ]
    PROGRESS_MD.write_text("\n".join(progress) + "\n", encoding="utf-8")

    status = [
        "# Project Status Update: P1-I Multi-Issuer Event-Window Pilot",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        f"Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`)",
        "",
        "## Current Status",
        "",
        "P1-I/P1-J has generated a cross-issuer descriptive event-window extension using all event-study-ready multi-issuer records, with the USDT Q1 2024 PDF/news pair merged into one analytic disclosure episode.",
        "",
        "## Main Outputs",
        "",
        f"- `{EVENT_UNITS_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_EFFECTS_CSV.relative_to(ROOT)}`",
        f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{COMPARISON_CSV.relative_to(ROOT)}`",
        f"- `{MEMO_MD.relative_to(ROOT)}`",
        "",
        "## Readiness Judgment",
        "",
        "The project is ready for source-verification closure and release-level integration of the multi-issuer extension. Non-USDC results remain descriptive until source verification and small-sample limitations are explicitly resolved.",
    ]
    STATUS_MD.write_text("\n".join(status) + "\n", encoding="utf-8")

    log = [
        "# Multi-Issuer Event-Window Build Log",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        f"Event index input: `{EVENT_INDEX_CSV.relative_to(ROOT)}`",
        f"Market input: `{MARKET_CSV.relative_to(ROOT)}`",
        f"Output directory: `{OUT_DIR.relative_to(ROOT)}`",
        "",
        f"Ready event records: {len(ready)}",
        f"Analytic event units: {len(units)}",
        f"Non-USDC analytic event units: {len(non_usdc_units)}",
        f"Episode-override records applied: {override_records}",
        f"Episode-override analytic units: {override_units}",
        f"Window panel rows: {len(window_panel)}",
        f"Event effect rows: {len(effects)}",
        "",
        "Analytic design: same stablecoin, linked_event_group, and event_date collapsed into one event unit; explicit episode overrides are applied before collapsing.",
        "Interpretation: descriptive-only extension; source verification remains pending for most non-USDC units.",
    ]
    LOG_MD.write_text("\n".join(log) + "\n", encoding="utf-8")


def main() -> None:
    market = load_market()
    ready = load_ready_events()
    units = build_event_units(ready, market)
    window_panel = build_window_panel(units, market)
    effects = build_event_effects(window_panel, units)
    event_time = build_event_time_average(window_panel)
    summary = build_summary(effects)
    comparison = build_comparison_matrix(summary)
    write_reports(ready, units, window_panel, effects, summary, comparison)
    update_task_backlog()

    _ = event_time


if __name__ == "__main__":
    main()
