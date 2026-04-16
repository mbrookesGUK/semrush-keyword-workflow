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

API_KEY=os.environ.get("SEMRUSH_API_KEY", "YOUR_SEMRUSH_API_KEY_HERE")
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
        # Normalise: 'Keyword' is what SEMrush actually returns for 'phrase' column
        if "Keyword" in row and "Phrase" not in row:
            row["Phrase"] = row["Keyword"]
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


def _load_csv(path: str) -> list[dict]:
    """Load a CSV file and return rows as dicts."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _sv(row: dict, key: str) -> int:
    """Safely get search volume as int."""
    try:
        return int(row.get(key, 0) or 0)
    except (ValueError, TypeError):
        return 0


def _rel(row: dict) -> float:
    """Safely get related relevance as float."""
    try:
        return float(row.get("Related Relevance", 0) or 0)
    except (ValueError, TypeError):
        return 0.0


def _generate_cluster_report(project_slug: str,
                              seed_map: dict,
                              question_map: dict) -> Path:
    """
    Build a cluster report from cached CSVs.
    seed_map: { seed_name: [related_rows] }
    question_map: { seed_name: [question_rows] }
    """
    today = date.today().isoformat()
    output_dir = OUTPUT_DIR / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"{project_slug}-cluster-report-{today}.md"

    lines = [
        f"# {project_slug.replace('-', ' ').title()} — Keyword Cluster Report",
        f"**Date:** {today}",
        f"**Seeds:** {', '.join(seed_map.keys())}",
        f"**Note:** UK (gb) SEMRush database returned no data for all seeds — US (us) database used.",
        "",
        "---",
        "",
        "## Cluster Summary",
        "",
        "| Seed Topic | Related Keywords | Questions |",
        "|---|---|---|",
    ]

    total_related = 0
    total_questions = 0
    for seed, rows in seed_map.items():
        q_count = len(question_map.get(seed, []))
        total_related += len(rows)
        total_questions += q_count
        lines.append(f"| {seed} | {len(rows)} | {q_count} |")

    lines += [
        f"| **TOTAL** | **{total_related}** | **{total_questions}** |",
        "",
        "---",
        "",
        "## Content Clusters",
        "",
    ]

    for seed, rows in seed_map.items():
        seed_slug = seed.replace(" ", "-")
        vol_rows = sorted(rows, key=lambda r: _sv(r, "Search Volume"), reverse=True)
        high_rel_rows = [r for r in rows if _rel(r) >= 0.65]
        high_rel_rows.sort(key=lambda r: _sv(r, "Search Volume"), reverse=True)

        # Top terms by volume
        lines += [
            f"### Cluster: {seed.title()}",
            f"**Keyword files:** `{seed_slug}-related.csv`, `{seed_slug}-questions.csv`",
            "",
            "#### Top terms by search volume",
            "",
            "| Keyword | Volume | CPC | Competition | Intent | Tier | Rel |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in vol_rows[:15]:
            phrase = r.get("Phrase", r.get("Keyword", "?"))
            vol = _sv(r, "Search Volume")
            cpc = r.get("CPC", "0")
            comp = r.get("Competition", "0")
            intent = classify_intent(phrase)
            tier = classify_tier(r)
            rel = f"{_rel(r):.2f}"
            lines.append(f"| {phrase} | {vol} | ${cpc} | {comp} | {intent} | {tier} | {rel} |")

        # High relevance terms (strong cluster signals)
        if high_rel_rows:
            lines += [
                "",
                "#### High-relevance keywords (rel >= 0.65) — strong cluster signals",
                "",
                "| Keyword | Volume | Rel |",
                "|---|---|---|",
            ]
            for r in high_rel_rows:
                phrase = r.get("Phrase", r.get("Keyword", "?"))
                lines.append(f"| {phrase} | {_sv(r, 'Search Volume')} | {_rel(r):.2f} |")

        lines += ["", "---", ""]

    # AEO Question Targets section
    lines += [
        "## AEO Question Targets",
        "",
        "Questions from `phrase_questions` endpoint — high-value for featured snippets and People Also Ask.",
        "",
    ]

    for seed, rows in question_map.items():
        if not rows:
            continue
        non_zero = [r for r in rows if _sv(r, "Search Volume") > 0]
        if not non_zero:
            continue
        non_zero.sort(key=lambda r: _sv(r, "Search Volume"), reverse=True)
        lines += [
            f"### {seed.title()}",
            "",
            "| Question | Volume | CPC |",
            "|---|---|---|",
        ]
        for r in non_zero[:20]:
            phrase = r.get("Phrase", r.get("Keyword", "?"))
            lines.append(f"| {phrase} | {_sv(r, 'Search Volume')} | ${r.get('CPC', '0')} |")
        lines.append("")

    # Internal link architecture
    lines += [
        "---",
        "",
        "## Internal Link Architecture",
        "",
        "Every cluster article should link to its pillar page. Cross-link between",
        "related clusters to distribute authority.",
        "",
        "```",
        "                    HOME",
        "                      |",
    ]

    pillars = [f"    {s.title()} (PILLAR)" for s in seed_map.keys()]
    lines.append("          |".join([""] + ["           |           ".join([""] + pillars)]) + "")
    lines += [
        "                      |",
        "          [cluster articles link to their pillar]",
        "",
        "    Related clusters cross-link to each other",
        "```",
        "",
        "---",
        "",
        "## Content Priority",
        "",
        "| Priority | Description | Effort |",
        "|---|---|---|",
        "| P1 | AEO \"what is X\" guide per cluster | Medium |",
        "| P1 | Comparison articles (X vs Y) | Low |",
        "| P2 | Process / how-it-works articles | Medium |",
        "| P2 | Industry-specific (aerospace, defence) | Medium |",
        "| P3 | Long-tail niche / specification pages | Variable |",
        "",
        f"*Report generated by semrush_research.py — {today}*",
    ]

    report_path.write_text("\n".join(lines))
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

    elif cmd == "report":
        project_slug = sys.argv[2] if len(sys.argv) > 2 else ""
        if not project_slug:
            print("Usage: python semrush_research.py report <project_slug> [seed_slug ...] [--client </path/to/client-report.md>]")
            print("  With no seed slugs: scans project_slug dir for all cached CSVs")
            print("  With seed slugs: only includes those seeds")
            print("  --client </path>: copy the generated report to a client folder")
            sys.exit(1)

        seed_slugs = sys.argv[3:] if len(sys.argv) > 3 else None

        # Strip flag arguments before seed filtering
        if seed_slugs:
            filtered = []
            skip_next = False
            for s in seed_slugs:
                if skip_next:
                    skip_next = False
                    continue
                if s in ("--client", "-c"):
                    skip_next = True
                    continue
                filtered.append(s)
            seed_slugs = filtered if filtered else None

        # Determine which seeds to include
        seed_slugs_norm = None
        if seed_slugs:
            seed_slugs_norm = {s.replace("-", " ") for s in seed_slugs}

        output_dir = OUTPUT_DIR / project_slug
        if not output_dir.exists():
            print(f"Project directory not found: {output_dir}")
            print("Run 'expand' first to generate data.")
            sys.exit(1)

        # Discover all seed subdirs (each seed has its own folder)
        seed_dirs = {}
        for subdir in sorted(output_dir.iterdir()):
            if subdir.is_dir():
                related_files = sorted(subdir.glob("*-related.csv"))
                question_files = sorted(subdir.glob("*-questions.csv"))
                if related_files or question_files:
                    seed_name = subdir.name.replace("-", " ")
                    if seed_slugs_norm:
                        if seed_name.replace("-", " ") not in seed_slugs_norm and seed_name not in seed_slugs_norm:
                            continue
                    seed_dirs[seed_name] = subdir

        if not seed_dirs:
            print(f"No seed data found in {output_dir}")
            print("Run 'expand' first to generate data.")
            sys.exit(1)

        # Load data per seed
        seed_map = {}
        question_map = {}
        for seed_name, subdir in seed_dirs.items():
            related_files = sorted(subdir.glob("*-related.csv"))
            question_files = sorted(subdir.glob("*-questions.csv"))
            seed_map[seed_name] = []
            question_map[seed_name] = []

            for f in related_files:
                rows = _load_csv(str(f))
                for row in rows:
                    row["_seed"] = seed_name
                seed_map[seed_name].extend(rows)

            for f in question_files:
                rows = _load_csv(str(f))
                for row in rows:
                    row["_seed"] = seed_name
                question_map[seed_name].extend(rows)

        # Handle optional --client flag (save copy to client folder)
        # Looks for --client </path/to/client-report.md> anywhere in args
        client_path = None
        argv = sys.argv
        for i, arg in enumerate(argv):
            if arg == "--client" and i + 1 < len(argv):
                client_path = Path(argv[i + 1])
                break
            if arg == "-c" and i + 1 < len(argv):
                client_path = Path(argv[i + 1])
                break

        # Generate combined cluster report
        report_path = _generate_cluster_report(project_slug, seed_map, question_map)

        # Copy to client folder if specified
        if client_path:
            import shutil
            client_dest = Path(client_path)
            client_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report_path, client_dest)
            print(f"Also copied to: {client_dest}")

        print(f"\nCluster report saved to: {report_path}")

    elif cmd == "help":
        print(__doc__)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
