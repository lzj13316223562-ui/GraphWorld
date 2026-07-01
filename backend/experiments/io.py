from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from tqdm import tqdm

def write_json_array(path: Path, rows: list[dict[str, Any]], *, desc: str) -> None:
    with path.open("w", encoding="utf-8") as handle:
        handle.write("[\n")
        for index, row in enumerate(tqdm(rows, desc=desc, unit="row", dynamic_ncols=True)):
            if index:
                handle.write(",\n")
            handle.write(json.dumps(row, ensure_ascii=False))
        handle.write("\n]\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False))
        handle.write("\n")


def append_csv_row(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    needs_header = not path.exists() or path.stat().st_size == 0
    fieldnames = list(row.keys())
    existing_rows: list[dict[str, str]] = []
    if not needs_header:
        with path.open(newline="", encoding="utf-8") as existing:
            reader = csv.DictReader(existing)
            old_fieldnames = list(reader.fieldnames or [])
            if old_fieldnames and any(key not in old_fieldnames for key in row):
                existing_rows = list(reader)
                fieldnames = old_fieldnames + [key for key in row if key not in old_fieldnames]
                needs_header = True
            elif old_fieldnames:
                fieldnames = old_fieldnames
    if existing_rows:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer_csv = csv.DictWriter(handle, fieldnames=fieldnames)
            writer_csv.writeheader()
            writer_csv.writerows(existing_rows)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=fieldnames)
        if needs_header and not existing_rows:
            writer_csv.writeheader()
        writer_csv.writerow(row)


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer_csv = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer_csv.writeheader()
        writer_csv.writerows(rows)


def write_jsonl_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def convert_jsonl_to_json_array(jsonl_path: Path, json_path: Path, *, desc: str) -> int:
    if not jsonl_path.exists():
        json_path.write_text("[]\n", encoding="utf-8")
        return 0
    count = 0
    with jsonl_path.open("r", encoding="utf-8") as source, json_path.open("w", encoding="utf-8") as target:
        target.write("[\n")
        for line in tqdm(source, desc=desc, unit="row", dynamic_ncols=True):
            line = line.strip()
            if not line:
                continue
            if count:
                target.write(",\n")
            target.write(line)
            count += 1
        target.write("\n]\n")
    return count


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
