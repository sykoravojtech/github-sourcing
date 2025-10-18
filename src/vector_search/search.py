"""Vector search functionality for finding similar GitHub profiles."""

import os
import re
import time
from typing import Any, Dict, List, Tuple

import numpy as np
from dotenv import load_dotenv
from groq import Groq
from sklearn.metrics.pairwise import cosine_similarity

# Load environment variables
load_dotenv()


class VectorSearch:
    """Simple in-memory vector search using cosine similarity."""

    def __init__(
        self,
        embeddings: np.ndarray,
        users_data: List[Dict[str, Any]],
        use_llm_reasoning: bool = True,
    ):
        """
        Initialize the vector search index.

        Args:
            embeddings: Matrix of user profile embeddings (n_users, embedding_dim)
            users_data: List of user profile dictionaries corresponding to embeddings
            use_llm_reasoning: Whether to use Groq LLM for generating reasons (default: True)
        """
        self.embeddings = embeddings
        self.users_data = users_data
        self.use_llm_reasoning = use_llm_reasoning

        # Initialize Groq client if LLM reasoning is enabled
        if self.use_llm_reasoning:
            groq_api_key = os.getenv("GROQ_API_KEY")
            if groq_api_key:
                self.groq_client = Groq(api_key=groq_api_key)
                print(
                    f"Vector search initialized with {len(users_data)} profiles (LLM reasoning: enabled)"
                )
            else:
                print(
                    "Warning: GROQ_API_KEY not found, falling back to keyword-based reasoning"
                )
                self.use_llm_reasoning = False
                print(
                    f"Vector search initialized with {len(users_data)} profiles (LLM reasoning: disabled)"
                )
        else:
            print(
                f"Vector search initialized with {len(users_data)} profiles (LLM reasoning: disabled)"
            )

    def _generate_llm_reasons(self, user: Dict[str, Any], query: str) -> List[str]:
        """
        Generate reasons using Groq LLM (qwen/qwen3-32b).

        Args:
            user: User profile data
            query: Search query

        Returns:
            List of 3 HR-focused reasons
        """
        # Build comprehensive profile text
        profile_parts = []

        login = user.get("login", "Unknown")
        profile_parts.append(f"GitHub Username: @{login}")

        if user.get("bio"):
            profile_parts.append(f"Bio: {user['bio']}")

        if user.get("location"):
            profile_parts.append(f"Location: {user['location']}")

        if user.get("company"):
            profile_parts.append(f"Company: {user['company']}")

        # Add repository information with READMEs
        repositories = user.get("repositories", {})
        nodes = repositories.get("nodes", [])

        if nodes:
            profile_parts.append(f"\nRepositories ({len(nodes)} total):")
            for i, repo in enumerate(
                nodes[:5], 1
            ):  # Include all top 5 repos (Llama has higher capacity)
                repo_info = [f"\n{i}. {repo.get('name', 'Unknown')}"]
                if repo.get("description"):
                    repo_info.append(f"   Description: {repo['description']}")
                if repo.get("primaryLanguage"):
                    lang = repo.get("primaryLanguage", {}).get("name", "")
                    if lang:
                        repo_info.append(f"   Language: {lang}")
                if repo.get("stargazerCount"):
                    repo_info.append(f"   Stars: {repo['stargazerCount']}")
                if repo.get("readme"):
                    # Include full README (Llama has 30K token capacity)
                    readme = repo["readme"]
                    if len(readme) > 2000:  # Increased from 400
                        readme = readme[:2000] + "..."
                    repo_info.append(f"   README: {readme}")
                profile_parts.append("\n".join(repo_info))

        profile_text = "\n".join(profile_parts)

        # Less aggressive truncation for Llama
        if len(profile_text) > 4000:  # Increased from 1500
            profile_text = profile_text[:4000] + "\n... [profile truncated for brevity]"

        # Simple plain-text prompt asking for 3 reasons
        prompt = f"""You are an HR specialist. Based on this GitHub profile, write exactly 3 reasons why this candidate matches the job requirements.

JOB REQUIREMENTS:
{query}

CANDIDATE PROFILE:
{profile_text}

Write 3 specific reasons. Each reason should mention a specific repository or technology from their profile. Number them 1, 2, 3."""

        try:
            # Call Groq API with rate limiting (30 RPM = 1 request per 2 seconds)
            time.sleep(2.1)  # Sleep 2.1 seconds to stay under 30 RPM

            completion = self.groq_client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional HR specialist. Provide concise, numbered responses. No preambles or extra text.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=400,
            )

            response_text = completion.choices[0].message.content.strip()

            # Debug: Print the raw response
            # print(f"[DEBUG] LLM response for @{login}:")
            # print(f"[DEBUG] {response_text[:300]}...")

            # Parse numbered reasons - simple extraction
            import re

            lines = response_text.split("\n")
            reasons = []

            for line in lines:
                line = line.strip()
                # Match "1. " or "1) " at start
                if re.match(r"^[1-3][\.)]\s+", line):
                    reason = re.sub(r"^[1-3][\.)]\s+", "", line).strip()
                    if len(reason) > 20:  # Ensure substantive
                        reasons.append(reason)

            if len(reasons) >= 2:
                print(
                    f"[DEBUG] Successfully extracted {len(reasons)} reasons for @{login}"
                )
                return reasons[:3]
            else:
                print(
                    f"Warning: Only extracted {len(reasons)} reasons for @{login}, falling back"
                )
                return self._extract_relevant_info_keyword(user, query)

        except Exception as e:
            print(
                f"Warning: LLM reasoning failed for @{login} ({type(e).__name__}: {e}), falling back to keyword-based"
            )
            return self._extract_relevant_info_keyword(user, query)

        try:
            # Call Groq API with rate limiting (60 RPM = 1 request per second)
            time.sleep(1.1)  # Sleep 1.1 seconds to stay under 60 RPM

            completion = self.groq_client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # Slightly higher for more natural text
                max_tokens=250,  # Just need a paragraph
            )

            response_text = completion.choices[0].message.content.strip()

            # Debug: Print the raw response
            print(f"[DEBUG] LLM response for @{login}:")
            print(f"[DEBUG] {response_text}")

            # Simple validation - just check we got something substantive
            if len(response_text) > 30:
                print(f"[DEBUG] Successfully generated reasoning for @{login}")
                # Return as a single-item list to match expected format
                return [response_text]
            else:
                print(
                    f"Warning: LLM returned too-short response for @{login}, falling back"
                )
                return self._extract_relevant_info_keyword(user, query)

        except Exception as e:
            print(
                f"Warning: LLM reasoning failed for @{login} ({type(e).__name__}: {e}), falling back to keyword-based"
            )
            return self._extract_relevant_info_keyword(user, query)

    def _extract_relevant_info_keyword(
        self, user: Dict[str, Any], query: str
    ) -> List[str]:
        """
        Extract top 3 reasons using keyword matching (fallback method).

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

    def _extract_relevant_info(self, user: Dict[str, Any], query: str) -> List[str]:
        """
        Extract top 3 reasons why this profile matches the search query.
        Uses LLM if enabled, otherwise falls back to keyword matching.

        Args:
            user: User profile data
            query: Search query

        Returns:
            List of 3 reasons
        """
        if self.use_llm_reasoning and hasattr(self, "groq_client"):
            return self._generate_llm_reasons(user, query)
        else:
            return self._extract_relevant_info_keyword(user, query)

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
