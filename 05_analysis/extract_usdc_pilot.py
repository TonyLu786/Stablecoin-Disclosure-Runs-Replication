from __future__ import annotations

import csv
import datetime as dt
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULE_CONFIG_PATH = ROOT / "00_admin" / "rqi_dii_rules_v1_config.json"
PDF_DIR = ROOT / "01_raw_sources" / "issuer_disclosures" / "USDC"
OUT_CSV = ROOT / "02_manual_coding" / "rqi_dii_pilot_coding_v1.csv"
DISPUTES_MD = ROOT / "02_manual_coding" / "coding_disputes_v1.md"
LOG_MD = ROOT / "99_logs" / "usdc_pilot_extraction_log_20260522.md"

MONTHS = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}
MONTH_RE = "|".join(MONTHS)
DATE_RE = re.compile(rf"\b({MONTH_RE})\s+(\d{{1,2}}),\s+(\d{{4}})\b")


def load_rule_config() -> dict:
    with RULE_CONFIG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


RULE_CONFIG = load_rule_config()
RULE_VERSION = RULE_CONFIG.get("rule_version", "RQI_DII_v1.0")
RULE_STATUS = RULE_CONFIG.get("rule_status", "frozen_confirmed_by_researcher")
RQI_WEIGHTS = RULE_CONFIG["rqi_weights_primary"]
DII_CONFIG = RULE_CONFIG["dii_components"]


def run_pdftotext(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return normalize_text(result.stdout)


def normalize_text(text: str) -> str:
    replacements = {
        "\ufb01": "fi",
        "\ufb02": "fl",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\xa0": " ",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def parse_filename(path: Path) -> tuple[int, str, int]:
    match = re.match(r"USDC_assurance_(\d{4})_([A-Za-z]+)\.pdf", path.name)
    if not match:
        raise ValueError(f"Unexpected file name: {path.name}")
    year = int(match.group(1))
    month_name = match.group(2)
    return year, month_name, MONTHS[month_name]


def parse_date(value: tuple[str, str, str]) -> dt.date:
    month_name, day, year = value
    return dt.date(int(year), MONTHS[month_name], int(day))


def date_str(value: dt.date | None) -> str:
    return value.isoformat() if value else ""


def month_end(year: int, month: int) -> dt.date:
    if month == 12:
        return dt.date(year, 12, 31)
    return dt.date(year, month + 1, 1) - dt.timedelta(days=1)


def extract_dates(text: str, year: int, month: int) -> tuple[list[dt.date], dt.date | None, str]:
    # The first pages contain the independent accountant date and the report date(s).
    head = text[:7000]
    dates = [parse_date(m.groups()) for m in DATE_RE.finditer(head)]
    seen: set[dt.date] = set()
    unique_dates: list[dt.date] = []
    for value in dates:
        if value not in seen:
            seen.add(value)
            unique_dates.append(value)

    report_dates = [d for d in unique_dates if d.year == year and d.month == month]
    report_dates = sorted(report_dates)
    latest = report_dates[-1] if report_dates else None

    publication_date = None
    if latest:
        later_dates = [d for d in unique_dates if d > latest]
        if later_dates:
            publication_date = later_dates[0]

    status = "ok"
    if not report_dates:
        status = "no_report_date"
    elif not publication_date:
        status = "no_publication_date"
    return report_dates, publication_date, status


def money_to_float(value: str) -> float:
    return float(value.replace(",", ""))


def money_values(line: str) -> list[str]:
    return re.findall(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d{4,}\b", line)


def amount_near_line(lines: list[str], idx: int) -> float:
    candidates = [lines[idx]]
    if idx > 0:
        candidates.append(lines[idx - 1])
    if idx + 1 < len(lines):
        candidates.append(lines[idx + 1])
    for line in candidates:
        nums = money_values(line)
        if nums:
            return money_to_float(nums[-1])
    return 0.0


def extract_amount_after(label_re: str, text: str) -> list[float]:
    pattern = re.compile(label_re, re.IGNORECASE)
    amounts: list[float] = []
    for line in text.splitlines():
        if pattern.search(line):
            nums = money_values(line)
            if nums:
                amounts.append(money_to_float(nums[-1]))
    return amounts


def latest_date_segment(text: str, latest_report_date: dt.date | None) -> str:
    if not latest_report_date:
        return text
    month_name = [name for name, idx in MONTHS.items() if idx == latest_report_date.month][0]
    day = latest_report_date.day
    year = latest_report_date.year
    table_candidates = [
        f"CIRCLE RESERVE FUND ASSETS AS OF {month_name.upper()} {day}, {year}",
        f"CIRCLE RESERVE FUND ASSETS AS OF {month_name.upper()} {day:02d}, {year}",
        f"CIRCLE RESERVE FUND ASSETS AS OF {month_name} {day}, {year}",
        f"CIRCLE RESERVE FUND ASSETS AS OF {month_name} {day:02d}, {year}",
    ]
    candidates = [
        f"AS OF {month_name.upper()} {day}, {year}",
        f"AS OF {month_name.upper()} {day:02d}, {year}",
        f"AS OF {month_name} {day}, {year}",
        f"AS OF {month_name} {day:02d}, {year}",
        f"as of {month_name} {day}, {year}",
        f"as of {month_name} {day:02d}, {year}",
        f"Report Date {month_name} {day}, {year}",
        f"{month_name.upper()} {day}, {year}",
        f"{month_name} {day}, {year}",
    ]
    for candidate_group in (table_candidates, candidates):
        positions: list[int] = []
        for candidate in candidate_group:
            start = 0
            while True:
                idx = text.find(candidate, start)
                if idx < 0:
                    break
                positions.append(idx)
                start = idx + len(candidate)
        if positions:
            for start in sorted(set(positions), reverse=True):
                tail = text[start:]
                note_pos = tail.find("\nNotes")
                if note_pos < 0:
                    note_pos = tail.find("\n     Notes")
                segment = tail[:note_pos] if note_pos > 0 else tail
                if re.search(r"TOTAL USDC RESERVE ASSETS", segment, re.IGNORECASE):
                    return segment
    return text


def extract_reserve_components(text: str, latest_report_date: dt.date | None) -> dict[str, float | str]:
    segment = latest_date_segment(text, latest_report_date)

    total_assets_candidates = extract_amount_after(r"TOTAL USDC RESERVE ASSETS(?: AS OF [A-Z]+\s+\d{1,2},\s+\d{4})?", segment)
    treasury_candidates = extract_amount_after(r"TOTAL U\.S\. TREASURY SECURITIES(?: OWNED)?", segment)
    repo_candidates = extract_amount_after(r"U\.S\. Treasury Repurchase Agreements", segment)

    lines = [line.strip() for line in segment.splitlines()]
    cash_deposit_totals: list[float] = []
    bank_cash_candidates: list[float] = []
    reserve_fund_cash_candidates: list[float] = []
    for idx, line in enumerate(lines):
        if not line or "due to/" in line.lower() or "owed by" in line.lower():
            continue
        lower = line.lower()
        if lower.startswith("total cash deposits"):
            amount = amount_near_line(lines, idx)
            if amount:
                cash_deposit_totals.append(amount)
        elif (
            lower.startswith("cash held at")
            and "regulated" in lower
            or lower.startswith("cash held at u.s.")
            or lower.startswith("cash held at us")
        ):
            amount = amount_near_line(lines, idx)
            if amount:
                bank_cash_candidates.append(amount)
        elif lower.startswith("cash held in circle reserve fund") or lower == "cash":
            amount = amount_near_line(lines, idx)
            if amount:
                reserve_fund_cash_candidates.append(amount)

    reserve_fund_cash_total = sum(reserve_fund_cash_candidates)
    if cash_deposit_totals:
        bank_cash_total = sum(cash_deposit_totals)
    else:
        bank_cash_total = sum(bank_cash_candidates)
    cash_total = reserve_fund_cash_total + bank_cash_total

    total_assets = total_assets_candidates[-1] if total_assets_candidates else 0.0
    treasury_total = sum(treasury_candidates)
    repo_total = sum(repo_candidates)

    has_cusip = "Cusip" in segment or "CUSIP" in segment
    has_detail = bool(treasury_candidates or repo_candidates or cash_total)

    observed_total = treasury_total + repo_total + cash_total
    if total_assets <= 0:
        confidence = "low"
    elif observed_total > total_assets * 1.05:
        confidence = "low"
    elif has_detail:
        confidence = "medium" if has_cusip else "low"
    else:
        confidence = "low"

    return {
        "total_reserve_assets_usd": total_assets,
        "treasury_securities_usd": treasury_total,
        "treasury_repo_usd": repo_total,
        "reserve_fund_cash_usd": reserve_fund_cash_total,
        "bank_cash_usd": bank_cash_total,
        "cash_total_usd": cash_total,
        "asset_extraction_confidence": confidence,
        "has_cusip_level_detail": "1" if has_cusip else "0",
    }


def score_timeliness(publication_date: dt.date | None, latest_report_date: dt.date | None) -> tuple[str, str]:
    if not publication_date or not latest_report_date:
        return "", ""
    lag = (publication_date - latest_report_date).days
    if lag <= 7:
        score = 1.0
    elif lag <= 30:
        score = 0.70
    elif lag <= 90:
        score = 0.40
    else:
        score = 0.15
    return str(lag), f"{score:.2f}"


def safe_share(numerator: float, denominator: float) -> str:
    if denominator <= 0:
        return ""
    return f"{numerator / denominator:.6f}"


def compute_rqi(components: dict[str, float | str]) -> str:
    total = float(components["total_reserve_assets_usd"])
    if total <= 0:
        return ""
    treasury = float(components["treasury_securities_usd"])
    repo = float(components["treasury_repo_usd"])
    reserve_cash = float(components["reserve_fund_cash_usd"])
    bank_cash = float(components["bank_cash_usd"])
    observed = treasury + repo + reserve_cash + bank_cash
    if observed > total * 1.05:
        return ""
    other = max(total - observed, 0.0)
    weights = RQI_WEIGHTS
    rqi = (
        float(weights["treasury_securities"]) * treasury
        + float(weights["treasury_repo"]) * repo
        + float(weights["reserve_fund_cash"]) * reserve_cash
        + float(weights["bank_cash"]) * bank_cash
        + float(weights["other_residual"]) * other
    ) / total
    return f"{rqi:.4f}"


def compute_granularity_score(year: int, components: dict[str, float | str]) -> str:
    if components["has_cusip_level_detail"] == "1":
        return "1.00"
    if float(components["total_reserve_assets_usd"]) > 0:
        return "0.40"
    return "0.15"


def compute_dii(freq: str, granularity: str, timeliness: str, assurance: str) -> str:
    values = [freq, granularity, timeliness, assurance]
    if any(v == "" for v in values):
        return ""
    f, g, t, a = [float(v) for v in values]
    return f"{0.25 * f + 0.25 * g + 0.20 * t + 0.30 * a:.4f}"


def infer_attestor(year: int) -> tuple[str, str]:
    if year == 2022:
        return "Grant Thornton LLP", "AICPA attestation standards"
    return "Big Four accounting firm per Circle transparency page; manual PDF-name verification required", "AICPA attestation standards"


def main() -> None:
    rows: list[dict[str, str]] = []
    disputes: list[str] = []

    for pdf in sorted(PDF_DIR.glob("USDC_assurance_*.pdf")):
        year, month_name, month = parse_filename(pdf)
        text = run_pdftotext(pdf)
        report_dates, publication_date, date_status = extract_dates(text, year, month)
        latest_report_date = report_dates[-1] if report_dates else None
        components = extract_reserve_components(text, latest_report_date)
        publication_lag_days, timeliness_score = score_timeliness(publication_date, latest_report_date)
        attestor, assurance_basis = infer_attestor(year)

        frequency_score = f"{float(DII_CONFIG.get('monthly_assurance_frequency_score', 0.60)):.2f}"
        granularity_score = compute_granularity_score(year, components)
        assurance_score = f"{float(DII_CONFIG.get('assurance_score_aicpa', 1.00)):.2f}"
        dii = compute_dii(frequency_score, granularity_score, timeliness_score, assurance_score)
        rqi = compute_rqi(components)

        total = float(components["total_reserve_assets_usd"])
        treasury = float(components["treasury_securities_usd"])
        repo = float(components["treasury_repo_usd"])
        reserve_cash = float(components["reserve_fund_cash_usd"])
        bank_cash = float(components["bank_cash_usd"])
        cash_total = float(components["cash_total_usd"])

        confidence = str(components["asset_extraction_confidence"])
        review_required = "0"
        reasons = []
        if date_status != "ok":
            review_required = "1"
            reasons.append(date_status)
        if confidence != "medium":
            review_required = "1"
            reasons.append(f"asset_extraction_{confidence}")
        if year >= 2023:
            review_required = "1"
            reasons.append("auditor_name_not_text_visible")
        if rqi == "":
            review_required = "1"
            reasons.append("rqi_missing")
        if total > 0 and (treasury + repo + cash_total) > total * 1.05:
            review_required = "1"
            reasons.append("components_exceed_total")
        if reasons:
            disputes.append(f"- {pdf.name}: {', '.join(reasons)}")

        rows.append(
            {
                "event_id": f"USDC_ASSURANCE_{year}_{month:02d}",
                "stablecoin": "USDC",
                "issuer": "Circle",
                "document_family": "monthly_assurance",
                "rule_version": RULE_VERSION,
                "rule_status": RULE_STATUS,
                "rqi_weight_profile": RULE_CONFIG.get("rqi_weight_profile", "primary_path_b"),
                "report_year": str(year),
                "report_month": month_name,
                "report_dates": ";".join(date_str(d) for d in report_dates),
                "latest_report_date": date_str(latest_report_date),
                "publication_date": date_str(publication_date),
                "publication_lag_days": publication_lag_days,
                "scheduled_flag": "1",
                "ad_hoc_flag": "0",
                "stress_regime_flag": "banking_stress" if year == 2023 and month_name in {"March", "April"} else "normal",
                "attestor_or_provider": attestor,
                "assurance_basis": assurance_basis,
                "total_reserve_assets_usd": f"{total:.0f}" if total else "",
                "treasury_securities_usd": f"{treasury:.0f}" if treasury else "",
                "treasury_repo_usd": f"{repo:.0f}" if repo else "",
                "reserve_fund_cash_usd": f"{reserve_cash:.0f}" if reserve_cash else "",
                "bank_cash_usd": f"{bank_cash:.0f}" if bank_cash else "",
                "cash_total_usd": f"{cash_total:.0f}" if cash_total else "",
                "treasury_share": safe_share(treasury, total),
                "repo_share": safe_share(repo, total),
                "cash_total_share": safe_share(cash_total, total),
                "bank_cash_share": safe_share(bank_cash, total),
                "pilot_rqi": rqi,
                "disclosure_frequency_score": frequency_score,
                "disclosure_granularity_score": granularity_score,
                "disclosure_timeliness_score": timeliness_score,
                "assurance_score": assurance_score,
                "pilot_dii": dii,
                "asset_extraction_confidence": confidence,
                "date_extraction_status": date_status,
                "manual_review_required": review_required,
                "local_file_path": str(pdf.relative_to(ROOT)).replace("\\", "/"),
                "notes": "; ".join(reasons),
            }
        )

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    DISPUTES_MD.write_text(
        "# Coding Disputes v1\n\n"
        "Date: 2026-05-22\n\n"
        "## Scope\n\n"
        f"This file lists source-level items from the USDC extraction that remain under human review after `{RULE_VERSION}` rule freeze.\n\n"
        "## Disputes and Review Items\n\n"
        + ("\n".join(disputes) if disputes else "No disputes detected.")
        + "\n\n## Remaining Human Review Gates\n\n"
        "1. Verify whether 2023-2024 Circle assurance provider names should be coded from PDF visual review or official issuer source.\n"
        "2. Reconcile low-confidence or component-mismatch reserve tables before using affected rows for final RQI interpretation.\n"
        "3. Add Circle weekly reserve/mint-burn disclosures as separate future event-layer observations.\n"
        "4. Preserve bank-cash robustness checks at 0.70 and 0.90 as required by the frozen rule file.\n"
        "5. Preserve March/April 2023 banking-stress coding as provisional pending stress-window robustness.\n",
        encoding="utf-8",
    )

    LOG_MD.write_text(
        "# USDC Pilot Extraction Log\n\n"
        "Date: 2026-05-22\n\n"
        f"Input PDFs: {len(rows)}\n\n"
        f"Output CSV: `{OUT_CSV.relative_to(ROOT)}`\n\n"
        f"Disputes file: `{DISPUTES_MD.relative_to(ROOT)}`\n\n"
        f"Rule version: `{RULE_VERSION}` (`{RULE_STATUS}`)\n\n"
        "Method: `pdftotext -layout` extraction followed by rule-based parsing of report dates, publication dates, reserve categories, and pilot RQI/DII components.\n\n"
        "Important limitation: RQI/DII rules are frozen for pilot analysis, but source-level evidence flags remain active. Rows with missing dates, low asset confidence, or non-visible auditor names are routed to `coding_disputes_v1.md`.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
