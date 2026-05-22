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
DISCLOSURE_CSV = ROOT / "02_manual_coding" / "rqi_dii_pilot_coding_v1.csv"
MARKET_CSV = ROOT / "04_processed_data" / "minimum_viable_panel_v1.csv"
EVENT_CLASS_CSV = ROOT / "02_manual_coding" / "event_classification_table_v1.csv"
OUT_DIR = ROOT / "05_analysis" / "event_study_results_v1"
WINDOW_PANEL_CSV = OUT_DIR / "event_window_panel_v1.csv"
EVENT_EFFECTS_CSV = OUT_DIR / "event_level_effects_v1.csv"
EVENT_TIME_CSV = OUT_DIR / "event_time_average_v1.csv"
SUMMARY_CSV = OUT_DIR / "event_study_summary_v1.csv"
LOG_MD = ROOT / "99_logs" / "event_study_log_20260522.md"
MEMO_MD = ROOT / "06_outputs" / "P1B_EVENT_STUDY_PILOT_MEMO_20260522.md"
PROGRESS_MD = ROOT / "06_outputs" / "P1_PHASE_B_PROGRESS_20260522.md"

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
WINDOW_MAX = max([*PRIMARY_WINDOWS, *ROBUSTNESS_WINDOWS])
PROVISIONAL_REASON = "event_classification_and_source_expansion_pending"


def parse_date(value: Any) -> dt.date | None:
    if pd.isna(value) or value == "":
        return None
    try:
        return dt.date.fromisoformat(str(value))
    except ValueError:
        return None


def fmt(value: Any, digits: int = 6) -> str:
    if value is None or pd.isna(value):
        return ""
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.{digits}f}".rstrip("0").rstrip(".")


def load_disclosures() -> pd.DataFrame:
    df = pd.read_csv(DISCLOSURE_CSV)
    df = df[df["stablecoin"] == "USDC"].copy()
    df["publication_date_obj"] = df["publication_date"].apply(parse_date)
    df["latest_report_date_obj"] = df["latest_report_date"].apply(parse_date)
    for col in ["pilot_rqi", "pilot_dii", "publication_lag_days"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["manual_review_required"] = pd.to_numeric(df["manual_review_required"], errors="coerce").fillna(1).astype(int)
    return df


def load_market() -> pd.DataFrame:
    df = pd.read_csv(MARKET_CSV)
    df["date_obj"] = pd.to_datetime(df["date"]).dt.date
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
        "market_stress_flag",
        "pilot_rqi_asof",
        "pilot_dii_asof",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df["abs_peg_dev_bps"] = df["abs_peg_dev"] * 10000
    df["peg_dev_bps"] = df["peg_dev"] * 10000
    return df


def build_event_classification(disclosures: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    market_by_date = market.set_index("date_obj")
    events = disclosures[disclosures["publication_date_obj"].notna()].copy()
    events = events.sort_values("publication_date_obj").reset_index(drop=True)
    event_dates = list(events["publication_date_obj"])

    rows = []
    for i, row in events.iterrows():
        event_date = row["publication_date_obj"]
        market_row = market_by_date.loc[event_date] if event_date in market_by_date.index else None
        previous_gap = (event_date - event_dates[i - 1]).days if i > 0 else None
        next_gap = (event_dates[i + 1] - event_date).days if i + 1 < len(event_dates) else None
        overlap_7d = (
            previous_gap is not None and previous_gap <= 14
        ) or (
            next_gap is not None and next_gap <= 14
        )
        overlap_14d = (
            previous_gap is not None and previous_gap <= 28
        ) or (
            next_gap is not None and next_gap <= 28
        )
        rows.append(
            {
                "event_id": row["event_id"],
                "stablecoin": row["stablecoin"],
                "issuer": row["issuer"],
                "event_date": event_date.isoformat(),
                "publication_date": event_date.isoformat(),
                "report_date": row.get("latest_report_date", ""),
                "event_type": row.get("document_family", "monthly_assurance"),
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "scheduled_flag": row.get("scheduled_flag", "1"),
                "ad_hoc_flag": row.get("ad_hoc_flag", "0"),
                "stress_regime_disclosure": row.get("stress_regime_flag", "normal"),
                "market_stress_on_event_date": int(market_row["market_stress_flag"]) if market_row is not None and not pd.isna(market_row["market_stress_flag"]) else "",
                "market_stress_types_on_event_date": market_row["market_stress_types"] if market_row is not None else "",
                "pilot_rqi": fmt(row["pilot_rqi"], 6),
                "pilot_dii": fmt(row["pilot_dii"], 6),
                "has_rqi": int(not pd.isna(row["pilot_rqi"])),
                "has_dii": int(not pd.isna(row["pilot_dii"])),
                "manual_review_required": int(row["manual_review_required"]),
                "asset_extraction_confidence": row.get("asset_extraction_confidence", ""),
                "publication_lag_days": fmt(row["publication_lag_days"], 0),
                "previous_event_gap_days": "" if previous_gap is None else previous_gap,
                "next_event_gap_days": "" if next_gap is None else next_gap,
                "overlap_risk_7d_window": int(overlap_7d),
                "overlap_risk_14d_window": int(overlap_14d),
                "classification_status": "rules_frozen_source_review_required" if int(row["manual_review_required"]) else "rules_frozen_high_confidence",
                "provisional_reason": PROVISIONAL_REASON if int(row["manual_review_required"]) else "pilot_single_issuer_event_set",
                "notes": row.get("notes", ""),
            }
        )
    out = pd.DataFrame(rows)
    EVENT_CLASS_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(EVENT_CLASS_CSV, index=False)
    return out


def build_window_panel(events: pd.DataFrame, market: pd.DataFrame) -> pd.DataFrame:
    market_by_date = market.set_index("date_obj")
    rows = []
    for _, event in events.iterrows():
        event_date = parse_date(event["event_date"])
        if event_date is None:
            continue
        for rel_day in range(-WINDOW_MAX, WINDOW_MAX + 1):
            day = event_date + dt.timedelta(days=rel_day)
            if day not in market_by_date.index:
                continue
            m = market_by_date.loc[day]
            rows.append(
                {
                    "event_id": event["event_id"],
                    "event_date": event["event_date"],
                    "date": day.isoformat(),
                    "relative_day": rel_day,
                    "in_window_3d": int(abs(rel_day) <= 3),
                    "in_window_7d": int(abs(rel_day) <= 7),
                    "pre_3d": int(-3 <= rel_day <= -1),
                    "post_3d": int(0 <= rel_day <= 3),
                    "pre_7d": int(-7 <= rel_day <= -1),
                    "post_7d": int(0 <= rel_day <= 7),
                    "event_day": int(rel_day == 0),
                    "price_usd": m["price_usd"],
                    "peg_dev_bps": m["peg_dev_bps"],
                    "abs_peg_dev_bps": m["abs_peg_dev_bps"],
                    "tail_depeg_50bp": m["tail_depeg_50bp"],
                    "tail_depeg_100bp": m["tail_depeg_100bp"],
                    "market_stress_flag": m["market_stress_flag"],
                    "market_stress_types": m["market_stress_types"],
                    "circulating_face_usd": m["circulating_face_usd"],
                    "event_pilot_rqi": pd.to_numeric(event["pilot_rqi"], errors="coerce"),
                    "event_pilot_dii": pd.to_numeric(event["pilot_dii"], errors="coerce"),
                    "event_has_rqi": event["has_rqi"],
                    "event_has_dii": event["has_dii"],
                    "event_manual_review_required": event["manual_review_required"],
                    "event_stress_regime_disclosure": event["stress_regime_disclosure"],
                    "overlap_risk_7d_window": event["overlap_risk_7d_window"],
                    "overlap_risk_14d_window": event["overlap_risk_14d_window"],
                    "classification_status": event["classification_status"],
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    out = pd.DataFrame(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(WINDOW_PANEL_CSV, index=False)
    return out


def mean_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else np.nan


def max_or_nan(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.max()) if len(values) else np.nan


def build_event_effects(window_panel: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, event in events.iterrows():
        event_rows = window_panel[window_panel["event_id"] == event["event_id"]].copy()
        event_day = event_rows[event_rows["relative_day"] == 0]
        for window in PRIMARY_WINDOWS:
            pre = event_rows[(event_rows["relative_day"] >= -window) & (event_rows["relative_day"] <= -1)]
            post = event_rows[(event_rows["relative_day"] >= 0) & (event_rows["relative_day"] <= window)]
            pre_abs = mean_or_nan(pre["abs_peg_dev_bps"])
            post_abs = mean_or_nan(post["abs_peg_dev_bps"])
            pre_tail50 = mean_or_nan(pre["tail_depeg_50bp"])
            post_tail50 = mean_or_nan(post["tail_depeg_50bp"])
            rows.append(
                {
                    "event_id": event["event_id"],
                    "event_date": event["event_date"],
                    "window_days": window,
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
                    "event_pilot_rqi": pd.to_numeric(event["pilot_rqi"], errors="coerce"),
                    "event_pilot_dii": pd.to_numeric(event["pilot_dii"], errors="coerce"),
                    "event_has_rqi": event["has_rqi"],
                    "event_has_dii": event["has_dii"],
                    "event_manual_review_required": event["manual_review_required"],
                    "event_stress_regime_disclosure": event["stress_regime_disclosure"],
                    "market_stress_on_event_date": event["market_stress_on_event_date"],
                    "overlap_risk_7d_window": event["overlap_risk_7d_window"],
                    "classification_status": event["classification_status"],
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
    grouped = window_panel.groupby("relative_day", as_index=False).agg(
        n_events=("event_id", "nunique"),
        n_rows=("event_id", "count"),
        mean_abs_peg_dev_bps=("abs_peg_dev_bps", "mean"),
        median_abs_peg_dev_bps=("abs_peg_dev_bps", "median"),
        mean_peg_dev_bps=("peg_dev_bps", "mean"),
        tail50_rate=("tail_depeg_50bp", "mean"),
        tail100_rate=("tail_depeg_100bp", "mean"),
        market_stress_share=("market_stress_flag", "mean"),
        manual_review_event_share=("event_manual_review_required", "mean"),
        has_rqi_share=("event_has_rqi", "mean"),
    )
    grouped["rule_version"] = RULE_VERSION
    grouped["rule_status"] = RULE_STATUS
    grouped.to_csv(EVENT_TIME_CSV, index=False)
    return grouped


def build_summary(event_effects: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = {
        "all_scheduled_publication_events": event_effects,
        "events_with_rqi": event_effects[event_effects["event_has_rqi"] == 1],
        "manual_review_free_events": event_effects[event_effects["event_manual_review_required"] == 0],
        "manual_review_required_events": event_effects[event_effects["event_manual_review_required"] == 1],
        "banking_stress_disclosure_events": event_effects[event_effects["event_stress_regime_disclosure"] == "banking_stress"],
        "normal_disclosure_events": event_effects[event_effects["event_stress_regime_disclosure"] == "normal"],
    }
    for group_name, data in groups.items():
        for window in PRIMARY_WINDOWS:
            subset = data[data["window_days"] == window]
            rows.append(
                {
                    "group": group_name,
                    "window_days": window,
                    "events": subset["event_id"].nunique(),
                    "mean_pre_abs_peg_dev_bps": mean_or_nan(subset["pre_mean_abs_peg_dev_bps"]),
                    "mean_post_abs_peg_dev_bps": mean_or_nan(subset["post_mean_abs_peg_dev_bps"]),
                    "mean_delta_abs_peg_dev_bps": mean_or_nan(subset["delta_post_minus_pre_abs_peg_dev_bps"]),
                    "median_delta_abs_peg_dev_bps": float(pd.to_numeric(subset["delta_post_minus_pre_abs_peg_dev_bps"], errors="coerce").median()) if len(subset) else np.nan,
                    "max_event_day_abs_peg_dev_bps": max_or_nan(subset["event_day_abs_peg_dev_bps"]),
                    "mean_post_tail50_rate": mean_or_nan(subset["post_tail50_rate"]),
                    "mean_delta_tail50_rate": mean_or_nan(subset["delta_post_minus_pre_tail50_rate"]),
                    "rule_version": RULE_VERSION,
                    "rule_status": RULE_STATUS,
                    "provisional_flag": 1,
                    "provisional_reason": PROVISIONAL_REASON,
                }
            )
    out = pd.DataFrame(rows)
    out.to_csv(SUMMARY_CSV, index=False)
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
            value = row[col]
            if isinstance(value, float):
                values.append(fmt(value, 4))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_reports(
    disclosures: pd.DataFrame,
    events: pd.DataFrame,
    window_panel: pd.DataFrame,
    event_effects: pd.DataFrame,
    event_time: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    missing_pub = int(disclosures["publication_date_obj"].isna().sum())
    event_count = len(events)
    manual_events = int(pd.to_numeric(events["manual_review_required"], errors="coerce").sum())
    has_rqi = int(pd.to_numeric(events["has_rqi"], errors="coerce").sum())
    has_dii = int(pd.to_numeric(events["has_dii"], errors="coerce").sum())
    overlap_7 = int(pd.to_numeric(events["overlap_risk_7d_window"], errors="coerce").sum())
    overlap_14 = int(pd.to_numeric(events["overlap_risk_14d_window"], errors="coerce").sum())

    LOG_MD.write_text(
        "\n".join(
            [
                "# Event Study Log",
                "",
                f"Date: {ACCESS_DATE}",
                "",
                f"Disclosure input: `{DISCLOSURE_CSV.relative_to(ROOT)}`",
                f"Market input: `{MARKET_CSV.relative_to(ROOT)}`",
                "",
                f"Event classification output: `{EVENT_CLASS_CSV.relative_to(ROOT)}`",
                f"Event-study output directory: `{OUT_DIR.relative_to(ROOT)}`",
                "",
                f"USDC disclosures loaded: {len(disclosures)}",
                f"Disclosures excluded for missing publication_date: {missing_pub}",
                f"Events included: {event_count}",
                f"Window panel rows: {len(window_panel)}",
                f"Event-level effect rows: {len(event_effects)}",
                "",
                f"Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`)",
                "",
                "Window rule: relative days -14 to +14 around publication_date; primary windows are [-3,+3] and [-7,+7].",
                "All outputs remain pilot because event classification, ad hoc event coverage, and source expansion are not yet final.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_cols = [
        "group",
        "window_days",
        "events",
        "mean_pre_abs_peg_dev_bps",
        "mean_post_abs_peg_dev_bps",
        "mean_delta_abs_peg_dev_bps",
        "mean_post_tail50_rate",
    ]
    memo = [
        "# P1-B Event Study Pilot Memo",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        "## Purpose",
        "",
        "This memo documents the first USDC scheduled-disclosure event-study dataset. It tests event-window construction around disclosure publication dates. It does not estimate final causal disclosure effects.",
        "",
        "## Identification Boundary",
        "",
        "- Events are USDC monthly assurance publications with non-missing `publication_date`.",
        "- Event date equals `publication_date`, not reserve report date.",
        "- Current event set is scheduled disclosure only; no ad hoc issuer events are included.",
        "- Windows are calendar-day windows, not intraday windows.",
        f"- RQI/DII rules use `{RULE_VERSION}`; results remain pilot pending event-classification review and source expansion.",
        "",
        "## Event Coverage",
        "",
        f"- USDC disclosure rows loaded: {len(disclosures)}.",
        f"- Events included with publication date: {event_count}.",
        f"- Disclosures excluded for missing publication date: {missing_pub}.",
        f"- Events with RQI: {has_rqi}.",
        f"- Events with DII: {has_dii}.",
        f"- Events requiring manual review: {manual_events}.",
        f"- Events with +/-7 day overlap risk: {overlap_7}.",
        f"- Events with +/-14 day overlap risk: {overlap_14}.",
        "",
        "## Event-Study Summary",
        "",
        md_table(summary, summary_cols),
        "",
        "## Technical Reading",
        "",
        f"The event-window machinery is now operational under `{RULE_VERSION}`. The scheduled monthly USDC disclosures generally have limited overlap in +/-7 day windows, but many events inherit manual-review flags because source-level verification is still open. The event-study output should therefore be used to evaluate design feasibility and window behavior, not to make a final empirical claim.",
        "",
        "## Next Research Step",
        "",
        "The next substantive step is to add ad hoc and multi-issuer events, especially USDT reserve-report releases and Paxos/BUSD regulatory events, so scheduled and ad hoc disclosures can be compared rather than merely described for USDC.",
    ]
    MEMO_MD.write_text("\n".join(memo) + "\n", encoding="utf-8")

    progress = [
        "# P1-B 阶段进展报告：Disclosure Event-Study Pilot",
        "",
        f"日期：{ACCESS_DATE}",
        "",
        "## 阶段结论",
        "",
        "P1-B 已完成第一版 USDC scheduled-disclosure event-study 数据构建。事件日、事件窗口、pre/post 变化、relative-day 平均路径均已生成。",
        "",
        "这一步确认了事件研究管线可运行；但当前只覆盖 USDC 月度 scheduled assurance disclosure，不包括 ad hoc 事件，因此还不能支撑 scheduled vs ad hoc 的正式比较。",
        "",
        "## 已保存输出",
        "",
        f"- `{EVENT_CLASS_CSV.relative_to(ROOT)}`",
        f"- `{WINDOW_PANEL_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_EFFECTS_CSV.relative_to(ROOT)}`",
        f"- `{EVENT_TIME_CSV.relative_to(ROOT)}`",
        f"- `{SUMMARY_CSV.relative_to(ROOT)}`",
        f"- `{LOG_MD.relative_to(ROOT)}`",
        f"- `{MEMO_MD.relative_to(ROOT)}`",
        f"- `{PROGRESS_MD.relative_to(ROOT)}`",
        "",
        "## 质量检查",
        "",
        f"- USDC disclosure rows：{len(disclosures)}。",
        f"- 纳入事件数：{event_count}。",
        f"- 因缺少 publication_date 排除：{missing_pub}。",
        f"- 事件窗口行数：{len(window_panel)}。",
        f"- 事件层面 pre/post rows：{len(event_effects)}。",
        f"- 需要人工复核的事件：{manual_events}。",
        f"- +/-7 day overlap risk events：{overlap_7}。",
        f"- +/-14 day overlap risk events：{overlap_14}。",
        "",
        "## 下一步计划",
        "",
        "1. 推进 USDT 与 Paxos 披露事件归档，补足 ad hoc 与非 USDC 事件。",
        "2. 人工审核 `event_classification_table_v1.csv`。",
        "3. 在冻结规则下执行 +/-14、压力期、manual-review-free 等稳健性检验。",
        "4. 推进多发行人与 ad hoc 事件扩展，使 scheduled vs ad hoc 比较具备样本基础。",
    ]
    PROGRESS_MD.write_text("\n".join(progress) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    disclosures = load_disclosures()
    market = load_market()
    events = build_event_classification(disclosures, market)
    window_panel = build_window_panel(events, market)
    event_effects = build_event_effects(window_panel, events)
    event_time = build_event_time_average(window_panel)
    summary = build_summary(event_effects)
    write_reports(disclosures, events, window_panel, event_effects, event_time, summary)


if __name__ == "__main__":
    main()
