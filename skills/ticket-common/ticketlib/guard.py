#!/usr/bin/env python3
"""
The one definition of a protected branch, and what may be done to it.

A protected branch is the repository's default branch (named by `origin/HEAD`)
plus any branch matching a pattern in the effective config's
`protected_branches`. A skill may read one and fast-forward it from its remote;
it never writes to one. The rule lives here and not in each skill's prose so
that every skill agrees on what is protected, and so it can be tested.
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path

from . import proc
from .errors import EXIT_ERROR, TicketError

# Operations that only read, or that bring a protected branch up to its remote.
ALLOWED_ON_PROTECTED = frozenset(
    {"fetch", "fast-forward", "log", "diff", "blame", "show", "cherry-pick-from"}
)

# Operations that would write to the branch they are run on.
FORBIDDEN_ON_PROTECTED = {
    "commit": "it would add a commit",
    "push": "it would publish to the remote branch",
    "force-push": "it would rewrite the remote branch",
    "merge": "a merge that is not a fast-forward adds a commit",
    "rebase": "it would rewrite the branch",
    "reset": "it would move the branch",
    "revert": "it would add a commit",
    "cherry-pick": "it would add a commit",
    "edit": "the files would change in a worktree that has it checked out",
}

OPERATIONS = tuple(sorted(ALLOWED_ON_PROTECTED | set(FORBIDDEN_ON_PROTECTED)))


@dataclass
class Verdict:
    allowed: bool
    operation: str
    branch: str | None
    protected: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "operation": self.operation,
            "branch": self.branch,
            "protected": self.protected,
            "reason": self.reason,
        }


def git(repo: Path, *args: str) -> tuple[int, str]:
    code, stdout, stderr = proc.run(["git", *args], cwd=str(repo), timeout=120)
    return code, (stdout if code == 0 else stderr or stdout).strip()


def require_repository(repo: Path) -> None:
    code, _ = git(repo, "rev-parse", "--git-dir")
    if code != 0:
        raise TicketError(f"{repo} is not inside a git repository", EXIT_ERROR)


def default_branch(repo: Path) -> str | None:
    """The branch `origin/HEAD` names, or None where the remote has no HEAD recorded."""
    code, out = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if code != 0 or "/" not in out:
        return None
    return out.split("/", 1)[1]


def current_branch(repo: Path) -> str | None:
    code, out = git(repo, "branch", "--show-current")
    return (out or None) if code == 0 else None


def patterns_from(config: dict) -> list[str]:
    value = config.get("protected_branches")
    return [str(item) for item in value] if isinstance(value, list) else []


def is_protected(branch: str | None, default: str | None, patterns: list[str]) -> bool:
    if not branch:
        return False
    if branch == default:
        return True
    return any(fnmatch.fnmatchcase(branch, pattern) for pattern in patterns)


def classify(
    operation: str, branch: str | None, default: str | None, patterns: list[str]
) -> Verdict:
    if operation not in OPERATIONS:
        raise TicketError(
            f"unknown operation '{operation}'",
            EXIT_ERROR,
            "Known operations: " + ", ".join(OPERATIONS) + ".",
        )

    protected = is_protected(branch, default, patterns)
    if not protected:
        return Verdict(True, operation, branch, False, "the branch is not protected")
    if operation in ALLOWED_ON_PROTECTED:
        return Verdict(
            True, operation, branch, True, f"{operation} only reads or fast-forwards"
        )
    return Verdict(
        False,
        operation,
        branch,
        True,
        f"'{branch}' is a protected branch and {FORBIDDEN_ON_PROTECTED[operation]}",
    )


def worktree_of(repo: Path, branch: str) -> Path | None:
    """The worktree that has `branch` checked out, if any."""
    code, out = git(repo, "worktree", "list", "--porcelain")
    if code != 0:
        return None
    current: Path | None = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree ") :])
        elif line == f"branch refs/heads/{branch}":
            return current
    return None


def refusal(branch: str, reason: str) -> dict:
    return {"updated": False, "refused": True, "branch": branch, "reason": reason}


def fast_forward(repo: Path, branch: str) -> dict:
    """
    Bring a local branch up to its remote when that cannot lose anything.

    Refused, with the reason, when the tree of the worktree holding it is
    dirty, when it has commits the remote lacks, or when the two diverged.
    """
    remote_ref = f"refs/remotes/origin/{branch}"
    code, out = git(repo, "fetch", "origin")
    if code != 0:
        return refusal(branch, f"fetching origin failed: {out}")

    if git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")[0] != 0:
        return refusal(branch, f"there is no local branch '{branch}'")
    if git(repo, "rev-parse", "--verify", "--quiet", remote_ref)[0] != 0:
        return refusal(branch, f"the remote has no branch '{branch}'")

    _, counts = git(
        repo, "rev-list", "--left-right", "--count", f"refs/heads/{branch}...{remote_ref}"
    )
    ahead, behind = (int(part) for part in counts.split())
    if ahead and behind:
        return refusal(
            branch,
            f"'{branch}' has diverged: {ahead} local-only and {behind} remote-only commits",
        )
    if ahead:
        return refusal(
            branch, f"'{branch}' has {ahead} local-only commit(s) the remote lacks"
        )
    if not behind:
        return {
            "updated": False,
            "refused": False,
            "branch": branch,
            "reason": "already up to date",
        }

    holder = worktree_of(repo, branch)
    if holder:
        _, status = git(holder, "status", "--porcelain")
        if status:
            return refusal(branch, f"the worktree {holder} has uncommitted changes")
        code, out = git(holder, "merge", "--ff-only", remote_ref)
    else:
        code, out = git(repo, "update-ref", f"refs/heads/{branch}", remote_ref)
    if code != 0:
        return refusal(branch, f"the fast-forward failed: {out}")

    return {
        "updated": True,
        "refused": False,
        "branch": branch,
        "reason": f"advanced {behind} commit(s)",
    }
