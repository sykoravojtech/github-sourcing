import json
import os
import sys
import time
from datetime import datetime

import requests

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import config

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
                repositories(first: {config.REPOS_PER_USER}, orderBy: {{field: STARGAZERS, direction: DESC}}, ownerAffiliations: OWNER) {{
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


def run_query(query, variables, max_retries=None, base_delay=None):
    """
    Execute GraphQL query with retry logic for 502 errors.

    Args:
        query: GraphQL query string
        variables: Query variables
        max_retries: Maximum number of retry attempts (default from config)
        base_delay: Base delay in seconds (default from config)

    Returns:
        JSON response from GitHub API

    Raises:
        Exception: If all retries fail
    """
    if max_retries is None:
        max_retries = config.MAX_RETRIES
    if base_delay is None:
        base_delay = config.RETRY_BASE_DELAY

    current_delay = base_delay

    for attempt in range(max_retries):
        try:
            request = requests.post(
                config.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=config.get_headers(),
                timeout=config.REQUEST_TIMEOUT,
            )

            if request.status_code == 200:
                return request.json()
            elif request.status_code == 502:
                # 502 Bad Gateway - retry with increased delay
                if attempt < max_retries - 1:
                    print(
                        f"  ⚠️  Got 502 error, retrying in {current_delay}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(current_delay)
                    current_delay += config.RETRY_BACKOFF_INCREMENT
                    continue
                else:
                    raise Exception(
                        f"Query failed after {max_retries} attempts with 502 errors"
                    )
            else:
                raise Exception(
                    f"Query failed to run by returning code of {request.status_code}. {request.text}"
                )
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️  Request error: {e}, retrying in {current_delay}s...")
                time.sleep(current_delay)
                current_delay += config.RETRY_BACKOFF_INCREMENT
                continue
            else:
                raise

    raise Exception(f"Query failed after {max_retries} attempts")


def run_query_old(query, variables, max_retries=3, base_delay=config.API_DELAY):
    """
    Execute GraphQL query with retry logic for 502 errors.

    Args:
        query: GraphQL query string
        variables: Query variables
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds (increases with each retry)

    Returns:
        JSON response from GitHub API

    Raises:
        Exception: If all retries fail
    """
    current_delay = base_delay

    for attempt in range(max_retries):
        try:
            request = requests.post(
                config.GRAPHQL_URL,
                json={"query": query, "variables": variables},
                headers=config.get_headers(),
            )

            if request.status_code == 200:
                return request.json()
            elif request.status_code == 502:
                # 502 Bad Gateway - retry with increased delay
                if attempt < max_retries - 1:
                    print(
                        f"  ⚠️  Got 502 error, retrying in {current_delay}s (attempt {attempt + 1}/{max_retries})..."
                    )
                    time.sleep(current_delay)
                    current_delay += 2  # Increase delay by 2 seconds each retry
                    continue
                else:
                    raise Exception(
                        f"Query failed after {max_retries} attempts with 502 errors"
                    )
            else:
                raise Exception(
                    f"Query failed to run by returning code of {request.status_code}. {request.text}"
                )
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️  Request error: {e}, retrying in {current_delay}s...")
                time.sleep(current_delay)
                current_delay += 2
                continue
            else:
                raise

    raise Exception(f"Query failed after {max_retries} attempts")


def get_readme_content(owner, repo_name):
    """Fetch README content using GitHub REST API."""
    url = f"{config.REST_API_BASE}/repos/{owner}/{repo_name}/readme"

    try:
        response = requests.get(
            url, headers=config.get_rest_headers(), timeout=config.REQUEST_TIMEOUT
        )
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


def fetch_all_users(search_query=None, max_pages=None):
    """Fetches all users matching the location query, handling pagination."""
    if max_pages is None:
        max_pages = config.MAX_PAGES

    if search_query is None:
        search_query = build_search_query(config.CZECH_KEYWORDS)

    all_users = []
    has_next_page = True
    after_cursor = None
    page_count = 0

    print(f"Search query: {search_query[:200]}...")  # Print first 200 chars
    print(
        f"Max pages to fetch: {max_pages} (up to {max_pages * config.USERS_PER_PAGE} users)\n"
    )

    while has_next_page and page_count < max_pages:
        variables = {
            "query": search_query,
            "first": config.USERS_PER_PAGE,
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
            if config.FETCH_READMES:
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
                                time.sleep(config.README_DELAY)

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
            time.sleep(config.API_DELAY)

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
        if config.USE_TIMESTAMPED_FOLDER:
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
        json.dump(
            users, f, indent=config.JSON_INDENT, ensure_ascii=config.JSON_ENSURE_ASCII
        )

    return output_path, output_folder


if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("🚀 GitHub User Scraper - Two-Phase Strategy")
    print(f"{'='*60}\n")

    print("📋 Configuration:")
    print(
        f"  Phase 1: {config.MAX_PAGES} pages × {config.USERS_PER_PAGE} users = {config.MAX_PAGES * config.USERS_PER_PAGE} total users"
    )
    print(f"  Repos per user: {config.REPOS_PER_USER}")
    print(
        f"  README fetching: {'Enabled' if config.FETCH_READMES else 'Disabled (Phase 1 only)'}"
    )
    if not config.FETCH_READMES:
        print(f"  Phase 2 target: Top {config.TOP_N_USERS} users for README enrichment")
    print(
        f"  API delays: {config.API_DELAY}s (pages), {config.README_DELAY}s (READMEs)"
    )
    print(
        f"  Output: {'Timestamped folder' if config.USE_TIMESTAMPED_FOLDER else 'data/raw/'}"
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
    if not config.FETCH_READMES and len(users_data) > 0:
        print(f"\n💡 Next Steps for Phase 2:")
        print(
            f"   1. Rank users: python src/processing/rank_users.py {output_path} {config.TOP_N_USERS}"
        )
        print(
            f"   2. Fetch READMEs: python src/data_collection/fetch_readmes.py <ranked_file>"
        )
        print(f"\n   Full workflow:")
        print(f"   uv run python src/processing/rank_users.py \\")
        print(f"     {output_path} {config.TOP_N_USERS}")
        print(f"   uv run python src/data_collection/fetch_readmes.py \\")
        print(f"     {output_folder}/phase2_ranked_top_{config.TOP_N_USERS}.json")
        print(f"\n{'='*60}")
