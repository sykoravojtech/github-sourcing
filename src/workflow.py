"""
Main orchestrator for GitHub user scraping workflow.

This script runs the complete three-phase process:
1. Fetch users from GitHub (bulk)
2. Rank users by custom scoring
3. Fetch READMEs for top-ranked users

Usage:
    python src/workflow.py [--max-pages N] [--top-n N] [--readme-n N] [--location QUERY]
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import config first
from src import config

# Use optimized fetch implementatsion (Oct 2025)
from src.data_collection.fetch_users import (
    fetch_users_batch,
    retry_failed_batches,
    save_users,
    search_users,
)
from src.processing.fetch_readmes import fetch_readmes_for_users
from src.processing.rank_users import rank_users, save_ranked_users


def print_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def run_workflow(
    max_pages=None, top_n=None, readme_n=None, location=None, fetch_readmes=None
):
    """
    Run the complete three-phase workflow.

    Args:
        max_pages: Number of pages to fetch (default: from config)
        top_n: Number of top users to rank and save (default: from config)
        readme_n: Number of top users to fetch READMEs for (default: same as top_n)
        location: GitHub search query for location (default: from config)
        fetch_readmes: Whether to fetch READMEs in phase 3 (default: from config)

    Returns:
        Dictionary with paths to all output files
    """
    # Use config defaults if not specified
    if max_pages is None:
        max_pages = config.MAX_PAGES
    if top_n is None:
        top_n = config.TOP_N_USERS
    if readme_n is None:
        readme_n = top_n  # Default: README count same as rank count
    if location is None:
        location = config.DEFAULT_LOCATION
    if fetch_readmes is None:
        fetch_readmes = config.FETCH_READMES

    start_time = datetime.now()

    print_header("🚀 GitHub User Scraper - Complete Workflow")

    print("📋 Workflow Configuration:")
    print(
        f"  • Max pages: {max_pages} (up to {max_pages * config.USERS_PER_PAGE} users)"
    )
    print(f"  • Top N users (rank): {top_n}")
    if fetch_readmes:
        print(f"  • Top N users (README): {readme_n}")
    print(f"  • Location query: {location}")
    print(f"  • Fetch READMEs: {'Yes' if fetch_readmes else 'No'}")
    print(f"  • Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}
    timings = {}

    # ========== PHASE 1: FETCH USERS ==========
    print_header("📥 Phase 1: Fetching User Profiles (Optimized Two-Phase)")

    phase1_start = datetime.now()
    try:
        # Phase 1a: Search for user logins
        logins = search_users(location, max_pages=max_pages, users_per_page=100)

        if not logins:
            print("❌ No users found. Exiting workflow.")
            return None

        # Phase 1b: Batch fetch full user data
        users_data, failed_batches = fetch_users_batch(
            logins, batch_size=config.OPTIMAL_BATCH_SIZE, from_days_ago=365
        )

        # Phase 1c: Retry failed batches (if any)
        if failed_batches:
            print(f"\n🔄 Retrying {len(failed_batches)} failed batches...")
            recovered_users = retry_failed_batches(
                failed_batches, reduced_batch_size=10
            )
            users_data.extend(recovered_users)

        if not users_data:
            print("❌ No users fetched. Exiting workflow.")
            return None

        print(f"\n✅ Successfully fetched {len(users_data)}/{len(logins)} users")

        # Save Phase 1 results (with user count in filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_folder = os.path.join(
            os.path.dirname(__file__), "..", "data", "raw", timestamp
        )
        phase1_filename = f"phase1_all_{len(users_data)}_users.json"
        output_path = save_users(users_data, output_folder, phase1_filename)

        results["phase1_file"] = output_path
        results["output_folder"] = output_folder

        print(f"💾 Saved to: {output_path}")

        phase1_end = datetime.now()
        phase1_duration = (phase1_end - phase1_start).total_seconds()
        timings["phase1"] = phase1_duration
        print(
            f"⏱️  Phase 1 Duration: {phase1_duration:.1f}s ({phase1_duration/60:.1f} min)"
        )
        print(f"   Rate: {len(users_data)/phase1_duration:.1f} users/second")

    except Exception as e:
        print(f"❌ Error in Phase 1: {e}")
        import traceback

        traceback.print_exc()
        return None

    # ========== PHASE 2: RANK USERS ==========
    print_header("🎯 Phase 2: Ranking Users")

    phase2_start = datetime.now()
    try:
        # Rank all users first (filtering happens inside rank_users)
        all_ranked = rank_users(users_data, top_n=None)  # Get all ranked users

        # Select top N for display and saving
        top_ranked_users = all_ranked[:top_n]

        # Print table of top N users only
        print(f"\n🏆 Top {len(top_ranked_users)} Users (Score 0-100):")
        print(
            f"{'Rank':<6} {'Score':<8} {'Login':<20} {'Contrib':<9} {'Stars':<8} {'Trend':<8}"
        )
        print("-" * 70)

        for i, user in enumerate(top_ranked_users, 1):
            login = user.get("login", "N/A")
            score = user.get("ranking_score", 0)
            contributions = (
                user.get("contributionsCollection", {})
                .get("contributionCalendar", {})
                .get("totalContributions", 0)
            )
            total_stars = sum(
                r.get("stargazerCount", 0)
                for r in user.get("repositories", {}).get("nodes", [])
            )
            # Calculate trend score
            from src.processing.rank_users import calculate_trend_score

            trend_score = calculate_trend_score(user)

            print(
                f"{i:<6} {score:<8.1f} {login:<20} {contributions:<9} {total_stars:<8} {trend_score:<8.1f}"
            )

        print(f"\n{'='*70}\n")

        # Save ranked results (with user count in filename)
        ranked_file = os.path.join(
            output_folder, f"phase2_ranked_top_{len(top_ranked_users)}_users.json"
        )
        save_ranked_users(top_ranked_users, ranked_file)
        results["phase2_file"] = ranked_file
        results["ranked_users"] = top_ranked_users  # Store for Phase 3

        print(f"\n💾 Saved to: {ranked_file}")

        phase2_end = datetime.now()
        phase2_duration = (phase2_end - phase2_start).total_seconds()
        timings["phase2"] = phase2_duration
        print(f"⏱️  Phase 2 Duration: {phase2_duration:.1f}s")
        print(
            f"   Rate: {len(users_data)/phase2_duration:.1f} users/second (processed)"
        )

    except Exception as e:
        print(f"❌ Error in Phase 2: {e}")
        return results

    # ========== PHASE 3: FETCH READMES ==========
    if fetch_readmes:
        print_header(f"📚 Phase 3: Fetching READMEs for Top {readme_n} Users")

        phase3_start = datetime.now()
        try:
            # Get top readme_n users from ranked list
            readme_users = results.get("ranked_users", [])[:readme_n]
            print(f"Fetching READMEs for top {len(readme_users)} users...\n")

            readme_file = fetch_readmes_for_users(readme_users, output_folder)
            results["phase3_file"] = readme_file

            phase3_end = datetime.now()
            phase3_duration = (phase3_end - phase3_start).total_seconds()
            timings["phase3"] = phase3_duration
            print(
                f"\n⏱️  Phase 3 Duration: {phase3_duration:.1f}s ({phase3_duration/60:.1f} min)"
            )
            print(f"   Rate: {len(readme_users)/phase3_duration:.1f} users/second")

        except Exception as e:
            print(f"❌ Error in Phase 3: {e}")
            timings["phase3"] = 0
    else:
        print_header("⏭️  Phase 3: Skipped (fetch_readmes=False)")
        timings["phase3"] = 0

    # ========== SUMMARY ==========
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_header("✅ Workflow Complete!")

    print(f"⏱️  Total Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"📁 Output Folder: {output_folder}")
    print(f"\n📊 Results:")
    print(f"  • Users fetched: {len(users_data)}")
    print(f"  • Users ranked: {len(all_ranked)}")
    print(f"  • Top saved: {top_n}")
    if fetch_readmes and "phase3_file" in results:
        print(f"  • READMEs fetched: {readme_n}")

    print(f"\n⏱️  Phase Timings:")
    print(
        f"  • Phase 1 (Fetch): {timings.get('phase1', 0):.1f}s ({timings.get('phase1', 0)/60:.1f} min) - {timings.get('phase1', 0)/duration*100:.1f}%"
    )
    print(
        f"  • Phase 2 (Rank):  {timings.get('phase2', 0):.1f}s - {timings.get('phase2', 0)/duration*100:.1f}%"
    )
    if fetch_readmes:
        print(
            f"  • Phase 3 (README): {timings.get('phase3', 0):.1f}s - {timings.get('phase3', 0)/duration*100:.1f}%"
        )

    print(f"\n📄 Output Files:")
    for key, path in results.items():
        if path and isinstance(path, str) and os.path.isfile(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print(f"  • {key}: {os.path.basename(path)} ({size_mb:.2f} MB)")

    print(f"\n{'='*70}")

    return results


def main():
    """Parse arguments and run workflow."""
    parser = argparse.ArgumentParser(
        description="GitHub User Scraper - Complete Workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test: 50 users, top 20 with READMEs
    python src/workflow.py --max-pages 2 --top-n 20
  
    # Medium run: 250 users, top 50 with READMEs
    python src/workflow.py --max-pages 10 --top-n 50
  
    # Large run: 500 users, top 100 with READMEs
    python src/workflow.py --max-pages 20 --top-n 100
  
    # Without READMEs (fast)
    python src/workflow.py --max-pages 10 --top-n 50 --no-readmes
  
    # Different location
    python src/workflow.py --location "location:brno" --top-n 20
        """,
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=f"Number of pages to fetch ({config.USERS_PER_PAGE} users per page). Default: {config.MAX_PAGES} ({config.MAX_PAGES * config.USERS_PER_PAGE} users)",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=None,
        help=f"Number of top-ranked users to save. Default: {config.TOP_N_USERS}",
    )

    parser.add_argument(
        "--readme-n",
        type=int,
        default=None,
        help=f"Number of top users to fetch READMEs for (default: same as --top-n)",
    )

    parser.add_argument(
        "--location",
        type=str,
        default=None,
        help=f'GitHub location search query. Default: "{config.DEFAULT_LOCATION}"',
    )

    parser.add_argument(
        "--no-readmes",
        action="store_true",
        help="Skip README fetching in Phase 3 (faster)",
    )

    args = parser.parse_args()

    # Run workflow
    results = run_workflow(
        max_pages=args.max_pages,
        top_n=args.top_n,
        readme_n=args.readme_n,
        location=args.location,
        fetch_readmes=not args.no_readmes,
    )

    if results:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
