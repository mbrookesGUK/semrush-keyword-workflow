# SEMrush Keyword Research & Clustering Workflow

**Skill ID:** `semrush-keyword-cluster`
**Type:** Keyword Research + Content Strategy
**Data Source:** SEMrush API (not Keyword Insights API)
**Methodology:** seo-aeo-keyword-research + seo-aeo-content-cluster
**Last Updated:** April 2026

---

## TRIGGER

Load this skill when the user asks to:
- Research keywords for a client/project
- Cluster keywords into topic groups
- Build a content cluster or pillar page strategy
- Generate AEO (Answer Engine Optimisation) targets
- Pull keyword data from SEMrush for a specific topic or competitor domain

---

## PREREQUISITES

### API Key
SEMRUSH_API_KEY must be set in your environment or passed as an argument.
Get your own at: https://developer.semrush.com/

### Python Environment
Requires: `openpyxl`, `pandas`, `python-docx`, `pymupdf`
Install into active venv:
```bash
pip install openpyxl pandas python-docx pymupdf requests
```

---

## ENDPOINTS USED

| Endpoint | Type | Purpose |
|---|---|---|
| `phrase_related` | Discovery | Keyword expansion + Related Relevance clustering signal |
| `phrase_questions` | Discovery | AEO question targets ("what is...", "how to...") |
| `phrase_all` | Discovery | Broad keyword expansion |
| `domain_organic` | Discovery | Competitor keyword mining (positions, URLs) |

### Database
- Default: `us` (US market — most reliable)
- UK-focused: `gb` (note: many niche B2B terms return ERROR 50 — no data)
- German: `de` (useful for DE market)
- Always confirm the target database returns data for your client's niche before running full analysis

---

## METHODOLOGY

### STEP 1 — SEED KEYWORD EXTRACTION

**Goal:** Build a seed keyword list from the client's business description or topic area.

**Inputs:** A brief description of the client, their services, and target market.

**Process:**
1. Identify 3-5 core topics from the client description
2. Translate each topic into 1-2 seed keyword phrases
3. These become your starting points for SEMrush queries

**Output:** Seed Keyword List (5-15 keywords)

**Example (CWST Surface Technologies):**
- Shot peening services
- Laser peening for aerospace
- Thermal spray coating
- Engineered coatings
- Parylene coating services

---

### STEP 2 — KEYWORD EXPANSION

**Goal:** Expand seed keywords into a comprehensive keyword universe.

**Process — Run both endpoints:**

**A) phrase_related (Primary — used for clustering)**
```bash
curl -s "https://api.semrush.com/?key=KEY&type=phrase_related&phrase=SEED_KEYWORD&database=us&export_columns=phrase,search_volume,cpc,competition,number_of_results,trends,related_relevance&count=100" | tr ';' '\t'
```
Returns up to 100 related keywords with:
- `phrase` — keyword
- `search_volume` — monthly searches
- `cpc` — cost per click (indicates commercial intent)
- `competition` — advertiser competition level
- `number_of_results` — SERP size
- `trends` — 12-month trend array
- `related_relevance` — **SEMRush's clustering signal (0.0–1.0)**

**B) phrase_questions (AEO targets)**
```bash
curl -s "https://api.semrush.com/?key=KEY&type=phrase_questions&phrase=SEED_KEYWORD&database=us&export_columns=phrase,search_volume,cpc,competition,number_of_results&count=50" | tr ';' '\t'
```
Returns question-format keywords:
- "what is laser peening" (20/mo)
- "how does shot peening work" (10/mo)
- "what is thermal spray coating" (30/mo)

**C) domain_organic (Competitor mining — optional)**
```bash
curl -s "https://api.semrush.com/?key=KEY&type=domain_organic&domain=COMPETITOR.com&database=us&export_columns=phrase,search_volume,position,cpc,url&count=200&display_offset=0" | tr ';' '\t'
```
Returns competitor's ranking keywords with positions and landing pages.

**Note:** phrase_match returned "query type not found" — do not use.

**Output:** Raw keyword tables (phrase_related + phrase_questions + optionally domain_organic)

---

### STEP 3 — INTENT CLASSIFICATION

**Goal:** Assign search intent to every keyword.

**Rules:**

| Pattern | Intent |
|---|---|
| Starts with "what is", "how to", "why does", "can you" | Informational |
| Contains "buy", "price", "cost", "quote", "near me" | Transactional |
| Contains "vs", "versus", "comparison", "difference between" | Commercial Investigation |
| Contains "review", "best", "top", "recommended" | Commercial Investigation |
| Brand name only (no modifier) | Navigational |
| Industry term without intent modifier | Informational (default) |

**Output:** Each keyword tagged with Intent: Informational | Commercial Investigation | Transactional | Navigational

---

### STEP 4 — TIER CLASSIFICATION

**Goal:** Prioritise keywords by difficulty and potential.

**Rules (based on search volume + competition + CPC):**

| Tier | Volume | Competition | CPC | Strategy |
|---|---|---|---|---|
| **T1 (Pillar)** | 500+/mo | High | Any | Build dedicated pillar page. High authority required. |
| **T2 (Cluster)** | 50-500/mo | Medium | >$1.00 | Cluster articles targeting sub-topics. |
| **T3 (Long-tail)** | <50/mo | Low | Any | FAQ sections, blog posts, service pages. |

**Additional signals:**
- High CPC (>$3) = strong commercial intent → transactional T2
- `number_of_results` <10,000 = easier ranking → promote one tier
- `number_of_results` >1,000,000 = very competitive → demote one tier

**Output:** Keywords labelled T1 / T2 / T3

---

### STEP 5 — CLUSTERING (Related Relevance)

**Goal:** Group keywords into topic clusters using SEMRush's Related Relevance scores.

**Primary clustering method — Shared seed association:**
- Each `phrase_related` result already knows its parent seed keyword
- Keywords with the same parent seed = same cluster
- Sort by `related_relevance` descending to find strongest associations

**Strength threshold:**
- Related Relevance >= 0.7 = strong cluster membership
- Related Relevance 0.4–0.7 = possible cluster membership
- Related Relevance < 0.4 = weak or cross-topic (handle with care)

**Cluster naming:** Use the highest-volume keyword in the cluster, or the seed keyword that generated most members.

**Secondary clustering — Intent coherence:**
- A cluster should not mix intents arbitrarily
- If a cluster has both informational and transactional keywords, split by intent
- Exception: informational clusters can include commercial investigation keywords

**Output:** Keyword clusters, each with:
- Cluster name
- Keywords (with volume, CPC, intent, related_relevance)
- Tier assignment
- Cluster coherence score (avg related_relevance)

---

### STEP 6 — AEO KEYWORD TARGETS

**Goal:** Identify keywords to target for featured snippet and answer box wins.

**Sources:**
1. `phrase_questions` results — already in question format
2. Keywords starting with "what is", "how to", "why does"
3. Keywords with volume >50/mo and competition <0.5

**Target format:** Questions with straightforward factual answers.

**Output:** AEO target list with:
- Question keyword
- Search volume
- Recommended answer structure (definition / step-by-step / comparison)

---

### STEP 7 — PILLAR PAGE DEFINITION

**Goal:** Identify 1-3 topics for pillar page creation.

**Criteria for a pillar:**
- T1 keyword at cluster core
- Volume >= 500/mo OR cluster has 10+ related keywords
- Clear, broad topic (not a long-tail phrase)
- Cluster supports 8-15 satellite cluster articles

**Pillar page structure:**
1. Overview/definition section (targets informational intent + AEO)
2. Sub-topic sections (each becomes a cluster article)
3. Links to all cluster articles in the topic cluster

**Output:** Pillar page candidates (1-3) with:
- Pillar keyword + volume
- Supporting cluster size
- Internal linking plan

---

### STEP 8 — CONTENT CLUSTER MAP

**Goal:** Define specific content pieces and their internal linking relationships.

**For each pillar cluster:**
1. Identify 8-15 cluster articles based on T2 and T3 keywords
2. Each article targets 1-2 keywords from the cluster
3. Every article links to the pillar page
4. Pillar page links to all cluster articles
5. Cluster articles can cross-link to each other where relevant

**Content type by tier:**
- T1: Pillar page (comprehensive guide)
- T2: Cluster articles (service/process deep-dives)
- T3: FAQ sections, blog posts, comparison pages

**Internal link rule:** Every piece of content in a cluster must link to the pillar. Cross-links between cluster articles are optional but encouraged for topical authority.

---

### STEP 9 — REPORT DELIVERY

**Output file:** `{project-slug}-keyword-research-YYYY-MM-DD.md`

**Sections:**
1. Executive Summary (top 3 clusters, top 5 AEO targets, estimated content工作量)
2. Seed Keywords Used
3. Keyword Universe (full phrase_related table)
4. AEO Targets (phrase_questions results)
5. Intent Distribution (pie chart of Informational / Commercial / Transactional)
6. Tier Distribution (T1 / T2 / T3 breakdown)
7. Topic Clusters (each cluster: name, keywords, tier, volume, internal linking)
8. Pillar Page Candidates
9. Content Cluster Map (what to create, in what order)
10. Recommended Next Steps

---

## EXAMPLE WORKFLOW — CWST SURFACE TECHNOLOGIES

### Seed keywords:
- laser peening
- shot peening
- thermal spray coating
- parylene coating
- engineered coatings

### phrase_related results for "laser peening" (us database):
- laser shock peening — 170/mo — CPC $3.50 — Related Relevance: [high]
- laser heat treating — 140/mo — CPC $2.80 — Related Relevance: [high]
- metal peening — 110/mo — Related Relevance: [medium]

### phrase_questions for "laser peening":
- what is laser peening — 20/mo
- what is laser shock peening — 20/mo
- how does laser peening work — 0/mo

### Clusters identified:
1. **Laser Peening cluster** (pillar candidate) — 5 keywords, ~350 combined volume
2. **Shot Peening cluster** — 8 keywords, ~900 combined volume (strongest)
3. **Thermal Spray Coating cluster** — 6 keywords, ~200 combined volume
4. **Parylene Coating cluster** — 4 keywords, ~150 combined volume

### Pillar page decision:
- "Shot Peening" cluster is largest (T1 keyword "shot peening" at 1,900/mo)
- "Laser Peening" is smaller but growing (MOSA/defence applications)
- Recommend: Shot Peening pillar first, Laser Peening as second pillar

---

## CAVEATS & PITFALLS

1. **UK database gap:** The `gb` database returns ERROR 50 for most niche B2B terms. Default to `us` for international clients. Confirm data exists before running full analysis for UK-only clients.

2. **API rate limits:** SEMrush API has daily/monthly limits. Cache results — don't re-query the same keyword within 24 hours.

3. **phrase_match is unavailable:** The `phrase_match` endpoint returned "query type not found" in April 2026. Do not use.

4. **Related Relevance is directional:** The score tells you how relevant a keyword is to the seed — not how related two keywords are to each other. Use it as a filter, not an absolute threshold.

5. **CPC data gaps:** Some keywords return CPC=0 — treat as unknown commercial intent, not necessarily low intent.

6. **Volume = 0/mo:** Many long-tail and niche keywords show 0 volume in SEMrush but have real traffic. Use related_relevance and number_of_results as secondary signals.

7. **Multiple positions for same keyword:** A domain can appear multiple times in domain_organic for the same keyword (different URLs). De-duplicate by phrase before analysing.

---

## TOOLS & SCRIPTS

### Python helper script (save as `semrush_research.py`)

```python
#!/usr/bin/env python3
"""
SEMrush Keyword Research Helper
Usage: python semrush_research.py <command> [args]

Commands:
  expand <keyword> <database>  - Run phrase_related + phrase_questions
  competitor <domain> <database> - Run domain_organic
  cluster <file.csv>          - Cluster keywords from CSV output
  report <project_slug>        - Generate markdown report from cached CSVs
"""

import sys
import csv
import time
import requests
from pathlib import Path

API_KEY = os.environ.get("SEMRUSH_API_KEY", "YOUR_SEMRUSH_API_KEY_HERE")
BASE_URL = "https://api.semrush.com/"
OUTPUT_DIR = Path.home() / "brain" / "projects"

def phrase_related(keyword: str, database: str = "us", count: int = 100) -> list[dict]:
    """Expand keyword using phrase_related endpoint."""
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
    """Get question keywords using phrase_questions endpoint."""
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

def domain_organic(domain: str, database: str = "us", count: int = 200, offset: int = 0) -> list[dict]:
    """Get competitor keywords using domain_organic endpoint."""
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
    """Parse SEMrush TSV response into list of dicts."""
    lines = text.strip().split("\n")
    if len(lines) < 2:
        return []
    headers = lines[0].split(";")
    rows = []
    for line in lines[1:]:
        values = line.split(";")
        row = {h.strip(): v.strip() for h, v in zip(headers, values)}
        rows.append(row)
    return rows

def save_csv(data: list[dict], filename: str, project_slug: str):
    """Save keyword data to CSV."""
    output_dir = OUTPUT_DIR / project_slug
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    if not data:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    print(f"Saved {len(data)} rows to {path}")

if __name__ == "__main__":
    print("SEMrush Research Helper — use via skill workflow")
    print("See SKILL.md for full usage instructions")
```

---

## RELATED SKILLS

- `seo-aeo-keyword-research` — AEO methodology (question targeting, cannibalisation check, content map)
- `seo-aeo-content-cluster` — Topic cluster methodology (pillar pages, internal link maps)
- `seo-aeo-blog-writer` — Long-form blog content generation
- `seo-aeo-landing-page-writer` — Landing page content generation

---

## FILE OUTPUTS

All outputs go to: `~/brain/projects/{project-slug}/`

| File | Contents |
|---|---|
| `{project-slug}-seed-keywords.md` | Step 1 seed list |
| `{project-slug}-keywords-related.csv` | Step 2 phrase_related results |
| `{project-slug}-keywords-questions.csv` | Step 2 phrase_questions results |
| `{project-slug}-competitor-keywords.csv` | Step 2 domain_organic results (if used) |
| `{project-slug}-keyword-research-YYYY-MM-DD.md` | Final report (all steps) |

---

*Skill built April 2026 — tested with SEMrush API key confirmed working. UK database gap noted (gb returns ERROR 50 for niche B2B). phrase_match unavailable — do not use.*
