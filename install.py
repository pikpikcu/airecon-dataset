#!/usr/bin/env python3
"""AIRecon Dataset Installer — downloads HuggingFace datasets and indexes to ~/.airecon/datasets/"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sqlite3
import sys
from pathlib import Path
from typing import Iterator

DATASETS_DIR = Path(__file__).parent / "datasets"
CUSTOM_DIR = Path(__file__).parent / "custom"

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("airecon-dataset")


def info(msg: str) -> None:
    print(f"{CYAN}[INFO]{NC}  {msg}")


def ok(msg: str) -> None:
    print(f"{GREEN}[OK]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC}  {msg}")


def err(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}", file=sys.stderr)


def _get_install_dir() -> Path:
    d = Path.home() / ".airecon" / "datasets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_cache_dir() -> Path:
    d = Path.home() / ".cache" / "airecon-dataset"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _check_deps() -> bool:
    missing = []
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        missing.append("huggingface_hub")
    if missing:
        err(f"Missing dependencies: {', '.join(missing)}")
        err(f"Install with: pip install {' '.join(missing)}")
        return False
    return True


def _load_all_metas() -> list[dict]:
    """Load all meta.json files from datasets/*/meta.json, sorted by folder name."""
    metas = []
    if not DATASETS_DIR.exists():
        err(f"datasets/ directory not found: {DATASETS_DIR}")
        return metas
    for meta_file in sorted(DATASETS_DIR.glob("*/meta.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            dataset_name = meta_file.parent.name
            if "hf_path" not in meta:
                warn(f"Skipping {meta_file} — missing required field (hf_path)")
                continue
            aliases: list[str] = []
            legacy_id = str(meta.get("id") or "").strip()
            if legacy_id and legacy_id != dataset_name:
                aliases.append(legacy_id)
            for alias in meta.get("aliases", []):
                alias = str(alias).strip()
                if alias and alias != dataset_name and alias not in aliases:
                    aliases.append(alias)
            meta["aliases"] = aliases
            meta["id"] = dataset_name
            metas.append(meta)
        except Exception as e:
            warn(f"Failed to read {meta_file}: {e}")
    return metas


def _dataset_lookup(metas: list[dict]) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for meta in metas:
        for name in [meta["id"], *meta.get("aliases", [])]:
            existing = lookup.get(name)
            if existing and existing["id"] != meta["id"]:
                warn(f"Duplicate dataset selector '{name}' in datasets/")
                continue
            lookup[name] = meta
    return lookup


def _resolve_dataset_names(names: list[str], metas: list[dict], option_name: str) -> list[dict]:
    lookup = _dataset_lookup(metas)
    resolved: list[dict] = []
    seen: set[str] = set()
    for name in names:
        meta = lookup.get(name)
        if not meta:
            err(f"Dataset not found for {option_name}: '{name}' — run --list to see folders in datasets/")
            sys.exit(1)
        if name in meta.get("aliases", []):
            warn(f"{option_name}: '{name}' is a legacy alias, using '{meta['id']}'")
        if meta["id"] in seen:
            continue
        resolved.append(meta)
        seen.add(meta["id"])
    return resolved


def _db_paths(install_dir: Path, dataset_id: str) -> tuple[Path, Path]:
    final_db = install_dir / f"{dataset_id}.db"
    temp_db = install_dir / f".{dataset_id}.tmp.db"
    if temp_db.exists():
        temp_db.unlink()
    return final_db, temp_db


def _remove_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def _cleanup_legacy_alias_artifacts(meta: dict, install_dir: Path) -> None:
    cache_dir = _get_cache_dir()
    for alias in meta.get("aliases", []):
        legacy_db = install_dir / f"{alias}.db"
        if legacy_db.exists():
            legacy_db.unlink()
            info(f"Removed legacy database alias: {legacy_db.name}")
        legacy_cache = cache_dir / alias
        if legacy_cache.exists():
            shutil.rmtree(legacy_cache, ignore_errors=True)
            info(f"Removed legacy cache alias: {legacy_cache}")


# ── SQLite FTS builder ───────────────────────────────────────────────────────

def _build_db(db_path: Path) -> tuple[sqlite3.Connection, sqlite3.Cursor]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS records (
            id       INTEGER PRIMARY KEY,
            query    TEXT NOT NULL,
            answer   TEXT NOT NULL,
            context  TEXT DEFAULT '',
            category TEXT DEFAULT '',
            source   TEXT DEFAULT ''
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS records_fts USING fts5(
            query, answer, context,
            content='records',
            content_rowid='id',
            tokenize='unicode61'
        );
        CREATE TRIGGER IF NOT EXISTS records_ai AFTER INSERT ON records BEGIN
            INSERT INTO records_fts(rowid, query, answer, context)
            VALUES (new.id, new.query, new.answer, new.context);
        END;
    """)
    con.commit()
    return con, cur


# ── File readers ─────────────────────────────────────────────────────────────

def _iter_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row
            except json.JSONDecodeError:
                continue


def _iter_json(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8", errors="replace") as f:
        first_line = ""
        for line in f:
            stripped = line.strip()
            if stripped:
                first_line = stripped
                break

    if first_line.startswith("{"):
        try:
            json.loads(first_line)
            yield from _iter_jsonl(path)
            return
        except json.JSONDecodeError:
            pass

    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            data = json.load(f)
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    yield row
        elif isinstance(data, dict):
            yield data
    except Exception as e:
        logger.debug("Failed to parse %s: %s", path, e)


def _iter_parquet(path: Path) -> Iterator[dict]:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        logger.warning("pyarrow not installed — skipping %s (run: pip install pyarrow)", path.name)
        return
    try:
        table = pq.read_table(path)
        for row in table.to_pylist():
            if isinstance(row, dict):
                yield row
    except Exception as e:
        logger.debug("Failed to read parquet %s: %s", path, e)


def _iter_file(path: Path) -> Iterator[dict]:
    if path.suffix == ".jsonl":
        yield from _iter_jsonl(path)
    elif path.suffix == ".json":
        yield from _iter_json(path)
    elif path.suffix == ".parquet":
        yield from _iter_parquet(path)


# ── File finder ──────────────────────────────────────────────────────────────

_SKIP_STEMS = {
    "readme", "gitattributes", "message_counts", "teams", "valid_ids",
    "dqed_ids", "filtered_defense", "defense_submission", "valid_defense",
    "secret_guess", "secret", "defense",
}


def _find_data_files(local_dir: Path, dataset_id: str) -> list[Path]:
    """Find indexable data files, skip meta/config files and hidden dirs."""
    if dataset_id == "ctf-satml":
        full = local_dir / "chat.json"
        if full.exists():
            return [full]
        sample = local_dir / "chat.50.json"
        if sample.exists():
            return [sample]

    result = []
    for suffix in ("*.jsonl", "*.json", "*.parquet"):
        for f in sorted(local_dir.rglob(suffix)):
            if any(part.startswith(".") for part in f.relative_to(local_dir).parts[:-1]):
                continue
            if f.stem.lower().rstrip(".") in _SKIP_STEMS:
                continue
            result.append(f)

    return result


# ── Row extractors ───────────────────────────────────────────────────────────

def _val(row: dict, key: str | None) -> str:
    if not key or key not in row:
        return ""
    v = row[key]
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return " ".join(str(x) for x in v).strip()
    return str(v).strip() if v is not None else ""


def _build_extra(row: dict, extra_fields: list[str]) -> str:
    parts = []
    for f in extra_fields:
        v = row.get(f)
        if not v:
            continue
        if isinstance(v, list):
            v = "\n".join(str(x) for x in v)
        parts.append(f"{f}: {v}")
    return "\n".join(parts)


def _rows_standard(row: dict, fields: dict) -> list[tuple[str, str, str]]:
    query = _val(row, fields.get("query"))
    answer = _val(row, fields.get("answer"))
    context = _val(row, fields.get("context"))
    extra = _build_extra(row, fields.get("extra_fields", []))
    if extra:
        context = f"{context}\n{extra}".strip() if context else extra
    if query and answer:
        return [(query, answer, context)]
    return []


def _rows_conversations(row: dict, conv_field: str) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    convs = row.get(conv_field, [])
    if not isinstance(convs, list):
        return pairs
    i = 0
    while i < len(convs) - 1:
        h, a = convs[i], convs[i + 1]
        hv = (h.get("value") or h.get("content") or "") if isinstance(h, dict) else str(h)
        av = (a.get("value") or a.get("content") or "") if isinstance(a, dict) else str(a)
        if hv.strip() and av.strip() and len(hv.strip()) > 10:
            pairs.append((hv.strip(), av.strip(), ""))
        i += 2
    return pairs


def _rows_satml(row: dict) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    history = row.get("history", [])
    if not isinstance(history, list):
        return pairs
    defense_prompt = ""
    defense = row.get("defense", {})
    if isinstance(defense, dict):
        defense_prompt = str(defense.get("prompt") or "").strip()[:500]
    i = 0
    while i < len(history) - 1:
        tu, ta = history[i], history[i + 1]
        if not (isinstance(tu, dict) and isinstance(ta, dict)):
            i += 1
            continue
        if tu.get("role") != "user" or ta.get("role") != "assistant":
            i += 1
            continue
        q = str(tu.get("content") or "").strip()
        a = str(ta.get("content") or "").strip()
        if len(q) >= 20 and len(a) >= 20:
            pairs.append((q, a, defense_prompt))
        i += 2
    return pairs


def _list_to_str(v: object, bullet: str = "- ") -> str:
    if isinstance(v, list):
        return "\n".join(f"{bullet}{x}" for x in v if x)
    return str(v).strip() if v else ""


def _rows_bug_bounty(row: dict) -> list[tuple[str, str, str]]:
    row_type = row.get("type", "")
    parts: list[str] = []
    query = ""
    ctx = ""

    if row_type == "qa":
        q = str(row.get("question") or "").strip()
        a = str(row.get("answer") or "").strip()
        if q and a:
            return [(q, a, str(row.get("category", "")))]

    elif row_type == "technique":
        name = row.get("technique_name", "")
        query = f"How to exploit {name}? Provide exploitation steps, payloads, and WAF bypass."
        if row.get("description"):
            parts.append(f"Description: {row['description']}")
        if row.get("exploitation_steps"):
            parts.append(f"Exploitation Steps:\n{_list_to_str(row['exploitation_steps'], '  1. ')}")
        if row.get("payload_examples"):
            parts.append(f"Payload Examples:\n{_list_to_str(row['payload_examples'])}")
        if row.get("detection_bypass"):
            parts.append(f"Detection/WAF Bypass:\n{_list_to_str(row['detection_bypass'])}")
        if row.get("remediation"):
            parts.append(f"Remediation: {row['remediation']}")
        ctx = f"category:{row.get('category','')} cvss:{row.get('cvss_range','')} bounty:{row.get('bounty_range_usd','')}"

    elif row_type == "report_template":
        vuln = row.get("vulnerability_type", "")
        query = f"How to write a bug bounty report for {vuln}?"
        if row.get("title_template"):
            parts.append(f"Title: {row['title_template']}")
        if row.get("description_template"):
            parts.append(f"Description: {row['description_template']}")
        if row.get("steps_to_reproduce"):
            parts.append(f"Steps to Reproduce:\n{_list_to_str(row['steps_to_reproduce'], '  - ')}")
        if row.get("impact_description"):
            parts.append(f"Impact: {row['impact_description']}")
        if row.get("severity_justification"):
            parts.append(f"Severity: {row['severity_justification']}")
        if row.get("remediation_suggestion"):
            parts.append(f"Remediation: {row['remediation_suggestion']}")
        ctx = "report_template"

    elif row_type == "checklist":
        name = row.get("checklist_name", "")
        query = f"What are the security testing checklist items for {name}?"
        if row.get("items"):
            parts.append(_list_to_str(row["items"]))
        ctx = f"target:{row.get('target_type','')}"

    elif row_type == "methodology":
        name = row.get("methodology_name", "")
        query = f"Explain the {name} penetration testing methodology."
        if row.get("description"):
            parts.append(f"Description: {row['description']}")
        if row.get("phases"):
            parts.append(f"Phases:\n{_list_to_str(row['phases'])}")
        if row.get("scope"):
            parts.append(f"Scope: {row['scope']}")
        if row.get("deliverables"):
            parts.append(f"Deliverables: {_list_to_str(row['deliverables'])}")
        ctx = f"org:{row.get('organization','')}"

    elif row_type == "tool":
        name = row.get("name", "")
        query = f"How to use {name} for security testing? What are the flags and examples?"
        if row.get("description"):
            parts.append(f"Description: {row['description']}")
        if row.get("usage_examples"):
            parts.append(f"Usage Examples:\n{_list_to_str(row['usage_examples'])}")
        if row.get("flags_important"):
            parts.append(f"Important Flags:\n{_list_to_str(row['flags_important'])}")
        ctx = f"category:{row.get('category','')}"

    elif row_type == "platform":
        name = row.get("platform_name", "")
        query = f"What are the top programs and features of {name} bug bounty platform?"
        if row.get("description"):
            parts.append(f"Description: {row['description']}")
        if row.get("features"):
            parts.append(f"Features:\n{_list_to_str(row['features'])}")
        if row.get("top_programs"):
            parts.append(f"Top Programs:\n{_list_to_str(row['top_programs'])}")
        if row.get("average_bounty_range"):
            parts.append(f"Average Bounty: {row['average_bounty_range']}")
        ctx = f"payout:{row.get('payout_model','')}"

    answer = "\n\n".join(parts)
    if query and answer:
        return [(query, answer, ctx)]
    return []


def _rows_llama_text(row: dict, text_field: str = "text") -> list[tuple[str, str, str]]:
    text = str(row.get(text_field) or "").strip()
    if not text:
        return []
    sep = "[/INST]"
    idx = text.find(sep)
    if idx == -1:
        return []
    inst = text[:idx].strip()
    resp = text[idx + len(sep):].strip()
    inst = inst.replace("<s>", "").replace("[INST]", "").strip()
    resp = resp.replace("</s>", "").strip()
    if len(inst) < 20 or len(resp) < 20:
        return []
    return [(inst, resp, "")]


def _extract_rows(row: dict, meta: dict) -> list[tuple[str, str, str]]:
    dataset_id = meta.get("id", "")
    fields = meta.get("fields", {})

    if dataset_id == "ctf-satml":
        return _rows_satml(row)
    if dataset_id == "bug-bounty-pentest":
        return _rows_bug_bounty(row)
    if dataset_id == "nvd-security-instructions":
        return _rows_llama_text(row, fields.get("text_field", "text"))

    conv_field = fields.get("conversations_field")
    if conv_field:
        return _rows_conversations(row, conv_field)

    return _rows_standard(row, fields)


# ── Download + index ─────────────────────────────────────────────────────────

_STANDARD_SPLITS = {"train", "test", "validation", "default"}


def _download_and_index(meta: dict, install_dir: Path, keep_cache: bool = False, dry_run: bool = False) -> bool:
    from huggingface_hub import snapshot_download

    dataset_id = meta["id"]
    hf_path = meta["hf_path"]
    category = meta.get("category", "general")
    cache_dir = _get_cache_dir() / dataset_id
    final_db, temp_db = _db_paths(install_dir, dataset_id)

    info(f"Downloading {dataset_id} ({hf_path}) ...")

    if dry_run:
        ok(f"[dry-run] Would download and index {dataset_id}")
        return True

    try:
        local_dir = Path(snapshot_download(
            repo_id=hf_path,
            repo_type="dataset",
            local_dir=str(cache_dir),
            ignore_patterns=["*.zip", "*.tar.gz", "*.bin", "*.png", "*.jpg", "*.jpeg"],
        ))
    except Exception as e:
        err(f"Failed to download {dataset_id}: {e}")
        return False

    data_files = _find_data_files(local_dir, dataset_id)
    if not data_files:
        warn(f"No indexable files found for {dataset_id}")
        warn(f"  Cache dir: {local_dir}")
        return False

    # Filter to config-specific subdirectory when split is a config name (not a standard HF split).
    split = meta.get("split", "train")
    if split not in _STANDARD_SPLITS:
        filtered = [f for f in data_files if split in f.parts]
        if filtered:
            data_files = filtered

    info(f"Indexing {len(data_files)} file(s): {[f.name for f in data_files]}")
    con: sqlite3.Connection | None = None
    total = 0
    try:
        con, cur = _build_db(temp_db)
        batch: list[tuple] = []

        for data_file in data_files:
            file_rows = 0
            for row in _iter_file(data_file):
                for query, answer, context in _extract_rows(row, meta):
                    if not query or not answer:
                        continue
                    batch.append((query[:2000], answer[:4000], context[:1000], category, dataset_id))
                    file_rows += 1
                    if len(batch) >= 1000:
                        cur.executemany(
                            "INSERT INTO records (query,answer,context,category,source) VALUES (?,?,?,?,?)",
                            batch,
                        )
                        con.commit()
                        total += len(batch)
                        batch.clear()
            logger.debug("  %s: %d rows", data_file.name, file_rows)

        if batch:
            cur.executemany(
                "INSERT INTO records (query,answer,context,category,source) VALUES (?,?,?,?,?)",
                batch,
            )
            con.commit()
            total += len(batch)
    except Exception as e:
        if con is not None:
            con.close()
        _remove_file(temp_db)
        err(f"Failed to index {dataset_id}: {e}")
        return False
    else:
        if con is not None:
            con.close()

    if total == 0:
        _remove_file(temp_db)
        warn(f"No records indexed for {dataset_id} — check fields in meta.json")
        return False

    try:
        temp_db.replace(final_db)
    except Exception as e:
        _remove_file(temp_db)
        err(f"Failed to finalize database for {dataset_id}: {e}")
        return False

    ok(f"Indexed {total:,} records → {final_db}")
    _cleanup_legacy_alias_artifacts(meta, install_dir)

    if not keep_cache and cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)
        info(f"Cache cleaned: {cache_dir}")

    return True


# ── Custom data ──────────────────────────────────────────────────────────────

def _install_custom(install_dir: Path, custom_path: Path | None, dry_run: bool) -> list[str]:
    paths: list[Path] = []
    if custom_path:
        paths = [Path(custom_path)]
    elif CUSTOM_DIR.exists():
        paths = [p for p in CUSTOM_DIR.glob("*.jsonl") if p.stem != "example"]

    failed: list[str] = []
    for p in paths:
        if not p.exists():
            err(f"Custom file not found: {p}")
            failed.append(str(p))
            continue

        dataset_id = f"custom-{p.stem}"
        final_db, temp_db = _db_paths(install_dir, dataset_id)
        info(f"Indexing custom: {p.name}")

        if dry_run:
            ok(f"[dry-run] Would index {p.name}")
            continue

        con: sqlite3.Connection | None = None
        total = 0
        try:
            con, cur = _build_db(temp_db)
            for row in _iter_jsonl(p):
                query = str(row.get("query", row.get("instruction", row.get("question", "")))).strip()
                answer = str(row.get("answer", row.get("output", row.get("response", "")))).strip()
                context = str(row.get("context", row.get("system", ""))).strip()
                category = str(row.get("category", "custom"))
                if query and answer:
                    cur.execute(
                        "INSERT INTO records (query,answer,context,category,source) VALUES (?,?,?,?,?)",
                        (query[:2000], answer[:4000], context[:1000], category, f"custom:{p.name}"),
                    )
                    total += 1
            con.commit()
        except Exception as e:
            if con is not None:
                con.close()
            _remove_file(temp_db)
            err(f"Failed to index custom file {p}: {e}")
            failed.append(str(p))
            continue
        else:
            if con is not None:
                con.close()

        if total == 0:
            _remove_file(temp_db)
            warn(f"No custom records indexed for {p.name}")
            failed.append(str(p))
            continue

        try:
            temp_db.replace(final_db)
        except Exception as e:
            _remove_file(temp_db)
            err(f"Failed to finalize custom database for {p.name}: {e}")
            failed.append(str(p))
            continue

        ok(f"Indexed {total:,} custom records → {final_db}")

    return failed


# ── CLI commands ─────────────────────────────────────────────────────────────

def cmd_list(metas: list[dict]) -> None:
    if not metas:
        warn("No datasets found in datasets/ — check the directory.")
        return

    print(f"\n  {BOLD}Available Datasets{NC}  ({len(metas)} total)\n")
    print(f"  {'Dataset':<32} {'Category':<14} {'Size':<16} {'Status'}")
    print("  " + "─" * 80)
    for m in metas:
        if m.get("gated"):
            status = f"{YELLOW}gated{NC} (huggingface-cli login)"
        elif not m.get("enabled", True):
            status = f"{YELLOW}disabled{NC}"
        else:
            status = f"{GREEN}enabled{NC}"
        size = m.get("size", "—")
        print(f"  {m['id']:<32} {m.get('category',''):<14} {size:<16} {status}")
    aliased = [m for m in metas if m.get("aliases")]
    if aliased:
        print()
        print(f"  {BOLD}Legacy Aliases{NC}")
        for m in aliased:
            print(f"  {m['id']:<32} {', '.join(m['aliases'])}")
    print()
    print(f"  Install all :  python3 install.py --all")
    print(f"  Install one :  python3 install.py --dataset <dataset-name>")
    print()


def cmd_install(args: argparse.Namespace) -> int:
    needs_hf_download = bool((args.all or args.dataset) and not args.dry_run)
    if needs_hf_download and not _check_deps():
        return 1

    install_dir = _get_install_dir()
    metas: list[dict] = []
    exclude: set[str] = set()

    if args.all or args.dataset or args.exclude:
        metas = _load_all_metas()
        if not metas:
            err("No datasets found. Check that datasets/ directory contains meta.json files.")
            return 1
        if args.exclude:
            exclude = {m["id"] for m in _resolve_dataset_names(args.exclude, metas, "--exclude")}

    # Build selected list
    selected: list[dict] = []

    if args.dataset:
        # --dataset: install specific dataset folder names (can force even if disabled)
        for m in _resolve_dataset_names(args.dataset, metas, "--dataset"):
            if m.get("gated"):
                warn(f"Skipping {m['id']} — gated: {m.get('gated_note', 'requires huggingface-cli login')}")
                continue
            selected.append(m)

    elif args.all:
        # --all: install all enabled, non-gated datasets
        for m in metas:
            if m["id"] in exclude:
                continue
            if m.get("gated"):
                warn(f"Skipping {m['id']} — gated (requires: huggingface-cli login)")
                continue
            if not m.get("enabled", True):
                warn(f"Skipping {m['id']} — disabled (use --dataset {m['id']} to force)")
                continue
            selected.append(m)
    elif args.custom:
        selected = []
    else:
        err("No action specified. Use --all, --dataset <dataset-name>, --custom <file>, or --list.")
        err("Run: python3 install.py --help")
        return 1

    if not selected and not args.custom:
        warn("No datasets selected.")
        return 0

    print()
    print(f"  {BOLD}AIRecon Dataset Installer{NC}")
    print(f"  Install dir : {install_dir}")
    print(f"  Cache dir   : {_get_cache_dir()}")
    print(f"  Datasets    : {len(selected)} selected")
    print(f"  Keep cache  : {args.keep_cache}")
    print()

    failed = []
    for meta in selected:
        success = _download_and_index(
            meta, install_dir,
            keep_cache=args.keep_cache,
            dry_run=args.dry_run,
        )
        if not success:
            failed.append(meta["id"])

    custom_failed: list[str] = []
    if args.custom:
        custom_failed = _install_custom(install_dir, Path(args.custom), dry_run=args.dry_run)
    elif not args.no_custom:
        custom_failed = _install_custom(install_dir, None, dry_run=args.dry_run)

    print()
    if failed:
        warn(f"Failed: {', '.join(failed)}")
    if custom_failed:
        warn(f"Custom failed: {', '.join(custom_failed)}")
    if failed or custom_failed:
        err("Installation finished with errors.")
        return 1
    ok(f"Done → {install_dir}")
    info("Restart AIRecon to activate dataset_search tool.")
    return 0


def cmd_installed(args: argparse.Namespace) -> None:
    install_dir = _get_install_dir()
    dbs = sorted(install_dir.glob("*.db"))
    if not dbs:
        info("No datasets installed yet. Run: python3 install.py --all")
        return

    metas = _load_all_metas()
    lookup = _dataset_lookup(metas)

    print(f"\n  {BOLD}Installed Datasets{NC}\n")
    print(f"  {'Dataset':<32} {'Records':>10}  {'Size':>8}  Path")
    print("  " + "─" * 80)
    for db in dbs:
        label = db.stem
        meta = lookup.get(db.stem)
        if meta and db.stem in meta.get("aliases", []):
            label = f"{meta['id']} [legacy alias]"
        try:
            con = sqlite3.connect(db)
            count = con.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            con.close()
            size_mb = db.stat().st_size / 1024 / 1024
            print(f"  {label:<32} {count:>10,}  {size_mb:>6.1f}MB  {db}")
        except Exception:
            print(f"  {label:<32} {'(error)':>10}")
    print()


def cmd_remove(args: argparse.Namespace) -> None:
    install_dir = _get_install_dir()
    cache_dir = _get_cache_dir()
    metas = _load_all_metas()
    lookup = _dataset_lookup(metas)
    for dataset_name in args.datasets:
        meta = lookup.get(dataset_name)
        candidate_names = [dataset_name]
        if meta:
            candidate_names = [meta["id"], *meta.get("aliases", [])]
        removed = False
        seen: set[str] = set()
        for candidate in candidate_names:
            if candidate in seen:
                continue
            seen.add(candidate)
            db = install_dir / f"{candidate}.db"
            if db.exists():
                db.unlink()
                ok(f"Removed {candidate}.db")
                removed = True
            cache = cache_dir / candidate
            if cache.exists():
                shutil.rmtree(cache, ignore_errors=True)
                ok(f"Removed cache: {cache}")
                removed = True
        if not removed:
            warn(f"Not found: {dataset_name}")


def cmd_clean_cache(args: argparse.Namespace) -> None:
    cache_dir = _get_cache_dir()
    if not cache_dir.exists():
        info("Cache is already empty.")
        return
    size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
    shutil.rmtree(cache_dir, ignore_errors=True)
    ok(f"Cleaned cache ({size / 1024 / 1024:.1f} MB freed): {cache_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AIRecon Dataset Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 install.py --list                           List all available datasets
  python3 install.py --all                            Install all enabled datasets
  python3 install.py --dataset airecon-api-security   Install one dataset
  python3 install.py --dataset ctf-instruct red-team-offensive  Install multiple
  python3 install.py --all --exclude ctf-satml        Install all except specific
  python3 install.py --all --keep-cache               Install and keep download cache
  python3 install.py --all --dry-run                  Preview without downloading
  python3 install.py --custom mydata.jsonl            Index a custom JSONL file
  python3 install.py installed                        Show installed datasets
  python3 install.py remove ctf-instruct              Remove an installed dataset
  python3 install.py clean-cache                      Delete all download caches
        """,
    )
    sub = parser.add_subparsers(dest="cmd")

    # Main flags
    parser.add_argument("--list",    action="store_true", help="List all available datasets from datasets/")
    parser.add_argument("--all",     action="store_true", help="Install all enabled datasets")
    parser.add_argument("--dataset", nargs="+", metavar="DATASET", help="Install specific dataset folder(s) from datasets/")
    parser.add_argument("--exclude", nargs="+", metavar="DATASET", help="Skip these dataset folder names (use with --all)")
    parser.add_argument("--custom",  metavar="FILE", help="Custom JSONL file to index")
    parser.add_argument("--no-custom", action="store_true", help="Skip custom/ directory")
    parser.add_argument("--keep-cache", action="store_true", help="Keep download cache after indexing")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading")

    # Subcommands
    sub.add_parser("installed",   help="List installed datasets with record counts")
    rm = sub.add_parser("remove", help="Remove installed dataset(s)")
    rm.add_argument("datasets", nargs="+", metavar="DATASET")
    sub.add_parser("clean-cache", help="Delete all download caches")

    args = parser.parse_args()

    if args.cmd == "installed":
        cmd_installed(args)
    elif args.cmd == "remove":
        cmd_remove(args)
    elif args.cmd == "clean-cache":
        cmd_clean_cache(args)
    elif args.list:
        cmd_list(_load_all_metas())
    else:
        sys.exit(cmd_install(args))


if __name__ == "__main__":
    main()
