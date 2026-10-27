# Indian Business Cases

A free, lightweight, static information archive documenting researched, real-life outcomes of commercial enterprises in India: what founders invested, running costs, earnings, and documented factors behind success or closure.

---

## 1. Operating Ethics & Non-Advisory Stance

- **Strictly Non-Advisory**: The site NEVER advises or recommends ("you should", "best business to start"). We document solely "what happened" based on public records and news reporting.
- **The "Not Found" Rule**: No metric is ever estimated or extrapolated. If a source did not report a figure, it appears as **"Not found"**.
- **Evidence-First**: Every number is linked to a verbatim quote under 25 words from a whitelisted source.
- **Equal Weight for Failures**: Business closures receive identical visual hierarchy and typographic weight as profitable ventures.
- **Universal Disclaimer**: Displayed in the footer of every page: factual documentation only, not financial or business advice.

---

## 2. Zero-Cost Architecture

- **Static Site Hosting**: GitHub repository connected to [Netlify](https://www.netlify.com/).
  - **Publish directory**: `site/`
  - **Build command**: *None* (Netlify simply serves the committed HTML/CSS/JS files).
- **Automation**: GitHub Actions cron jobs (free tier) run the extraction pipeline, build static HTML into `site/`, and commit changes back to the repository.
- **Free-Tier AI Pipeline**:
  - Primary extraction: Google Gemini free tier (`gemini-2.5-flash`).
  - Cross-checking: Groq free tier (`llama-3.3-70b-versatile`).
- **No Database**: All records live in version-controlled JSON files under `data/`.

---

## 3. Getting Free API Keys

1. **Google Gemini API Key**:
   - Visit [Google AI Studio](https://aistudio.google.com/).
   - Click "Get API key" and create a free API key.
2. **Groq API Key**:
   - Visit [Groq Cloud Console](https://console.groq.com/).
   - Sign up and generate a free API key under "API Keys".

---

## 4. GitHub Secrets Setup

In your GitHub repository:
1. Navigate to **Settings > Secrets and variables > Actions**.
2. Under **Repository secrets**, click **New repository secret**:
   - `GEMINI_API_KEY`: Paste your Google AI Studio API key.
   - `GROQ_API_KEY`: Paste your Groq Cloud API key.

---

## 5. Local Development

### Requirements
- Python 3.11+
- Virtual environment (recommended)

```bash
# Clone the repository
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Running the Pipeline Locally
```bash
# Dry run mode (Zero API calls, uses saved fixture article)
python -m pipeline.run_pipeline --dry-run

# Live extraction run (requires GEMINI_API_KEY and GROQ_API_KEY in environment)
export GEMINI_API_KEY="your-key"
export GROQ_API_KEY="your-key"
python -m pipeline.run_pipeline --max-articles 5
```

### Building the Static Site
```bash
# Build production site from data/cases/ (writes strictly to site/)
python build_site.py

# Build demonstration site with test fixtures (SAMPLE – NOT REAL)
# Writes strictly to preview/ and NEVER touches production site/
python build_site.py --use-fixtures
```

### Running Tests
```bash
python -m unittest discover tests
```

---

## 6. Manual Review of Generated Cases

Before new cases are published live:
1. Review newly created files in `data/cases/<id>.json`.
2. Verify that `verification.quotes_verified` is `true`.
3. Check `own_summary` to ensure it is neutral and does not use advisory terms.
4. Run `python build_site.py` and inspect `site/cases/<id>/index.html`.

---

## 7. Connecting to Netlify

1. Go to [Netlify](https://app.netlify.com/) and click **Add new site > Import an existing project**.
2. Select your GitHub repository.
3. In Site configuration:
   - **Branch to deploy**: `main`
   - **Base directory**: Leave blank
   - **Build command**: Leave blank
   - **Publish directory**: `site`
4. Click **Deploy site**. Any GitHub Actions commit will instantly trigger Netlify's CDN deployment.

> [!NOTE]
> Scheduled GitHub Actions cron runs may occasionally experience delays of a few minutes during peak GitHub platform usage.
