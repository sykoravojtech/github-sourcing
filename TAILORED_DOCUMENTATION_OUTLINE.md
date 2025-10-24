# Czech GitHub Report - Project Documentation

**What we built:** Automated system to discover, rank, and search Czech developers on GitHub  
**Status:** Working prototype  
**Cost so far:** Minimal (GitHub API is free, Groq LLM on free tier)

---

## 1. 🎯 What We Built & Why

### The Problem
HR needs to find Czech developers with specific skills, but:
- Manual GitHub searching takes hours
- Hard to compare developer quality
- Can't find specialists by expertise ("find React developers with TypeScript")
- No overview of Czech open-source ecosystem

### What Works Now
**Automated data collection** - Fetch 1000+ Czech developers in 12 minutes  
**Smart ranking system** - 0-100 score combining 6 metrics (contributions, stars, followers, activity, trend, repos)  
**AI-powered search** - "Find React developers" or "machine learning experts" using semantic search  
**Web interface** - Simple UI for searching and browsing results  
**Cost optimization** - 17× cheaper than naive approach (0.06 vs 1.0 API points per user)

### Key Numbers
- **Speed:** 12.4 minutes to fetch, rank, and enrich 962 users
- **Coverage:** Up to 1000 users per location query (GitHub limit)
- **Search quality:** Semantic matching with AI explanations
- **Cost:** FREE (GitHub API 5000 pts/hour, Groq LLM free tier)

### Current Limitations
**GitHub 1000-result limit** - Can only get 1000 users per query (need multi-query approach)  
**Location accuracy** - Relies on self-reported locations (need .cz domain checks)  
**No tech categories yet** - Can't filter by AI/Web/Backend/Data (planned)  
**JSON storage only** - Need database for historical trends and faster queries

---

## 2. ⚙️ How It Works - Technical Overview

### Three-Phase Pipeline

**Phase 1: Fetch Users (52% of time - 6.5 min for 962 users)**
```
Search GitHub → Get user logins → Batch fetch full profiles
```
- Searches by location: `location:prague OR location:brno OR ...`
- Filters: 5+ followers, 3+ repos
- Fetches full data in batches of 20 users (optimal for stability)
- Gets 365 days of contribution data (FREE from GitHub API!)
- **Speed:** 2.5 users/second

**Phase 2: Rank Users (0.1% of time - 1 second)**
```
Filter inactive users → Calculate scores → Sort → Return top-N
```
- Filters inactive users first (trend < 0.1, contributions < 1)
- Calculates 6-metric score (0-100) only for active users
- **Speed:** 992 users/second

**Phase 3: Enrich with READMEs (48% of time - 5.9 min for 50 users)**
```
Fetch README content → Enable semantic search
```
- Only for top-ranked users (configurable, default: 50)
- Required for AI-powered search to work
- **Speed:** 0.14 users/second (GitHub rate limits)

---

## 3. 🏆 Ranking System - How We Score Developers

### 6-Metric Formula (0-100 scale)

We use **fixed thresholds** for each metric, but also apply **linear scaling** (normalization up to the threshold) to ensure fair scoring:

| Metric           | Weight | Threshold (100 pts) | Why This Matters                        |
|------------------|--------|---------------------|-----------------------------------------|
| **Contributions**| 25%    | 3000/year           | Long-term commitment & work ethic       |
| **Stars**        | 20%    | 1000 total          | Code quality & project impact           |
| **Followers**    | 15%    | 500 followers       | Community recognition                   |
| **Activity**     | 15%    | 15 in 30 days       | Currently active (not abandoned account)|
| **Trend**        | 15%    | 100 points          | Rising star vs declining activity       |
| **Repos**        | 10%    | 50 repos            | Breadth of experience                   |

**How Scoring Works:**
- For each metric, a developer gets a score from 0 to 100, scaled linearly up to the threshold (e.g., 250 followers = 50 pts for the Followers metric).
- Scores above the threshold are capped at 100.
- Final score is a weighted sum of all metrics.

**Why This Hybrid Approach?**

- **Thresholds** prevent "influencer" outliers from dominating the rankings.
- **Linear scaling** (normalization up to the threshold) ensures fair comparison for everyone else.

**Example:**
```
Followers metric (threshold = 500):
- 10000 followers → 100 pts (capped)
- 500 followers  → 100 pts
- 250 followers  → 50 pts
- 100 followers  → 20 pts
```
This balances recognition for standout contributors while keeping the system fair for typical developers.
```

### Trend Score Explained (15 points)

Measures momentum using two factors:

**Contribution Momentum (60%):**
- Last 30 days: 25 pts (50+ contributions = max score, scales linearly)
- Last 90 days: 20 pts (150+ contributions = max score, scales linearly)
- Consistency: 15 pts (ratio of active days to total days)

**Project Momentum (40%):**
- Active high-value projects: 25 pts (repos with 10+ stars updated in last 6 months)
- Recent project work: 15 pts (3+ repos pushed in last 90 days = max score)

**Note:** GitHub API doesn't provide star timestamps, so we track contribution velocity instead of star growth.

---

## 4. 🇨🇿 Czech Developer Identification

**Current method:** Location keyword matching (33 keywords)

```
location:prague OR location:brno OR location:czechia OR location:ostrava ...
```

**Quality filters:**
- 5+ followers (reduces spam)
- 3+ repos (shows actual work)

**Known issues:**
- "Prague, Texas" counts as Czech → Need better filtering
- No .cz domain checks yet
- No Czech company verification (Avast, Kiwi.com, Seznam, etc.)

**This needs work but good enough for MVP.**

---

## 5. 🔍 AI-Powered Semantic Search

**The killer feature:** Find developers by what they do, not just keywords.

### How It Works

**Example queries:**
- "Find React developers with TypeScript experience"
- "Machine learning engineers working on NLP"
- "Backend developers with Kubernetes"
- "Text-to-speech specialists"

**Technology:**
- **Embeddings:** Sentence Transformers (all-MiniLM-L6-v2)
- **Vector math:** Cosine similarity between query and profiles
- **Profile text:** Bio + repos + languages + README content
- **LLM reasoning:** Groq API (using `meta-llama/llama-4-scout-17b-16e-instruct`) explains why each match is relevant

**Example output:**
```
Match 1: johndoe (94% match)
✓ Has 3 React projects with TypeScript
✓ Active contributor to Next.js ecosystem
✓ Recently published TypeScript utility library

Match 2: janenovak (87% match)
✓ Maintains popular React component library
✓ TypeScript expert based on repo languages
✓ Contributed to TypeScript documentation
```

**Why this matters:** HR can search by job requirements, not just GitHub metadata.

---

## 6. ⚡ Performance & Costs

### Speed (for 962 users, Prague query)

```
Total: 12.4 minutes

Phase 1 (Fetch):  52% - 6.5 minutes @ 2.5 users/sec
Phase 2 (Rank):    0% - 1 second   @ 992 users/sec  
Phase 3 (README): 48% - 5.9 minutes @ 0.14 users/sec
```

**Bottleneck:** README fetching (GitHub rate limits individual file requests)

### API Costs

**GitHub API:** FREE
- 5000 points/hour quota
- Uses only 60 points for 1000 users (1.2% of quota)
- Can run 83 batches of 1000 users per hour

**Groq LLM:** FREE (for now)
- Used for search result explanations
- ~100 tokens per explanation
- Can be disabled to save tokens

**Total monthly cost:** $0

---

## 7. 📊 Sample Results

### Top 5 Prague Developers (October 2025)

```
Rank  Score   Login           Followers  Contributions  Stars
------------------------------------------------------------
1     99.2    piskvorky       960        1217          22,774
2     97.5    mosra           976        1770          6,500
3     97.4    TomasVotruba    1604       5301          894
4     91.7    Borda           3771       5722          666
5     90.0    filiph          4245       1378          2,782
```

**Observations:**
- Balanced mix of "star power" (piskvorky: 22K stars) and active contributors (TomasVotruba: 5.3K contributions)
- All users have recent activity (not abandoned accounts)
- Range from niche specialists to generalists

### Known Issues

**1000-result GitHub limit** - Need multi-query approach (by language) to get more users  
**No tech categories yet** - Can't filter by AI/Web/Backend/Data streams  
**Location ambiguity** - "Prague, Texas" vs "Prague, Czech Republic"  
**No historical data** - Can't track trends over time (JSON storage only)

---

## 8. 📋 What We Need to Do Next (Priority Order)

### Critical (needed for HR lady's requirements)

**1. Break GitHub's 1000-user limit with multi-query approach**
```bash
# Query by language to get more users
location:prague language:Python    → 1000 users
location:prague language:JavaScript → 1000 users  
location:prague language:TypeScript → 1000 users
location:prague language:Go         → 1000 users

# After deduplication: ~3000-4000 unique users
```

**2. Add tech category classification (AI/Web/Backend/Data)**
- Classify by primary languages and topics
- Filter web interface by category
- Show category-specific leaderboards

**3. Switch from JSON to SQL database**
- Store historical data for trend tracking
- Enable faster queries and filtering
- Track changes over time (new repos, star growth)

### Important (makes it more useful)

**4. Better embeddings model**
- Current: all-MiniLM-L6-v2 (basic, fast)
- Upgrade: all-mpnet-base-v2 or instructor-xl (better quality)

**5. Improve Czech identity detection**
- Check for .cz domains in profile URLs
- Cross-reference with Czech companies (Avast, Kiwi, Seznam, STRV, etc.)
- Filter out "Prague, Texas" false positives

**6. Export functionality**
- CSV for Excel analysis
- Shareable report URLs
- PDF generation for presentations

### Nice to Have (later)

**7. Scheduled daily/weekly runs**
- Auto-update rankings
- Track trending developers  
- Email reports to HR

**8. Organization-level analysis**
- Top Czech companies by GitHub activity
- Company-specific developer lists

**9. Contributor network analysis**
- Find developers who collaborate
- Identify project teams

---

## 9. 💡 Key Technical Insights

### What We Learned Building This

**1. GitHub API Optimization (17× cost reduction)**

**Naive approach: Get full data directly from search (1 API point per user)**
```graphql
query {
  search(query: "location:prague", type: USER, first: 100) {
    nodes {
      ... on User {
        login, name, bio
        followers { totalCount }
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { date, contributionCount } }
          }
        }
        repositories(first: 5, orderBy: {field: STARGAZERS, direction: DESC}) {
          nodes { name, stargazerCount, description }
        }
      }
    }
  }
  rateLimit { cost }  # Cost: 100 points! (1 per user)
}
```
Problem: GitHub charges 1 point PER USER when you fetch full data in search results = 100 points per 100 users

**Our two-phase approach: 0.06 points per user**

*Phase 1: Search for logins only (1 point per 100 users)*
```graphql
query {
  search(query: "location:prague", type: USER, first: 100) {
    nodes { ... on User { login } }  # Just get logins!
  }
  rateLimit { cost }  # Cost: 1 point for 100 users
}
```

*Phase 2: Batch fetch full data (1 point per 20 users)*
```graphql
query {
  user1: user(login: "john") { name, bio, followers, contributionsCollection, ... }
  user2: user(login: "jane") { name, bio, followers, contributionsCollection, ... }
  # ... 18 more users
  rateLimit { cost }  # Cost: 1 point for 20 users
}
```

**Result:** 100 users = 1 search point + 5 batch points = 6 total (vs 100 naive)

**2. Contribution Calendar is Free**

We discovered that GitHub's contribution calendar costs ZERO extra API points:

```graphql
query {
  user(login: "johndoe") {
    contributionsCollection(from: "2024-01-01", to: "2025-01-01") {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount  # 366 days of data!
          }
        }
      }
    }
  }
  rateLimit { cost }  # Still just 1 point!
}
```

This gives us 365 days × contribution counts = most valuable metric for FREE!

**3. Deduplication Saves 25% on API Costs**

GitHub's paginated search returns duplicates:
```
Page 1: [user1, user2, user3, ..., user100]  # 100 users
Page 2: [user80, user81, ..., user180]       # 27 duplicates!
Page 3: [user160, user161, ..., user260]     # 20 duplicates!
```

**Without dedup:** Fetch 300 logins → 300 unique → 15 batch queries (300 API points wasted)
**With dedup:** Fetch 300 logins → 230 unique → 12 batch queries (saves 70 API points!)

Simple fix:
```python
# Dedup BEFORE fetching full data
unique_logins = list(set(all_logins))  # 300 → 230
# Then batch fetch only 230 users
```

**4. Thresholds Beat Normalization for Ranking**

**Bad: Normalization approach**
```python
# Normalize to top user in dataset
max_followers = max(u['followers'] for u in users)  # 50,000
score = (followers / max_followers) * 100

# Results:
# Influencer with 50K followers: 100 pts
# Good dev with 500 followers: 1 pt  ❌ Unfair!
```

**Good: Fixed threshold approach**
```python
# Fixed threshold for 100 points
threshold = 500  # Reasonable for hireable devs
score = min(100, (followers / threshold) * 100)

# Results:
# Influencer with 50K followers: 100 pts (capped)
# Good dev with 500 followers: 100 pts ✓ Fair!
# Active dev with 250 followers: 50 pts  ✓ Fair!
```

**5. README Content is Critical for Search**

**Without READMEs (mediocre results):**
```python
profile_text = f"{user['bio']} {user['name']}"
# Query: "React developer"
# Match: "john" (bio: "Software engineer") → 12% match ❌
```

**With READMEs (excellent results):**
```python
profile_text = f"{user['bio']} {readme_content} {repo_descriptions}"
# Query: "React developer"  
# Match: "john" (README: "Built React dashboard, 10 React components...") 
#        → 94% match ✓
```

README content provides 50-100× more text with actual technical details vs bio alone.

### Architecture Decisions That Paid Off

**JSON files over database (initially)** - Fast iteration, no schema migrations  
**Batch size of 20 users** - Sweet spot for stability vs speed  
**Sentence Transformers over OpenAI** - Free, fast, CPU-only, good quality  
**Groq over OpenAI for LLM** - 10× faster inference, free tier generous  
**Streamlit over custom web app** - Working UI in hours, not days

---

## 10. 💰 Why This Deserves More Budget

### What HR Lady Gets Today

Search 1000+ Czech developers in 12 minutes  
AI-powered search: "Find React developers" actually works  
Fair ranking system (not dominated by influencers)  
Web interface anyone can use  
Zero ongoing costs (GitHub + Groq free tiers)

### What's Blocking Production Use

**Can't get past 1000 users per query** (GitHub limit)  
**No AI/Web/Backend/Data categories** (HR requirement)  
**No historical trends** (need database, not JSON)  
**Location accuracy ~80%** (false positives like "Prague, Texas")

### What We Need

**Time:** 2-3 weeks additional development  
**Resources:**  
- Fix multi-query approach for 3000+ users
- Implement tech category classification  
- Migrate to SQL database
- Improve Czech identity detection

**Cost:** Still $0/month in API fees (everything stays on free tiers)

### ROI Estimate

**Without this tool:**
- HR spends 5 hours/week manually searching GitHub
- Finds maybe 20-30 relevant candidates
- Misses 90% of qualified developers

**With this tool:**
- HR spends 10 minutes/week reviewing search results
- Gets 100+ ranked candidates
- Can filter by expertise ("machine learning", "React", "DevOps")

**Time saved:** ~20 hours/month = €600-1000/month value

---

## Appendix: Technical Documentation

All detailed docs are in `docs/` folder:

- `GITHUB_API_COSTS.md` - Cost analysis and optimization strategy
- `TWO_PHASE_WORKFLOW.md` - How the pipeline works
- `COMPLETE_WORKFLOW_GUIDE.md` - Usage instructions
- `TREND_SCORE_EXPLAINED.md` - Ranking formula details
- `WEB_APP_GUIDE.md` - Web interface documentation
- `BATCH_SIZE_TESTING_RESULTS.md` - Performance benchmarks
