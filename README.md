<h1 align="center">airecon-datasets</h1>
<h4 align="center">Airecon Dataset Installer for <a href="https://github.com/pikpikcu/airecon">AIRecon</a></h4>

<p align="center">
  <img src="https://img.shields.io/badge/AIRecon-compatible-green.svg">
  <img src="https://img.shields.io/badge/datasets-10-blue.svg">
</p>

Local security knowledge base for [AIRecon](https://github.com/pikpikcu/airecon). Downloads datasets from HuggingFace, indexes them into SQLite FTS5 databases, and makes them searchable via AIRecon's `dataset_search` tool — **100% offline** after installation.

> **Privacy-first:** all data stays on your machine. No cloud API calls at query time.

---

## Quick Start

```bash
# Install all enabled datasets (~2.4 GB total)
python install.py

# Check what got installed
python install.py installed
```

Restart AIRecon — the `dataset_search` tool picks up new databases automatically.

---

## Datasets

### Active (installed by default)

| ID | Name | Records | Category | Content |
|----|------|---------|----------|---------|
| `cybersecurity-qa` | Trendyol Cybersecurity Instruction Tuning | 53,199 | general | Attack techniques, defense, tools — broad Q&A pairs |
| `cybersecurity-fenrir` | Cybersecurity Dataset Fenrir v2.0 | 83,918 | general | High-quality attack/defense instruction pairs |
| `cybersecurity-cve` | Cybersecurity LLM CVE Dataset | 124,732 | vulnerability | CVE analysis, exploitation knowledge, patch context |
| `bug-bounty-pentest` | Bug Bounty & Pentest Methodology | 146 | bug-bounty | Techniques, exploitation steps, payloads, bypass methods |
| `ctf-instruct` | CTF Instruct Dataset | 141,182 | ctf | Pwn, web, crypto, forensics, reverse engineering writeups |
| `ctf-satml24` | CTF SaTML 2024 (Attack/Defense) | 190,657 | ctf | Real attack/defense interaction data from SaTML 2024 |
| `red-team-offensive` | Ultimate Offensive Red Team | 78,430 | pentest | Attack chains, privilege escalation, lateral movement |
| `nuclei-templates` | Nuclei Templates Instruct (Ernest v3) | 23,180 | pentest | Nuclei template generation — YAML, matchers, extractors |
| `pentest-agent-chatml` | Pentest Agent Dataset (ChatML) | 322,433 | pentest | CVE-based workflows: enumeration → exploitation → post-ex |
| `nvd-security-instructions` | NVD Security Instructions (CVE Analysis) | 2,063 | vulnerability | Structured CVE instruction-completion pairs from NVD |
| `apt-privesc` | APT-Style Privilege Escalation Dataset | 1,000 | pentest | Linux priv esc techniques with APT tactics and commands |
| `stackexchange-re` | StackExchange Reverse Engineering Q&A | 20,641 | ctf | Binary analysis, disassembly, debugging, malware, CTF RE |
| `sql-injection-qa` | SQL Injection Conversational Q&A | 50,632 | pentest | Conversational SQLi pairs — detection, bypass, exploitation |

**Total: ~1,092,213 records across 13 datasets**

### Gated (requires HuggingFace login)

| ID | Name | Records | Notes |
|----|------|---------|-------|
| `pentest-books` | Cybersecurity Penetration Testing Books | — | Login required: `huggingface-cli login` |

```bash
pip install huggingface_hub
huggingface-cli login
python install.py --include pentest-books
```

---

## Dataset Details

### cybersecurity-qa
General-purpose cybersecurity Q&A from Trendyol. Covers attack techniques (SQLi, XSS, SSRF, LFI), defensive controls, tool usage, and incident response. Good baseline for any security query.

**Sample queries:** `how to exploit SQL injection`, `what is SSRF`, `XSS payload examples`, `explain privilege escalation`

---

### cybersecurity-fenrir
83k high-quality instruction pairs with diverse attack/defense scenarios. Fenrir v2.0 has broader coverage than cybersecurity-qa with more detailed technical answers.

**Sample queries:** `bypass WAF SQL injection`, `enumerate subdomains`, `JWT token attack`, `IDOR vulnerability testing`

---

### cybersecurity-cve
CVE-focused dataset — each entry covers a specific vulnerability: description, impact, CVSS score, exploitation steps, and patch context. Best for looking up specific CVEs or vulnerability classes.

**Sample queries:** `CVE 2021 44228` *(note: use space not dash for FTS5)*, `log4j vulnerability`, `Apache struts deserialization`, `spring4shell exploit`

---

### bug-bounty-pentest
Rich methodology dataset from AYI-NEDJIMI. Covers 7 types of entries: techniques, payloads, bypass methods, exploitation steps, detection evasion, remediation, and full report templates. Small but dense.

**Sample queries:** `SSRF bypass cloud metadata`, `IDOR privilege escalation`, `open redirect exploitation`, `SQL injection WAF bypass`

---

### ctf-instruct
141k CTF challenge instruction pairs from Luoberta. Covers: web exploitation, binary pwn, cryptography (RSA, AES), forensics (PCAP, steganography), and reverse engineering. Useful for understanding CTF-style attack patterns.

**Sample queries:** `buffer overflow exploit`, `RSA CTF attack`, `SQL injection CTF bypass`, `format string vulnerability`

---

### ctf-satml24
190k real interaction pairs from the SaTML 2024 CTF competition (attack/defense format). Actual attacker strategies and defender responses — more realistic than synthetic datasets.

**Sample queries:** `prompt injection attack`, `jailbreak strategy`, `system prompt extraction`, `defense against injection`

---

### red-team-offensive
78k offensive red team instruction pairs. Covers advanced attack techniques: lateral movement, pass-the-hash, Kerberoasting, LDAP enumeration, C2 communication, EDR evasion concepts.

**Sample queries:** `lateral movement techniques`, `pass the hash attack`, `privilege escalation Linux`, `Windows enumeration commands`

---

### nuclei-templates
23k nuclei template generation pairs. Given a vulnerability type or CVE, provides the YAML template — matchers, extractors, paths, headers, and test payloads. Directly useful for AIRecon since nuclei is a core sandbox tool.

**Sample queries:** `nuclei template XSS detection`, `nuclei CVE template`, `nuclei SSRF template`, `nuclei exposed admin panel`

---

### pentest-agent-chatml
322k CVE-based pentesting workflows in ChatML format. Each conversation covers: reconnaissance (nmap, httpx), vulnerability identification, exploitation chain, and post-exploitation steps. Sourced from MITRE ATT&CK, NVD, and ExploitDB.

**Sample queries:** `nmap enumeration workflow`, `CVE 2022 33915 exploit`, `privilege escalation after RCE`, `post exploitation persistence`

---

### nvd-security-instructions
2k structured instruction-completion pairs built from the NIST National Vulnerability Database. Each entry pairs a CVE-specific question with a structured analysis: severity, affected systems, attack vector, impact, and remediation steps.

**Sample queries:** `CVE 2023 remote code execution`, `Apache vulnerability severity analysis`, `authentication bypass NVD`, `deserialization CVE remediation`

---

### apt-privesc
1k Linux privilege escalation techniques modeled on APT (Advanced Persistent Threat) tradecraft. Each entry maps a technique description to its exact shell command, MITRE tactics classification, and category (kernel exploit, SUID abuse, cron job, etc.).

**Sample queries:** `SUID binary privilege escalation`, `cron job writable escalation`, `kernel exploit Linux`, `sudo misconfiguration privilege`

---

### stackexchange-re
20k reverse engineering Q&A sourced from StackExchange. Covers: x86/x64 disassembly, PE/ELF format analysis, GDB/radare2/Ghidra usage, dynamic analysis, anti-debug bypass, malware unpacking, and CTF reverse engineering challenges.

**Sample queries:** `radare2 disassembly commands`, `ELF binary analysis`, `anti debug techniques bypass`, `malware unpacking PE`

---

### sql-injection-qa
10k conversational SQL injection Q&A pairs. Covers all major SQLi types: error-based, blind (time/boolean), union-based, out-of-band, second-order, and NoSQL injection. Includes WAF bypass, filter evasion, and modern database-specific techniques.

**Sample queries:** `blind SQL injection boolean`, `SQL injection WAF bypass`, `time based SQL injection`, `union select injection attack`

---

## CLI Reference

```
python install.py [OPTIONS] [SUBCOMMAND]

Options:
  --include ID [ID ...]   Install only these dataset IDs
  --exclude ID [ID ...]   Skip these dataset IDs
  --keep-cache            Keep HuggingFace download cache after indexing
  --dry-run               Show what would happen, no downloads
  --list                  List all datasets from manifest.json

Subcommands:
  installed               Show installed databases with record counts and sizes
  remove ID [ID ...]      Remove installed dataset(s)
  clean-cache             Delete the download cache (~/.cache/airecon-dataset/)
```

### Examples

```bash
# See what's available
python install.py --list

# Dry run — preview without downloading
python install.py --dry-run

# Install only specific datasets
python install.py --include nuclei-templates red-team-offensive apt-privesc

# Skip large CTF datasets
python install.py --exclude ctf-instruct ctf-satml24

# Install new additions only
python install.py --include nvd-security-instructions apt-privesc stackexchange-re sql-injection-qa

# Install and keep download cache
python install.py --keep-cache

# Remove a dataset
python install.py remove cybersecurity-fenrir

# Clean download cache
python install.py clean-cache
```

---

## AIRecon Integration

After installation, the AIRecon agent uses `dataset_search` automatically when it needs reference knowledge. You can also query it directly:

```
dataset_search: {"query": "log4j RCE exploitation", "limit": 3}
dataset_search: {"query": "SSRF bypass cloud metadata", "category": "bug-bounty"}
dataset_search: {"query": "nuclei template XSS detection"}
dataset_search: {"query": "CVE 2021 44228", "category": "vulnerability"}
```

### FTS5 Query Tips

The search uses SQLite FTS5. A few things to know:

| Input | What to do |
|-------|-----------|
| `CVE-2021-44228` | Use spaces: `CVE 2021 44228` |
| `<script>alert(1)</script>` | Use plain words: `XSS script alert` |
| Phrase search | Just type normally: `SQL injection WAF bypass` |
| Category filter | Add `"category": "bug-bounty"` or `"ctf"` or `"pentest"` |

The handler automatically strips FTS5 operator characters before querying, so special chars in CVEs, payloads, and tags are safe.

---

## Custom Datasets

Drop `.jsonl` files into the `custom/` directory — they're indexed automatically:

```jsonl
{"query": "How to exploit Apache Struts S2-045?", "answer": "Send Content-Type header with OGNL expression..."}
{"query": "JWT none algorithm bypass", "answer": "Change alg to 'none', remove the signature..."}
```

Required fields: `query`, `answer`. Optional: `context`, `category`.

---

## Architecture

```
airecon-dataset/
├── install.py          # Dataset downloader and indexer
├── manifest.json       # Dataset registry (hf_path, fields, enabled)
├── datasets/           # Per-dataset metadata
│   └── <id>/meta.json
└── custom/             # Your own .jsonl files

~/.airecon/datasets/    # Installed SQLite FTS5 databases (gitignored)
│   ├── cybersecurity-qa.db
│   ├── bug-bounty-pentest.db
│   └── ...

~/.cache/airecon-dataset/  # HF download cache (auto-deleted after indexing)
```

Each `.db` uses SQLite FTS5 with `unicode61` tokenizer over `query + answer + context`. The `dataset_search` tool fans out across all installed databases, deduplicates by full query string, truncates answers to 500 chars, and returns top results ranked by FTS5 relevance score.

---

## Adding a New Dataset

1. Add entry to `manifest.json`:

```json
{
  "id": "my-dataset",
  "name": "My Security Dataset",
  "hf_path": "author/repo-name",
  "split": "train",
  "category": "pentest",
  "fields": {"query": "instruction", "answer": "output"},
  "license": "mit",
  "description": "One-line description",
  "enabled": true
}
```

2. Create `datasets/my-dataset/meta.json` with full metadata (see any existing `meta.json` as template).

3. Run: `python install.py --include my-dataset`

**Supported field formats:**

| Format | Config |
|--------|--------|
| Flat key-value | `{"query": "instruction", "answer": "output", "context": "input"}` |
| ChatML conversations | `{"conversations_field": "messages"}` (expects `role`/`content`) |
| Custom conversations | `{"conversations_field": "conversations"}` (expects `value`/`content`) |

---

## Related

- [AIRecon](https://github.com/pikpikcu/airecon) — the main agent
- [airecon-skills](https://github.com/pikpikcu/airecon-skills) — skill files for domain-specific knowledge
