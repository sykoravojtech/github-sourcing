"""
Rank GitHub users based on custom scoring formula.
Identifies top developers for recruitment/sourcing.
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from src import config


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


def calculate_trend_score(user: Dict) -> float:
    """
    Calculate trend/momentum score (0-100) based on contribution patterns.

    Uses two data sources:
    1. Contribution Calendar (60 points) - Daily commit activity over 365 days
       - Recent momentum (last 30 days): 25 pts
       - Quarterly momentum (last 90 days): 20 pts
       - Consistency (activity distribution): 15 pts

    2. Project Momentum (40 points) - Repository activity patterns
       - Active high-value projects: 25 pts
       - Recent project work: 15 pts

    Total: 100 points possible

    Note: GitHub API does NOT provide star timestamps, so we cannot track
    "star growth". We use contribution velocity as the momentum indicator.
    """
    # ===== PART 1: CONTRIBUTION MOMENTUM (60 points) =====
    contrib_collection = user.get("contributionsCollection", {})
    calendar = contrib_collection.get("contributionCalendar", {})
    weeks = calendar.get("weeks", [])

    if not weeks:
        # No contribution data - inactive user
        return 0.0

    # Extract daily contributions for different time windows
    all_days = []
    for week in weeks:
        for day in week.get("contributionDays", []):
            all_days.append(
                {"date": day.get("date"), "count": day.get("contributionCount", 0)}
            )

    # Sort by date (newest first)
    all_days.sort(key=lambda d: d["date"], reverse=True)

    # Calculate contribution counts for different periods
    last_30_days = sum(d["count"] for d in all_days[:30]) if len(all_days) >= 30 else 0
    last_90_days = sum(d["count"] for d in all_days[:90]) if len(all_days) >= 90 else 0
    total_365_days = calendar.get("totalContributions", 0)

    # 1a. Recent Momentum (last 30 days) - 25 points max
    # Threshold: 50+ contributions in 30 days = very active
    recent_momentum = min(25, (last_30_days / 50) * 25)

    # 1b. Quarterly Momentum (last 90 days) - 20 points max
    # Threshold: 150+ contributions in 90 days = sustained activity
    quarterly_momentum = min(20, (last_90_days / 150) * 20)

    # 1c. Consistency - 15 points max
    # Active days / total days (higher = more consistent)
    active_days = sum(1 for d in all_days if d["count"] > 0)
    consistency_ratio = active_days / len(all_days) if all_days else 0
    consistency_score = consistency_ratio * 15

    contribution_score = recent_momentum + quarterly_momentum + consistency_score

    # ===== PART 2: PROJECT MOMENTUM (40 points) =====
    repos = user.get("repositories", {}).get("nodes", [])
    if not repos:
        # No repos but has contributions? (contributes to others' projects)
        # Still give them credit for contribution momentum
        return round(contribution_score, 2)

    now = datetime.now()

    # 2a. Active High-Value Projects - 25 points max
    # Projects with stars that are still being actively maintained
    high_value_active = 0
    for repo in repos:
        stars = repo.get("stargazerCount", 0)
        pushed_at = parse_datetime(repo.get("pushedAt"))

        if pushed_at and stars >= 10:  # Has some impact
            days_since = (now - pushed_at.replace(tzinfo=None)).days
            if days_since < 180:  # Updated in last 6 months
                # Weight by stars: more stars = more points
                high_value_active += min(stars / 100, 1.0)  # Max 1 point per repo

    # Normalize: 3+ high-value active projects = max score
    high_value_score = min(25, (high_value_active / 3) * 25)

    # 2b. Recent Project Work - 15 points max
    # How many projects pushed to in last 90 days?
    recent_projects = 0
    for repo in repos:
        pushed_at = parse_datetime(repo.get("pushedAt"))
        if pushed_at:
            days_since = (now - pushed_at.replace(tzinfo=None)).days
            if days_since < 90:
                recent_projects += 1

    # Normalize: 3+ recent projects = max score
    recent_work_score = min(15, (recent_projects / 3) * 15)

    project_score = high_value_score + recent_work_score

    # ===== TOTAL TREND SCORE =====
    total_score = contribution_score + project_score
    return round(total_score, 2)


def calculate_user_score(user: Dict, all_users: List[Dict] = None) -> float:
    """
    Calculate ranking score for a user (0-100 scale).

    Uses weights and thresholds from config module.
    Each metric is normalized to 0-100 before applying weights.
    Total possible: 100 points
    """
    repos = user.get("repositories", {}).get("nodes", [])

    # Get weights and thresholds from config
    weights = config.SCORING_WEIGHTS
    thresholds = config.SCORING_THRESHOLDS

    # ===== 1. FOLLOWERS =====
    followers = user.get("followers", {}).get("totalCount", 0)
    followers_score = min(100, (followers / thresholds["followers"]) * 100)

    # ===== 2. CONTRIBUTIONS LAST YEAR =====
    contributions = 0
    contrib_data = user.get("contributionsCollection", {})
    if contrib_data:
        calendar = contrib_data.get("contributionCalendar", {})
        contributions = calendar.get("totalContributions", 0)
    contributions_score = min(100, (contributions / thresholds["contributions"]) * 100)

    # ===== 3. TOTAL STARS =====
    total_stars = sum(repo.get("stargazerCount", 0) for repo in repos)
    stars_score = min(100, (total_stars / thresholds["stars"]) * 100)

    # ===== 4. PUBLIC REPOS =====
    total_repos = user.get("repositories", {}).get("totalCount", 0)
    repos_score = min(100, (total_repos / thresholds["repos"]) * 100)

    # ===== 5. ACTIVITY LAST 30 DAYS =====
    # Use contribution calendar for precise activity measurement
    contrib_collection = user.get("contributionsCollection", {})
    calendar = contrib_collection.get("contributionCalendar", {})
    weeks = calendar.get("weeks", [])

    last_30_days_contributions = 0
    if weeks:
        # Get all days and sort by date (newest first)
        all_days = []
        for week in weeks:
            for day in week.get("contributionDays", []):
                all_days.append(
                    {"date": day.get("date"), "count": day.get("contributionCount", 0)}
                )
        all_days.sort(key=lambda d: d["date"], reverse=True)

        # Sum last 30 days
        last_30_days_contributions = (
            sum(d["count"] for d in all_days[:30]) if len(all_days) >= 30 else 0
        )

    # Score based on contribution intensity in last 30 days
    # Threshold: 15+ contributions in 30 days = active (from config)
    activity_threshold = 15  # Can be made configurable
    activity_score = min(100, (last_30_days_contributions / activity_threshold) * 100)

    # ===== 6. TREND/MOMENTUM =====
    trend_score = calculate_trend_score(user)

    # ===== WEIGHTED TOTAL (0-100) =====
    total_score = (
        followers_score * weights["followers"]
        + contributions_score * weights["contributions"]
        + stars_score * weights["stars"]
        + repos_score * weights["repos"]
        + activity_score * weights["activity"]
        + trend_score * weights["trend"]
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

    # Deduplicate users by login (can happen with paginated searches)
    seen_logins = set()
    unique_users = []
    duplicates = 0

    for user in users:
        login = user.get("login")
        if login and login not in seen_logins:
            seen_logins.add(login)
            unique_users.append(user)
        elif login:
            duplicates += 1

    if duplicates > 0:
        print(
            f"🔍 Removed {duplicates} duplicate users (from paginated search results)"
        )
        print(f"📊 Unique users: {len(unique_users)}\n")

    users = unique_users

    # Filter BEFORE calculating scores (optimization: skip inactive users)
    active_users = []
    filtered_contributions = 0
    filtered_inactive = 0

    for user in users:
        contributions = (
            user.get("contributionsCollection", {})
            .get("contributionCalendar", {})
            .get("totalContributions", 0)
        )

        # Filter by contributions first (cheap check)
        if contributions < config.MIN_CONTRIBUTIONS_REQUIRED:
            filtered_contributions += 1
            continue

        # Calculate trend score only for users who passed first filter
        trend_score = calculate_trend_score(user)

        # Filter by trend (recent activity)
        if trend_score < config.MIN_TREND_SCORE_REQUIRED:
            filtered_inactive += 1
            continue

        active_users.append(user)

    # Print filtering summary
    total_filtered = filtered_contributions + filtered_inactive
    if total_filtered > 0:
        print(f"🔍 Filtering Summary:")
        if filtered_contributions > 0:
            print(
                f"   • {filtered_contributions} users with < {config.MIN_CONTRIBUTIONS_REQUIRED} contributions/year"
            )
        if filtered_inactive > 0:
            print(
                f"   • {filtered_inactive} users with no recent activity (trend score < {config.MIN_TREND_SCORE_REQUIRED})"
            )
            print(f"     (No commits in last 90 days - likely inactive/unavailable)")
        print(f"   • Total filtered: {total_filtered}/{len(users)}")
        print(f"📊 Active users remaining: {len(active_users)}\n")

    # Calculate scores ONLY for active users (performance optimization)
    print(f"⚙️ Calculating scores for {len(active_users)} active users...")
    for user in active_users:
        user["ranking_score"] = calculate_user_score(user, active_users)

    # Sort by score (descending)
    ranked = sorted(active_users, key=lambda u: u["ranking_score"], reverse=True)

    # Note: Table printing moved to workflow.py for better control
    # (workflow.py can print top_n users as specified by user)

    if top_n:
        return ranked[:top_n]
    return ranked


def save_ranked_users(users: List[Dict], output_path: str):
    """Save ranked users to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            users, f, indent=config.JSON_INDENT, ensure_ascii=config.JSON_ENSURE_ASCII
        )
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
