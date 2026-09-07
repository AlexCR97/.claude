#!/usr/bin/env python3
"""
Collects the read-only git state of a working directory as JSON.

Shared by az-workitem-checkpoint (which records the state in journal.md) and
az-workitem-resume (which compares the live state against what was recorded).
Both need the same facts described the same way, so they read them from here
rather than each running its own set of git commands.

Every command is read-only. Nothing is written, fetched, checked out or staged.

Usage:
    python collect-git-state.py [--path DIR]

Output: a single JSON object on stdout. Every field is optional — a directory
that is not a repository yields {"is_repo": false}, and any individual fact
that git cannot answer is null or omitted rather than fatal, because a partial
picture is still worth reporting.

Exit codes:
    0  state collected (check is_repo for whether it is a repository)
    1  git is unavailable, or the path is not a directory
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Field separator for --format; safe because git will not emit it itself.
UNIT = "\x1f"

# Consulted in order when origin/HEAD does not name the default branch.
BASE_BRANCH_CANDIDATES = ("origin/main", "origin/master", "main", "master")

DEFAULT_BRANCH_NAMES = ("main", "master")

# An ADO work item ID is 4-7 digits; anything shorter matches version numbers.
WORK_ITEM_ID_PATTERN = re.compile(r"\d{4,7}")

RECENT_COMMIT_LIMIT = 8

# A long list of paths is noise in a briefing; the counts carry the signal.
DIRTY_FILE_LIMIT = 20


class Git:
    """Runs read-only git commands in one directory."""

    def __init__(self, executable: str, path: Path):
        self._executable = executable
        self._path = path

    def run(self, *args: str) -> tuple[bool, str]:
        """Returns (succeeded, stdout); a failed command reads as empty."""
        try:
            result = subprocess.run(
                [self._executable, *args],
                cwd=self._path,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return False, ""

        if result.returncode != 0:
            return False, ""

        return True, result.stdout.strip()

    def value(self, *args: str) -> str | None:
        ok, out = self.run(*args)
        return (out or None) if ok else None

    def count(self, *args: str) -> int | None:
        ok, out = self.run(*args)
        if not ok or not out.isdigit():
            return None
        return int(out)


def parse_commit(raw: str) -> dict | None:
    """Parse one commit line formatted as sha, subject, author, ISO date."""
    if not raw:
        return None

    parts = raw.split(UNIT)
    if len(parts) < 4:
        return None

    return {
        "sha": parts[0],
        "subject": parts[1],
        "author": parts[2],
        "date": parts[3],
    }


def read_commit(git: Git, rev: str) -> dict | None:
    formatted = git.value("log", "-1", f"--format=%h{UNIT}%s{UNIT}%an{UNIT}%cI", rev)
    return parse_commit(formatted or "")


def resolve_base_branch(git: Git, branch: str | None) -> str | None:
    """
    The branch this work is expected to merge into.

    A branch that is already the default branch is its own base: there is no
    feature branch, so "commits ahead of base" is not a meaningful number.
    """
    if branch in DEFAULT_BRANCH_NAMES:
        return branch

    head_ref = git.value("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    if head_ref:
        # refs/remotes/origin/main reduces to origin/main
        candidate = head_ref.replace("refs/remotes/", "", 1)
        if git.value("rev-parse", "--verify", "--quiet", candidate):
            return candidate

    for candidate in BASE_BRANCH_CANDIDATES:
        if git.value("rev-parse", "--verify", "--quiet", candidate):
            return candidate

    return None


def collect_dirty(git: Git) -> dict:
    """
    Summarize the working tree from porcelain v1 status.

    Counts are reported per state rather than as one total: "3 modified, 1
    untracked" says something a bare "4 changed" does not, and a tree holding
    only untracked files is a different situation from one holding uncommitted
    edits to tracked files.
    """
    ok, out = git.run("status", "--porcelain")
    if not ok:
        return {"available": False}

    counts = {"modified": 0, "added": 0, "deleted": 0, "renamed": 0, "untracked": 0}
    files: list[str] = []

    for line in out.splitlines():
        if len(line) < 3:
            continue

        code, path = line[:2], line[3:]

        if code == "??":
            counts["untracked"] += 1
        elif "R" in code:
            counts["renamed"] += 1
        elif "D" in code:
            counts["deleted"] += 1
        elif "A" in code:
            counts["added"] += 1
        else:
            counts["modified"] += 1

        files.append(f"{code.strip() or '??'} {path}")

    return {
        "available": True,
        "is_dirty": bool(files),
        **counts,
        "total": len(files),
        "files": files[:DIRTY_FILE_LIMIT],
        "files_truncated": len(files) > DIRTY_FILE_LIMIT,
    }


def collect_stashes(git: Git) -> list[dict]:
    ok, out = git.run("stash", "list", f"--format=%gd{UNIT}%s{UNIT}%cI")
    if not ok or not out:
        return []

    stashes = []
    for line in out.splitlines():
        parts = line.split(UNIT)
        if len(parts) >= 3:
            stashes.append({"ref": parts[0], "subject": parts[1], "date": parts[2]})

    return stashes


def collect_recent_commits(
    git: Git, base_branch: str | None, branch: str | None
) -> list[dict]:
    """
    The commits that make up this branch's work, newest first.

    Bounded by the merge base when there is one, so the list is the work done
    on this branch rather than an arbitrary slice of the repository history.
    """
    revision_range = "HEAD"
    if base_branch and branch not in DEFAULT_BRANCH_NAMES:
        merge_base = git.value("merge-base", "HEAD", base_branch)
        if merge_base:
            revision_range = f"{merge_base}..HEAD"

    ok, out = git.run(
        "log",
        f"-{RECENT_COMMIT_LIMIT}",
        f"--format=%h{UNIT}%s{UNIT}%an{UNIT}%cI",
        revision_range,
    )
    if not ok or not out:
        return []

    commits = [parse_commit(line) for line in out.splitlines()]
    return [commit for commit in commits if commit]


def collect(path: Path, executable: str) -> dict:
    git = Git(executable, path)

    root = git.value("rev-parse", "--show-toplevel")
    if not root:
        return {"is_repo": False, "path": str(path)}

    branch = git.value("rev-parse", "--abbrev-ref", "HEAD")
    # A detached HEAD reports the literal string "HEAD" as its branch name.
    is_detached = branch == "HEAD"
    if is_detached:
        branch = None

    base_branch = resolve_base_branch(git, branch)

    state: dict = {
        "is_repo": True,
        "root": root,
        "repo_name": Path(root).name,
        "branch": branch,
        "is_detached_head": is_detached,
        "upstream": git.value(
            "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
        ),
        "head": read_commit(git, "HEAD"),
        "base_branch": base_branch,
        "dirty": collect_dirty(git),
        "stashes": collect_stashes(git),
        "recent_commits": collect_recent_commits(git, base_branch, branch),
        "work_item_ids_in_branch": (
            WORK_ITEM_ID_PATTERN.findall(branch) if branch else []
        ),
    }

    if base_branch and branch not in DEFAULT_BRANCH_NAMES:
        merge_base = git.value("merge-base", "HEAD", base_branch)
        state["merge_base"] = read_commit(git, merge_base) if merge_base else None
        state["commits_ahead_of_base"] = git.count(
            "rev-list", "--count", f"{base_branch}..HEAD"
        )
        # Commits the base gained while this branch sat idle: the staleness
        # signal that matters after days away, and the reason a plan built
        # against an older tree may no longer apply cleanly.
        state["base_commits_not_merged"] = git.count(
            "rev-list", "--count", f"HEAD..{base_branch}"
        )

    return state


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect read-only git state of a working directory as JSON."
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Directory to inspect (default: the current directory)",
    )
    args = parser.parse_args()

    executable = shutil.which("git")
    if not executable:
        print("ERROR: git not found on PATH.", file=sys.stderr)
        raise SystemExit(1)

    path = Path(args.path).resolve()
    if not path.is_dir():
        print(f"ERROR: not a directory — {path}", file=sys.stderr)
        raise SystemExit(1)

    print(json.dumps(collect(path, executable), indent=2))


if __name__ == "__main__":
    main()
