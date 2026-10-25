"""Append-only experiment registry (single source of truth).

Layout (committed to git, except where noted):
  research/registry/runs.jsonl      one JSON line per completed/failed run unit
  research/registry/batches.jsonl   one line per batch submission / sync event
  research/registry/legacy.jsonl    imported pre-registry results (never mixed with new runs)
  research/raw/<batch_id>/<run_id>.json.gz   raw round-level outputs (immutable once written)

Writes are atomic (temp file + rename for raw files; single appended line under an
exclusive lock file for JSONL). Records are never edited; a re-run of the same unit is a
new record only if its ``replicate`` differs, otherwise it is skipped as a duplicate.
"""
from __future__ import annotations

import gzip, json, os, time
from pathlib import Path
from typing import Any, Iterable

from src.research.ids import canonical_json, sha256_file, utc_now

ROOT = Path(__file__).resolve().parents[2] / "research"


class Registry:
    def __init__(self, root: str | os.PathLike | None = None):
        self.root = Path(root) if root else ROOT
        self.reg = self.root / "registry"
        self.raw = self.root / "raw"
        self.reg.mkdir(parents=True, exist_ok=True)
        self.raw.mkdir(parents=True, exist_ok=True)

    # ---- locking -------------------------------------------------------------------------
    def _lock(self, name: str, timeout: float = 30.0):
        path = self.reg / f".{name}.lock"
        start = time.time()
        while True:
            try:
                fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode()); os.close(fd)
                return path
            except FileExistsError:
                if time.time() - start > timeout:
                    if time.time() - path.stat().st_mtime > 300:  # stale lock from a crashed writer
                        os.remove(path)
                        continue
                    raise TimeoutError(f"registry lock busy: {path}")
                time.sleep(0.05)

    def _append(self, name: str, record: dict) -> None:
        line = canonical_json(record) + "\n"
        lock = self._lock(name)
        try:
            with open(self.reg / f"{name}.jsonl", "a", encoding="utf-8") as f:
                f.write(line); f.flush(); os.fsync(f.fileno())
        finally:
            os.remove(lock)

    # ---- reading -------------------------------------------------------------------------
    def records(self, name: str = "runs") -> list[dict]:
        path = self.reg / f"{name}.jsonl"
        if not path.exists():
            return []
        out = []
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except json.JSONDecodeError as exc:  # never silently drop: surface corruption
                        raise ValueError(f"{path}:{i + 1} is not valid JSON") from exc
        return out

    def completed_ids(self) -> set[str]:
        return {r["run_id"] for r in self.records() if r.get("status") == "completed"}

    # ---- writing -------------------------------------------------------------------------
    def write_raw(self, batch_id: str, run_id: str, payload: dict) -> tuple[str, str]:
        d = self.raw / batch_id
        d.mkdir(parents=True, exist_ok=True)
        final = d / f"{run_id}.json.gz"
        if final.exists():
            return str(final.relative_to(self.root.parent)), sha256_file(str(final))
        tmp = d / f".{run_id}.{os.getpid()}.tmp"
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(payload, f, default=str)
        os.replace(tmp, final)
        return str(final.relative_to(self.root.parent)), sha256_file(str(final))

    def read_raw(self, rel_path: str) -> dict:
        with gzip.open(self.root.parent / rel_path, "rt", encoding="utf-8") as f:
            return json.load(f)

    def register_run(self, record: dict) -> bool:
        """Append a run record unless a completed record with the same run_id exists."""
        for k in ("run_id", "batch_id", "status"):
            if k not in record:
                raise ValueError(f"run record missing {k}")
        if record["status"] == "completed" and record["run_id"] in self.completed_ids():
            return False
        record = {"record_type": "run", "registered_at": utc_now(), **record}
        self._append("runs", record)
        return True

    def register_batch_event(self, event: dict) -> None:
        self._append("batches", {"record_type": "batch_event", "at": utc_now(), **event})

    def register_legacy(self, records: Iterable[dict]) -> int:
        have = {r["legacy_id"] for r in self.records("legacy")}
        n = 0
        for r in records:
            if r["legacy_id"] in have:
                continue
            self._append("legacy", {"record_type": "legacy", "registered_at": utc_now(), **r})
            n += 1
        return n

    def verify(self) -> dict[str, Any]:
        """Integrity check: unique completed run_ids, raw files present with matching checksums."""
        recs = self.records()
        problems, seen = [], set()
        for r in recs:
            if r.get("status") != "completed":
                continue
            if r["run_id"] in seen:
                problems.append(f"duplicate completed run {r['run_id']}")
            seen.add(r["run_id"])
            raw = r.get("raw_path")
            if raw:
                p = self.root.parent / raw
                if not p.exists():
                    problems.append(f"missing raw {raw}")
                elif r.get("raw_sha256") and sha256_file(str(p)) != r["raw_sha256"]:
                    problems.append(f"checksum mismatch {raw}")
        return {"n_records": len(recs), "n_completed": len(seen), "problems": problems}
