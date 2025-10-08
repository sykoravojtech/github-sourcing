"""
Main orchestrator for GitHub user scraping workflow.

This script runs the complete three-phase process:
1. Fetch users from GitHub (bulk)
2. Rank users by custom scoring
3. Fetch READMEs for top-ranked users

Usage:
    python main.py [--max-pages N] [--top-n N] [--location QUERY]
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Import config first
import config

# Add src directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "data_collection"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src", "processing"))

from fetch_readmes import fetch_readmes_for_users
from fetch_users import fetch_all_users, save_users_to_file
from rank_users import rank_users, save_ranked_users


def print_header(title):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def run_workflow(max_pages=None, top_n=None, location=None, fetch_readmes=None):
    """
    Run the complete three-phase workflow.

    Args:
        max_pages: Number of pages to fetch (default: from config)
        top_n: Number of top users to enrich with READMEs (default: from config)
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
    print(f"  • Top N users: {top_n}")
    print(f"  • Location query: {location}")
    print(f"  • Fetch READMEs: {'Yes' if fetch_readmes else 'No'}")
    print(f"  • Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {}

    # ========== PHASE 1: FETCH USERS ==========
    print_header("📥 Phase 1: Fetching User Profiles")

    try:
        users_data = fetch_all_users(search_query=location, max_pages=max_pages)

        if not users_data:
            print("❌ No users fetched. Exiting workflow.")
            return None

        print(f"\n✅ Successfully fetched {len(users_data)} users")

        # Save Phase 1 results
        output_path, output_folder = save_users_to_file(
            users_data, "phase1_all_users.json"
        )
        results["phase1_file"] = output_path
        results["output_folder"] = output_folder

        print(f"💾 Saved to: {output_path}")

    except Exception as e:
        print(f"❌ Error in Phase 1: {e}")
        return None

    # ========== PHASE 2: RANK USERS ==========
    print_header("🎯 Phase 2: Ranking Users")

    try:
        ranked_users = rank_users(users_data, top_n=top_n)

        # Save ranked results
        ranked_file = os.path.join(
            output_folder, f"phase2_ranked_top_{len(ranked_users)}.json"
        )
        save_ranked_users(ranked_users, ranked_file)
        results["phase2_file"] = ranked_file

        print(f"\n💾 Saved to: {ranked_file}")

    except Exception as e:
        print(f"❌ Error in Phase 2: {e}")
        return results

    # ========== PHASE 3: FETCH READMES ==========
    if fetch_readmes:
        print_header("📚 Phase 3: Fetching READMEs for Top Users")

        try:
            readme_file = fetch_readmes_for_users(ranked_users, output_folder)
            results["phase3_file"] = readme_file

        except Exception as e:
            print(f"❌ Error in Phase 3: {e}")
    else:
        print_header("⏭️  Phase 3: Skipped (fetch_readmes=False)")

    # ========== SUMMARY ==========
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print_header("✅ Workflow Complete!")

    print(f"⏱️  Total Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"📁 Output Folder: {output_folder}")
    print(f"\n📊 Results:")
    print(f"  • Users fetched: {len(users_data)}")
    print(f"  • Top ranked: {len(ranked_users)}")
    if fetch_readmes and "phase3_file" in results:
        print(f"  • READMEs enriched: ✅")

    print(f"\n📄 Output Files:")
    for key, path in results.items():
        if path:
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
  python main.py --max-pages 2 --top-n 20
  
  # Medium run: 250 users, top 50 with READMEs
  python main.py --max-pages 10 --top-n 50
  
  # Large run: 500 users, top 100 with READMEs
  python main.py --max-pages 20 --top-n 100
  
  # Without READMEs (fast)
  python main.py --max-pages 10 --top-n 50 --no-readmes
  
  # Different location
  python main.py --location "location:brno" --top-n 20
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
        help=f"Number of top-ranked users to enrich with READMEs. Default: {config.TOP_N_USERS}",
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
        location=args.location,
        fetch_readmes=not args.no_readmes,
    )

    if results:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
