# airecon-dataset

Local security knowledge base for [AIRecon](https://github.com/pikpikcu/airecon). Downloads datasets from HuggingFace, indexes them into SQLite FTS5 databases, and makes them searchable via AIRecon's `dataset_search` tool — 100% offline after installation.

## Quick Start

```bash
# Install all enabled datasets (~2.4GB)
python install.py

# Install specific datasets only
python install.py --include nuclei-templates red-team-offensive

# Check what's installed
python install.py installed
```

AIRecon picks up new datasets automatically. Restart AIRecon after installing.

## Datasets

| ID | Name | Records | Category | License |
|----|------|---------|----------|---------|
| `cybersecurity-qa` | Trendyol Cybersecurity Instruction Tuning | 53,199 | general | Apache-2.0 |
| `cybersecurity-fenrir` | Cybersecurity Dataset Fenrir v2.0 | 83,918 | general | MIT |
| `cybersecurity-cve` | Cybersecurity LLM CVE Dataset | 124,732 | vulnerability | MIT |
| `bug-bounty-pentest` | Bug Bounty & Pentest Methodology | 146 | bug-bounty | MIT |
| `ctf-instruct` | CTF Instruct Dataset | 141,182 | ctf | MIT |
| `ctf-satml24` | CTF SaTML 2024 (Attack/Defense) | 190,657 | ctf | MIT |
| `red-team-offensive` | Ultimate Offensive Red Team Dataset | 78,430 | pentest | MIT |
| `nuclei-templates` | Nuclei Templates Instruct (Ernest v3) | 23,180 | pentest | MIT |
| `pentest-agent-chatml` | Pentest Agent Dataset (ChatML) | 322,433 | pentest | Apache-2.0 |
| `pentest-books` *(gated)* | Cybersecurity Penetration Testing Books | — | pentest | unknown |

**Total: ~1,017,877 records** across 9 active datasets.

### Gated datasets

`pentest-books` requires a HuggingFace account:

```bash
pip install huggingface_hub
huggingface-cli login
python install.py --include pentest-books
```

## CLI Reference

```
python install.py [OPTIONS] [SUBCOMMAND]

Options:
  --include ID [ID ...]   Install only these dataset IDs (plus always-on defaults)
  --exclude ID [ID ...]   Skip these dataset IDs
  --keep-cache            Keep the HuggingFace download cache after indexing
  --dry-run               Show what would be installed, without downloading
  --list                  List all available datasets from manifest

Subcommands:
  installed               Show installed datasets with record counts and sizes
  remove ID [ID ...]      Remove installed dataset(s)
  clean-cache             Delete the download cache (~/.cache/airecon-dataset/)
```

### Examples

```bash
# Dry run — see what would happen
python install.py --dry-run

# Install everything except large CTF datasets
python install.py --exclude ctf-instruct ctf-satml24

# Remove a dataset
python install.py remove cybersecurity-fenrir

# Clean download cache
python install.py clean-cache
```

## Custom Datasets

Drop your own `.jsonl` files into `custom/` and they'll be picked up automatically:

```jsonl
{"query": "How to exploit Apache Struts S2-045?", "answer": "Send Content-Type header with OGNL expression..."}
{"query": "JWT none algorithm bypass", "answer": "Change alg to 'none', remove signature..."}
```

Fields: `query` (required), `answer` (required), `context` (optional), `category` (optional).

## AIRecon Integration

After installation, the AIRecon agent uses `dataset_search` automatically. You can also query it directly in chat:

```
dataset_search: {"query": "log4j RCE exploitation", "limit": 3}
dataset_search: {"query": "SSRF bypass", "category": "bug-bounty"}
dataset_search: {"query": "CVE 2021 44228"}
```

The agent searches all installed databases in parallel and returns ranked results (max 500 chars per answer to preserve LLM context).

## Architecture

```
~/.airecon/datasets/
├── cybersecurity-qa.db        # SQLite FTS5 index
├── bug-bounty-pentest.db
├── nuclei-templates.db
└── ...

~/.cache/airecon-dataset/      # Temporary HF download cache
└── <dataset-id>/              # Cleaned up after indexing
```

Each `.db` uses SQLite FTS5 (`unicode61` tokenizer) over `query + answer + context` columns. The `dataset_search` tool fans out across all DBs, deduplicates, and returns the top-ranked results by FTS5 relevance score.

## Adding a New Dataset

1. Add an entry to `manifest.json`:

```json
{
  "id": "my-dataset",
  "name": "My Security Dataset",
  "hf_path": "author/repo-name",
  "split": "train",
  "category": "pentest",
  "fields": {"query": "instruction", "answer": "output"},
  "license": "mit",
  "description": "Short description",
  "enabled": true
}
```

2. Create `datasets/my-dataset/meta.json` with full metadata.

3. Run `python install.py --include my-dataset`.

**Supported field formats:**
- Flat: `{"query": "field_name", "answer": "field_name"}`
- Conversations: `{"conversations_field": "messages"}` (ChatML with `role`/`content`)
- Bug bounty multi-type: handled automatically for `bug-bounty-pentest`
