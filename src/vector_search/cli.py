"""Command-line interface for vector search."""

import json
import sys
from pathlib import Path
from typing import Optional

from .embeddings import ProfileEmbedder
from .search import VectorSearch


class VectorSearchCLI:
    """Interactive command-line interface for searching GitHub talent."""

    def __init__(self, data_path: str):
        """
        Initialize the CLI with data from a Phase 3 JSON file.

        Args:
            data_path: Path to the Phase 3 JSON file with README data
        """
        self.data_path = Path(data_path)
        self.embedder = None
        self.search_engine = None
        self.users_data = None

        # Load and index data
        self._load_and_index()

    def _load_and_index(self):
        """Load data and create embeddings index."""
        print(f"Loading data from: {self.data_path}")

        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        with open(self.data_path, "r", encoding="utf-8") as f:
            self.users_data = json.load(f)

        print(f"Loaded {len(self.users_data)} user profiles")

        # Initialize embedder
        self.embedder = ProfileEmbedder()

        # Generate embeddings
        embeddings, filtered_users = self.embedder.embed_profiles(self.users_data)

        # Update users data to only include those with embeddings
        self.users_data = filtered_users

        # Initialize search engine
        self.search_engine = VectorSearch(embeddings, self.users_data)

        print("\n✓ Vector search system ready!\n")

    def search(self, query: str, top_k: int = 10):
        """
        Perform a search and display results.

        Args:
            query: Search query string
            top_k: Number of results to return
        """
        if not query.strip():
            print("Please enter a valid search query.")
            return

        print(f"Searching for: '{query}'...")

        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)

        # Search
        results = self.search_engine.search(query_embedding, top_k=top_k)

        # Display results
        self.search_engine.print_results(results, query)

    def run_interactive(self):
        """Run interactive search loop."""
        print("=" * 80)
        print("GitHub Talent Vector Search")
        print("=" * 80)
        print("\nSearch for GitHub users by entering keywords related to their skills,")
        print(
            "projects, or areas of expertise (e.g., 'text-to-speech', 'machine learning',"
        )
        print("'react developer', 'data visualization', etc.)")
        print("\nCommands:")
        print("  - Type your search query and press Enter")
        print("  - Type 'quit' or 'exit' to exit")
        print("  - Type 'help' for this message")
        print("=" * 80 + "\n")

        while True:
            try:
                query = input("Search query: ").strip()

                if not query:
                    continue

                if query.lower() in ["quit", "exit", "q"]:
                    print("\nGoodbye!")
                    break

                if query.lower() == "help":
                    print("\nEnter keywords to search for GitHub talent.")
                    print(
                        "Examples: 'text-to-speech', 'rust compiler', 'mobile development'"
                    )
                    continue

                # Perform search
                self.search(query, top_k=10)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue


def main():
    """Main entry point for the CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Search GitHub talent using vector embeddings"
    )
    parser.add_argument(
        "--data",
        type=str,
        help="Path to Phase 3 JSON file with README data",
        default=None,
    )
    parser.add_argument(
        "--query",
        type=str,
        help="Single query to search (non-interactive mode)",
        default=None,
    )
    parser.add_argument(
        "--top-k", type=int, help="Number of results to return", default=10
    )

    args = parser.parse_args()

    # Find data file if not specified
    if args.data is None:
        # Look for most recent phase3 file
        data_dir = Path("data/raw")
        phase3_files = list(data_dir.glob("*/phase3_top_*_with_readmes.json"))

        if not phase3_files:
            # Fallback to old location
            phase3_files = list(data_dir.glob("phase3_top_*_with_readmes.json"))

        if not phase3_files:
            print("Error: No Phase 3 data file found.")
            print("Please specify the data file with --data option.")
            sys.exit(1)

        # Use most recent file
        args.data = str(sorted(phase3_files)[-1])
        print(f"Using data file: {args.data}\n")

    # Initialize CLI
    cli = VectorSearchCLI(args.data)

    # Run in single-query or interactive mode
    if args.query:
        cli.search(args.query, top_k=args.top_k)
    else:
        cli.run_interactive()


if __name__ == "__main__":
    main()
