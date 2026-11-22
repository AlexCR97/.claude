"""
`guard`: the one definition of a protected branch, and what may be done to it.

A protected branch is the repository's default branch (the one `origin/HEAD`
names, or `main` or `master` where it is unset) plus any branch matching a pattern in the effective config's
`protected_branches`. A skill may read one and fast-forward it from its remote;
it never writes to one (ADR 0001). The rule lives here and not in each skill's
prose so that every skill agrees on what is protected, and so it can be tested.

A fast-forward is allowed here but not run here: the model runs
`git merge --ff-only` itself once the guard has said yes.
"""

import fnmatch
import shutil
from pathlib import Path

from . import config as configuration
from . import layout, process
from .errors import SdlcError

# Operations that only read, or that bring a protected branch up to its remote.
ALLOWED_ON_PROTECTED = frozenset(
    {"fetch", "fast-forward", "log", "diff", "blame", "show", "cherry-pick-from"}
)

# Operations that would write to the branch they run on, with why each is refused.
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

USUAL_DEFAULTS = ("main", "master")
SOURCE_ORIGIN_HEAD = "origin/HEAD"
SOURCE_INFERRED = "inferred"
SOURCE_UNKNOWN = "unknown"

OPERATIONS = tuple(sorted(ALLOWED_ON_PROTECTED | set(FORBIDDEN_ON_PROTECTED)))


def git(repo: Path, *args: str) -> tuple[int, str]:
    executable = shutil.which("git")
    if not executable:
        raise SdlcError("git was not found on PATH")
    result = process.run([executable, *args], cwd=repo, text=True)
    return result.returncode, (result.stdout or result.stderr).strip()


def require_repository(repo: Path) -> None:
    if not repo.is_dir() or git(repo, "rev-parse", "--git-dir")[0] != 0:
        raise SdlcError(f"{repo} is not inside a git repository")


def local_branches(repo: Path) -> list[str]:
    code, out = git(repo, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return out.splitlines() if code == 0 else []


def default_branch(repo: Path) -> tuple[str | None, str]:
    """
    The default branch and how it was found: `origin/HEAD`, `inferred` or `unknown`.

    A clone made without `origin/HEAD` (or one whose remote was added by hand)
    must not leave `main` writable, so the usual names are tried before giving up.
    """
    code, out = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and "/" in out:
        return out.split("/", 1)[1], SOURCE_ORIGIN_HEAD

    usual = [name for name in USUAL_DEFAULTS if name in local_branches(repo)]
    if len(usual) == 1:
        return usual[0], SOURCE_INFERRED
    current = current_branch(repo)
    if current in USUAL_DEFAULTS:
        return current, SOURCE_INFERRED
    return None, SOURCE_UNKNOWN


def current_branch(repo: Path) -> str | None:
    code, out = git(repo, "branch", "--show-current")
    return (out or None) if code == 0 else None


def is_protected(branch: str | None, default: str | None, patterns: list[str]) -> bool:
    if not branch:
        return False
    return branch == default or any(
        fnmatch.fnmatchcase(branch, pattern) for pattern in patterns
    )


def policy_for(
    repo_text: str | None, context_text: str | None
) -> tuple[Path, str | None, str, list[str]]:
    """The repository, its default branch, where that came from, and the effective protected patterns."""
    repo = Path(repo_text).expanduser().resolve() if repo_text else Path.cwd()
    require_repository(repo)

    context = layout.parse_context(context_text)
    effective = configuration.load().effective(
        context.namespace if context else None,
        context.product if context else None,
    )
    patterns = [str(pattern) for pattern in effective.get("protected_branches", [])]
    default, source = default_branch(repo)
    return repo, default, source, patterns


def check(
    operation: str, repo_text: str | None, branch: str | None, context_text: str | None
) -> dict:
    if operation not in OPERATIONS:
        raise SdlcError(
            f"unknown operation '{operation}'",
            hint="Known operations: " + ", ".join(OPERATIONS) + ".",
        )
    repo, default, source, patterns = policy_for(repo_text, context_text)
    branch = branch or current_branch(repo)

    protected = is_protected(branch, default, patterns)
    if not protected:
        allowed, reason = True, "the branch is not protected"
    elif operation in ALLOWED_ON_PROTECTED:
        allowed, reason = True, f"{operation} only reads or fast-forwards"
    else:
        allowed = False
        reason = (
            f"'{branch}' is a protected branch and {FORBIDDEN_ON_PROTECTED[operation]}"
        )
    return {
        "allowed": allowed,
        "operation": operation,
        "branch": branch,
        "protected": protected,
        "reason": reason,
        "default_branch_source": source,
    }


def protected_branches(
    repo_text: str | None, branch: str | None, context_text: str | None
) -> dict:
    repo, default, source, patterns = policy_for(repo_text, context_text)
    branch = branch or current_branch(repo)
    return {
        "branch": branch,
        "default_branch": default,
        "default_branch_source": source,
        "patterns": patterns,
        "protected_branches": [*([default] if default else []), *patterns],
        "protected": is_protected(branch, default, patterns),
    }
