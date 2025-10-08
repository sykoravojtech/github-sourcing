import json
import os
import time
from datetime import datetime

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ========== CONFIGURATION ==========
# Your GitHub Personal Access Token
GITHUB_TOKEN = os.getenv("GITHUB_API_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GitHub API token not found. Please set it in the .env file.")

# Czech location keywords for user identification
# GitHub search is case-insensitive, so we use lowercase for consistency
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

# ===== PHASE 1: BULK FETCH CONFIGURATION =====
# Fetch many users quickly without READMEs
MAX_PAGES = 2  # Number of pages to fetch (USERS_PER_PAGE per page)
USERS_PER_PAGE = 25  # Reduced to 25 for contributionsCollection reliability
REPOS_PER_USER = 5  # Top repos per user (ordered by stars)

# ===== PHASE 2: README FETCH CONFIGURATION =====
# After ranking, fetch READMEs only for top users
FETCH_READMES = False  # Set True only when fetching READMEs for top-ranked users
TOP_N_USERS = 20  # Number of top-ranked users to enrich with READMEs

# ===== API RATE LIMITING =====
API_DELAY = 5  # Seconds between page requests (increased for contributionsCollection)
README_DELAY = 0.5  # Seconds between README requests

# ===== OUTPUT SETTINGS =====
USE_TIMESTAMPED_FOLDER = True  # Create dated folder: data/raw/YYYYMMDD_HHMMSS/

# ===================================

# The GraphQL API endpoint
URL = "https://api.github.com/graphql"

# Headers for the API request, including authorization
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# The GraphQL query with pagination
#
# HOW GITHUB SEARCH WORKS:
# ------------------------
# When searching for users (e.g., 15,107 users in Prague), GitHub returns them in a
# specific order based on their internal ranking algorithm which considers:
# 1. Best match score (how well the user matches the search criteria)
# 2. Number of followers (more popular users ranked higher)
# 3. Recent activity (more active users ranked higher)
# 4. Repository count and quality
#
# This means the first 50 users you get are the "most relevant" or "most prominent"
# users from that search, NOT random users or the first 50 who signed up.
#
# PAGINATION:
# - Each page fetches USERS_PER_PAGE users (e.g., 50)
# - For each user, we fetch their top REPOS_PER_USER repositories (ordered by stars)
# - Use the 'after' cursor to get the next page
# - Total users available: shown in 'userCount' field
#
GRAPHQL_QUERY = f"""
query SearchUsers($query: String!, $first: Int!, $after: String) {{
    search(query: $query, type: USER, first: $first, after: $after) {{
        userCount
        pageInfo {{
            endCursor
            hasNextPage
        }}
        nodes {{
            ... on User {{
                login
                name
                bio
                location
                company
                email
                websiteUrl
                followers {{
                    totalCount
                }}
                contributionsCollection {{
                    contributionCalendar {{
                        totalContributions
                    }}
                }}
                repositories(first: {REPOS_PER_USER}, orderBy: {{field: STARGAZERS, direction: DESC}}, ownerAffiliations: OWNER) {{
                    totalCount
                    nodes {{
                        name
                        description
                        stargazerCount
                        forkCount
                        url
                        updatedAt
                        pushedAt
                        primaryLanguage {{
                            name
                        }}
                    }}
                }}
            }}
        }}
    }}
}}
"""


def run_query(query, variables):
    """A simple function to use requests.post to make the API call."""
    request = requests.post(
        URL, json={"query": query, "variables": variables}, headers=HEADERS
    )
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(
            f"Query failed to run by returning code of {request.status_code}. {request.text}"
        )


def get_readme_content(owner, repo_name):
    """Fetch README content using GitHub REST API."""
    url = f"https://api.github.com/repos/{owner}/{repo_name}/readme"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        return None


def build_search_query(keywords):
    """Build a search query from location keywords."""
    # Only quote keywords with spaces
    location_queries = []
    for keyword in keywords:
        if " " in keyword:
            location_queries.append(f'location:"{keyword}"')
        else:
            location_queries.append(f"location:{keyword}")
    return " OR ".join(location_queries)


def fetch_all_users(search_query=None, max_pages=MAX_PAGES):
    """Fetches all users matching the location query, handling pagination."""
    if search_query is None:
        search_query = build_search_query(CZECH_KEYWORDS)

    all_users = []
    has_next_page = True
    after_cursor = None
    page_count = 0

    print(f"Search query: {search_query[:200]}...")  # Print first 200 chars
    print(
        f"Max pages to fetch: {max_pages} (up to {max_pages * USERS_PER_PAGE} users)\n"
    )

    while has_next_page and page_count < max_pages:
        variables = {
            "query": search_query,
            "first": USERS_PER_PAGE,
            "after": after_cursor,
        }

        try:
            print(f"Fetching page {page_count + 1}...")
            result = run_query(GRAPHQL_QUERY, variables)

            # Check for errors
            if "errors" in result:
                print("Error in GraphQL query:", result["errors"])
                break

            # Extract data
            search_data = result.get("data", {}).get("search", {})
            user_count = search_data.get("userCount", 0)
            users = search_data.get("nodes", [])
            page_info = search_data.get("pageInfo", {})

            print(f"  → Total matching users in GitHub: {user_count}")

            # Fetch READMEs for each repository (if enabled)
            if FETCH_READMES:
                print(f"  → Fetching READMEs for repositories...")
                readme_count = 0
                for user in users:
                    if (
                        user
                        and "repositories" in user
                        and "nodes" in user["repositories"]
                    ):
                        for repo in user["repositories"]["nodes"]:
                            if repo:
                                readme_content = get_readme_content(
                                    user["login"], repo["name"]
                                )
                                repo["readme_content"] = readme_content
                                if readme_content:
                                    readme_count += 1
                                # Rate limiting
                                time.sleep(README_DELAY)

                print(f"  → Successfully fetched {readme_count} READMEs")
            else:
                print(f"  → Skipping README fetching (Phase 1: bulk fetch only)")

            all_users.extend(users)

            # Update pagination info
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")

            print(f"  → Fetched {len(users)} users. Total so far: {len(all_users)}")

            page_count += 1

            # Rate limiting: Respect API rate limits
            time.sleep(API_DELAY)

        except Exception as e:
            print(f"Error fetching users: {e}")
            break

    print(f"\nTotal users fetched: {len(all_users)}")
    return all_users


def save_users_to_file(users, filename="github_users.json", output_folder=None):
    """Saves the fetched users to a JSON file."""
    # Determine output folder
    base_path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "raw")

    if output_folder is None:
        if USE_TIMESTAMPED_FOLDER:
            # Create timestamped folder: YYYYMMDD_HHMMSS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_folder = os.path.join(base_path, timestamp)
        else:
            output_folder = base_path

    output_folder = os.path.abspath(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    # Save file
    output_path = os.path.join(output_folder, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    return output_path, output_folder


def load_users_from_file(filepath):
    """Load users from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_readmes_for_users(users, output_folder):
    """Fetch READMEs for a list of users and save to file."""
    print(f"\n{'='*60}")
    print(f"📚 Phase 2: Fetching READMEs for {len(users)} top-ranked users")
    print(f"{'='*60}\n")

    readme_count = 0
    total_repos = sum(
        len(user.get("repositories", {}).get("nodes", [])) for user in users
    )

    for i, user in enumerate(users, 1):
        print(f"Processing user {i}/{len(users)}: {user['login']}")

        for repo in user.get("repositories", {}).get("nodes", []):
            readme_content = get_readme_content(user["login"], repo["name"])
            if readme_content:
                repo["readme"] = readme_content
                readme_count += 1
            time.sleep(README_DELAY)

    # Save enhanced users with READMEs
    filename = f"phase2_top_{len(users)}_with_readmes.json"
    output_path = os.path.join(output_folder, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    print(f"\n📚 Fetched {readme_count}/{total_repos} READMEs")
    print(f"✅ Saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("🚀 GitHub User Scraper - Two-Phase Strategy")
    print(f"{'='*60}\n")

    print("📋 Configuration:")
    print(
        f"  Phase 1: {MAX_PAGES} pages × {USERS_PER_PAGE} users = {MAX_PAGES * USERS_PER_PAGE} total users"
    )
    print(f"  Repos per user: {REPOS_PER_USER}")
    print(
        f"  README fetching: {'Enabled' if FETCH_READMES else 'Disabled (Phase 1 only)'}"
    )
    if not FETCH_READMES:
        print(f"  Phase 2 target: Top {TOP_N_USERS} users for README enrichment")
    print(f"  API delays: {API_DELAY}s (pages), {README_DELAY}s (READMEs)")
    print(
        f"  Output: {'Timestamped folder' if USE_TIMESTAMPED_FOLDER else 'data/raw/'}"
    )
    print(f"  Location: Prague (testing)")
    print(f"{'='*60}\n")

    # Phase 1: Fetch users without READMEs
    print(f"{'='*60}")
    print("📥 Phase 1: Fetching user profiles (no READMEs)")
    print(f"{'='*60}\n")

    users_data = fetch_all_users(search_query="location:prague")

    # Save Phase 1 results
    output_path, output_folder = save_users_to_file(users_data, "phase1_all_users.json")

    print(f"\n{'='*60}")
    print(f"✅ Phase 1 Complete!")
    print(f"   Users fetched: {len(users_data)}")
    print(f"   Saved to: {output_path}")
    print(f"   Folder: {output_folder}")
    print(f"{'='*60}")

    # Instructions for Phase 2
    if not FETCH_READMES and len(users_data) > 0:
        print(f"\n💡 Next Steps for Phase 2:")
        print(f"   1. Rank the {len(users_data)} users using your custom formula")
        print(f"   2. Select top {TOP_N_USERS} users")
        print(f"   3. Use fetch_readmes_for_users() to enrich them with READMEs")
        print(f"\n   Example:")
        print(
            f"   >>> from fetch_users import load_users_from_file, fetch_readmes_for_users"
        )
        print(f"   >>> users = load_users_from_file('{output_path}')")
        print(f"   >>> top_users = users[:20]  # or use your ranking function")
        print(f"   >>> fetch_readmes_for_users(top_users, '{output_folder}')")
        print(f"\n{'='*60}")
