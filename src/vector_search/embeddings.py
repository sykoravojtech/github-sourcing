"""Generate embeddings for GitHub user profiles."""

import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sentence_transformers import SentenceTransformer


class ProfileEmbedder:
    """Generate embeddings for GitHub user profiles using README and profile data."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedder with a sentence transformer model.

        Args:
            model_name: Name of the sentence transformer model to use.
                       Default is all-MiniLM-L6-v2 (fast, CPU-friendly, good quality)
        """
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully!")

    def create_profile_text(self, user_data: Dict[str, Any]) -> str:
        """
        Create a comprehensive text representation of a user's profile.

        Combines:
        - Username and bio
        - README content from repositories
        - Repository descriptions, names, and languages

        Args:
            user_data: Dictionary containing user profile and README data

        Returns:
            Combined text string for embedding
        """
        text_parts = []

        # Add username
        if user_data.get("login"):
            text_parts.append(f"GitHub username: {user_data['login']}")

        # Add bio
        if user_data.get("bio"):
            text_parts.append(f"Bio: {user_data['bio']}")

        # Add location (can be relevant for HR)
        if user_data.get("location"):
            text_parts.append(f"Location: {user_data['location']}")

        # Add company
        if user_data.get("company"):
            text_parts.append(f"Company: {user_data['company']}")

        # Add repository information with READMEs
        repositories = user_data.get("repositories", {})
        nodes = repositories.get("nodes", [])

        if nodes:
            repo_texts = []
            readme_texts = []

            for repo in nodes:
                repo_info = []
                if repo.get("name"):
                    repo_info.append(f"Repository: {repo['name']}")
                if repo.get("description"):
                    repo_info.append(f"Description: {repo['description']}")
                if repo.get("primaryLanguage") and repo.get("primaryLanguage", {}).get(
                    "name"
                ):
                    repo_info.append(f"Language: {repo['primaryLanguage']['name']}")
                if repo_info:
                    repo_texts.append(" | ".join(repo_info))

                # Collect README content
                readme = repo.get("readme", "")
                if readme and readme.strip():
                    readme_texts.append(
                        f"README for {repo.get('name', 'repository')}: {readme}"
                    )

            if repo_texts:
                text_parts.append("Repositories: " + " || ".join(repo_texts))

            # Add README content (most important for semantic search)
            if readme_texts:
                text_parts.append("Repository READMEs: " + " || ".join(readme_texts))

        return " ".join(text_parts)

    def embed_profiles(
        self, users_data: List[Dict[str, Any]]
    ) -> tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Generate embeddings for all user profiles that have README content.

        Args:
            users_data: List of user profile dictionaries

        Returns:
            Tuple of (embeddings matrix, filtered users list)
            Only includes users with README content
        """
        # Filter users who have README content in their repositories
        users_with_readmes = []
        for user in users_data:
            repositories = user.get("repositories", {})
            nodes = repositories.get("nodes", [])
            # Check if any repository has a readme
            has_readme = any(
                repo.get("readme") and repo.get("readme").strip() for repo in nodes
            )
            if has_readme:
                users_with_readmes.append(user)

        print(
            f"Found {len(users_with_readmes)} users with README content out of {len(users_data)} total users"
        )

        if not users_with_readmes:
            print("Warning: No users with README content found!")
            return np.array([]), []

        # Create text representations
        print("Creating text representations...")
        profile_texts = [self.create_profile_text(user) for user in users_with_readmes]

        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.model.encode(
            profile_texts, show_progress_bar=True, convert_to_numpy=True
        )

        print(f"Generated embeddings with shape: {embeddings.shape}")
        return embeddings, users_with_readmes

    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.

        Args:
            query: Search query string

        Returns:
            Query embedding vector
        """
        return self.model.encode([query], convert_to_numpy=True)[0]
