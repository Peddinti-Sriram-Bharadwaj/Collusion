"""Stable identifiers, hashing and provenance helpers."""
from __future__ import annotations

import hashlib, json, os, platform, subprocess
from datetime import datetime, timezone
from typing import Any

UNKNOWN = "unknown"


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def short_hash(obj: Any, n: int = 12) -> str:
    data = obj if isinstance(obj, (bytes, bytearray)) else canonical_json(obj).encode()
    return hashlib.sha256(data).hexdigest()[:n]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git_state(repo: str | None = None) -> dict[str, Any]:
    def run(*args):
        return subprocess.check_output(["git", *args], cwd=repo, text=True, stderr=subprocess.DEVNULL).strip()
    try:
        return {"commit": run("rev-parse", "HEAD"), "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
                "dirty": bool(run("status", "--porcelain"))}
    except Exception:
        return {"commit": os.environ.get("RESEARCH_GIT_COMMIT", UNKNOWN),
                "branch": os.environ.get("RESEARCH_GIT_BRANCH", UNKNOWN),
                "dirty": os.environ.get("RESEARCH_GIT_DIRTY", UNKNOWN)}


def host_info() -> dict[str, Any]:
    info = {"platform": platform.platform(), "python": platform.python_version()}
    try:
        import torch
        info["torch"] = torch.__version__
        info["cuda"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        info["torch"] = UNKNOWN
    try:
        import transformers
        info["transformers"] = transformers.__version__
    except Exception:
        pass
    return info
