# GitHub Sourcing - Czech Developer Talent Pipeline

Intelligent GitHub scraper for sourcing Czech developers with AI-powered ranking and README analysis.

## 🚀 Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure settings (optional)
# Edit config.py to adjust limits, weights, delays, etc.

# 3. Run complete workflow
uv run python -m src.workflow

# Or customize via command-line
uv run python -m src.workflow -- --max-pages 10 --top-n 50
```
Run the web app:

```bash
uv run streamlit run src/web_app.py
```

Then open your browser at: http://localhost:8501

**That's it!** All three phases run automatically.

> 💡 **New:** All configuration is centralized in `config.py` for easy customization. See [Configuration Guide](docs/CONFIGURATION.md).

---

## ✨ Features

- 🎯 **Smart Ranking Algorithm** - Weighted scoring (0-100) based on:
  - 35% Contributions (last year)
  - 25% Total Stars
  - 20% Followers
  - 10% Public Repos
  - 10% Recent Activity
  
- 🔄 **Automatic Retry Logic** - Handles 502 errors with exponential backoff

- 📦 **Two-Phase Strategy** - Fetch all users fast, enrich only top candidates

- 📁 **Organized Output** - Timestamped folders with clear phase separation

- 🛠️ **Fully Configurable** - Easy command-line options and config files

---

## 📋 Workflow

### Option 1: Automated (Recommended)

```bash
# Run everything at once
uv run python -m src.workflow -- --max-pages 5 --top-n 30
```

### Option 2: Manual Steps

```bash
# Phase 1: Fetch users
python src/data_collection/fetch_users.py

# Phase 2: Rank users
python src/processing/rank_users.py data/raw/.../phase1_all_users.json 20

# Phase 3: Fetch READMEs
python src/processing/fetch_readmes.py data/raw/.../phase2_ranked_top_20.json
```

---

## 📊 Output Structure

```
data/raw/20251008_172333/
├── phase1_all_users.json          # All fetched users (no READMEs)
├── phase2_ranked_top_20.json      # Top 20 ranked by score
└── phase2_top_20_with_readmes.json # Top 20 with README content
```

### Example Rankings

```
🏆 Top 10 Users (Score 0-100):
Rank   Score    Login                Followers  Contrib    Stars   
----------------------------------------------------------------------
1      99.2     piskvorky            960        1217       22774   
2      97.52    mosra                976        1770       6500    
3      97.35    TomasVotruba         1604       5301       894     
4      91.65    Borda                3771       5722       666     
5      90.0     filiph               4245       1378       2782    
```

---

## ⚙️ Configuration

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--max-pages N` | Pages to fetch (25 users each) | 2 |
| `--top-n N` | Top users for README enrichment | 20 |
| `--location QUERY` | GitHub location search | `location:prague` |
| `--no-readmes` | Skip README fetching (faster) | False |

### Examples

```bash
# Small test (30 seconds)
uv run python -m src.workflow -- --max-pages 1 --top-n 5

# Medium run (5 minutes)
uv run python -m src.workflow -- --max-pages 10 --top-n 50

# Large run (10 minutes)
uv run python -m src.workflow -- --max-pages 20 --top-n 100

# Fast ranking only (no READMEs)
uv run python -m src.workflow -- --max-pages 10 --top-n 50 --no-readmes

# Different city
uv run python -m src.workflow -- --location "location:brno" --top-n 30
```

---

## 🔧 Advanced Configuration

Edit files for fine-grained control:

**`src/data_collection/fetch_users.py`**
```python
MAX_PAGES = 2              # Pages to fetch
USERS_PER_PAGE = 25        # Users per page
REPOS_PER_USER = 5         # Repos per user
API_DELAY = 5              # Delay between requests
```

**`src/processing/rank_users.py`**
```python
# Adjust scoring weights in calculate_user_score()
followers_score * 0.20     # Followers weight
contributions_score * 0.35 # Contributions weight
stars_score * 0.25         # Stars weight
```

---

## 🔄 Retry Logic

Automatically handles GitHub API 502 errors:

```
Fetching page 2...
  ⚠️  Got 502 error, retrying in 5s (attempt 1/3)...
  → Total matching users in GitHub: 15109
  ✅ Success after retry!
```

**Benefits:**
- 3 automatic retry attempts
- Exponential backoff (5s → 7s → 9s)
- ~95% success rate vs ~50% without retries

---

## 📚 Documentation

- **[QUICK_START.md](docs/QUICK_START.md)** - Fast 3-step guide
- **[MAIN_WORKFLOW.md](docs/MAIN_WORKFLOW.md)** - Complete workflow & retry logic
- **[TWO_PHASE_WORKFLOW.md](docs/TWO_PHASE_WORKFLOW.md)** - Two-phase strategy details
- **[NOVY_SCORING_SYSTEM.md](docs/NOVY_SCORING_SYSTEM.md)** - Scoring algorithm
- **[PROJECT_ORGANIZATION.md](docs/PROJECT_ORGANIZATION.md)** - Code structure
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** - All configuration options

---

## 📁 Project Structure

```
src/
├── data_collection/          # API calls & data fetching
│   ├── fetch_users.py        # Phase 1: Bulk user fetching
│   └── fetch_readmes.py      # Phase 3: README enrichment
│
└── processing/               # Data processing & analysis
    ├── rank_users.py         # Phase 2: Ranking algorithm
    └── text_processor.py     # Text utilities

workflow.py                   # Automated workflow orchestrator (use 'uv run python -m src.workflow')
```

---

## 🎯 Use Cases

### Recruitment
- Find active Czech developers
- Rank by experience and activity
- Analyze project portfolios

### Market Research
- Identify trending technologies
- Map developer communities
- Track skill distributions

### Open Source
- Find contributors for projects
- Identify maintainers
- Build communities

---

## 🛠️ Requirements

- Python 3.8+
- GitHub Personal Access Token
- `uv` package manager (or pip)

### Setup

```bash
# Clone repository
git clone https://github.com/sykoravojtech/github-sourcing.git
cd github-sourcing

# Install dependencies
uv sync

# Create .env file
echo "GITHUB_API_TOKEN=your_token_here" > .env

# Run
uv run python -m src.workflow
```

---

## 📈 Performance

| Users | Time | Success Rate |
|-------|------|--------------|
| 25 | ~10s | 99% |
| 50 | ~25s | 95% |
| 250 | ~5min | 90% |
| 500 | ~10min | 85% |

*With retry logic and 5s delays*

---

## ⚙️ Configuration

All settings are centralized in `config.py`:

- **Phase 1:** Page limits, users per page, repos per user
- **Phase 2:** Ranking weights and thresholds
- **API:** Rate limiting, retry logic, timeouts
- **Output:** Folder structure, JSON formatting

See the [Configuration Guide](docs/CONFIGURATION.md) for detailed documentation.

Quick validation:
```bash
python config.py  # Validate and view current settings
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional ranking factors
- More data sources (LinkedIn, Twitter)
- Machine learning for skill extraction
- Web interface/dashboard
- Automated scheduling

---

## 📝 License

MIT

---

## 🙏 Acknowledgments

- GitHub GraphQL API for user data
- GitHub REST API for README content
- Czech developer community

---

**Happy Sourcing!** 🚀