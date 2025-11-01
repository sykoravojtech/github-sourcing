"""
Phase 3: Fetch READMEs for top-ranked users.

This module handles README enrichment for selected users after ranking.
Called from workflow.py as Phase 3 of the workflow.
"""

import base64
import json
import os
import sys
import time

import requests

import src.config as config


def get_readme_content(owner, repo_name, verbose=False):
    """Fetch README content using GitHub REST API."""
    url = f"{config.REST_API_BASE}/repos/{owner}/{repo_name}/readme"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",  # Get JSON response
    }

    try:
        response = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            # Content is base64 encoded
            if "content" in data and data.get("encoding") == "base64":
                content_base64 = data["content"].replace("\n", "")
                content_decoded = base64.b64decode(content_base64).decode("utf-8")
                return content_decoded
            return None
        elif verbose and response.status_code == 404:
            print(f"    ⚠️  No README found for {owner}/{repo_name}")
        elif verbose:
            print(f"    ⚠️  {owner}/{repo_name}: HTTP {response.status_code}")
        return None
    except Exception as e:
        if verbose:
            print(f"    ⚠️  {owner}/{repo_name}: {str(e)[:50]}")
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
    print(f"📚 Fetching READMEs for {len(users)} top-ranked users")
    print(f"{'='*60}\n")

    readme_count = 0
    no_readme_count = 0
    total_repos = sum(
        len(user.get("repositories", {}).get("nodes", [])) for user in users
    )

    # Enable verbose mode if configured
    verbose = getattr(config, "VERBOSE", False)

    for i, user in enumerate(users, 1):
        login = user.get("login", "Unknown")
        repos = user.get("repositories", {}).get("nodes", [])
        print(f"Processing user {i}/{len(users)}: {login} ({len(repos)} repos)")

        for repo in repos:
            if not repo:
                continue

            repo_name = repo.get("name")
            repo_url = repo.get("url", "")
            if not repo_name:
                continue

            # Extract actual owner from URL (handles forks correctly)
            # URL format: https://github.com/owner/repo
            owner = login  # Default to user's login
            is_fork = repo.get("isFork", False)

            if repo_url and "github.com/" in repo_url:
                parts = repo_url.split("github.com/")[-1].split("/")
                if len(parts) >= 2:
                    owner = parts[0]  # Actual repo owner

            # Warn if fetching README from someone else's repo (fork)
            if verbose and owner != login:
                print(f"    ⚠️  {repo_name}: Fork of {owner}'s repo")

            readme_content = get_readme_content(owner, repo_name, verbose)
            if readme_content:
                repo["readme"] = readme_content
                readme_count += 1
                if verbose:
                    print(f"    ✅ {repo_name}: {len(readme_content)} bytes")
            else:
                no_readme_count += 1

            # Rate limiting
            time.sleep(config.README_DELAY)

    # Save enhanced users with READMEs
    filename = f"phase3_top_{len(users)}_with_readmes.json"
    output_path = os.path.join(output_folder, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            users, f, indent=config.JSON_INDENT, ensure_ascii=config.JSON_ENSURE_ASCII
        )

    print(f"\n📚 README Fetch Summary:")
    print(f"  ✅ Successfully fetched: {readme_count}/{total_repos} READMEs")
    print(f"  ⚠️  No README found: {no_readme_count}/{total_repos} repos")
    success_rate = (readme_count / total_repos * 100) if total_repos > 0 else 0
    print(f"  📊 Success rate: {success_rate:.1f}%")
    print(f"\n✅ Saved to: {output_path}")
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
