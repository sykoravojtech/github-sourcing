"""
Centralized Configuration for GitHub Sourcing Project

All configurable parameters in one place for easy management.
Edit these values to customize the scraper behavior.
"""

import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ========== AUTHENTICATION ==========
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError(
        "GitHub API token not found. Please set GITHUB_API_TOKEN in the .env file."
    )

# ========== SEARCH CONFIGURATION ==========
# Czech location keywords for user identification
# GitHub search is case-insensitive
CZECH_KEYWORDS = [
    "czechia",
    "czech republic",
    "the czech republic",
    "czech",
    "cesko",
    "česko",
    "cz",
    "prague",
    "praha",
    "brno",
    "ostrava",
    "plzen",
    "plzeň",
    "liberec",
    "olomouc",
    "ústí nad labem",
    "české budějovice",
    "hradec králové",
    "pardubice",
    "zlín",
    "havířov",
    "kladno",
    "most",
    "opava",
    "frýdek-místek",
    "karviná",
    "jihlava",
    "teplice",
    "děčín",
    "karlovy vary",
    "chomutov",
    "přerov",
    "jablonec nad nisou",
]


def build_czech_location_query():
    """
    Build a GitHub search query using all Czech location keywords.

    Returns a query string like:
    location:"czechia" OR location:"czech republic" OR location:"prague" OR ...

    Usage:
        query = build_czech_location_query()
        users = fetch_all_users(search_query=query)
    """
    # Quote keywords that contain spaces, leave others as-is
    quoted_keywords = [
        f'location:"{keyword}"' if " " in keyword else f"location:{keyword}"
        for keyword in CZECH_KEYWORDS
    ]
    return " OR ".join(quoted_keywords)


# Default search location (can be overridden in workflow.py)
# Use ALL 33 Czech keywords for broadest search
# DEFAULT_LOCATION = build_czech_location_query()  # All Czech locations
DEFAULT_LOCATION = "location:prague"  # Single city (most focused)
# DEFAULT_LOCATION = "location:czechia OR location:czech OR location:praha OR location:brno OR location:ostrava"  # Major cities

# ========== PHASE 1: BULK FETCH CONFIGURATION ==========
# Number of pages to fetch (each page has USERS_PER_PAGE users)
# Recommended: 2 for testing, 20 for medium, 100+ for production
MAX_PAGES = 10

# Number of users to fetch per page
# Note: GitHub API allows max 100, but 25 is more reliable with contributionsCollection
# Range: 10-100 (lower = more stable, higher = faster but more 502 errors)
USERS_PER_PAGE = 15

# Number of top repositories to fetch per user (ordered by stars)
# Range: 3-10 (lower = faster, higher = more data but slower)
REPOS_PER_USER = 5

# Whether to fetch README content during Phase 1
# Recommended: False (fetch READMEs only for top users in Phase 3)
FETCH_READMES = False

# ========== PHASE 2: RANKING CONFIGURATION ==========
# Number of top-ranked users to select for README enrichment
# This is the default, can be overridden in workflow.py with --top-n
TOP_N_USERS = 20

# Scoring weights (must sum to 1.0)
# Adjust these to change ranking priorities
SCORING_WEIGHTS = {
    "contributions": 0.25,  # GitHub contributions in last year (12 měsíců)
    "stars": 0.20,  # Total stars across repositories (dopad projektů)
    "followers": 0.15,  # Number of followers (počet sledujících)
    "activity": 0.15,  # Recent activity (last 30 days) (aktuální pulse)
    "repos": 0.10,  # Number of public repositories (rozsah práce)
    "trend": 0.15,  # Trend growth/momentum (trendový růst)
}

# Normalization thresholds for scoring
# Values at or above threshold get maximum score (100 points)
SCORING_THRESHOLDS = {
    "contributions": 1000,  # 1000+ contributions/year = 100 points
    "stars": 1000,  # 1000+ stars total = 100 points
    "followers": 1000,  # 1000+ followers = 100 points
    "repos": 50,  # 50+ repos = 100 points
    "activity_30_days": 15,  # 15+ contributions in last 30 days = 100 points (active)
    # Trend score thresholds (Oct 2025: Uses contribution calendar + repo activity)
    "trend_recent_contributions": 50,  # 50+ contributions in 30 days = max recent momentum
    "trend_quarterly_contributions": 150,  # 150+ contributions in 90 days = max quarterly momentum
    "trend_active_projects": 3,  # 3+ high-value projects active in 180 days = max project score
    "trend_recent_projects": 3,  # 3+ projects pushed in 90 days = max recent work
}

# Minimum contributions required to be included in rankings
# Users with fewer contributions in the last year will be filtered out
MIN_CONTRIBUTIONS_REQUIRED = 1  # Set to 0 to include everyone

# Minimum trend score required to be included in rankings
# Users with trend score of 0 (no activity in last 90 days) will be filtered out
# This is a red flag for talent sourcing - inactive developers are less likely to be hireable
MIN_TREND_SCORE_REQUIRED = 0.1  # Set to 0 to include everyone (even inactive users)

# ========== API RATE LIMITING ==========
# Delay between page requests (seconds)
# Recommended: 5-10 for contributionsCollection queries
# Higher delay = more stable but slower
API_DELAY = 10

# Delay between README requests (seconds)
# Recommended: 0.5-1.0
README_DELAY = 1.0

# ========== RETRY LOGIC ==========
# Maximum number of retry attempts for failed requests
# Recommended: 3-5
MAX_RETRIES = 3

# Base delay for retry attempts (seconds)
# Each retry increases delay by RETRY_BACKOFF_INCREMENT
RETRY_BASE_DELAY = 5

# Seconds to add to delay on each retry
# Example: attempt 1 = 5s, attempt 2 = 7s, attempt 3 = 9s
RETRY_BACKOFF_INCREMENT = 2

# ========== OUTPUT CONFIGURATION ==========
# Create timestamped folders for each run
# True: data/raw/YYYYMMDD_HHMMSS/
# False: data/raw/
USE_TIMESTAMPED_FOLDER = True

# Output file names
OUTPUT_PHASE1_FILE = "phase1_all_users.json"
OUTPUT_PHASE2_PREFIX = "phase2_ranked_top_"
OUTPUT_PHASE3_PREFIX = "phase2_top_"
OUTPUT_PHASE3_SUFFIX = "_with_readmes.json"

# JSON formatting
JSON_INDENT = 2
JSON_ENSURE_ASCII = False

# ========== GITHUB API CONFIGURATION ==========
# GitHub API endpoints
GRAPHQL_URL = "https://api.github.com/graphql"
REST_API_BASE = "https://api.github.com"

# Request timeout (seconds)
REQUEST_TIMEOUT = 10

# ========== DISPLAY CONFIGURATION ==========
# Number of top users to display in ranking output
DISPLAY_TOP_N = 50 if TOP_N_USERS > 50 else TOP_N_USERS

# Console output formatting
SEPARATOR_LENGTH = 70
USE_EMOJI = True  # Set False for plain text output

# ========== ADVANCED SETTINGS ==========
# These generally don't need to be changed

# ========== VECTOR SEARCH / EMBEDDINGS ==========
# Sentence transformer model for generating profile embeddings
# all-mpnet-base-v2: Higher quality, slower, more accurate semantic search (recommended)
# all-MiniLM-L6-v2: Faster, cheaper, CPU-friendly, good quality (lighter alternative)
EMBEDDING_MODEL = "all-mpnet-base-v2"

# ========== REPOSITORY FILTERING ==========
# Whether to exclude forked repositories from analysis
# TRUE = Only original work (recommended for talent sourcing)
# FALSE = Include forks (may credit users for others' work)
EXCLUDE_FORKS = True  # Only count repositories the user actually created

# ========== TWO-PASS STRATEGY ==========
# To avoid GitHub's 5,000 point/hour complexity limit:
# Pass 1: Fetch only cheap fields (id, login, basic info)
# Pass 2: Fetch expensive fields (contributions) for top users only

# Whether to fetch expensive fields during initial search
# FALSE = Two-pass approach (recommended, avoids complexity limits)
# TRUE = Single-pass (may hit RESOURCE_LIMITS_EXCEEDED on large queries)
FETCH_CONTRIBUTIONS_IN_SEARCH = False  # Expensive! ~200 points per user
FETCH_REPOSITORIES_IN_SEARCH = (
    False  # Moderately expensive: ~20 points per repo × N repos
)

# Pass 2: Batch size for fetching contributions/repos separately
# Based on Oct 2025 testing (see docs/BATCH_SIZE_TESTING_RESULTS.md):
# UPDATE Oct 19: With full contribution calendar (365 days), batch size 20
# hits GitHub resource limits ~50% of the time (non-deterministic).
# Reduced to 15 for more reliability with contribution calendar.
#
# Previous testing:
#   20 users/batch = 100% success (WITHOUT contribution calendar details)
#   15 users/batch = ~95% success (WITH contribution calendar - current)
#   25 users/batch = 75% success rate (needs retry logic)
#   30+ users/batch = <50% success rate (not recommended)
OPTIMAL_BATCH_SIZE = 15  # Reduced from 20 due to contribution calendar complexity
CONTRIBUTIONS_BATCH_SIZE = (
    15  # Users per batch when fetching contributions with calendar
)
REPOSITORIES_BATCH_SIZE = (
    25  # Users per batch when fetching repositories (less complex)
)

# Contribution time window (for Pass 2)
# GitHub limits to 1 year maximum
CONTRIBUTIONS_FROM_DAYS_AGO = 365  # Fetch last 365 days of contributions

# GraphQL query fields to fetch in Pass 2 (when not in search)
FETCH_PUSHED_AT = True  # pushedAt timestamp per repo
FETCH_UPDATED_AT = True  # updatedAt timestamp per repo

# Verbose logging
VERBOSE = False  # Set True for detailed debug output


# ========== VALIDATION ==========
def validate_config():
    """Validate configuration values."""
    errors = []

    # Validate weights sum to 1.0
    weights_sum = sum(SCORING_WEIGHTS.values())
    if abs(weights_sum - 1.0) > 0.01:
        errors.append(f"SCORING_WEIGHTS must sum to 1.0, got {weights_sum}")

    # Validate ranges
    if USERS_PER_PAGE < 1 or USERS_PER_PAGE > 100:
        errors.append(f"USERS_PER_PAGE must be between 1-100, got {USERS_PER_PAGE}")

    if REPOS_PER_USER < 1 or REPOS_PER_USER > 20:
        errors.append(f"REPOS_PER_USER must be between 1-20, got {REPOS_PER_USER}")

    if MAX_RETRIES < 1 or MAX_RETRIES > 10:
        errors.append(f"MAX_RETRIES must be between 1-10, got {MAX_RETRIES}")

    if API_DELAY < 0:
        errors.append(f"API_DELAY must be positive, got {API_DELAY}")

    if errors:
        raise ValueError(
            "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
        )


# Validate on import
validate_config()


# ========== HELPER FUNCTIONS ==========
def get_headers():
    """Get HTTP headers for GitHub API requests."""
    return {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }


def get_rest_headers():
    """Get HTTP headers for GitHub REST API requests."""
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw",
    }


def print_config_summary():
    """Print current configuration summary."""
    print(f"\n{'='*SEPARATOR_LENGTH}")
    print("⚙️  CONFIGURATION SUMMARY")
    print(f"{'='*SEPARATOR_LENGTH}\n")

    # Authentication
    print("� Authentication:")
    print(f"  • GitHub Token: {'✅ Set' if GITHUB_TOKEN else '❌ Missing'}")

    # Search Configuration
    print("\n🔍 Search Configuration:")
    print(f"  • Default location: {DEFAULT_LOCATION}")
    print(f"  • Czech keywords: {len(CZECH_KEYWORDS)} locations")

    # Phase 1: Fetch
    print("\n�📥 Phase 1 (Fetch):")
    print(f"  • Max pages: {MAX_PAGES}")
    print(f"  • Users per page: {USERS_PER_PAGE}")
    print(f"  • Total users: {MAX_PAGES * USERS_PER_PAGE}")
    print(f"  • Repos per user: {REPOS_PER_USER}")
    print(f"  • Fetch READMEs in Phase 1: {FETCH_READMES}")

    # Phase 2: Ranking
    print("\n🎯 Phase 2 (Ranking):")
    print(f"  • Top N users for enrichment: {TOP_N_USERS}")
    print(f"  • Scoring weights:")
    for metric, weight in SCORING_WEIGHTS.items():
        print(f"    - {metric}: {weight:.2%}")
    print(f"  • Scoring thresholds:")
    for metric, threshold in SCORING_THRESHOLDS.items():
        print(f"    - {metric}: {threshold}")

    # API Configuration
    print("\n🌐 API Configuration:")
    print(f"  • GraphQL URL: {GRAPHQL_URL}")
    print(f"  • REST API Base: {REST_API_BASE}")
    print(f"  • Request timeout: {REQUEST_TIMEOUT}s")

    # Rate Limiting
    print("\n⏱️  Rate Limiting:")
    print(f"  • API delay (pages): {API_DELAY}s")
    print(f"  • README delay: {README_DELAY}s")
    print(f"  • Max retries: {MAX_RETRIES}")
    print(f"  • Retry base delay: {RETRY_BASE_DELAY}s")
    print(f"  • Retry backoff increment: {RETRY_BACKOFF_INCREMENT}s")
    retry_delays = [
        RETRY_BASE_DELAY + (i * RETRY_BACKOFF_INCREMENT) for i in range(MAX_RETRIES)
    ]
    print(f"  • Retry pattern: {' → '.join(f'{d}s' for d in retry_delays)}")

    # Output Configuration
    print("\n📁 Output Configuration:")
    print(f"  • Timestamped folders: {USE_TIMESTAMPED_FOLDER}")
    print(f"  • Phase 1 filename: {OUTPUT_PHASE1_FILE}")
    print(f"  • Phase 2 prefix: {OUTPUT_PHASE2_PREFIX}")
    print(f"  • Phase 3 prefix: {OUTPUT_PHASE3_PREFIX}")
    print(f"  • JSON indent: {JSON_INDENT}")
    print(f"  • JSON ASCII only: {JSON_ENSURE_ASCII}")

    # Display Configuration
    print("\n🖥️  Display Configuration:")
    print(f"  • Display top N in rankings: {DISPLAY_TOP_N}")
    print(f"  • Separator length: {SEPARATOR_LENGTH}")
    print(f"  • Use emoji: {USE_EMOJI}")

    # Advanced Settings
    print("\n🔧 Advanced Settings (Two-Pass Strategy):")
    print(f"  • Fetch contributions in search: {FETCH_CONTRIBUTIONS_IN_SEARCH}")
    print(f"  • Fetch repositories in search: {FETCH_REPOSITORIES_IN_SEARCH}")
    print(f"  • Contributions batch size: {CONTRIBUTIONS_BATCH_SIZE}")
    print(f"  • Repositories batch size: {REPOSITORIES_BATCH_SIZE}")
    print(f"  • Contributions time window: {CONTRIBUTIONS_FROM_DAYS_AGO} days")
    print(f"  • Fetch pushedAt: {FETCH_PUSHED_AT}")
    print(f"  • Fetch updatedAt: {FETCH_UPDATED_AT}")
    print(f"  • Verbose logging: {VERBOSE}")
    
    # Vector Search
    print("\n🔍 Vector Search / Embeddings:")
    print(f"  • Embedding model: {EMBEDDING_MODEL}")

    print(f"\n{'='*SEPARATOR_LENGTH}\n")


if __name__ == "__main__":
    # Print config when run directly
    print_config_summary()
    print("✅ Configuration valid!")
    print(f"\nEstimated users to fetch: {MAX_PAGES * USERS_PER_PAGE}")
    print(
        f"Estimated time: ~{(MAX_PAGES * API_DELAY) / 60:.1f} minutes (without retries)"
    )
