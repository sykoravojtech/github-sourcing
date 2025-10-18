"""
Phase 2: Fetch READMEs for top-ranked users.

This module handles README enrichment for selected users after ranking.
Run this after ranking users with rank_users.py
"""

import json
import os
import sys
import time

import requests

# Add parent directory to path to import config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import config


def get_readme_content(owner, repo_name):
    """Fetch README content using GitHub REST API."""
    url = f"{config.REST_API_BASE}/repos/{owner}/{repo_name}/readme"
    headers = config.get_rest_headers()

    try:
        response = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        return None


def load_users_from_file(filepath):
    """Load users from a JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_readmes_for_users(users, output_folder):
    """
    Fetch READMEs for a list of users and save to file.

    Args:
        users: List of user dictionaries with repositories
        output_folder: Folder to save the enriched data

    Returns:
        Path to the output file
    """
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
            time.sleep(config.README_DELAY)

    # Save enhanced users with READMEs
    filename = f"phase2_top_{len(users)}_with_readmes.json"
    output_path = os.path.join(output_folder, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            users, f, indent=config.JSON_INDENT, ensure_ascii=config.JSON_ENSURE_ASCII
        )

    print(f"\n📚 Fetched {readme_count}/{total_repos} READMEs")
    print(f"✅ Saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_readmes.py <ranked_users_json_file>")
        print(
            "Example: python fetch_readmes.py data/raw/20251008_162951/phase2_ranked_top_20.json"
        )
        sys.exit(1)

    input_file = sys.argv[1]

    # Load ranked users
    print(f"Loading ranked users from: {input_file}")
    users = load_users_from_file(input_file)

    # Get output folder (same as input)
    output_folder = os.path.dirname(input_file)

    # Fetch READMEs
    fetch_readmes_for_users(users, output_folder)
