#!/usr/bin/env python3
"""
Ticket branches and the worktrees they live in.

A ticket branch is cut from the remote's default branch, never from a local
one that may be behind, and its worktree sits in a hidden directory beside the
code it belongs to unless `worktree_root` says otherwise. The branch name is a
label for people: nothing here, or in any skill, infers a ticket from it.

Creation is proposed before it is performed, and goes through the
protected-branch guard so that a configured pattern can never make a ticket
branch protected from its own creation.
"""

from dataclasses import dataclass
from pathlib import Path

from . import guard, layout
from .errors import EXIT_ERROR, TicketError

HIDDEN_DIRNAME = ".worktrees"

PREFIX_BY_TYPE = {
    "user-story": "feat",
    "task": "feat",
    "bug": "fix",
    "spike": "spike",
    "tech-debt": "chore",
}

# Caps the whole branch name, so the worktree directory named after it fits too.
MAX_BRANCH_LENGTH = 26


def branch_name(ticket_type: str | None, ticket_id: str, title: str | None) -> str:
    prefix = PREFIX_BY_TYPE.get(ticket_type or "")
    if not prefix:
        raise TicketError(
            f"no branch prefix is known for ticket type '{ticket_type}'",
            EXIT_ERROR,
            "Known types: " + ", ".join(sorted(PREFIX_BY_TYPE)) + ".",
        )
    base = f"{prefix}/{ticket_id}"
    slug = layout.slugify(title or "", fallback="")
    # A local ticket's id is already its title's slug.
    name = base if not slug or slug == ticket_id else f"{base}-{slug}"
    if len(name) <= MAX_BRANCH_LENGTH:
        return name

    cut = name[:MAX_BRANCH_LENGTH]
    # End on a whole word, unless that would drop every title word: half a word says more than none.
    floor = len(prefix) if name == base else len(base)
    boundary = cut.rfind("-")
    if name[MAX_BRANCH_LENGTH] != "-" and boundary > floor:
        cut = cut[:boundary]
    return cut.rstrip("-")


def directory_name(branch: str) -> str:
    return branch.replace("/", "-")


def repository_root(directory: Path) -> Path:
    """The main worktree of the repository `directory` is inside."""
    code, out = guard.git(directory, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if code != 0:
        raise TicketError(f"{directory} is not inside a git repository", EXIT_ERROR)
    common = Path(out)
    return common.parent if common.name == ".git" else common


def is_ignored(repo: Path, relative: str) -> bool:
    code, _ = guard.git(repo, "check-ignore", "-q", relative)
    return code == 0


def branch_exists(repo: Path, branch: str) -> bool:
    return (
        guard.git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")[0]
        == 0
    )


@dataclass
class Plan:
    repository: Path
    default_branch: str
    branch: str
    worktree: Path
    inside_repository: bool
    ignored: bool
    branch_exists: bool
    worktree_exists: bool
    refusal: str | None = None

    @property
    def ignore_entry(self) -> str:
        return f"/{HIDDEN_DIRNAME}/"

    @property
    def needs_ignore_entry(self) -> bool:
        return self.inside_repository and not self.ignored

    def as_dict(self) -> dict:
        return {
            "repository": str(self.repository),
            "default_branch": self.default_branch,
            "base": f"origin/{self.default_branch}",
            "branch": self.branch,
            "worktree": str(self.worktree),
            "branch_exists": self.branch_exists,
            "worktree_exists": self.worktree_exists,
            "ignore_offer": (
                {"file": str(self.repository / ".gitignore"), "entry": self.ignore_entry}
                if self.needs_ignore_entry
                else None
            ),
            "refusal": self.refusal,
        }


def propose(
    directory: Path, branch: str, patterns: list[str], worktree_root: str | None
) -> Plan:
    repo = repository_root(directory)
    default = guard.default_branch(repo)
    if not default:
        raise TicketError(
            f"{repo} has no origin/HEAD, so its default branch is unknown",
            EXIT_ERROR,
            "Run `git remote set-head origin --auto` in it.",
        )

    if worktree_root:
        root = Path(worktree_root).expanduser().resolve() / repo.name
        inside = False
    else:
        root = repo / HIDDEN_DIRNAME
        inside = True
    worktree = root / directory_name(branch)

    ignored = is_ignored(repo, f"{HIDDEN_DIRNAME}/") if inside else True
    refusal = None
    if guard.is_protected(branch, default, patterns):
        refusal = f"'{branch}' matches a protected branch pattern, so no ticket branch may carry it"

    return Plan(
        repository=repo,
        default_branch=default,
        branch=branch,
        worktree=worktree,
        inside_repository=inside,
        ignored=ignored,
        branch_exists=branch_exists(repo, branch),
        worktree_exists=worktree.is_dir(),
        refusal=refusal,
    )


def create(plan: Plan, add_ignore_entry: bool) -> dict:
    """Cut the branch from the freshly fetched remote default and give it a worktree."""
    if plan.refusal:
        raise TicketError(plan.refusal, EXIT_ERROR)

    if plan.worktree_exists:
        return {**plan.as_dict(), "created": False}

    code, out = guard.git(plan.repository, "fetch", "origin")
    if code != 0:
        raise TicketError(f"fetching origin failed: {out}", EXIT_ERROR)

    plan.worktree.parent.mkdir(parents=True, exist_ok=True)
    if plan.branch_exists:
        args = ["worktree", "add", str(plan.worktree), plan.branch]
    else:
        args = [
            "worktree",
            "add",
            "--no-track",
            "-b",
            plan.branch,
            str(plan.worktree),
            f"refs/remotes/origin/{plan.default_branch}",
        ]
    code, out = guard.git(plan.repository, *args)
    if code != 0:
        raise TicketError(f"could not create the worktree: {out}", EXIT_ERROR)

    ignore_added = False
    if add_ignore_entry and plan.needs_ignore_entry:
        gitignore = plan.repository / ".gitignore"
        existing = gitignore.read_text(encoding="utf-8") if gitignore.is_file() else ""
        separator = "" if not existing or existing.endswith("\n") else "\n"
        gitignore.write_text(
            f"{existing}{separator}{plan.ignore_entry}\n", encoding="utf-8"
        )
        ignore_added = True

    report = plan.as_dict()
    if ignore_added:
        report["ignore_offer"] = None
    report.update({"created": True, "ignore_entry_added": ignore_added})
    return report


@dataclass
class Candidate:
    path: Path
    branch: str | None
    protected: bool
    ahead: int
    behind: int

    @property
    def status(self) -> str:
        if not self.branch:
            return "detached"
        if self.ahead and self.behind:
            return "diverged"
        return "behind" if self.behind else "current"

    @property
    def is_current_ticket_branch(self) -> bool:
        return bool(self.branch) and not self.protected and self.status == "current"

    def as_dict(self) -> dict:
        return {
            "worktree": str(self.path),
            "branch": self.branch,
            "protected": self.protected,
            "ahead": self.ahead,
            "behind": self.behind,
            "status": self.status,
        }


def list_worktrees(repo: Path) -> list[tuple[Path, str | None]]:
    """Every worktree of the repository with its branch, skipping those git marks prunable."""
    code, out = guard.git(repo, "worktree", "list", "--porcelain")
    if code != 0:
        raise TicketError(f"could not list the worktrees of {repo}: {out}", EXIT_ERROR)
    found: list[tuple[Path, str | None]] = []
    for block in out.split("\n\n"):
        path: Path | None = None
        branch: str | None = None
        prunable = False
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = Path(line[len("worktree ") :])
            elif line.startswith("branch refs/heads/"):
                branch = line[len("branch refs/heads/") :]
            elif line.startswith("prunable"):
                prunable = True
        if path and not prunable:
            found.append((path, branch))
    return found


def survey(repo: Path, patterns: list[str]) -> dict:
    """
    Fetch, then say how far each worktree of a repository is behind the remote default branch.

    The fetch changes no worktree. An offer to cut a new ticket worktree is
    made only when none of the existing ones is a non-protected branch that is
    already up to date, so re-running a skill in a good workspace stays quiet.
    """
    repo = repository_root(repo)
    default = guard.default_branch(repo)
    if not default:
        raise TicketError(
            f"{repo} has no origin/HEAD, so its default branch is unknown",
            EXIT_ERROR,
            "Run `git remote set-head origin --auto` in it.",
        )
    code, out = guard.git(repo, "fetch", "origin")
    if code != 0:
        raise TicketError(f"fetching origin failed: {out}", EXIT_ERROR)

    base = f"refs/remotes/origin/{default}"
    candidates: list[Candidate] = []
    for path, branch in list_worktrees(repo):
        _, counts = guard.git(path, "rev-list", "--left-right", "--count", f"HEAD...{base}")
        ahead, behind = (int(part) for part in counts.split())
        candidates.append(
            Candidate(path, branch, guard.is_protected(branch, default, patterns), ahead, behind)
        )

    return {
        "repository": str(repo),
        "default_branch": default,
        "worktrees": [candidate.as_dict() for candidate in candidates],
        "offer": not any(c.is_current_ticket_branch for c in candidates),
    }
