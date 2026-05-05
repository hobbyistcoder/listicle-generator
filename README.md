# Listicle Generator · Zuddl Content Engine

An AI-powered pipeline that turns keyword inputs into publish-ready software comparison articles. Built for Zuddl's content team to eliminate the research and first-draft bottleneck.

**Live tool:** https://olwgcf6fuqgn9675o4durm.streamlit.app

---

## What it does

1. **Research** — searches Google via Serper API for top-ranked pages in the software category
2. **Scrape** — pulls readable content from each page using Jina.ai (no API key needed)
3. **Extract** — GPT-4o parses the content into structured tool data (name, features, pricing, best-for)
4. **Human checkpoint** — you review and edit the tool list before any draft is generated
5. **Draft** — GPT-4o writes a full listicle following Zuddl's blog structure and tone
6. **Humanize** — second GPT-4o pass removes AI clichés, adds opinions, varies rhythm
7. **Export** — download as Markdown or copy as HTML for direct paste into any CMS

---

## Stack

| Layer | Tool |
|-------|------|
| UI | Streamlit |
| Orchestration | Python |
| Search | Serper API |
| Scraping | Jina.ai Reader (free, no key) |
| LLM | GPT-4o |
| Hosting | Streamlit Community Cloud |
| Version control | GitHub |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/hobbyistcoder/listicle-generator.git
cd listicle-generator
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run locally

Set your API keys as environment variables:

```bash
export OPENAI_API_KEY="your-openai-key"
export SERPER_API_KEY="your-serper-key"
streamlit run app.py
```

Get a free Serper key at [serper.dev](https://serper.dev) — free tier includes 2,500 searches.

---

## Deploying to Streamlit Cloud

1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo, set `app.py` as the main file
4. Under **Advanced Settings → Secrets**, add:

```toml
OPENAI_API_KEY = "your-openai-key"
SERPER_API_KEY = "your-serper-key"
```

5. Deploy — you'll get a live public URL

---

## How to use

1. Enter a **primary keyword** (e.g. `event registration software`)
2. Enter **secondary keywords** comma-separated (e.g. `event ticketing, attendee management`)
3. Set how many tools to include (3–15)
4. Hit **Research** — the pipeline searches, scrapes, and extracts tools automatically
5. Review the tool list JSON — add, remove, or edit any entry
6. Hit **Approve & Generate Draft**
7. Get your article in three formats: rendered preview, raw markdown, and CMS-ready HTML

---

## Known limitations

- **Ratings are usually null** — G2 and Capterra block scrapers, so verified ratings rarely come through. Firecrawl integration would fix this.
- **Thin categories return fewer tools** — niche software verticals have fewer comparison pages indexed, so the pipeline may return fewer tools than requested.
- **Single-threaded** — concurrent runs queue up. A job queue (Celery + Redis or Supabase) would be needed at scale.
- **Humanization loses consistency on long articles** — chunking per tool section would improve this.

---

## Security

API keys are never stored in code. Use environment variables locally and Streamlit secrets on Cloud.
