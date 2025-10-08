"""
Phase 2: Fetch READMEs for top-ranked users.
Run this after ranking users with rank_users.py
"""

import os
import sys

# Add parent directory to path to import fetch_users
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "data_collection"))

from fetch_users import fetch_readmes_for_users, load_users_from_file

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
