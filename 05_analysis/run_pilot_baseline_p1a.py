from __future__ import annotations

import csv
import datetime as dt
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG_PATH = ROOT / "00_admin" / "rqi_dii_rules_v1_config.json"
INPUT_CSV = ROOT / "04_processed_data" / "minimum_viable_panel_v1.csv"
OUT_DIR = ROOT / "05_analysis" / "baseline_results_v1"
COEF_CSV = OUT_DIR / "baseline_model_coefficients_v1.csv"
MODEL_CSV = OUT_DIR / "baseline_model_summary_v1.csv"
DIAG_CSV = OUT_DIR / "baseline_sample_diagnostics_v1.csv"
PRED_CSV = OUT_DIR / "baseline_model_predictions_v1.csv"
LOG_MD = ROOT / "99_logs" / "baseline_model_log_20260522.md"
MEMO_MD = ROOT / "06_outputs" / "P1A_BASELINE_PILOT_MEMO_20260522.md"
PROGRESS_MD = ROOT / "06_outputs" / "P1_PHASE_A_PROGRESS_20260522.md"

ACCESS_DATE = "2026-05-22"
HAC_LAGS = 7


def load_rule_config() -> dict[str, Any]:
    with RULE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


RULE_CONFIG = load_rule_config()
RULE_VERSION = RULE_CONFIG.get("rule_version", "RQI_DII_v1.0")
RULE_STATUS = RULE_CONFIG.get("rule_status", "frozen_confirmed_by_researcher")
PROVISIONAL_REASON = "single_issuer_pilot_pending_multi_issuer_and_market_qc"


def parse_date(value: Any) -> dt.date | None:
    if pd.isna(value) or value == "":
        return None
    return dt.date.fromisoformat(str(value))


def load_panel() -> pd.DataFrame:
    df = pd.read_csv(INPUT_CSV)
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
        "pilot_rqi_asof",
        "pilot_dii_asof",
        "disclosure_manual_review_required_asof",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    first_date = df["date_obj"].min()
    df["trend_years"] = (df["date_obj"] - first_date).dt.days / 365.25
    df["abs_peg_dev_bps"] = df["abs_peg_dev"] * 10000
    df["tail_depeg_50bp_pct"] = df["tail_depeg_50bp"] * 100
    df["downside_depeg_50bp_pct"] = df["downside_depeg_50bp"] * 100
    df["rqi_10pp"] = df["pilot_rqi_asof"] * 10
    df["dii_10pp"] = df["pilot_dii_asof"] * 10
    df["days_since_disclosure_30d"] = df["days_since_disclosure"] / 30
    df["log_supply"] = np.log(df["circulating_face_usd"])
    df["manual_review_asof"] = df["disclosure_manual_review_required_asof"].fillna(0)
    df["stress_x_rqi_10pp"] = df["market_stress_flag"] * df["rqi_10pp"]
    df["stress_x_dii_10pp"] = df["market_stress_flag"] * df["dii_10pp"]
    return df


def clean_design(df: pd.DataFrame, y_col: str, x_cols: list[str]) -> tuple[pd.DataFrame, np.ndarray, np.ndarray, list[str]]:
    cols = [y_col] + x_cols
    data = df[["date", *cols]].replace([np.inf, -np.inf], np.nan).dropna(subset=cols).copy()
    kept_x = []
    for col in x_cols:
        values = data[col].to_numpy(dtype=float)
        if len(values) == 0:
            continue
        if np.nanstd(values) < 1e-12:
            continue
        kept_x.append(col)
    y = data[y_col].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(data)), *[data[col].to_numpy(dtype=float) for col in kept_x]])
    names = ["Intercept", *kept_x]
    return data, y, X, names


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


def ols_hac(df: pd.DataFrame, model_id: str, label: str, y_col: str, x_cols: list[str]) -> tuple[list[dict[str, Any]], dict[str, Any], pd.DataFrame]:
    data, y, X, names = clean_design(df, y_col, x_cols)
    n, k = X.shape
    if n <= k + 5:
        raise ValueError(f"Insufficient rows for {model_id}: n={n}, k={k}")
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
                "model_id": model_id,
                "model_label": label,
                "outcome": y_col,
                "term": name,
                "coef": b,
                "hac_se_lag7": s,
                "t_stat": t_stat,
                "p_value": p_value,
                "n": n,
                "r2": r2,
                "adj_r2": adj_r2,
                "interpretation_unit": interpretation_unit(name),
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "provisional_flag": 1,
                "provisional_reason": PROVISIONAL_REASON,
            }
        )

    summary = {
        "model_id": model_id,
        "model_label": label,
        "outcome": y_col,
        "n": n,
        "k": k,
        "start_date": data["date"].iloc[0],
        "end_date": data["date"].iloc[-1],
        "y_mean": float(np.mean(y)),
        "y_sd": float(np.std(y, ddof=1)),
        "y_min": float(np.min(y)),
        "y_max": float(np.max(y)),
        "r2": r2,
        "adj_r2": adj_r2,
        "hac_lags": HAC_LAGS,
        "sample_rule": "drop rows with missing outcome or model covariates",
        "rule_version": RULE_VERSION,
        "rule_status": RULE_STATUS,
        "provisional_flag": 1,
        "provisional_reason": PROVISIONAL_REASON,
    }

    predictions = data[["date"]].copy()
    predictions["model_id"] = model_id
    predictions["rule_version"] = RULE_VERSION
    predictions["rule_status"] = RULE_STATUS
    predictions["actual"] = y
    predictions["fitted"] = fitted
    predictions["residual"] = residuals
    return coef_rows, summary, predictions


def interpretation_unit(term: str) -> str:
    if term in {"rqi_10pp", "dii_10pp", "stress_x_rqi_10pp", "stress_x_dii_10pp"}:
        return "coefficient per 10 percentage point increase in index"
    if term == "days_since_disclosure_30d":
        return "coefficient per 30 days since latest disclosure"
    if term == "log_supply":
        return "coefficient per one log point of circulating face supply"
    if term in {"market_stress_flag", "stale_disclosure_45d", "manual_review_asof"}:
        return "coefficient for indicator changing from 0 to 1"
    if term == "trend_years":
        return "coefficient per calendar year"
    return ""


def model_specs() -> list[dict[str, Any]]:
    controls = ["days_since_disclosure_30d", "stale_disclosure_45d", "market_stress_flag", "log_supply", "trend_years"]
    return [
        {
            "model_id": "M1_absdev_dii",
            "label": "Abs peg deviation on DII and controls",
            "outcome": "abs_peg_dev_bps",
            "covariates": ["dii_10pp", *controls],
        },
        {
            "model_id": "M2_absdev_rqi_dii",
            "label": "Abs peg deviation on RQI, DII, and controls",
            "outcome": "abs_peg_dev_bps",
            "covariates": ["rqi_10pp", "dii_10pp", *controls],
        },
        {
            "model_id": "M3_tail50_rqi_dii_lpm",
            "label": "50bp tail depeg linear probability pilot",
            "outcome": "tail_depeg_50bp_pct",
            "covariates": ["rqi_10pp", "dii_10pp", *controls],
        },
        {
            "model_id": "M4_downside50_rqi_dii_lpm",
            "label": "50bp downside depeg linear probability pilot",
            "outcome": "downside_depeg_50bp_pct",
            "covariates": ["rqi_10pp", "dii_10pp", *controls],
        },
        {
            "model_id": "M5_absdev_stress_interaction",
            "label": "Abs peg deviation with stress interactions",
            "outcome": "abs_peg_dev_bps",
            "covariates": [
                "rqi_10pp",
                "dii_10pp",
                "market_stress_flag",
                "stress_x_rqi_10pp",
                "stress_x_dii_10pp",
                "days_since_disclosure_30d",
                "stale_disclosure_45d",
                "log_supply",
                "trend_years",
            ],
        },
        {
            "model_id": "M6_absdev_high_confidence",
            "label": "Abs peg deviation, manual-review-free disclosure rows",
            "outcome": "abs_peg_dev_bps",
            "covariates": ["rqi_10pp", "dii_10pp", *controls],
            "filter": "manual_review_asof == 0",
        },
    ]


def run_models(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    coef_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    prediction_frames = []
    for spec in model_specs():
        sample = df.copy()
        if spec.get("filter") == "manual_review_asof == 0":
            sample = sample[sample["manual_review_asof"] == 0].copy()
        rows, summary, predictions = ols_hac(
            sample,
            spec["model_id"],
            spec["label"],
            spec["outcome"],
            spec["covariates"],
        )
        coef_rows.extend(rows)
        summary_rows.append({**summary, "filter": spec.get("filter", "")})
        prediction_frames.append(predictions)

    return pd.DataFrame(coef_rows), pd.DataFrame(summary_rows), pd.concat(prediction_frames, ignore_index=True)


def diagnostics(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = {
        "all_usdc_market_days": df,
        "with_prior_disclosure": df[df["latest_disclosure_event_id"].notna() & (df["latest_disclosure_event_id"] != "")],
        "with_rqi_asof": df[df["pilot_rqi_asof"].notna()],
        "with_dii_asof": df[df["pilot_dii_asof"].notna()],
        "manual_review_free": df[df["manual_review_asof"] == 0],
        "market_stress_rows": df[df["market_stress_flag"] == 1],
    }
    for name, subset in groups.items():
        rows.append(
            {
                "sample": name,
                "rows": len(subset),
                "start_date": subset["date"].iloc[0] if len(subset) else "",
                "end_date": subset["date"].iloc[-1] if len(subset) else "",
                "mean_abs_peg_dev_bps": subset["abs_peg_dev_bps"].mean(),
                "max_abs_peg_dev_bps": subset["abs_peg_dev_bps"].max(),
                "tail_50bp_days": int(subset["tail_depeg_50bp"].sum(skipna=True)) if len(subset) else 0,
                "tail_100bp_days": int(subset["tail_depeg_100bp"].sum(skipna=True)) if len(subset) else 0,
                "mean_rqi": subset["pilot_rqi_asof"].mean(),
                "mean_dii": subset["pilot_dii_asof"].mean(),
                "stale_45d_days": int(subset["stale_disclosure_45d"].sum(skipna=True)) if len(subset) else 0,
                "manual_review_days": int(subset["manual_review_asof"].sum(skipna=True)) if len(subset) else 0,
            }
        )
    return pd.DataFrame(rows)


def fmt_num(value: Any, digits: int = 4) -> str:
    if value is None or pd.isna(value):
        return ""
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.2f}"
    return f"{value:.{digits}f}"


def key_term_table(coefs: pd.DataFrame) -> str:
    keep_terms = [
        "rqi_10pp",
        "dii_10pp",
        "market_stress_flag",
        "stress_x_rqi_10pp",
        "stress_x_dii_10pp",
        "stale_disclosure_45d",
    ]
    key = coefs[coefs["term"].isin(keep_terms)].copy()
    lines = [
        "| model | term | coef | HAC se | p-value |",
        "|---|---|---:|---:|---:|",
    ]
    for _, row in key.iterrows():
        lines.append(
            f"| {row['model_id']} | {row['term']} | {fmt_num(row['coef'])} | {fmt_num(row['hac_se_lag7'])} | {fmt_num(row['p_value'])} |"
        )
    return "\n".join(lines)


def write_reports(df: pd.DataFrame, coefs: pd.DataFrame, summaries: pd.DataFrame, diags: pd.DataFrame) -> None:
    rqi_rows = int(df["pilot_rqi_asof"].notna().sum())
    dii_rows = int(df["pilot_dii_asof"].notna().sum())
    tail50 = int(df["tail_depeg_50bp"].sum(skipna=True))
    tail100 = int(df["tail_depeg_100bp"].sum(skipna=True))
    stress_rows = int(df["market_stress_flag"].sum(skipna=True))
    manual_rows = int(df["manual_review_asof"].sum(skipna=True))

    LOG_MD.write_text(
        "\n".join(
            [
                "# Baseline Model Log",
                "",
                f"Date: {ACCESS_DATE}",
                "",
                f"Input: `{INPUT_CSV.relative_to(ROOT)}`",
                "",
                f"Output directory: `{OUT_DIR.relative_to(ROOT)}`",
                "",
                f"Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`)",
                "",
                "Method: OLS and linear probability models with 7-day Newey-West HAC standard errors.",
                "",
                "Model outputs remain pilot because the current sample is USDC-only and market/source QC gates remain active.",
                "",
                f"Rows: {len(df)}",
                f"RQI as-of rows: {rqi_rows}",
                f"DII as-of rows: {dii_rows}",
                f"50bp tail days: {tail50}",
                f"100bp tail days: {tail100}",
                f"Market stress rows: {stress_rows}",
                f"Rows inheriting manual-review flags: {manual_rows}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    memo = [
        "# P1-A Baseline Pilot Memo",
        "",
        f"Date: {ACCESS_DATE}",
        "",
        "## Purpose",
        "",
        "This memo reports a pilot baseline model run on the USDC minimum viable panel. It tests whether the empirical pipeline can run end to end. It does not provide final causal evidence.",
        "",
        "## Model Boundary",
        "",
        "- Sample is USDC only, so this is not yet a multi-issuer panel design.",
        "- Disclosure variables are assigned by `latest publication_date <= market date`.",
        "- Standard errors use 7-day Newey-West HAC adjustment.",
        "- Tail de-peg events are rare; 100bp outcomes are diagnostic only.",
        f"- RQI/DII rules use `{RULE_VERSION}`; coefficient interpretation remains pilot-only until multi-issuer and market-QC stages are complete.",
        "",
        "## Sample Diagnostics",
        "",
        "| sample | rows | mean_abs_peg_dev_bps | max_abs_peg_dev_bps | tail_50bp_days | tail_100bp_days | mean_rqi | mean_dii |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in diags.iterrows():
        memo.append(
            f"| {row['sample']} | {int(row['rows'])} | {fmt_num(row['mean_abs_peg_dev_bps'])} | {fmt_num(row['max_abs_peg_dev_bps'])} | {int(row['tail_50bp_days'])} | {int(row['tail_100bp_days'])} | {fmt_num(row['mean_rqi'])} | {fmt_num(row['mean_dii'])} |"
        )

    memo.extend(
        [
            "",
            "## Key Coefficients",
            "",
            key_term_table(coefs),
            "",
            "## Technical Reading",
            "",
            f"The baseline scripts run successfully under `{RULE_VERSION}` and produce interpretable diagnostic output. The strongest and most stable predictor in this pilot is the market-stress indicator, which is expected because the USDC SVB episode is directly visible in the daily price data. RQI and DII coefficients should not be interpreted substantively yet because the sample is single-issuer and manual-review rows still dominate large parts of the as-of series.",
            "",
            "## Research Status",
            "",
            "P1-A confirms that the data architecture can support regression-style analysis under a frozen pilot rule set. The project can proceed to robustness execution and multi-issuer disclosure expansion, but final inference remains blocked by source verification, ad hoc event coverage, and market-data abnormal-price decisions.",
        ]
    )
    MEMO_MD.write_text("\n".join(memo) + "\n", encoding="utf-8")

    progress = [
        "# P1-A 阶段进展报告：Baseline Pilot Model",
        "",
        f"日期：{ACCESS_DATE}",
        "",
        "## 阶段结论",
        "",
        "P1-A 已完成第一版 baseline pilot model。模型已经可以从 `minimum_viable_panel_v1.csv` 自动生成样本、运行 OLS/LPM、输出 HAC 标准误、保存系数表与诊断报告。",
        "",
        "这意味着项目已经从“数据合并可行”进入“模型管线可运行”的阶段；但它仍不是正式论文结果。",
        "",
        "## 已保存输出",
        "",
        f"- `{OUT_DIR.relative_to(ROOT)}/baseline_model_coefficients_v1.csv`",
        f"- `{OUT_DIR.relative_to(ROOT)}/baseline_model_summary_v1.csv`",
        f"- `{OUT_DIR.relative_to(ROOT)}/baseline_sample_diagnostics_v1.csv`",
        f"- `{OUT_DIR.relative_to(ROOT)}/baseline_model_predictions_v1.csv`",
        f"- `{LOG_MD.relative_to(ROOT)}`",
        f"- `{MEMO_MD.relative_to(ROOT)}`",
        f"- `{PROGRESS_MD.relative_to(ROOT)}`",
        "",
        "## 样本概况",
        "",
        f"- USDC 日频行数：{len(df)}。",
        f"- RQI as-of 可用行：{rqi_rows}。",
        f"- DII as-of 可用行：{dii_rows}。",
        f"- 50bp tail de-peg days：{tail50}。",
        f"- 100bp tail de-peg days：{tail100}。",
        f"- market stress rows：{stress_rows}。",
        f"- 继承人工复核标记的行：{manual_rows}。",
        "",
        "## 方法说明",
        "",
        "- 主结果变量为 `abs_peg_dev_bps`。",
        "- 稀有事件结果使用 50bp tail de-peg 的 linear probability model。",
        "- RQI/DII 均按 10 percentage point 缩放。",
        "- 标准误采用 7-day Newey-West HAC。",
        f"- RQI/DII 规则版本：`{RULE_VERSION}`。",
        "- 所有模型结果仍标记为 pilot/provisional，原因是当前样本仍为 USDC 单发行人且市场 QC 尚未最终完成。",
        "",
        "## 下一步计划",
        "",
        "1. 在冻结规则下重跑 P1-B event-study 输出。",
        "2. 执行 P1-C robustness 设计中的 bank-cash 权重和事件窗口敏感性检验。",
        "3. 扩展到多发行人 disclosure panel 后，再运行真正的 panel baseline。",
        "4. 对 BUSD/TUSD 异常价格进行人工规则确认后，再纳入跨币种稳健性检验。",
    ]
    PROGRESS_MD.write_text("\n".join(progress) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_panel()
    coefs, summaries, predictions = run_models(df)
    diags = diagnostics(df)

    coefs.to_csv(COEF_CSV, index=False)
    summaries.to_csv(MODEL_CSV, index=False)
    diags.to_csv(DIAG_CSV, index=False)
    predictions.to_csv(PRED_CSV, index=False)
    write_reports(df, coefs, summaries, diags)


if __name__ == "__main__":
    main()
