# Metaphorizer

**AI-powered literary metaphor analysis tool** — Extract, categorize, and analyze metaphors from literary texts using Claude.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)
![Claude](https://img.shields.io/badge/Claude-API-orange)

## Overview

Metaphorizer uses Claude's advanced language understanding to perform deep literary analysis, identifying metaphors, similes, extended metaphors, and symbolic imagery in texts. Originally built for analyzing F. Scott Fitzgerald's *The Great Gatsby*, but extensible to other literary works.

## Features

- 📖 **Metaphor Extraction** — Identifies all figurative language including similes, extended metaphors, personification, metonymy
- 🏷️ **Categorization** — Groups metaphors by thematic systems (Light/Darkness, Water/Drowning, Vision, Time, etc.)
- 📊 **Analysis Dashboard** — Web interface for reviewing and exploring extracted metaphors
- 📄 **PDF Export** — Generate formatted analysis reports
- 🌐 **Translation Support** — Analyze metaphors across language translations
- ⚡ **Rate Limited** — Production-ready with configurable rate limits

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Web UI    │────▶│   FastAPI   │────▶│   Claude    │
│  (Jinja2)   │     │   Backend   │     │    API      │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                    ┌─────▼─────┐
                    │  SQLite   │
                    │ (async)   │
                    └───────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone https://github.com/justin-nevins/metaphorizer.git
cd metaphorizer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY
```

### Running

```bash
# Development
uvicorn app.main:app --reload

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker-compose up --build
```

Visit `http://localhost:8000` to access the web interface.

## Usage

1. **Ingest** — Upload or paste literary text by chapter
2. **Extract** — Run Claude-powered metaphor extraction
3. **Review** — Browse and categorize identified metaphors
4. **Export** — Generate PDF reports of your analysis

## Project Structure

```
metaphorizer/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings management
│   ├── models/           # SQLAlchemy models
│   ├── routers/          # API endpoints
│   ├── schemas/          # Pydantic schemas
│   ├── services/         # Business logic & Claude integration
│   ├── static/           # CSS, JS assets
│   └── templates/        # Jinja2 HTML templates
├── data/                 # SQLite database
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Technical Highlights

- **Async-first** — Full async/await with SQLAlchemy 2.0 and aiosqlite
- **Claude Tool Use** — Structured extraction using Claude's tool calling
- **Rate Limiting** — SlowAPI integration for production deployments
- **PDF Generation** — WeasyPrint for high-quality report rendering

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key | Required |
| `DATABASE_URL` | SQLite connection string | `sqlite+aiosqlite:///./data/gatsby.db` |
| `CLAUDE_MODEL` | Claude model to use | `claude-opus-4-20250514` |

## License

MIT

---

*Built by [Justin Nevins](https://github.com/justin-nevins)*
