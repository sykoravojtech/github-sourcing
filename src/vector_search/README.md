# Vector Search for GitHub Talent

This module provides semantic search functionality to find GitHub developers based on their skills, projects, and expertise using AI embeddings.

## Overview

The vector search system:
- Uses **Sentence Transformers** (`all-MiniLM-L6-v2`) for CPU-friendly semantic embeddings
- Embeds user profiles including: READMEs, repository descriptions, languages, bio, and location
- Provides similarity-based ranking using cosine similarity
- Only includes users with README content for accurate results

## Installation

Dependencies are already included in the project's `pyproject.toml`:
```bash
uv sync
```

This will install:
- `sentence-transformers` - For generating embeddings
- `numpy` - For vector operations
- `scikit-learn` - For similarity calculations

## Usage

### Interactive Mode (Recommended)

Start an interactive search session:
```bash
uv run python search.py
```

Then enter search queries like:
- `"text-to-speech"`
- `"machine learning computer vision"`
- `"react developer mobile apps"`
- `"rust compiler optimization"`
- `"data visualization python"`

Type `quit` or `exit` to exit.

### Single Query Mode

Run a one-off search:
```bash
uv run python search.py --query "text-to-speech"
```

### Specify Data File

By default, the tool finds the most recent Phase 3 data file. To use a specific file:
```bash
uv run python search.py --data data/raw/20251012_221018/phase3_top_20_with_readmes.json
```

### Adjust Number of Results

Default is 10 results. To get more or fewer:
```bash
uv run python search.py --query "machine learning" --top-k 5
```

## How It Works

### 1. **Embedding Generation** (`embeddings.py`)
- Loads the `all-MiniLM-L6-v2` model (384-dimensional embeddings)
- Creates text representations combining:
  - Username and bio
  - Company and location
  - Repository names, descriptions, and languages
  - **README content** (most important for semantic matching)
- Generates embeddings for all profiles with README content

### 2. **Vector Search** (`search.py`)
- Stores embeddings in memory (numpy array)
- For each query:
  - Generates query embedding
  - Computes cosine similarity with all profile embeddings
  - Returns top-k most similar profiles
- Results include similarity scores (0-1, higher = more similar)

### 3. **CLI Interface** (`cli.py`)
- Provides interactive and single-query modes
- Auto-discovers Phase 3 data files
- Pretty-prints results with profile details

## Use Case: HR Talent Sourcing

This tool is designed for HR professionals to find GitHub talent matching specific requirements:

**Example Searches:**
- **"frontend developer react typescript"** - Find React/TypeScript experts
- **"devops kubernetes aws cloud"** - Find DevOps engineers with cloud experience
- **"natural language processing transformers"** - Find NLP specialists
- **"game development unity c#"** - Find game developers
- **"mobile development flutter ios android"** - Find mobile developers

The search understands semantic relationships, so:
- Searching for "AI" will also find "machine learning", "deep learning", "neural networks"
- Searching for "web development" will find "React", "Vue", "frontend"
- Searching for "backend" will find "API", "databases", "microservices"

## Architecture

```
src/vector_search/
├── __init__.py           # Package initialization
├── embeddings.py         # Embedding generation (ProfileEmbedder)
├── search.py             # Vector search logic (VectorSearch)
└── cli.py                # Command-line interface (VectorSearchCLI)

search.py                 # Convenience entry point script
```

## Model Information

**all-MiniLM-L6-v2:**
- Size: ~80MB
- Dimensions: 384
- Speed: Very fast on CPU (~1000 sentences/sec)
- Quality: Good for semantic similarity tasks
- License: Apache 2.0 (free for commercial use)

On first run, the model downloads automatically to `~/.cache/huggingface/`.

## Future Enhancements

Potential improvements:
- **Vector database** (ChromaDB, Pinecone) for larger datasets
- **Filtering** by location, language, or minimum stars
- **Hybrid search** combining vector search with keyword filters
- **Web interface** using Streamlit or Gradio
- **Batch processing** for analyzing many candidates at once
- **Export** results to CSV/JSON for further processing

## Troubleshooting

**No results found:**
- Ensure the Phase 3 data file includes README content
- Try broader search terms
- Check that embeddings were generated successfully

**Slow performance:**
- The all-MiniLM-L6-v2 model is already optimized for CPU
- First-time model download may take a minute
- Consider reducing the dataset size for faster testing

**Out of memory:**
- The current implementation uses ~50MB RAM for 20 profiles
- For thousands of profiles, consider batching or a vector database
