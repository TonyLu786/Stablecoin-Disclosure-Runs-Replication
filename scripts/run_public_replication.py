from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


SMOKE_FILES = [
    ROOT / "00_admin" / "rqi_dii_rules_v1_config.json",
    ROOT / "02_manual_coding" / "rqi_dii_pilot_coding_v1.csv",
    ROOT / "02_manual_coding" / "multi_issuer_disclosure_event_index_v1.csv",
    ROOT / "03_market_data" / "price_supply_panel_raw_v1.csv",
    ROOT / "04_processed_data" / "minimum_viable_panel_v1.csv",
    ROOT / "06_outputs" / "variable_dictionary_v1.csv",
]

ANALYSIS_SCRIPTS = [
    "05_analysis/run_pilot_baseline_p1a.py",
    "05_analysis/build_event_study_p1b.py",
    "05_analysis/run_robustness_p1e.py",
    "05_analysis/build_multi_issuer_event_window_p1i.py",
]

def run_script(script: str) -> None:
    print(f"running {script}")
    subprocess.run([sys.executable, script], cwd=ROOT, check=True)


def ensure_output_dirs() -> None:
    (ROOT / "06_outputs").mkdir(exist_ok=True)
    (ROOT / "99_logs").mkdir(exist_ok=True)


def smoke() -> None:
    missing = [path for path in SMOKE_FILES if not path.exists()]
    if missing:
        for path in missing:
            print(f"missing required file: {path.relative_to(ROOT)}")
        raise SystemExit(1)

    datasets = [
        ROOT / "02_manual_coding" / "rqi_dii_pilot_coding_v1.csv",
        ROOT / "02_manual_coding" / "multi_issuer_disclosure_event_index_v1.csv",
        ROOT / "03_market_data" / "price_supply_panel_raw_v1.csv",
        ROOT / "04_processed_data" / "minimum_viable_panel_v1.csv",
        ROOT / "06_outputs" / "variable_dictionary_v1.csv",
    ]
    for path in datasets:
        rows = len(pd.read_csv(path))
        print(f"{path.relative_to(ROOT)}: {rows} rows")

    subprocess.run([sys.executable, "scripts/check_public_release.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/check_readme_integrity.py"], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run public data and code replication stages.")
    parser.add_argument("--mode", choices=["smoke", "analysis", "all"], default="smoke")
    args = parser.parse_args()
    ensure_output_dirs()

    if args.mode in {"smoke", "all"}:
        smoke()
    if args.mode in {"analysis", "all"}:
        for script in ANALYSIS_SCRIPTS:
            run_script(script)

    subprocess.run([sys.executable, "scripts/check_public_release.py"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "scripts/check_readme_integrity.py"], cwd=ROOT, check=True)

    print(f"replication mode completed: {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
