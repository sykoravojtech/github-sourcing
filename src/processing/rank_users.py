"""
Rank GitHub users based on custom scoring formula.
Identifies top developers for recruitment/sourcing.
"""

import json
from datetime import datetime
from typing import Dict, List


def parse_datetime(dt_string):
    """Parse GitHub datetime string."""
    if not dt_string:
        return None
    try:
        return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    except:
        return None


def normalize_metric(value, max_value):
    """Normalize a metric to 0-100 scale."""
    if max_value == 0:
        return 0
    return min(100, (value / max_value) * 100)


def calculate_user_score(user: Dict, all_users: List[Dict] = None) -> float:
    """
    Calculate ranking score for a user (0-100 scale).

    Weighted Scoring System:
    - Followers: 20%
    - Contributions (last year): 35%
    - Total stars: 25%
    - Public repos: 10%
    - Activity (last 30 days): 10%

    Each metric is normalized to 0-100 before applying weights.
    Total possible: 100 points
    """
    repos = user.get("repositories", {}).get("nodes", [])

    # ===== 1. FOLLOWERS (20% weight) =====
    followers = user.get("followers", {}).get("totalCount", 0)
    # Normalize: 1000+ followers = 100 points
    followers_score = min(100, (followers / 1000) * 100)

    # ===== 2. CONTRIBUTIONS LAST YEAR (35% weight) =====
    # Get actual contributions from GitHub's contributionsCollection
    contributions = 0
    contrib_data = user.get("contributionsCollection", {})
    if contrib_data:
        calendar = contrib_data.get("contributionCalendar", {})
        contributions = calendar.get("totalContributions", 0)
    # Normalize: 1000+ contributions = 100 points
    contributions_score = min(100, (contributions / 1000) * 100)

    # ===== 3. TOTAL STARS (25% weight) =====
    total_stars = sum(repo.get("stargazerCount", 0) for repo in repos)
    # Normalize: 1000+ stars = 100 points
    stars_score = min(100, (total_stars / 1000) * 100)

    # ===== 4. PUBLIC REPOS (10% weight) =====
    total_repos = user.get("repositories", {}).get("totalCount", 0)
    # Normalize: 50+ repos = 100 points
    repos_score = min(100, (total_repos / 50) * 100)

    # ===== 5. ACTIVITY LAST 30 DAYS (10% weight) =====
    has_recent_activity = False
    for repo in repos:
        pushed_at = parse_datetime(repo.get("pushedAt"))
        if pushed_at:
            days_since = (datetime.now(pushed_at.tzinfo) - pushed_at).days
            if days_since < 30:
                has_recent_activity = True
                break
    activity_score = 100 if has_recent_activity else 0

    # ===== WEIGHTED TOTAL (0-100) =====
    total_score = (
        followers_score * 0.20
        + contributions_score * 0.35
        + stars_score * 0.25
        + repos_score * 0.10
        + activity_score * 0.10
    )

    return round(total_score, 2)


def rank_users(users: List[Dict], top_n: int = None) -> List[Dict]:
    """
    Rank users by score and return top N.

    Args:
        users: List of user dictionaries
        top_n: Number of top users to return (None = all)

    Returns:
        Sorted list of users with scores
    """
    print(f"\n{'='*60}")
    print(f"🎯 Ranking {len(users)} users...")
    print(f"{'='*60}\n")

    # Calculate scores
    for user in users:
        user["ranking_score"] = calculate_user_score(user, users)

    # Sort by score (descending)
    ranked = sorted(users, key=lambda u: u["ranking_score"], reverse=True)

    # Print top 10
    print("🏆 Top 10 Users (Score 0-100):")
    print(
        f"{'Rank':<6} {'Score':<8} {'Login':<20} {'Followers':<10} {'Contrib':<10} {'Stars':<8}"
    )
    print("-" * 70)

    for i, user in enumerate(ranked[:10], 1):
        login = user.get("login", "N/A")
        score = user.get("ranking_score", 0)
        followers = user.get("followers", {}).get("totalCount", 0)
        contributions = (
            user.get("contributionsCollection", {})
            .get("contributionCalendar", {})
            .get("totalContributions", 0)
        )
        total_stars = sum(
            r.get("stargazerCount", 0)
            for r in user.get("repositories", {}).get("nodes", [])
        )

        print(
            f"{i:<6} {score:<8} {login:<20} {followers:<10} {contributions:<10} {total_stars:<8}"
        )

    print(f"\n{'='*60}\n")

    if top_n:
        return ranked[:top_n]
    return ranked


def save_ranked_users(users: List[Dict], output_path: str):
    """Save ranked users to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(users)} ranked users to: {output_path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python rank_users.py <input_json_file> [top_n]")
        print(
            "Example: python rank_users.py data/raw/20251008_162951/phase1_all_users.json 20"
        )
        sys.exit(1)

    input_file = sys.argv[1]
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else None

    # Load users
    print(f"Loading users from: {input_file}")
    with open(input_file, "r", encoding="utf-8") as f:
        users = json.load(f)

    # Rank users
    ranked = rank_users(users, top_n)

    # Save ranked users
    import os

    output_dir = os.path.dirname(input_file)
    output_file = os.path.join(output_dir, f"phase2_ranked_top_{len(ranked)}.json")
    save_ranked_users(ranked, output_file)

    print(f"\n💡 Next step: Fetch READMEs for these {len(ranked)} users")
    print(f"   Use: fetch_readmes_for_users() from fetch_users.py")
