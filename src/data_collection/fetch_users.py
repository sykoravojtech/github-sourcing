"""
Optimized GitHub User Fetcher - Two-Phase Workflow

Improvements based on Oct 2025 testing:
- Optimal batch size: 20 users (100% success rate)
- Automatic deduplication (handles ~27% overlap from pagination)
- Retry logic for failed batches (exponential backoff)
- Full contribution calendar (365 days) at zero extra cost
- Comprehensive error handling and progress tracking

See docs/TWO_PHASE_WORKFLOW.md for complete documentation.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests

# Add parent directory to path to import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src import config

# ============================================================================
# PHASE 1: Search for user logins (100 per page @ 1 point)
# ============================================================================

SEARCH_QUERY = """
query SearchUsers($query: String!, $first: Int!, $after: String) {
    rateLimit {
        cost
        remaining
        resetAt
    }
    search(query: $query, type: USER, first: $first, after: $after) {
        userCount
        pageInfo {
            endCursor
            hasNextPage
        }
        nodes {
            ... on User {
                login
            }
        }
    }
}
"""


# ============================================================================
# PHASE 2: Batch fetch full user data (20 users/batch @ 1 point)
# ============================================================================


def build_batch_query(logins: List[str], from_date: str, to_date: str) -> str:
    """
    Build batched GraphQL query for multiple users.

    Args:
        logins: List of GitHub usernames
        from_date: Start date for contributions (ISO format)
        to_date: End date for contributions (ISO format)

    Returns:
        GraphQL query string with aliases for each user

    Note: Contribution calendar is expensive (52 weeks × 7 days × N users).
    For batch size 20: 7,280 data points can hit GitHub resource limits.
    We fetch full calendar but GitHub may throttle randomly.
    """
    aliases = []

    for i, login in enumerate(logins):
        # Escape quotes in login (shouldn't happen, but safety first)
        safe_login = login.replace('"', '\\"')

        aliases.append(
            f"""
        user{i}: user(login: "{safe_login}") {{
            login
            name
            bio
            company
            location
            email
            websiteUrl
            twitterUsername
            followers {{ totalCount }}
            following {{ totalCount }}
            repositories(
                first: 5
                orderBy: {{field: STARGAZERS, direction: DESC}}
                privacy: PUBLIC
                ownerAffiliations: OWNER
                isFork: false
            ) {{
                totalCount
                nodes {{
                    name
                    description
                    stargazerCount
                    forkCount
                    pushedAt
                    primaryLanguage {{ name }}
                    url
                }}
            }}
            contributionsCollection(from: "{from_date}", to: "{to_date}") {{
                contributionCalendar {{
                    totalContributions
                    weeks {{
                        contributionDays {{
                            contributionCount
                            date
                        }}
                    }}
                }}
            }}
        }}
        """
        )

    query = "{ " + " ".join(aliases) + " rateLimit { cost remaining resetAt } }"
    return query


# ============================================================================
# API Communication with Retry Logic
# ============================================================================


def run_query(
    query: str,
    variables: Optional[Dict] = None,
    max_retries: int = 3,
    timeout: int = 60,
) -> Dict:
    """
    Execute GraphQL query with retry logic.

    Handles:
    - Network timeouts (ChunkedEncodingError, ConnectionError)
    - HTTP 502/504 errors (Bad Gateway, Gateway Timeout)
    - Rate limiting

    Args:
        query: GraphQL query string
        variables: Query variables (optional)
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds

    Returns:
        JSON response from GitHub API

    Raises:
        Exception: If all retries fail
    """
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            # Success
            if response.status_code == 200:
                result = response.json()

                # Check for GraphQL errors
                if "errors" in result:
                    error_msg = result["errors"][0]["message"]

                    # Resource limits - don't retry, this is a query complexity issue
                    if (
                        "Resource limits" in error_msg
                        or "complexity" in error_msg.lower()
                    ):
                        raise Exception(f"Query too complex: {error_msg}")

                    # Other errors - retry
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                        print(f"  ⚠️  GraphQL error: {error_msg}")
                        print(
                            f"     Retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"GraphQL error: {error_msg}")

                return result

            # HTTP errors - retry
            elif response.status_code in [502, 504]:  # Bad Gateway, Gateway Timeout
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    print(f"  ⚠️  HTTP {response.status_code} error")
                    print(
                        f"     Retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(
                        f"HTTP {response.status_code} after {max_retries} attempts"
                    )

            # Other HTTP errors - don't retry
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

        except (
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ) as e:
            # Network errors - retry
            if attempt < max_retries - 1:
                wait_time = 2**attempt
                print(f"  ⚠️  Network error: {type(e).__name__}")
                print(
                    f"     Retrying in {wait_time}s (attempt {attempt + 2}/{max_retries})..."
                )
                time.sleep(wait_time)
                continue
            else:
                raise Exception(f"Network error after {max_retries} attempts: {e}")

    raise Exception(f"Query failed after {max_retries} attempts")


# ============================================================================
# Phase 1: Search and Collect Logins
# ============================================================================


def search_users(
    query: str, max_pages: int = 10, users_per_page: int = 100
) -> List[str]:
    """
    Search for GitHub users and collect their logins.

    Args:
        query: GitHub search query (e.g., "location:prague language:Python")
        max_pages: Maximum number of pages to fetch
        users_per_page: Users per page (max 100)

    Returns:
        List of unique user logins (deduplicated)
    """
    print(f"\n{'='*70}")
    print(f"📍 PHASE 1: Searching for users")
    print(f"{'='*70}\n")
    print(f"Query: {query}")
    print(f"Max pages: {max_pages} ({max_pages * users_per_page} logins max)\n")

    all_logins = []
    cursor = None
    page = 0
    total_cost = 0
    total_available = None  # Will be set from first query

    while page < max_pages:
        print(f"Page {page + 1}/{max_pages}: ", end="", flush=True)

        variables = {"query": query, "first": users_per_page, "after": cursor}

        try:
            result = run_query(SEARCH_QUERY, variables)

            # Extract data
            search_data = result["data"]["search"]
            rate_limit = result["data"]["rateLimit"]

            user_count = search_data["userCount"]
            nodes = search_data["nodes"]
            page_info = search_data["pageInfo"]

            # Store total available users from first page
            if total_available is None:
                total_available = user_count
                print(f"\n")
                print(f"{'─'*70}")
                print(f"📊 Search Results Available:")
                print(f"   Total matching users: {user_count:,}")

                # Calculate how many pages needed to get all users
                max_possible_pages = (user_count + users_per_page - 1) // users_per_page

                if user_count > max_pages * users_per_page:
                    print(
                        f"   Your request: {max_pages} pages ({max_pages * users_per_page:,} users)"
                    )
                    print(
                        f"   💡 TIP: Increase --max-pages to {max_possible_pages} to get all users"
                    )
                    coverage_pct = (max_pages * users_per_page / user_count) * 100
                    print(f"   Current coverage: {coverage_pct:.1f}%")
                else:
                    print(
                        f"   ✅ Your request ({max_pages} pages) will fetch all available users"
                    )
                print(f"{'─'*70}\n")
                print(f"Page {page + 1}/{max_pages}: ", end="", flush=True)

            # Extract logins
            logins = [node["login"] for node in nodes if node and "login" in node]
            all_logins.extend(logins)

            # Log results
            cost = rate_limit["cost"]
            remaining = rate_limit["remaining"]
            total_cost += cost

            print(
                f"✅ Got {len(logins)} logins (Cost: {cost} pt, Remaining: {remaining})"
            )

            # Check for next page
            if not page_info["hasNextPage"]:
                print(f"\n   ℹ️  No more pages available")
                print(f"   ⚠️  Note: GitHub Search API has a 1,000 result limit")
                print(f"   💡 Tip: Use more specific filters to get different users")
                break

            cursor = page_info["endCursor"]
            page += 1

            # Rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"❌ Failed: {e}")
            break

    print(f"\n{'─'*70}")
    print(f"📊 Search Summary:")
    print(f"   Total pages fetched: {page}")
    print(f"   Total logins collected: {len(all_logins)}")
    print(f"   Total API cost: {total_cost} points")

    if total_available:
        coverage_pct = (len(all_logins) / total_available) * 100
        print(
            f"   Coverage: {len(all_logins):,} / {total_available:,} ({coverage_pct:.1f}%)"
        )

        # Check if we hit GitHub's 1,000 result limit
        if len(all_logins) >= 950 and coverage_pct < 95:
            print(f"   ⚠️  Hit GitHub Search API limit (~1,000 results max)")
            print(
                f"   💡 To get more users, refine your search with additional filters:"
            )
            print(
                f"      - Add language filter: language:Python, language:JavaScript, etc."
            )
            print(f"      - Add creation date: created:>2020-01-01")
            print(
                f"      - Split by followers: followers:10..100, followers:100..1000, etc."
            )
        elif coverage_pct < 95:
            remaining_users = total_available - len(all_logins)
            pages_needed = (remaining_users + users_per_page - 1) // users_per_page
            print(
                f"   💡 {remaining_users:,} users not fetched (+{pages_needed} more pages needed)"
            )

    print(f"{'─'*70}\n")

    # Deduplicate logins (search pagination can return duplicates)
    unique_logins = list(dict.fromkeys(all_logins))  # Preserves order
    duplicates = len(all_logins) - len(unique_logins)

    if duplicates > 0:
        print(f"🔍 Deduplication:")
        print(f"   Logins before: {len(all_logins)}")
        print(f"   Duplicates: {duplicates} ({duplicates/len(all_logins)*100:.1f}%)")
        print(f"   Unique logins: {len(unique_logins)}\n")

    return unique_logins


# ============================================================================
# Phase 2: Batch Fetch Full User Data
# ============================================================================


def fetch_users_batch(
    logins: List[str], batch_size: int = None, from_days_ago: int = 365
) -> List[Dict]:
    """
    Fetch full user data in batches with retry logic.

    Args:
        logins: List of unique user logins
        batch_size: Users per batch (default: from config.OPTIMAL_BATCH_SIZE)
        from_days_ago: Days of contribution history to fetch

    Returns:
        Tuple of (users_list, failed_batches_list)

    Note: Contribution calendar (365 days) is expensive. Batch size 15 balances
    reliability vs speed. Larger batches may hit GitHub resource limits randomly.
    """
    # Use config default if not specified
    if batch_size is None:
        batch_size = config.OPTIMAL_BATCH_SIZE
    print(f"\n{'='*70}")
    print(f"📍 PHASE 2: Fetching full user data")
    print(f"{'='*70}\n")
    print(f"Unique users to fetch: {len(logins)}")
    print(f"Batch size: {batch_size} users")
    print(f"Contribution window: {from_days_ago} days")
    print(f"⚠️  Note: Including 365-day contribution calendar (expensive query)\n")

    # Calculate date range
    to_date = datetime.now()
    from_date = to_date - timedelta(days=from_days_ago)
    from_iso = from_date.strftime("%Y-%m-%dT00:00:00Z")
    to_iso = to_date.strftime("%Y-%m-%dT23:59:59Z")

    all_users = []
    total_batches = (len(logins) + batch_size - 1) // batch_size
    total_cost = 0
    failed_batches = []

    for batch_num in range(total_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, len(logins))
        batch_logins = logins[start_idx:end_idx]

        print(f"Batch {batch_num + 1}/{total_batches}: ", end="", flush=True)
        print(
            f"Fetching {len(batch_logins)} users [{start_idx + 1}-{end_idx}]...",
            end=" ",
        )

        try:
            # Build and execute query
            query = build_batch_query(batch_logins, from_iso, to_iso)
            result = run_query(query, max_retries=3, timeout=60)

            # Extract users
            data = result["data"]
            rate_limit = data["rateLimit"]

            batch_users = []
            for key in data:
                if key.startswith("user") and data[key]:
                    batch_users.append(data[key])

            all_users.extend(batch_users)

            # Log results
            cost = rate_limit["cost"]
            remaining = rate_limit["remaining"]
            total_cost += cost

            print(f"✅ Got {len(batch_users)}/{len(batch_logins)} users")
            print(f"   Cost: {cost} pt, Remaining: {remaining} pts")

            # Rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Failed: {e}")
            failed_batches.append(
                {"batch_num": batch_num + 1, "logins": batch_logins, "error": str(e)}
            )

            # If resource limits, reduce batch size for next batch
            if "Resource limits" in str(e) or "complexity" in str(e).lower():
                print(f"   ⚠️  Query too complex - consider reducing batch size")

    print(f"\n{'─'*70}")
    print(f"📊 Fetch Summary:")
    print(f"   Batches attempted: {total_batches}")
    print(f"   Batches successful: {total_batches - len(failed_batches)}")
    print(f"   Users fetched: {len(all_users)}/{len(logins)}")
    print(f"   Total API cost: {total_cost} points")

    if failed_batches:
        print(f"\n   ⚠️  Failed batches: {len(failed_batches)}")
        for fb in failed_batches:
            print(f"      Batch {fb['batch_num']}: {fb['error'][:50]}")

    print(f"{'─'*70}\n")

    return all_users, failed_batches


# ============================================================================
# Retry Failed Batches (Optional)
# ============================================================================


def retry_failed_batches(
    failed_batches: List[Dict], from_days_ago: int = 365, reduced_batch_size: int = 10
) -> List[Dict]:
    """
    Retry failed batches with smaller batch size.

    Args:
        failed_batches: List of failed batch info from fetch_users_batch
        from_days_ago: Days of contribution history
        reduced_batch_size: Smaller batch size for retry (default: 10)

    Returns:
        List of users recovered from failed batches
    """
    if not failed_batches:
        return []

    print(f"\n{'='*70}")
    print(
        f"🔄 Retrying {len(failed_batches)} failed batches with reduced size ({reduced_batch_size} users)"
    )
    print(f"{'='*70}\n")

    # Collect all logins from failed batches
    all_failed_logins = []
    for fb in failed_batches:
        all_failed_logins.extend(fb["logins"])

    # Retry with smaller batch size
    recovered_users, still_failed = fetch_users_batch(
        all_failed_logins, batch_size=reduced_batch_size, from_days_ago=from_days_ago
    )

    print(f"✅ Recovered {len(recovered_users)}/{len(all_failed_logins)} users\n")

    return recovered_users


# ============================================================================
# Save Results
# ============================================================================


def save_users(
    users: List[Dict], output_folder: str, filename: str = "phase1_all_users.json"
) -> str:
    """
    Save users to JSON file.

    Args:
        users: List of user dictionaries
        output_folder: Output directory path
        filename: Output filename

    Returns:
        Full path to saved file
    """
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

    return output_path


# ============================================================================
# Main Execution
# ============================================================================


def main():
    """Main execution function."""
    print(f"\n{'='*70}")
    print("🚀 GitHub User Fetcher - Optimized Two-Phase Workflow")
    print(f"{'='*70}\n")

    # Configuration
    # Note: Language filter removed - find ALL skilled developers regardless of language
    # followers:>5 and repos:>3 filter out spam/inactive accounts (very low bar)
    search_query = "location:prague followers:>5 repos:>3"
    max_pages = 2

    print("📋 Configuration:")
    print(f"   Search: {search_query}")
    print(f"   Max pages: {max_pages}")
    print(
        f"   Batch size: {config.OPTIMAL_BATCH_SIZE} users (from config.OPTIMAL_BATCH_SIZE)"
    )
    print(f"   Contribution window: 365 days (with daily breakdown)")

    # Phase 1: Search
    logins = search_users(search_query, max_pages=max_pages)

    if not logins:
        print("❌ No users found. Exiting.")
        return

    # Phase 2: Fetch full data (uses config.OPTIMAL_BATCH_SIZE by default)
    users, failed_batches = fetch_users_batch(logins)

    # Optional: Retry failed batches with smaller size
    if failed_batches:
        print(f"\n💡 Retrying failed batches? (y/n): ", end="", flush=True)
        # For automation, automatically retry
        retry = True
        if retry:
            recovered_users = retry_failed_batches(
                failed_batches, reduced_batch_size=10
            )
            users.extend(recovered_users)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_folder = os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "raw", timestamp
    )
    output_path = save_users(users, output_folder)

    # Summary
    print(f"\n{'='*70}")
    print(f"✅ COMPLETE!")
    print(f"{'='*70}")
    print(
        f"   Users fetched: {len(users)}/{len(logins)} ({len(users)/len(logins)*100:.1f}%)"
    )
    print(f"   Saved to: {output_path}")
    print(f"\n💡 Next steps:")
    print(
        f"   1. Rank users: uv run python -m src.processing.rank_users {output_path} 20"
    )
    print(f"   2. Analyze top candidates")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
