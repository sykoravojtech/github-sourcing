#!/usr/bin/env python3
"""
Streamlit Web Interface for GitHub Talent Search

A beautiful web interface for searching GitHub talent using vector embeddings.

uv run streamlit run src/web_app.py
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import streamlit as st

from vector_search.embeddings import ProfileEmbedder
from vector_search.search import VectorSearch

# Page configuration
st.set_page_config(
    page_title="GitHub Talent Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.3rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }
    .candidate-row {
        background: white;
        border-radius: 6px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        border-left: 3px solid #667eea;
        transition: all 0.2s ease;
    }
    .candidate-row:hover {
        box-shadow: 0 2px 6px rgba(0,0,0,0.12);
        transform: translateY(-1px);
    }
    .rank-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: bold;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.9rem;
        min-width: 30px;
        text-align: center;
    }
    .candidate-name {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin: 0;
    }
    .match-score-high {
        color: #10b981;
        font-weight: bold;
        font-size: 1rem;
    }
    .match-score-medium {
        color: #f59e0b;
        font-weight: bold;
        font-size: 1rem;
    }
    .match-score-low {
        color: #6b7280;
        font-weight: bold;
        font-size: 1rem;
    }
    .reason-text {
        font-size: 0.85rem;
        line-height: 1.4;
            color: #888;
        margin-bottom: 0.3rem;
    }
    .stTextInput > div > div > input {
        font-size: 1rem;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def load_search_engine(data_path: str):
    """
    Load and initialize the search engine (cached for performance).

    Args:
        data_path: Path to the Phase 3 JSON file

    Returns:
        Tuple of (embedder, search_engine, users_data)
    """
    data_path = Path(data_path)

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    # Load user data
    with open(data_path, "r", encoding="utf-8") as f:
        users_data = json.load(f)

    # Initialize embedder
    embedder = ProfileEmbedder()

    # Generate embeddings
    embeddings, filtered_users = embedder.embed_profiles(users_data)

    # Initialize search engine
    search_engine = VectorSearch(embeddings, filtered_users)

    return embedder, search_engine, filtered_users


def format_match_score(score: float) -> str:
    """Format the match score as a percentage with color."""
    percentage = score * 100
    if percentage >= 30:
        css_class = "match-score-high"
    elif percentage >= 20:
        css_class = "match-score-medium"
    else:
        css_class = "match-score-low"

    return f'<span class="{css_class}">{percentage:.1f}%</span>'


def display_candidate(
    rank: int,
    user: Dict[str, Any],
    score: float,
    query: str,
    search_engine: VectorSearch,
):
    """
    Display a single candidate in a compact leaderboard row.

    Args:
        rank: Candidate ranking
        user: User data dictionary
        score: Similarity score
        query: Search query
        search_engine: VectorSearch instance for extracting reasons
    """
    login = user.get("login", "Unknown")
    profile_url = f"https://github.com/{login}"

    # Get reasons
    reasons = search_engine._extract_relevant_info(user, query)

    if not reasons:
        # Fallback reasons
        reasons = ["Profile content matches search criteria"]
        if user.get("bio"):
            bio = user["bio"][:80] + "..." if len(user["bio"]) > 80 else user["bio"]
            reasons.append(f"Bio: {bio}")
        repositories = user.get("repositories", {})
        total_repos = repositories.get("totalCount", 0)
        if total_repos:
            reasons.append(
                f"Has {total_repos} repositories showing relevant experience"
            )

    # Create 2-column layout: Left for name/rank/score, Right for reasons
    col_left, col_right = st.columns([0.35, 0.65])

    with col_left:
        # Rank badge and name
        st.markdown(
            f'<span class="rank-badge">#{rank}</span> '
            f'<a href="{profile_url}" target="_blank" class="candidate-name">@{login}</a>',
            unsafe_allow_html=True,
        )
        # Match score
        st.markdown(f"**Match:** {format_match_score(score)}", unsafe_allow_html=True)

    with col_right:
        # Display reasons as numbered list
        for i, reason in enumerate(reasons[:3], 1):
            st.markdown(
                f'<div class="reason-text">{i}. {reason}</div>',
                unsafe_allow_html=True,
            )

    # Subtle separator
    st.markdown('<div style="margin: 0.3rem 0;"></div>', unsafe_allow_html=True)


def main():
    """Main application function."""

    # Header
    st.markdown(
        '<h1 class="main-header">🔍 GitHub Talent Search</h1>', unsafe_allow_html=True
    )
    st.markdown(
        '<p class="sub-header">Find the perfect developers using AI-powered semantic search</p>',
        unsafe_allow_html=True,
    )

    # Data file selector (in sidebar)
    with st.sidebar:
        st.header("⚙️ Settings")

        # Default data path
        # default_data_path = "data/raw/20251018_102552/phase3_top_20_with_readmes.json"
        default_data_path = "data/raw/20251019_102119/phase3_top_50_with_readmes.json"

        data_path = st.text_input(
            "Data file path",
            value=default_data_path,
            help="Path to the Phase 3 JSON file with README data",
        )

        top_k = st.slider(
            "Number of results",
            min_value=1,
            max_value=50,
            value=3,  # Default to 3 for testing
            help="How many candidates to show",
        )

        st.markdown("---")
        st.markdown("### About")
        st.markdown(
            "This tool uses **vector embeddings** and **semantic similarity** "
            "to find GitHub users whose profiles match your search criteria."
        )
        st.markdown("Built with Streamlit, sentence-transformers, and scikit-learn.")

    # Try to load the search engine
    try:
        with st.spinner("🔄 Loading search engine..."):
            embedder, search_engine, users_data = load_search_engine(data_path)

        # Check if LLM reasoning is enabled
        llm_status = (
            "🤖 AI-Powered"
            if search_engine.use_llm_reasoning and hasattr(search_engine, "groq_client")
            else "🔤 Keyword-based"
        )

        # Display success message with LLM status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success(f"✅ Loaded {len(users_data)} profiles and ready to search!")
        with col2:
            if search_engine.use_llm_reasoning and hasattr(
                search_engine, "groq_client"
            ):
                st.info("🤖 AI Mode")
            else:
                st.warning("🔤 Keyword Mode")

    except FileNotFoundError as e:
        st.error(f"❌ {str(e)}")
        st.info("Please check the data file path in the sidebar settings.")
        return
    except Exception as e:
        st.error(f"❌ Error loading search engine: {str(e)}")
        return

    # Search interface
    st.markdown("---")

    # Search input
    query = st.text_input(
        "🔎 Enter your search query",
        placeholder="e.g., 'ai, machine learning, langchain' or 'react developer' or 'data visualization'",
        help="Describe the skills, technologies, or expertise you're looking for",
        key="search_query",
    )

    # Search button
    col1, col2, col3 = st.columns([1, 1, 3])
    with col1:
        search_button = st.button("🚀 Search", type="primary", use_container_width=True)

    # Perform search
    if search_button and query.strip():
        with st.spinner(f"🔍 Searching for: '{query}'..."):
            # Generate query embedding
            query_embedding = embedder.embed_query(query)

            # Perform search
            results = search_engine.search(query_embedding, top_k=top_k)

        # Display results
        st.markdown("---")
        st.markdown(f"## Top {len(results)} Candidates")
        st.markdown(f"*Searching for:* **{query}**")
        st.markdown(
            '<div style="margin-bottom: 0.5rem;"></div>', unsafe_allow_html=True
        )

        # Add header row for the leaderboard
        header_col1, header_col2 = st.columns([0.35, 0.65])
        with header_col1:
            st.markdown("**👤 Candidate & Match Score**")
        with header_col2:
            st.markdown("**✨ Why they're a good fit**")

        st.markdown("---")

        if not results:
            st.warning("No results found. Try a different query.")
        else:
            for rank, (user, score) in enumerate(results, 1):
                display_candidate(rank, user, score, query, search_engine)

    elif search_button:
        st.warning("⚠️ Please enter a search query.")

    # Example queries
    with st.expander("💡 Example Search Queries"):
        st.markdown(
            """
        **Detailed structured queries:**
        - `Focus: modern web development and UI tools; Main languages: TypeScript, JavaScript; Typical tags: react, nextjs, frontend, ui, design-system, vite, webdev`
        - `Focus: server technologies, microservices, cloud, DevOps; Main languages: Go, Rust, Java, C#, Shell/Dockerfile/YAML; Typical tags: backend, api, microservices, kubernetes, docker, infra, devops`
        - `Focus: data analysis, scientific tools, visualization; Main languages: Python, R, SQL, Julia; Typical tags: data, analytics, etl, notebook, visualization, ml, science`
        - `Focus: artificial intelligence, models, agents, data science; Main languages: Python, Rust; Typical tags: ai, llm, langchain, transformers, mlops, neural-network, data-engineering`
        
        **Simple queries:**
        - `ai, machine learning, langchain`
        - `rust systems programming`
        - `react typescript frontend developer`
        - `data visualization python`
        - `devops kubernetes docker`
        - `computer vision opencv`
        - `natural language processing`
        """
        )


if __name__ == "__main__":
    main()
