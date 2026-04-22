<h1 align="center">airecon-datasets</h1>
<h4 align="center">Dataset installer for <a href="https://github.com/pikpikcu/airecon">AIRecon</a></h4>

<p align="center">
  <img src="https://img.shields.io/badge/AIRecon-compatible-green.svg">
  <img src="https://img.shields.io/badge/datasets-18-blue.svg">
</p>

Local security knowledge base for [AIRecon](https://github.com/pikpikcu/airecon). The installer downloads datasets from Hugging Face, indexes them into local SQLite FTS5 databases, and exposes them to AIRecon through `dataset_search`.

> Source of truth is now `datasets/<name>/meta.json`. The folder name is the canonical dataset selector for the CLI.

## Quick Start

```bash
pip install huggingface_hub

# Optional, needed for parquet-based datasets
pip install pyarrow

# See what is available from datasets/
python3 install.py --list

# Install all enabled datasets
python3 install.py --all

# Install one dataset by folder name
python3 install.py --dataset airecon-api-security

# Check installed databases
python3 install.py installed
```

Restart AIRecon after installation so `dataset_search` reloads the new databases.

## Available Datasets

The value passed to `--dataset` is the folder name inside `datasets/`.

| Dataset | Name | Category | Approx Size | Status |
|---|---|---|---|---|
| `airecon-api-security` | AIRecon API Security | `api` | `3,000 entries` | enabled |
| `airecon-network-recon` | AIRecon Network Recon | `network` | `3,000 entries` | enabled |
| `airecon-recon-playbook` | AIRecon Recon Playbook | `recon` | `3,000 entries` | enabled |
| `airecon-web-vuln-patterns` | AIRecon Web Vulnerability Patterns | `web` | `3,000 entries` | enabled |
| `apt-privesc` | APT-Style Privilege Escalation Dataset | `pentest` | `~1,000 entries` | enabled |
| `bug-bounty-pentest` | Bug Bounty & Pentest Methodology | `bug-bounty` | `varies` | enabled |
| `ctf-instruct` | CTF Instruct Dataset | `ctf` | `varies` | enabled |
| `ctf-satml` | CTF SaTML 2024 — Attack/Defense Interactions | `ctf` | `varies` | enabled |
| `cybersecurity-cve` | Cybersecurity LLM CVE Dataset | `vulnerability` | `varies` | enabled |
| `cybersecurity-fenrir` | Cybersecurity Dataset Fenrir v2.0 | `general` | `~83,900 rows` | enabled |
| `cybersecurity-qa` | Trendyol Cybersecurity Instruction Tuning | `general` | `~53,200 rows` | enabled |
| `nuclei-templates` | Nuclei Templates Instruct (Ernest v3) | `pentest` | `varies` | enabled |
| `nvd-security-instructions` | NVD Security Instructions (CVE Analysis) | `vulnerability` | `~2,000 entries` | enabled |
| `pentest-agent-chatml` | Pentest Agent Dataset (ChatML) | `pentest` | `~322,511 rows` | enabled |
| `pentest-books` | Cybersecurity Penetration Testing Books | `pentest` | `varies` | gated |
| `red-team-offensive` | Ultimate Offensive Red Team Dataset | `pentest` | `10K–100K rows` | enabled |
| `sql-injection-qa` | SQL Injection Conversational Q&A | `pentest` | `~10,000 entries` | enabled |
| `stackexchange-re` | StackExchange Reverse Engineering Q&A | `ctf` | `~20,000 entries` | enabled |

`ctf-satml24` is still accepted as a legacy alias, but the canonical name is `ctf-satml`.

## CLI Reference

```text
python3 install.py [OPTIONS] [SUBCOMMAND]

Options:
  --list                         List datasets discovered from datasets/*/meta.json
  --all                          Install all enabled, non-gated datasets
  --dataset DATASET [DATASET ...]
                                 Install one or more datasets by folder name
  --exclude DATASET [DATASET ...]
                                 Skip selected dataset names when used with --all
  --custom FILE                  Index a custom JSONL file
  --no-custom                    Skip automatic indexing of custom/*.jsonl
  --keep-cache                   Keep Hugging Face cache after indexing
  --dry-run                      Preview actions without downloading

Subcommands:
  installed                      Show installed databases with record counts
  remove DATASET [DATASET ...]   Remove installed dataset databases and caches
  clean-cache                    Delete ~/.cache/airecon-dataset/
```

## Examples

```bash
# List datasets from the local datasets/ directory
python3 install.py --list

# Install all enabled datasets except one
python3 install.py --all --exclude ctf-satml

# Install specific datasets by folder name
python3 install.py --dataset airecon-api-security airecon-web-vuln-patterns

# Preview without downloading
python3 install.py --all --dry-run

# Index only a custom JSONL file
python3 install.py --custom custom/example.jsonl

# Remove an installed dataset
python3 install.py remove cybersecurity-fenrir

# Clean download cache
python3 install.py clean-cache
```

If you need gated datasets:

```bash
huggingface-cli login
python3 install.py --dataset pentest-books
```

## AIRecon Integration

After installation, AIRecon can query the local databases through `dataset_search`.

```text
dataset_search: {"query": "GraphQL auth bypass", "limit": 3}
dataset_search: {"query": "nuclei template XSS detection", "category": "pentest"}
dataset_search: {"query": "CVE 2021 44228", "category": "vulnerability"}
dataset_search: {"query": "blind SQL injection boolean"}
```

The search engine uses SQLite FTS5 with the `unicode61` tokenizer over `query`, `answer`, and `context`.

## Custom Datasets

Place `.jsonl` files in `custom/` to have them indexed automatically during installs, or target one file directly with `--custom`.

Example format:

```jsonl
{"query": "How to exploit Apache Struts S2-045?", "answer": "Send a crafted Content-Type header with an OGNL expression."}
{"query": "JWT none algorithm bypass", "answer": "Change alg to none and test whether signature verification is skipped."}
```

Supported fields:

| Field | Required | Notes |
|---|---|---|
| `query` | yes | Searchable prompt or question |
| `answer` | yes | Stored response or solution |
| `context` | no | Extra searchable context |
| `category` | no | Defaults to `custom` |

## Repository Structure

```text
airecon-dataset/
├── install.py
├── datasets/
│   └── <dataset-name>/
│       └── meta.json
└── custom/
    └── *.jsonl

~/.airecon/datasets/
└── *.db

~/.cache/airecon-dataset/
└── <dataset-name>/
```

## Adding a New Dataset

1. Create a folder such as `datasets/my-dataset/`.
2. Add `datasets/my-dataset/meta.json`.
3. Use the folder name with the installer: `python3 install.py --dataset my-dataset`.

Minimal metadata example:

```json
{
  "name": "My Security Dataset",
  "hf_path": "author/repo-name",
  "split": "train",
  "category": "pentest",
  "fields": {
    "query": "instruction",
    "answer": "output"
  },
  "description": "One-line summary of the dataset",
  "size": "varies",
  "enabled": true
}
```

Notes:

- `hf_path` is required.
- The folder name is the canonical CLI selector and output DB name.
- If you need backward compatibility with an older selector, add `"aliases": ["old-name"]`.
- Supported field formats include flat `query`/`answer`, conversation-based datasets via `conversations_field`, and Llama-style text datasets via `text_field`.

## Related

- [AIRecon](https://github.com/pikpikcu/airecon)
- [airecon-skills](https://github.com/pikpikcu/airecon-skills)
