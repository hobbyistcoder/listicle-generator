import streamlit as st
import streamlit.components.v1 as components
import re
import requests
import json
from openai import OpenAI

# ── CONFIG ──────────────────────────────────────────────────────────────────
OPENAI_API_KEY = "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"   # ← replace with Zuddl key
SERPER_API_KEY = "42d88acfd41c33b04098846d5c7f4c5ad6d01bca"   # ← replace with key from serper.dev

client = OpenAI(api_key=OPENAI_API_KEY)

# ── PIPELINE FUNCTIONS ───────────────────────────────────────────────────────

def search_tools(primary_kw, secondary_kws):
    """Step 1: Search Google via Serper for top pages on this software category."""
    query = f"best {primary_kw} tools software comparison"
    headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
    response = requests.post(
        "https://google.serper.dev/search",
        headers=headers,
        json={"q": query, "num": 20}
    )
    results = response.json()
    urls = [r["link"] for r in results.get("organic", [])]
    return urls

def scrape_url(url):
    """Step 2: Use Jina.ai reader to scrape a URL — no API key needed."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=20)
        return response.text[:4000]  # cap per page to control token usage
    except Exception as e:
        return ""

def extract_tools(scraped_content, primary_kw):
    """Step 3: LLM extracts structured tool data from scraped content."""
    prompt = f"""
You are extracting software tool information from web content about "{primary_kw}".

From the content below, identify all distinct software tools/products mentioned.
For each tool return a JSON object with these fields:
- name (string)
- tagline (1 sentence)
- description (2-3 sentences about what it does)
- key_features (list of 4-5 strings)
- pricing (string, e.g. "Free tier + paid from $X/mo" or "Contact for pricing")
- best_for (string, who is this ideal for)
- rating (string, e.g. "4.5/5 on G2" — only if mentioned, else null)

Return ONLY a valid JSON object with a single key "tools" containing an array.
Do not include any markdown, explanation, or text outside the JSON.

Content:
{scraped_content}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )
    raw = response.choices[0].message.content
    data = json.loads(raw)
    return data.get("tools", [])

def deduplicate_tools(tools):
    """Remove duplicate tools by name (case-insensitive)."""
    seen = set()
    unique = []
    for t in tools:
        name = t.get("name", "").lower().strip()
        if name and name not in seen:
            seen.add(name)
            unique.append(t)
    return unique

def markdown_to_html(md):
    """Convert markdown to clean HTML suitable for pasting into a CMS."""
    html = md
    # Headings
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    # Bold / italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
    # Bullet lists — group consecutive lines starting with -
    def replace_list(match):
        items = match.group(0).strip().split('\n')
        lis = ''.join(f'<li>{re.sub(r"^- ", "", i).strip()}</li>' for i in items if i.strip())
        return f'<ul>{lis}</ul>'
    html = re.sub(r'(^- .+\n?)+', replace_list, html, flags=re.MULTILINE)
    # Table (basic — pipe-delimited)
    def replace_table(match):
        rows = [r.strip() for r in match.group(0).strip().split('\n') if '|' in r and not re.match(r'\|[-| ]+\|', r)]
        if not rows:
            return match.group(0)
        header, *body = rows
        ths = ''.join(f'<th>{c.strip()}</th>' for c in header.split('|') if c.strip())
        trs = ''.join('<tr>' + ''.join(f'<td>{c.strip()}</td>' for c in row.split('|') if c.strip()) + '</tr>' for row in body)
        return f'<table><thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>'
    html = re.sub(r'(\|.+\|\n)+', replace_table, html)
    # Horizontal rules
    html = re.sub(r'^---$', '<hr>', html, flags=re.MULTILINE)
    # Paragraphs — wrap non-tagged lines
    lines = html.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('<'):
            result.append(stripped)
        else:
            result.append(f'<p>{stripped}</p>')
    return '\n'.join(result)

def generate_draft(tools, primary_kw, secondary_kws):
    """Step 4: Generate the full listicle draft in Zuddl blog style."""
    num = len(tools)
    prompt = f"""
Write a complete, SEO-optimised listicle blog post in the style of a sharp B2B SaaS content team.

Primary keyword: {primary_kw}
Secondary keywords to weave in naturally: {secondary_kws}
Number of tools: {num}

Tools to cover:
{json.dumps(tools, indent=2)}

Follow this EXACT structure:

---

# [Number] Best {primary_kw.title()} for B2B Teams in 2025

*[One-sentence hook that states the core problem this category solves]*

---

## Quick Comparison: {primary_kw.title()} at a Glance

| Tool | Best For | Starting Price |
|------|----------|----------------|
[fill in a row for each tool]

---

## Introduction (150-200 words)
- What is this software category and what problem does it solve
- Who should read this guide
- How we evaluated these tools (criteria: ease of use, features, pricing, integrations, support)
- Include primary keyword naturally in first 100 words

---

For EACH tool, use this EXACT format:

## [N]. [Tool Name] — [one-line verdict]

[2 paragraphs: what it is, who uses it, what makes it distinct. Be opinionated. Not every tool is great for everyone.]

### Key Features
- [feature 1 with 1-sentence explanation]
- [feature 2 with 1-sentence explanation]
- [feature 3 with 1-sentence explanation]
- [feature 4 with 1-sentence explanation]

### Pros
- [pro 1]
- [pro 2]
- [pro 3]

### Cons
- [con 1]
- [con 2]

### Pricing
[Specific pricing info. If unknown, say "Contact for pricing" and explain what's typically included at enterprise tier.]

### Best For
[1-2 sentences on the ideal user/team size/use case]

---

## How to Choose the Right {primary_kw.title()} (200 words)
A practical decision framework. Cover: team size, budget, integrations needed, must-have vs nice-to-have features.

---

## Frequently Asked Questions

**Q: [Relevant question about the category]**
A: [2-3 sentence answer]

**Q: [Another relevant question]**
A: [2-3 sentence answer]

**Q: [One more relevant question]**
A: [2-3 sentence answer]

---

## Final Thoughts

[100-150 words. Summarise the landscape, who should pick what. End with a natural CTA placeholder: [CTA: Learn how Zuddl handles {primary_kw}]]

---

Writing rules:
- Tone: direct, informed, slightly opinionated. Like a senior analyst, not a copywriter.
- NEVER use: leverage, comprehensive, robust, delve, seamlessly, cutting-edge, game-changer, streamline, unlock, empower
- Vary sentence length aggressively
- Add [INTERNAL_LINK: anchor text] placeholders where relevant
- Write the FULL article. Do not truncate, summarise or leave placeholders unfilled.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096
    )
    return response.choices[0].message.content

def humanize(draft, primary_kw):
    """Step 5: Second pass to kill AI slop and tighten the writing."""
    prompt = f"""
Edit this listicle article about {primary_kw} tools. Your job is to make it sound like 
it was written by a sharp human analyst — not an AI.

Rules:
1. Remove any remaining AI filler phrases: "in today's fast-paced world", "look no further", 
   "in conclusion", "it's worth noting", "it's important to", "leverage", "seamlessly", etc.
2. Add one concrete, specific example or use case per tool (can be hypothetical but realistic)
3. Where the writing is vague, make it specific
4. Vary paragraph length — no more than 3 paragraphs the same length in a row
5. Add 1-2 mild opinions per section ("What sets it apart is...", "The catch is...", "Honestly...")
6. Keep ALL factual content, structure, headings, and internal link placeholders exactly as-is
7. Do not add new sections or remove existing ones
8. Output the full article. Do not summarise or truncate.

Article:
{draft}
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=4096
    )
    return response.choices[0].message.content


# ── UI ───────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Listicle Generator · Zuddl",
    page_icon="📝",
    layout="wide"
)

# Zuddl-inspired styling
st.markdown("""
<style>
    /* Base */
    [data-testid="stAppViewContainer"] {
        background-color: #0f0f1a;
        color: #e8e8f0;
    }
    [data-testid="stSidebar"] { background-color: #0f0f1a; }

    /* Header bar */
    .zuddl-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 24px 0 16px 0;
        border-bottom: 1px solid #2a2a3d;
        margin-bottom: 32px;
    }
    .zuddl-header img {
        height: 28px;
        filter: brightness(0) invert(1);
    }
    .zuddl-divider {
        width: 1px;
        height: 20px;
        background: #2a2a3d;
    }
    .zuddl-badge {
        background: #1e1e35;
        border: 1px solid #7c5cfc44;
        color: #a78bfa;
        font-size: 11px;
        font-weight: 600;
        padding: 3px 12px;
        border-radius: 20px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }

    /* Typography */
    h1, h2, h3 { color: #ffffff !important; }
    .step-label {
        font-size: 12px;
        font-weight: 600;
        color: #7c5cfc;
        letter-spacing: 1px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .step-title {
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 20px;
    }

    /* Inputs */
    .stTextInput input, .stTextArea textarea {
        background-color: #1a1a2e !important;
        border: 1px solid #2a2a4a !important;
        color: #e8e8f0 !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #7c5cfc !important;
        box-shadow: 0 0 0 2px #7c5cfc22 !important;
    }

    /* Buttons */
    .stButton button {
        background: linear-gradient(135deg, #7c5cfc, #9d7cfc) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
        transition: opacity 0.2s !important;
    }
    .stButton button:hover { opacity: 0.9 !important; }

    /* Info / alert boxes */
    .stInfo {
        background-color: #1a1a35 !important;
        border-left-color: #7c5cfc !important;
        color: #c4b5fd !important;
    }

    /* Progress */
    .stProgress > div > div { background-color: #7c5cfc !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        color: #888 !important;
        font-weight: 600 !important;
    }
    .stTabs [aria-selected="true"] {
        color: #7c5cfc !important;
        border-bottom-color: #7c5cfc !important;
    }

    /* Download button */
    .stDownloadButton button {
        background: #1a1a2e !important;
        border: 1px solid #7c5cfc !important;
        color: #a78bfa !important;
    }

    /* Select slider */
    .stSlider [data-baseweb="slider"] { color: #7c5cfc; }
</style>

<div class="zuddl-header">
    <svg height="28" viewBox="0 0 120 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <text x="0" y="26" font-family="'Inter', 'Helvetica Neue', Arial, sans-serif" 
            font-size="28" font-weight="700" letter-spacing="-1" fill="#ffffff">zuddl</text>
      <circle cx="113" cy="9" r="5" fill="#7c5cfc"/>
    </svg>
    <div class="zuddl-divider"></div>
    <div class="zuddl-badge">Content Engine</div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
for key in ["stage", "tools", "draft", "final"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "stage" else "input"

# ── STAGE 1: INPUT ───────────────────────────────────────────────────────────
if st.session_state.stage == "input":
    st.markdown('<div class="step-label">Step 01</div><div class="step-title">Enter your keywords</div>', unsafe_allow_html=True)

    with st.form("kw_form"):
        primary_kw = st.text_input(
            "Primary Keyword",
            placeholder="e.g. event registration software"
        )
        secondary_kws = st.text_input(
            "Secondary Keywords (comma-separated)",
            placeholder="e.g. event ticketing platform, online event check-in, attendee management"
        )

        max_tools = st.slider("Number of tools to include", min_value=3, max_value=15, value=7, step=1)

        go = st.form_submit_button("🔍 Research")

    if go and primary_kw:
        MAX_PAGES = 20  # hard cap on pages to scrape
        st.session_state.max_tools = max_tools
        st.session_state.primary_kw = primary_kw
        st.session_state.secondary_kws = secondary_kws

        with st.spinner("Searching Google for top pages in this category..."):
            urls = search_tools(primary_kw, secondary_kws)

        all_content = ""
        tools = []
        progress = st.progress(0, text="Starting research...")

        for i, url in enumerate(urls[:MAX_PAGES]):
            progress.progress(
                min((i + 1) / MAX_PAGES, 1.0),
                text=f"Scraping page {i+1} — {len(tools)} tools found so far..."
            )
            content = scrape_url(url)
            if not content:
                continue
            all_content += content + "\n\n---\n\n"

            # Re-extract every 3 pages or at end — stop early if we have enough tools
            if (i + 1) % 3 == 0 or i == len(urls[:MAX_PAGES]) - 1:
                raw_tools = extract_tools(all_content, primary_kw)
                tools = deduplicate_tools(raw_tools)
                if len(tools) >= max_tools:
                    break

        tools = tools[:max_tools]

        st.session_state.tools = tools
        st.session_state.stage = "review"
        st.rerun()

# ── STAGE 2: HUMAN CHECKPOINT ────────────────────────────────────────────────
elif st.session_state.stage == "review":
    st.markdown('<div class="step-label">Step 02</div><div class="step-title">Review the tool list</div>', unsafe_allow_html=True)
    st.info("✋ Human checkpoint — review tools found during research. Add, remove, or edit any entry, then approve to generate the draft.")

    edited = st.text_area(
        "Tools (editable JSON)",
        value=json.dumps(st.session_state.tools, indent=2),
        height=400
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        approve = st.button("✅ Approve & Generate Draft", type="primary")
    with col2:
        restart = st.button("🔄 Start Over")

    if restart:
        st.session_state.stage = "input"
        st.rerun()

    if approve:
        try:
            approved_tools = json.loads(edited)
        except json.JSONDecodeError:
            st.error("JSON is invalid — fix it before proceeding.")
            st.stop()

        st.session_state.tools = approved_tools

        with st.spinner("Writing listicle draft..."):
            draft = generate_draft(
                approved_tools,
                st.session_state.primary_kw,
                st.session_state.secondary_kws
            )

        with st.spinner("Humanizing the content..."):
            final = humanize(draft, st.session_state.primary_kw)

        st.session_state.draft = draft
        st.session_state.final = final
        st.session_state.stage = "output"
        st.rerun()

# ── STAGE 3: OUTPUT ──────────────────────────────────────────────────────────
elif st.session_state.stage == "output":
    st.markdown('<div class="step-label">Step 03</div><div class="step-title">Your draft is ready</div>', unsafe_allow_html=True)

    html_output = markdown_to_html(st.session_state.final)

    tab1, tab2, tab3 = st.tabs(["📄 Final Draft", "🌐 HTML Preview", "📝 Raw Draft"])

    with tab1:
        st.markdown(st.session_state.final)
        st.download_button(
            label="⬇️ Download as Markdown",
            data=st.session_state.final,
            file_name=f"{st.session_state.primary_kw.replace(' ', '_')}_listicle.md",
            mime="text/markdown"
        )

    with tab2:
        # Copy to clipboard button using JS
        escaped = html_output.replace('`', r'\`').replace('\\', '\\\\')
        components.html(f"""
        <div style="font-family: sans-serif; padding: 8px 0;">
            <button onclick="
                navigator.clipboard.writeText(`{escaped}`)
                    .then(() => {{ this.innerText = '✅ Copied!'; setTimeout(() => this.innerText = '📋 Copy HTML for CMS', 2000); }})
                    .catch(() => {{ this.innerText = '❌ Copy failed — use the text area below'; }});
            " style="
                background: linear-gradient(135deg, #7c5cfc, #9d7cfc);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                margin-bottom: 12px;
            ">📋 Copy HTML for CMS</button>
            <p style="color: #888; font-size: 12px; margin: 0;">
                Paste directly into Webflow, WordPress, Notion, or any rich-text CMS editor.
            </p>
        </div>
        """, height=90)
        st.code(html_output, language="html")

    with tab3:
        st.markdown(st.session_state.draft)

    if st.button("🔄 Generate Another"):
        for key in ["stage", "tools", "draft", "final", "primary_kw", "secondary_kws"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
