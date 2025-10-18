# GitHub Talent Search - Web Interface Guide

## 🚀 Quick Start

Run the web application:
```bash
uv run streamlit run web_app.py
```

Then open your browser at: **http://localhost:8501**

## 🎨 Design Features

### Compact Leaderboard Layout
The new design is optimized for displaying many profiles (up to 50+) efficiently:

1. **Two-Column Layout**:
   - **Left column (35%)**: Rank badge, candidate name/link, and match score
   - **Right column (65%)**: Three concise reasons why they're a good fit

2. **Removed Elements for Efficiency**:
   - ❌ Progress bars (redundant with percentage)
   - ❌ Repeated "Why this candidate is a good fit" headers
   - ❌ Large card-style containers with excessive padding
   - ❌ Horizontal separators between each candidate

3. **Space-Saving Improvements**:
   - Compact padding (0.8rem instead of 1.5rem)
   - Smaller margins between candidates (0.5rem)
   - Reduced font sizes while maintaining readability
   - Inline rank badges instead of separate columns
   - Hover effects for better interactivity

4. **Visual Enhancements**:
   - Color-coded match scores:
     - 🟢 **Green** (≥30%): High match
     - 🟡 **Orange** (20-30%): Medium match
     - ⚪ **Gray** (<20%): Lower match
   - Gradient rank badges
   - Subtle shadows and hover animations
   - Clear header row for the leaderboard

## 📊 Configuration

### Sidebar Settings
- **Data file path**: Path to your Phase 3 JSON file
- **Number of results**: Slider from 1 to 50 candidates

### Default Data Path
```
data/raw/20251018_102552/phase3_top_20_with_readmes.json
```

## 🔍 How to Use

1. **Enter a search query** in the search box:
   - "ai, machine learning, langchain"
   - "rust systems programming"
   - "react typescript frontend"
   
2. **Click "🚀 Search"**

3. **View results** in the leaderboard format:
   - Each row shows rank, name, score, and 3 reasons
   - Click on candidate names to visit their GitHub profiles
   - Scores are color-coded for quick scanning

## 💡 Example Queries

Try these in the web interface:
- `ai, machine learning, langchain`
- `rust systems programming`
- `react typescript frontend developer`
- `data visualization python`
- `mobile development flutter`
- `devops kubernetes docker`
- `computer vision opencv`
- `natural language processing`

## 🎯 Performance

- **Cached search engine**: Loads once and reuses for all searches
- **Fast embeddings**: Generates query embeddings in <1 second
- **Efficient display**: Can handle 50+ profiles smoothly
- **Auto-reload**: Changes to code automatically refresh the app

## 🛠️ Technical Stack

- **Streamlit**: Web framework
- **sentence-transformers**: Embedding generation
- **scikit-learn**: Cosine similarity search
- **NumPy**: Vector operations

## 📝 File Structure

```
web_app.py                 # Main Streamlit application
src/vector_search/
  ├── search.py           # Vector search logic
  ├── embeddings.py       # Embedding generation
  └── cli.py              # Original CLI interface (still works!)
```

## 🔧 Customization

### Adjust Number of Results
Use the sidebar slider to show 1-50 candidates.

### Change Color Thresholds
Edit the `format_match_score()` function in `web_app.py`:
```python
if percentage >= 30:      # High match threshold
    css_class = "match-score-high"
elif percentage >= 20:    # Medium match threshold
    css_class = "match-score-medium"
```

### Modify Layout Proportions
Adjust column widths in the `display_candidate()` function:
```python
col_left, col_right = st.columns([0.35, 0.65])  # Left: 35%, Right: 65%
```

## 📈 Comparison: Old vs New Design

| Feature | Old Design | New Design |
|---------|-----------|------------|
| Profiles per screen | ~3-4 | ~8-10 |
| Layout | Single column cards | Two-column leaderboard |
| Match score | Percentage + progress bar | Percentage only (color-coded) |
| Spacing | Large (1.5rem padding) | Compact (0.8rem padding) |
| Max results | 20 | 50 |
| Header repetition | Every profile | Once at top |
| Visual style | Cards | Table/leaderboard rows |

## 🚦 Original CLI Still Available

The command-line interface is still fully functional:
```bash
uv run python -m search --data data/raw/20251018_102552/phase3_top_20_with_readmes.json
```

Both interfaces use the same underlying search engine!
