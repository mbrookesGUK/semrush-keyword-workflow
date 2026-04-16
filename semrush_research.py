#!/usr/bin/env python3
"""
SEMrush Keyword Research Helper
Save to: ~/brain/projects/semrush_research.py
Usage: python semrush_research.py <command> [args]

Commands:
  expand <keyword> <database>  - Run phrase_related + phrase_questions
  competitor <domain> <database> - Run domain_organic
  cluster <file.csv>          - Cluster keywords from CSV output
  report <project_slug>       - Generate markdown report from cached CSVs
"""

import sys
import csv
import json
import time
import requests
from pathlib import Path
from datetime import date

API_KEY = "40dd9298dd7e07223531eb7b80659c52"
BASE_URL = "https://api.semrush.com/"
OUTPUT_DIR = Path.home() / "brain" / "projects"

# ─── API Calls ────────────────────────────────────────────────────────────────

def phrase_related(keyword: str, database: str = "us", count: int = 100) -> list[dict]:
    params = {
        "key": API_KEY,
        "type": "phrase_related",
        "phrase": keyword,
        "database": database,
        "export_columns": "phrase,search_volume,cpc,competition,number_of_results,trends,related_relevance",
        "count": count,
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return _parse_csv(r.text)


def phrase_questions(keyword: str, database: str = "us", count: int = 50) -> list[dict]:
    params = {
        "key": API_KEY,
        "type": "phrase_questions",
        "phrase": keyword,
        "database": database,
        "export_columns": "phrase,search_volume,cpc,competition,number_of_results",
        "count": count,
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return _parse_csv(r.text)


def domain_organic(domain: str, database: str = "us",
                   count: int = 200, offset: int = 0) -> list[dict]:
    params = {
        "key": API_KEY,
        "type": "domain_organic",
        "domain": domain,
        "database": database,
        "export_columns": "phrase,search_volume,position,cpc,url",
        "count": count,
        "display_offset": offset,
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    return _parse_csv(r.text)


def _parse_csv(text: str) -> list[dict]:
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].split(";")]
    rows = []
    for line in lines[1:]:
        values = [v.strip() for v in line.split(";")]
        row = dict(zip(headers, values))
        rows.append(row)
    return rows


# ─── CSV Saving ─────────────────────────────────────────────────────────────

def save_csv(data: list[dict], filename: str, project_slug: str):
    output_dir = OUTPUT_DIR / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    if not data:
        print(f"No data to save for {filename}")
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved {len(data)} rows to {path}")


# ─── Intent Classification ─────────────────────────────────────────────────

INTENT_PATTERNS = {
    "Informational": [
        r"^what is", r"^how to", r"^why does", r"^why is",
        r"^can you", r"^what are", r"^how does", r"^when to",
    ],
    "Transactional": [
        r"buy", r"price", r"cost", r"quote", r"near me",
        r"order", r"purchase", r"get a quote", r"schedule",
    ],
    "Commercial Investigation": [
        r"vs ", r" versus ", r"comparison", r"difference between",
        r"review", r"best ", r"top ", r"recommended",
    ],
}

def classify_intent(keyword: str) -> str:
    kw_lower = keyword.lower()
    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            import re
            if re.search(pat, kw_lower):
                return intent
    return "Informational"


# ─── Tier Classification ───────────────────────────────────────────────────

def classify_tier(row: dict) -> str:
    try:
        vol = int(row.get("Search Volume", 0) or 0)
    except (ValueError, TypeError):
        vol = 0
    try:
        cpc = float(row.get("CPC", 0) or 0)
    except (ValueError, TypeError):
        cpc = 0.0
    try:
        competition = float(row.get("Competition", 0) or 0)
    except (ValueError, TypeError):
        competition = 0.0

    if vol >= 500:
        return "T1"
    elif vol >= 50:
        return "T2"
    else:
        return "T3"


# ─── Clustering ─────────────────────────────────────────────────────────────

def cluster_by_seed_and_relevance(keywords: list[dict], threshold: float = 0.4) -> dict:
    """
    Group keywords into clusters.
    Keywords from the same seed AND high related_relevance = same cluster.
    Returns dict: cluster_name -> list[keyword_rows]
    """
    clusters = {}
    for row in keywords:
        seed = row.get("_seed", "unknown")
        rel = row.get("Related Relevance", "0")
        try:
            rel_val = float(rel)
        except (ValueError, TypeError):
            rel_val = 0.0

        if rel_val >= threshold:
            if seed not in clusters:
                clusters[seed] = []
            clusters[seed].append(row)
    return clusters


# ─── Report Generation ─────────────────────────────────────────────────────

def generate_report(project_slug: str, seeds: list[str],
                     related_data: list[dict],
                     questions_data: list[dict],
                     competitor_data: list[dict] = None):
    today = date.today().isoformat()
    output_dir = OUTPUT_DIR / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{project_slug}-keyword-research-{today}.md"

    # Intent summary
    intent_counts = {"Informational": 0, "Transactional": 0,
                     "Commercial Investigation": 0, "Navigational": 0}
    tier_counts = {"T1": 0, "T2": 0, "T3": 0}
    for row in related_data:
        intent_counts[classify_intent(row["Phrase"])] += 1
        tier_counts[classify_tier(row)] += 1

    lines = [
        f"# {project_slug.replace('-', ' ').title()} — Keyword Research",
        f"**Date:** {today}",
        f"**Seeds:** {', '.join(seeds)}",
        "",
        "## Executive Summary",
        "",
        f"- **{len(related_data)}** related keywords identified",
        f"- **{len(questions_data)}** AEO question targets",
        f"- Intent: {intent_counts['Informational']} informational / "
        f"{intent_counts['Commercial Investigation']} commercial / "
        f"{intent_counts['Transactional']} transactional",
        f"- Tiers: {tier_counts['T1']} T1 / {tier_counts['T2']} T2 / {tier_counts['T3']} T3",
        "",
        "## Seed Keywords",
        *[f"- {s}" for s in seeds],
        "",
        "## Related Keywords",
        "| Keyword | Volume | CPC | Competition | Intent | Tier | Relatedness |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in related_data:
        lines.append(
            f"| {row['Phrase']} | {row['Search Volume']} | "
            f"${row['CPC']} | {row['Competition']} | "
            f"{classify_intent(row['Phrase'])} | {classify_tier(row)} | "
            f"{row.get('Related Relevance', 'N/A')} |"
        )

    if questions_data:
        lines += ["", "## AEO Question Targets", "", "| Question | Volume | CPC |", "|---|---|---|"]
        for row in questions_data:
            lines.append(f"| {row['Phrase']} | {row['Search Volume']} | ${row['CPC']} |")

    if competitor_data:
        lines += ["", "## Competitor Keywords", "",
                  "| Keyword | Volume | Position | CPC | URL |", "|---|---|---|---|---|"]
        seen = set()
        for row in competitor_data:
            kw = row["Phrase"]
            if kw in seen:
                continue
            seen.add(kw)
            lines.append(
                f"| {kw} | {row['Search Volume']} | #{row['Position']} | "
                f"${row['CPC']} | {row['Url'][:60]}... |"
            )

    report_path.write_text("\n".join(lines))
    print(f"\nReport saved to: {report_path}")
    return report_path


# ─── CLI ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "expand":
        keyword = sys.argv[2] if len(sys.argv) > 2 else ""
        database = sys.argv[3] if len(sys.argv) > 3 else "us"
        slug = keyword.replace(" ", "-")
        if not keyword:
            print("Usage: python semrush_research.py expand <keyword> [database]")
            sys.exit(1)

        print(f"\n=== phrase_related: '{keyword}' ({database}) ===")
        related = phrase_related(keyword, database)
        for r in related:
            print(f"  {r['Phrase']} | vol:{r['Search Volume']} cpc:${r['CPC']} rel:{r.get('Related Relevance','?')}")
        save_csv(related, f"{slug}-related.csv", slug)

        print(f"\n=== phrase_questions: '{keyword}' ({database}) ===")
        questions = phrase_questions(keyword, database)
        for q in questions:
            print(f"  {q['Phrase']} | vol:{q['Search Volume']} cpc:${q['CPC']}")
        save_csv(questions, f"{slug}-questions.csv", slug)

    elif cmd == "competitor":
        domain = sys.argv[2] if len(sys.argv) > 2 else ""
        database = sys.argv[3] if len(sys.argv) > 3 else "us"
        slug = domain.replace(".", "-")
        if not domain:
            print("Usage: python semrush_research.py competitor <domain> [database]")
            sys.exit(1)

        print(f"\n=== domain_organic: '{domain}' ({database}) ===")
        data = domain_organic(domain, database)
        for r in data[:20]:
            print(f"  #{r['Position']} {r['Phrase']} | vol:{r['Search Volume']} cpc:${r['CPC']} | {r['Url'][:50]}")
        print(f"  ... +{len(data)-20} more")
        save_csv(data, f"{slug}-competitor.csv", slug)

    elif cmd == "help":
        print(__doc__)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
