# Haiti Anger Index (HAI™)
### A POLLNEX Insights Research Product

---

## Overview

The **Haiti Anger Index (HAI™)** is an automated sentiment-intelligence agent that:

1. **Crawls** major social media platforms and Haitian news RSS feeds for posts in **English, French, and Haitian Creole**
2. **Classifies** each post as `POSITIVE`, `NEGATIVE`, or `NEUTRAL` using a multilingual XLM-RoBERTa model
3. **Compiles** per-platform and per-topic statistics
4. **Computes** a composite HAI score (0–100) inspired by Pollara's Rage Index methodology
5. **Generates** a branded HTML report with charts, trend lines, and top anger drivers

---

## Architecture

```
haiti_anger_index/
├── agent.py                   ← Main orchestration loop (CLI entry point)
├── config.py                  ← All configuration & API credentials
├── __main__.py                ← `python -m haiti_anger_index`
│
├── crawlers/
│   ├── base.py                ← Abstract base crawler
│   ├── twitter_crawler.py     ← Twitter/X (API v2, Bearer Token)
│   ├── facebook_crawler.py    ← Facebook Graph API
│   ├── youtube_crawler.py     ← YouTube Data API v3
│   ├── reddit_crawler.py      ← Reddit PRAW
│   └── rss_crawler.py         ← 10+ Haitian news RSS feeds (no API key)
│
├── classifier/
│   ├── language_detector.py   ← EN / FR / HT detection
│   ├── sentiment_classifier.py← XLM-RoBERTa + keyword fallback
│   └── topic_classifier.py    ← 9 Haitian-specific topic categories
│
├── aggregator/
│   └── data_compiler.py       ← Per-platform / per-topic / per-language stats
│
├── index/
│   └── anger_index.py         ← HAI score formula + trend + top drivers
│
├── storage/
│   └── database.py            ← SQLite (posts + snapshots + reports)
│
└── reporting/
    ├── report_generator.py    ← Jinja2 HTML renderer
    └── templates/
        └── anger_index_report.html  ← POLLNEX-branded dashboard
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API credentials (optional but recommended)

At minimum, the RSS crawler works with **no API keys** and already covers
10 major Haitian news outlets.  Add API keys to enable richer social data:

```bash
export TWITTER_BEARER_TOKEN="..."
export YOUTUBE_API_KEY="..."
export REDDIT_CLIENT_ID="..."
export REDDIT_CLIENT_SECRET="..."
export FACEBOOK_ACCESS_TOKEN="..."   # Page Access Token
```

### 3. Run the agent

```bash
# Single run (all platforms)
python -m haiti_anger_index

# RSS only (no API keys needed)
python -m haiti_anger_index --platforms rss

# Dry run — print results, don't save to DB
python -m haiti_anger_index --dry-run --platforms rss

# Scheduled run every 6 hours
python -m haiti_anger_index --schedule 6h

# Custom paths
python -m haiti_anger_index --db /data/hai.db --reports /var/www/reports
```

---

## Haiti Anger Index Score

| Score | Level      | Description                             |
|-------|------------|-----------------------------------------|
| 0–25  | 🟢 Calm     | Low negative sentiment                  |
| 26–50 | 🟡 Concerned | Elevated concern but not acute anger   |
| 51–75 | 🟠 Agitated  | High frustration across key topics     |
| 76–100| 🔴 Enraged   | Critical anger levels — crisis signal  |

### Formula

```
raw_score = 0.40 × neg_rate
          + 0.40 × engagement_weighted_neg_rate
          + 0.20 × topic_severity_adjusted_neg_rate

HAI = round(raw_score × 100, 1)
```

**Topic severity weights** amplify issues that historically drive the
strongest public anger in Haiti:

| Topic                   | Weight |
|-------------------------|--------|
| Government & Corruption | 1.5    |
| Kidnapping & Safety     | 1.4    |
| Economy & Poverty       | 1.3    |
| Human Rights & Diaspora | 1.3    |
| Natural Disasters       | 1.2    |
| Health & Healthcare     | 1.1    |
| Infrastructure          | 1.0    |
| Education               | 0.9    |
| International Relations | 0.9    |

---

## Supported Platforms

| Platform      | Data Source                | API Key Required |
|---------------|----------------------------|-----------------|
| Twitter / X   | Twitter API v2             | ✅ Bearer Token  |
| Facebook      | Meta Graph API             | ✅ Page Token    |
| YouTube       | YouTube Data API v3        | ✅ API Key       |
| Reddit        | PRAW                       | ✅ Client ID/Secret |
| Haitian News  | 10+ RSS feeds              | ❌ None needed   |

### Haitian News RSS Sources
- Le Nouvelliste
- Haïti Libre
- AlterPresse
- Rezo Nodwes
- Loop Haiti
- Gazette Haïti
- HPN Haïti
- Radio Kiskeya
- Haïti Info Projet
- Haïti Chery

---

## Language Support

| Language        | Detection  | Sentiment |
|-----------------|------------|-----------|
| English (en)    | ✅          | ✅         |
| French (fr)     | ✅          | ✅         |
| Haitian Creole  | ✅ (heuristic) | ✅ (via XLM-RoBERTa) |

---

## Output

Each run produces:
- **SQLite database** with all posts, classifications, and index snapshots
- **HTML report** with interactive charts (Chart.js):
  - HAI gauge/speedometer
  - Platform breakdown bar chart
  - Language distribution doughnut chart
  - Top anger drivers table
  - Historical trend line

---

## Environment Variables

| Variable                | Default               | Description                     |
|-------------------------|-----------------------|---------------------------------|
| `TWITTER_BEARER_TOKEN`  | —                     | Twitter API v2 bearer token     |
| `YOUTUBE_API_KEY`       | —                     | Google/YouTube Data API key     |
| `REDDIT_CLIENT_ID`      | —                     | Reddit app client ID            |
| `REDDIT_CLIENT_SECRET`  | —                     | Reddit app client secret        |
| `FACEBOOK_ACCESS_TOKEN` | —                     | Meta Graph API page token       |
| `HAI_DB_PATH`           | `haiti_anger_index.db`| SQLite database path            |
| `HAI_REPORTS_DIR`       | `reports/`            | HTML reports output directory   |
| `MAX_POSTS_PER_PLATFORM`| `200`                 | Max posts per platform per run  |
| `CRAWL_DELAY`           | `1.0`                 | Seconds between API requests    |

---

## Ethical Notes

- Only **publicly accessible** content is collected (no login-gated scraping)
- Facebook crawling uses only the **official Graph API** on public pages
- Content is used for **aggregate analysis only** — no PII is stored
- Crawl rate is limited to respect platform terms of service

---

*© POLLNEX Insights — Haiti Anger Index™ is a proprietary research product.
Attribution required when citing results.*
