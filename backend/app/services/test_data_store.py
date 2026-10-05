from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List

_DATA_LOCK = RLock()
_DATA_CACHE: Dict[str, Any] = {}

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
TEST_DATA_FILE = DATA_DIR / "test_data.json"
TEST_DATA_DEFAULT_FILE = DATA_DIR / "test_data.default.json"

LIST_DATASETS = {
    "campaign_contacts",
    "campaign_templates",
    "campaign_lists",
    "campaign_items",
    "portal_items",
    "carrier_items",
    "day_report_rows",
    "job_results",
    "linkedin_jobs",
    "applications",
    "submission_months",
}


def _read_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        content = json.load(handle)
    if not isinstance(content, dict):
        raise ValueError("Test data file must contain a top-level JSON object.")
    return content


def _write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")
    temp_path.replace(path)


def _ensure_cache_loaded() -> None:
    global _DATA_CACHE
    if _DATA_CACHE:
        return
    if not TEST_DATA_FILE.exists() and TEST_DATA_DEFAULT_FILE.exists():
        default_payload = _read_json_file(TEST_DATA_DEFAULT_FILE)
        _write_json_file(TEST_DATA_FILE, default_payload)
    _DATA_CACHE = _read_json_file(TEST_DATA_FILE)


def get_test_data() -> Dict[str, Any]:
    with _DATA_LOCK:
        _ensure_cache_loaded()
        return _DATA_CACHE


def get_test_data_snapshot() -> Dict[str, Any]:
    with _DATA_LOCK:
        _ensure_cache_loaded()
        return deepcopy(_DATA_CACHE)


def save_test_data() -> None:
    with _DATA_LOCK:
        _ensure_cache_loaded()
        _write_json_file(TEST_DATA_FILE, _DATA_CACHE)


def reset_test_data() -> Dict[str, Any]:
    global _DATA_CACHE
    with _DATA_LOCK:
        baseline = _read_json_file(TEST_DATA_DEFAULT_FILE)
        _DATA_CACHE = baseline
        _write_json_file(TEST_DATA_FILE, _DATA_CACHE)
        return deepcopy(_DATA_CACHE)


def append_test_data(dataset: str, entries: List[Dict[str, Any]]) -> int:
    with _DATA_LOCK:
        _ensure_cache_loaded()
        if dataset not in LIST_DATASETS:
            raise ValueError(f"Dataset '{dataset}' is not appendable.")

        target = _DATA_CACHE.get(dataset)
        if not isinstance(target, list):
            raise ValueError(f"Dataset '{dataset}' is not list-based.")

        target.extend(entries)
        _write_json_file(TEST_DATA_FILE, _DATA_CACHE)
        return len(target)
