import json
import os
import time

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

# Maximum number of pages to fetch
MAX_PAGES = 1

# Number of users per page (max 100 allowed by GitHub API)
USERS_PER_PAGE = 100

# Delay between API requests (in seconds) to respect rate limits
API_DELAY = 1

# ===================================

# The GraphQL API endpoint
URL = "https://api.github.com/graphql"

# Headers for the API request, including authorization
HEADERS = {
    "Authorization": f"bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

# The GraphQL query with pagination
# This query searches for users and fetches their profile details and top repositories.
GRAPHQL_QUERY = """
query SearchUsers($query: String!, $first: Int!, $after: String) {
    search(query: $query, type: USER, first: $first, after: $after) {
        userCount
        pageInfo {
            endCursor
            hasNextPage
        }
        nodes {
            ... on User {
                login
                name
                bio
                location
                followers {
                    totalCount
                }
                repositories(first: 10, orderBy: {field: STARGAZERS, direction: DESC}, ownerAffiliations: OWNER) {
                    totalCount
                    nodes {
                        name
                        description
                        stargazerCount
                        forkCount
                        primaryLanguage {
                            name
                        }
                    }
                }
            }
        }
    }
}
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


def save_users_to_file(users, filename="github_users.json"):
    """Saves the fetched users to a JSON file."""
    # Build path relative to this script
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "raw", filename
    )
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

    print(f"\nData successfully saved to {output_path}")


if __name__ == "__main__":
    print("=" * 60)
    print("GitHub Czech Users Fetcher")
    print("=" * 60)
    print(f"Using {len(CZECH_KEYWORDS)} location keywords")
    print(f"Keywords: {', '.join(CZECH_KEYWORDS[:10])}...")
    print("=" * 60)
    print()

    # Fetch Czech users - start with just Prague for testing
    # users_data = fetch_all_users()  # Use all keywords
    users_data = fetch_all_users(
        search_query="location:prague"
    )  # Test with single location

    # Save the data
    save_users_to_file(users_data)
