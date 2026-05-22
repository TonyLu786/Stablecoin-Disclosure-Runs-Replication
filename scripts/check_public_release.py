from __future__ import annotations

import argparse
from pathlib import Path


TEXT_SUFFIXES = {
    ".bib",
    ".csv",
    ".html",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".tex",
    ".txt",
    ".yml",
    ".yaml",
}

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "01_raw_sources",
    "raw_defillama",
    "spotcheck_text_extracts_p2g3_v1",
}


def prohibited_terms() -> list[str]:
    two_letter_term = chr(65) + chr(73)
    return [
        "Open" + two_letter_term,
        "Co" + "dex",
        "Chat" + "GPT",
        "Use of " + two_letter_term,
        two_letter_term + "-use",
        two_letter_term + "-assisted",
        two_letter_term + "_",
        two_letter_term + "-",
        "L" + "LM",
        "language " + "model",
        two_letter_term + "/ML",
        "a" + "i_ml",
        "research " + "assist" + "ant",
        "model " + "prompt",
        "machine " + "learning",
        "causal " + "ML",
        "manu" + "script",
        "sub" + "mission",
        "La" + "TeX",
        "A" + "PA",
        "author " + "metadata",
        "cover " + "letter",
        "tar" + "get " + "jour" + "nal",
        "full_" + "paper",
        "Spring" + "er",
        "Research Workflow " + "Note",
        "the research support " + "workflow",
    ]


def iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def scan(root: Path) -> list[tuple[Path, int, str]]:
    findings: list[tuple[Path, int, str]] = []
    terms = prohibited_terms()
    for path in iter_text_files(root):
        try:
            lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            lowered = line.lower()
            for term in terms:
                if term.lower() in lowered:
                    findings.append((path.relative_to(root), line_no, term))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check public-release text for prohibited disclosure/tooling traces.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    root = args.root.resolve()
    findings = scan(root)
    if findings:
        for path, line_no, term in findings:
            print(f"{path}:{line_no}: prohibited term: {term}")
        return 1
    print("public release audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
