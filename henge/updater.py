"""Update notifier — checks origin for new commits, caches the result for 24h.

Best-effort by design: any failure (no git, no network, not a clone) is silent
and the MCP server keeps booting. The user is never blocked by a connectivity
hiccup with GitHub.

Behavior:
- At server boot we call ``get_update_status()``. If the cache is < 24h old, we
  use it. Otherwise we run ``git fetch`` + ``git rev-list HEAD..origin/<branch>``
  and write the result to ``~/.henge/.update-status.json``.
- The ``decide()`` tool injects an ``update_available`` block into its result
  whenever ``status.behind > 0``, so Claude Code can surface it to the user.

Opt-out: set ``HENGE_DISABLE_UPDATE_CHECK=1`` in ``.env`` to skip the check
entirely. The cache is also a hint, not a contract — delete it any time.
"""
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

CACHE_FILE = Path.home() / ".henge" / ".update-status.json"
CACHE_TTL_HOURS = 24
FETCH_TIMEOUT_S = 8


def _project_root():
    """Resolve the local clone root — only when this file lives under a git repo."""
    here = Path(__file__).resolve().parent.parent
    if (here / ".git").is_dir():
        return here
    return None


def _git(repo, *args, timeout=5.0):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _check_remote(repo):
    """Fetch + measure how far HEAD lags origin/<branch>. Returns dict or None."""
    # Fetch is best-effort; we still try to read locally even if fetch fails.
    _git(repo, "fetch", "--quiet", "origin", timeout=FETCH_TIMEOUT_S)

    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or "main"
    current = _git(repo, "rev-parse", "--short", "HEAD")
    latest = _git(repo, "rev-parse", "--short", f"origin/{branch}")
    if not current or not latest:
        return None

    behind_raw = _git(repo, "rev-list", "--count", f"HEAD..origin/{branch}")
    try:
        behind = int(behind_raw) if behind_raw is not None else 0
    except ValueError:
        return None

    return {
        "behind": behind,
        "current_sha": current,
        "latest_sha": latest,
        "branch": branch,
        "repo_path": str(repo),
        "last_check": datetime.now().isoformat(),
    }


def get_update_status(force=False):
    """Return cached status, refreshing if stale, missing, or ``force=True``.

    Returns None when checks are disabled, the project isn't a git clone, or
    every git operation failed. Callers should treat None as "no info".
    """
    if os.environ.get("HENGE_DISABLE_UPDATE_CHECK"):
        return None

    repo = _project_root()
    if not repo:
        return None

    if not force and CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            last = datetime.fromisoformat(cached.get("last_check", ""))
            if datetime.now() - last < timedelta(hours=CACHE_TTL_HOURS):
                return cached
        except (json.JSONDecodeError, ValueError, OSError):
            pass

    status = _check_remote(repo)
    if status:
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(status, indent=2), encoding="utf-8")
        except OSError:
            pass
    return status


def update_message(status):
    """Format a one-line user-facing notice. Returns None if up-to-date / no info."""
    if not status:
        return None
    behind = status.get("behind", 0)
    if behind <= 0:
        return None
    sha = status.get("latest_sha", "")
    repo_path = status.get("repo_path", "")
    plural = "commits" if behind != 1 else "commit"
    cmd = f"cd {repo_path} && git pull --ff-only" if repo_path else "git pull --ff-only"
    return f"Henge has {behind} new {plural} on origin ({sha}). Update with: {cmd}"
