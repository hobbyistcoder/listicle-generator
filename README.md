# Listicle Generator

Automated pipeline to turn keywords → publish-ready software comparison articles.

## Setup

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Add your API keys** in `app.py` (lines 7-8):
```python
OPENAI_API_KEY = "your-openai-key"
SERPER_API_KEY = "your-serper-key"
```
Get a free Serper key at https://serper.dev (2500 free searches)

3. **Run the app**
```bash
streamlit run app.py
```

## How it works

1. Enter a primary keyword + secondary keywords
2. Pipeline searches Google, scrapes top pages, extracts tools via GPT-4o
3. **Human checkpoint** — review and edit the tool list before drafting
4. GPT-4o writes the full listicle, then a second pass humanizes it
5. Download the final draft as Markdown

## Pipeline Architecture

```
Keywords → Serper Search → Jina Scrape → GPT-4o Extract → [Human Review] → GPT-4o Draft → GPT-4o Humanize → Markdown Output
```
