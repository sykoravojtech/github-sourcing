"""Vector search functionality for finding similar GitHub profiles."""

import re
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class VectorSearch:
    """Simple in-memory vector search using cosine similarity."""

    def __init__(self, embeddings: np.ndarray, users_data: List[Dict[str, Any]]):
        """
        Initialize the vector search index.

        Args:
            embeddings: Matrix of user profile embeddings (n_users, embedding_dim)
            users_data: List of user profile dictionaries corresponding to embeddings
        """
        self.embeddings = embeddings
        self.users_data = users_data
        print(f"Vector search initialized with {len(users_data)} profiles")

    def _extract_relevant_info(self, user: Dict[str, Any], query: str) -> List[str]:
        """
        Extract top 3 reasons why this profile matches the search query.

        Args:
            user: User profile data
            query: Search query

        Returns:
            List of 3 reasons (or fewer if not enough relevant info)
        """
        reasons = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        # Extract relevant repositories
        repositories = user.get("repositories", {})
        nodes = repositories.get("nodes", [])

        # Check bio for relevance
        bio = user.get("bio", "")
        if bio and any(term in bio.lower() for term in query_terms):
            reasons.append(f'Bio mentions relevant expertise: "{bio}"')

        # Find relevant repositories
        relevant_repos = []
        for repo in nodes[:10]:  # Check top 10 repos
            repo_name = repo.get("name", "")
            repo_desc = repo.get("description", "")
            readme = repo.get("readme", "")

            # Create searchable text
            searchable_text = f"{repo_name} {repo_desc} {readme}".lower()

            # Check if query terms appear in repo
            matches = sum(1 for term in query_terms if term in searchable_text)
            if matches > 0:
                relevance_score = matches

                # Extract a good snippet showing relevance
                snippet = ""
                if readme:
                    # Try to find a sentence mentioning the query terms
                    sentences = re.split(r"[.!?\n]+", readme)
                    for sentence in sentences[:20]:  # Check first 20 sentences
                        if any(term in sentence.lower() for term in query_terms):
                            snippet = sentence.strip()[:150]
                            break

                if not snippet and repo_desc:
                    snippet = repo_desc[:150]

                relevant_repos.append(
                    {
                        "name": repo_name,
                        "description": repo_desc,
                        "snippet": snippet,
                        "relevance": relevance_score,
                        "language": (
                            repo.get("primaryLanguage", {}).get("name", "N/A")
                            if repo.get("primaryLanguage")
                            else "N/A"
                        ),
                    }
                )

        # Sort by relevance
        relevant_repos.sort(key=lambda x: x["relevance"], reverse=True)

        # Add top repository reasons
        for repo in relevant_repos[:3]:
            if repo["snippet"]:
                reason = f"Repository '{repo['name']}' ({repo['language']}): {repo['snippet']}"
            elif repo["description"]:
                reason = f"Repository '{repo['name']}' ({repo['language']}): {repo['description']}"
            else:
                reason = f"Repository '{repo['name']}' ({repo['language']}) - relevant to search"

            if len(reason) > 200:
                reason = reason[:197] + "..."
            reasons.append(reason)

        # If we don't have enough reasons, add company or location if relevant
        if len(reasons) < 3:
            company = user.get("company", "")
            if company and any(term in company.lower() for term in query_terms):
                reasons.append(f"Works at {company} - relevant to field")

        # Return top 3 reasons
        return reasons[:3]

    def search(
        self, query_embedding: np.ndarray, top_k: int = 10
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for most similar profiles to the query.

        Args:
            query_embedding: Query embedding vector
            top_k: Number of top results to return

        Returns:
            List of (user_data, similarity_score) tuples, sorted by similarity (highest first)
        """
        if len(self.embeddings) == 0:
            print("Warning: No embeddings available for search!")
            return []

        # Reshape query embedding for cosine_similarity
        query_embedding = query_embedding.reshape(1, -1)

        # Compute cosine similarities
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]

        # Get top k indices
        top_k = min(top_k, len(similarities))
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Return results with similarity scores
        results = [
            (self.users_data[idx], float(similarities[idx])) for idx in top_indices
        ]

        return results

    def print_results(self, results: List[Tuple[Dict[str, Any], float]], query: str):
        """
        Pretty print search results in HR-friendly format.

        Args:
            results: List of (user_data, similarity_score) tuples
            query: Original search query
        """
        print(f"\n{'='*80}")
        print(f"🔍 Top Candidates for: '{query}'")
        print(f"{'='*80}\n")

        if not results:
            print("No results found.")
            return

        for rank, (user, score) in enumerate(results, 1):
            login = user.get("login", "Unknown")
            print(f"{rank}. @{login}")
            print(f"   🔗 Profile: https://github.com/{login}")
            print(f"   📊 Match Score: {score:.1%}")

            # Extract and show reasons
            reasons = self._extract_relevant_info(user, query)

            if reasons:
                print(f"\n   ✨ Why this candidate is a good fit:")
                for i, reason in enumerate(reasons, 1):
                    # Format reason nicely with line wrapping
                    print(f"      {i}. {reason}")
            else:
                # Fallback if we couldn't extract specific reasons
                print(f"\n   ✨ Why this candidate is a good fit:")
                print(f"      1. Profile content matches search criteria")
                if user.get("bio"):
                    bio = (
                        user["bio"][:100] + "..."
                        if len(user["bio"]) > 100
                        else user["bio"]
                    )
                    print(f"      2. Bio: {bio}")
                repositories = user.get("repositories", {})
                total_repos = repositories.get("totalCount", 0)
                if total_repos:
                    print(
                        f"      3. Has {total_repos} repositories showing relevant experience"
                    )

            print()
