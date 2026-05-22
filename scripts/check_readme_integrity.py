from __future__ import annotations

import re
import sys
from pathlib import Path

from check_public_release import prohibited_terms


ROOT = Path(__file__).resolve().parents[1]

README_FILES = [
    ROOT / "README.md",
    ROOT / "docs" / "readme" / "README.zh-CN.md",
    ROOT / "docs" / "readme" / "README.ja.md",
    ROOT / "docs" / "readme" / "README.fr.md",
    ROOT / "docs" / "readme" / "README.ru.md",
]

ROOT_REQUIRED_PHRASES = [
    "## Languages",
    "## Repository Map",
    "```mermaid",
    "## Quick Start",
    "## Replication Commands",
    "## Evidence Boundary",
    "## Data Provenance",
    "## Citation",
    "## License",
    "docs/readme/README.zh-CN.md",
    "docs/readme/README.ja.md",
    "docs/readme/README.fr.md",
    "docs/readme/README.ru.md",
]

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def local_target_exists(markdown_path: Path, target: str) -> bool:
    target = target.strip()
    if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
        return True
    clean = target.split("#", 1)[0]
    if not clean:
        return True
    if clean.startswith("<") and clean.endswith(">"):
        clean = clean[1:-1]
    candidate = (markdown_path.parent / clean).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return False
    return candidate.exists()


def scan_readme_terms(path: Path, text: str) -> list[str]:
    findings = []
    lowered = text.lower()
    for term in prohibited_terms():
        if term.lower() in lowered:
            findings.append(f"{path.relative_to(ROOT)}: prohibited term: {term}")
    return findings


def main() -> int:
    errors: list[str] = []

    for path in README_FILES:
        if not path.exists():
            errors.append(f"missing README file: {path.relative_to(ROOT)}")
            continue

        text = read_text(path)
        errors.extend(scan_readme_terms(path, text))

        for link in LINK_RE.findall(text):
            if not local_target_exists(path, link):
                errors.append(f"{path.relative_to(ROOT)}: broken local link: {link}")

    root_text = read_text(ROOT / "README.md") if (ROOT / "README.md").exists() else ""
    for phrase in ROOT_REQUIRED_PHRASES:
        if phrase not in root_text:
            errors.append(f"README.md missing required section or link: {phrase}")

    if errors:
        for error in errors:
            print(error)
        return 1

    print("README integrity audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
