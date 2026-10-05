#!/usr/bin/env python3
"""
A ticket's plan: one file per phase under `plan/`, joined by a dependency graph.

The phase files are the source of truth. `plan.md` is an index whose Progress
table and graph are a generated block, rewritten in full from the phase files
by `sync` — never hand-edited. Several sessions may work one ticket at once,
each on its own phase; were the table edited by hand, two of them would race to
write it. Regenerating from every phase file means whichever session syncs last
writes the correct state.

Renumbering is mechanical for the same reason: a phase number is also part of
a file name, every step heading, every `depends_on`, and every
`artifacts/step-{N}.{M}/` directory, and a rename that misses one leaves a
reference pointing nowhere.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import frontmatter
from .errors import EXIT_ERROR, EXIT_NOT_FOUND, TicketError

ACTIVITIES = (
    "Design",
    "Development",
    "Testing",
    "Documentation",
    "Deployment",
    "Human Review",
)

STATUSES = ("Pending", "In Progress", "Blocked", "Done")

STATUS_CELLS = {
    "Pending": "[ ] Pending",
    "In Progress": "[~] In Progress",
    "Blocked": "[!] Blocked",
    "Done": "[x] Done",
}

# Reserved for prerequisites more than one phase shares; renumbering never moves it.
PREREQUISITES_PHASE = 0

BLOCK_START = "<!-- plan-sync:start — generated from the phase files by `ticket.py plan-sync`; never edit by hand -->"
BLOCK_END = "<!-- plan-sync:end -->"
BLOCK_PATTERN = re.compile(
    r"<!-- plan-sync:start\b.*?-->.*?<!-- plan-sync:end -->", re.DOTALL
)

PHASE_FILE = re.compile(r"^(\d+)-([a-z0-9][a-z0-9-]*)\.md$")
STEP_HEADING = re.compile(r"^### +Step +(\d+)\.(\d+) *$", re.MULTILINE)
NEXT_HEADING = re.compile(r"^#{1,3} ", re.MULTILINE)
STATUS_LINE = re.compile(r"^\*\*Status:\*\* *(.+?) *$", re.MULTILINE)
TARGET_LINE = re.compile(r"^\*\*Target:\*\* *(.+?) *$", re.MULTILINE)
PREREQUISITES_HEADING = re.compile(r"^## +Prerequisites *$", re.MULTILINE)
CHECKLIST_ITEM = re.compile(r"^\s*[-*] \[([ xX])\] +(.+?) *$", re.MULTILINE)
GUIDANCE_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
NOTE_SEPARATOR = re.compile(r" +[—–-] +")

# Captured outputs are measurements; a renumbering pass never rewrites one,
# even where its text happens to contain something that reads like a step id.
CAPTURE_FILE = re.compile(r"\.(output|stderr)\.[^.]+$")


@dataclass
class Step:
    id: str
    status: str
    note: str
    target: str

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "note": self.note,
            "target": self.target,
        }


@dataclass
class Phase:
    number: int
    slug: str
    path: Path
    title: str
    activity: str
    estimate: float
    depends_on: list[int]
    projects: list[str]
    steps: list[Step] = field(default_factory=list)
    prerequisites: list[tuple[bool, str]] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return self.path.name

    @property
    def status(self) -> str:
        """Derived from the steps, by the table in ticket-common/STATUS.md."""
        statuses = [step.status for step in self.steps]
        if "Blocked" in statuses:
            return "Blocked"
        if statuses and all(status == "Done" for status in statuses):
            return "Done"
        if any(status in ("Done", "In Progress") for status in statuses):
            return "In Progress"
        return "Pending"

    @property
    def open_prerequisites(self) -> list[str]:
        return [text for checked, text in self.prerequisites if not checked]


@dataclass
class Plan:
    directory: Path
    phases: dict[int, Phase]
    warnings: list[str]

    @property
    def index(self) -> Path:
        return self.directory / "plan.md"

    def ordered(self) -> list[Phase]:
        return [self.phases[number] for number in sorted(self.phases)]

    def readiness(self, phase: Phase) -> tuple[bool, str]:
        """
        Ready means every dependency is Done and every prerequisite is checked.

        Derived, never stored: a recorded "waiting" would go stale the moment
        the dependency finished. A Blocked phase is never ready — what blocks
        it lies outside the graph.
        """
        if phase.status == "Done":
            return False, "—"
        if phase.status == "Blocked":
            return False, "blocked"

        reasons = []
        waiting = [
            number
            for number in phase.depends_on
            if self.phases[number].status != "Done"
        ]
        if waiting:
            reasons.append("waiting on " + ", ".join(str(number) for number in waiting))
        open_count = len(phase.open_prerequisites)
        if open_count:
            noun = "prerequisite" if open_count == 1 else "prerequisites"
            reasons.append(f"{open_count} {noun} open")

        if reasons:
            return False, "; ".join(reasons)
        return True, "✅"

    def critical_path(self) -> tuple[list[int], float]:
        """The longest dependency chain by estimate: the floor on wall-clock time."""
        best: dict[int, tuple[float, list[int]]] = {}

        def longest(number: int) -> tuple[float, list[int]]:
            if number not in best:
                phase = self.phases[number]
                prior = max(
                    (longest(dependency) for dependency in phase.depends_on),
                    key=lambda chain: chain[0],
                    default=(0.0, []),
                )
                best[number] = (prior[0] + phase.estimate, prior[1] + [number])
            return best[number]

        hours, chain = max(
            (longest(number) for number in self.phases),
            key=lambda chain: chain[0],
            default=(0.0, []),
        )
        return chain, hours


# --- reading ----------------------------------------------------------------


def load(plan_dir: Path) -> Plan:
    """Every phase file, validated as a graph. Structural problems raise, all at once."""
    if not (plan_dir / "plan.md").is_file():
        raise TicketError(f"no plan at {plan_dir}", EXIT_NOT_FOUND)

    problems: list[str] = []
    warnings: list[str] = []
    phases: dict[int, Phase] = {}

    for path in sorted(plan_dir.iterdir()):
        if path.name == "plan.md" or not path.is_file() or path.suffix != ".md":
            continue
        match = PHASE_FILE.match(path.name)
        if not match:
            warnings.append(f"{path.name} is not named `{{N}}-{{slug}}.md`; ignored")
            continue

        phase = read_phase(
            path, int(match.group(1)), match.group(2), problems, warnings
        )
        if phase is None:
            continue
        if phase.number in phases:
            problems.append(
                f"phase {phase.number} is in both {phases[phase.number].filename} and {path.name}"
            )
            continue
        phases[phase.number] = phase

    if not phases and not problems:
        problems.append(f"{plan_dir} holds no phase files")

    for phase in phases.values():
        for dependency in phase.depends_on:
            if dependency == phase.number:
                problems.append(f"phase {phase.number} depends on itself")
            elif dependency not in phases:
                problems.append(
                    f"phase {phase.number} depends on {dependency}, which does not exist"
                )

    if not problems:
        cycle = find_cycle(phases)
        if cycle:
            problems.append(
                "the phases form a cycle: "
                + " → ".join(str(number) for number in cycle)
            )

    if problems:
        raise TicketError(
            "the plan cannot be read as a graph:\n  - " + "\n  - ".join(problems),
            EXIT_ERROR,
            "Fix the phase files named above, then run this again.",
        )

    plan = Plan(plan_dir, phases, warnings)
    warnings.extend(overlap_warnings(plan))
    return plan


def read_phase(
    path: Path, number: int, slug: str, problems: list[str], warnings: list[str]
) -> Phase | None:
    text = path.read_text(encoding="utf-8")
    data, body = frontmatter.parse(text)
    name = path.name

    declared = str(data.get("number", "")).strip()
    if declared != str(number):
        problems.append(
            f"{name}: frontmatter `number: {declared}` does not match its file name"
        )
        return None

    title = str(data.get("title", "")).strip()
    if not title:
        problems.append(f"{name}: frontmatter has no `title`")

    activity = str(data.get("activity", "")).strip()
    if activity not in ACTIVITIES:
        problems.append(
            f"{name}: activity `{activity}` is not one of " + ", ".join(ACTIVITIES)
        )

    estimate = parse_hours(data.get("estimate"))
    if estimate is None:
        problems.append(
            f"{name}: estimate `{data.get('estimate')}` is not a number of hours"
        )
        estimate = 0.0
    if number == PREREQUISITES_PHASE and estimate > 1:
        warnings.append(f"{name}: a prerequisites phase is estimated at ~1 hr at most")

    depends_on: list[int] = []
    raw_dependencies = data.get("depends_on") or []
    if isinstance(raw_dependencies, str):
        raw_dependencies = [raw_dependencies] if raw_dependencies.strip() else []
    for item in raw_dependencies:
        if str(item).strip().isdigit():
            depends_on.append(int(item))
        else:
            problems.append(
                f"{name}: `depends_on` holds `{item}`, which is not a phase number"
            )

    projects = data.get("projects") or []
    if isinstance(projects, str):
        projects = [projects] if projects.strip() else []

    phase = Phase(
        number=number,
        slug=slug,
        path=path,
        title=title,
        activity=activity,
        estimate=estimate,
        depends_on=sorted(set(depends_on)),
        projects=list(projects),
    )
    phase.steps = read_steps(body, phase, problems, warnings)
    phase.prerequisites = read_prerequisites(body)
    return phase


def read_steps(
    body: str, phase: Phase, problems: list[str], warnings: list[str]
) -> list[Step]:
    steps: list[Step] = []
    name = phase.filename

    for match in STEP_HEADING.finditer(body):
        step_id = f"{match.group(1)}.{match.group(2)}"
        if int(match.group(1)) != phase.number:
            problems.append(
                f"{name}: `Step {step_id}` belongs to phase {match.group(1)}"
            )
            continue

        following = NEXT_HEADING.search(body, match.end())
        section = body[match.end() : following.start() if following else len(body)]
        section = GUIDANCE_COMMENT.sub("", section)

        status_match = STATUS_LINE.search(section)
        if not status_match:
            problems.append(f"{name}: Step {step_id} has no `**Status:**` line")
            continue

        status, note = split_status(status_match.group(1))
        if status not in STATUSES:
            problems.append(
                f"{name}: Step {step_id} has status `{status}`, not one of "
                + ", ".join(STATUSES)
            )
            continue
        if status in ("In Progress", "Blocked") and not note:
            warnings.append(f"{name}: Step {step_id} is `{status}` with no note")

        target_match = TARGET_LINE.search(section)
        target = target_match.group(1).strip() if target_match else ""
        steps.append(Step(step_id, status, note, target))

    if not steps:
        warnings.append(f"{name}: phase {phase.number} has no steps")
    return steps


def split_status(raw: str) -> tuple[str, str]:
    parts = NOTE_SEPARATOR.split(raw.strip(), maxsplit=1)
    status = parts[0].strip()
    note = parts[1].strip() if len(parts) > 1 else ""
    return status, note


def read_prerequisites(body: str) -> list[tuple[bool, str]]:
    heading = PREREQUISITES_HEADING.search(body)
    if not heading:
        return []
    following = re.compile(r"^## ", re.MULTILINE).search(body, heading.end())
    section = body[heading.end() : following.start() if following else len(body)]
    section = GUIDANCE_COMMENT.sub("", section)
    return [
        (mark.lower() == "x", text) for mark, text in CHECKLIST_ITEM.findall(section)
    ]


def parse_hours(raw) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip().lstrip("~").removesuffix("hrs").removesuffix("h").strip()
    try:
        return float(text)
    except ValueError:
        return None


def find_cycle(phases: dict[int, Phase]) -> list[int] | None:
    state: dict[int, str] = {}
    trail: list[int] = []

    def visit(number: int) -> list[int] | None:
        state[number] = "open"
        trail.append(number)
        for dependency in phases[number].depends_on:
            if state.get(dependency) == "open":
                return trail[trail.index(dependency) :] + [dependency]
            if dependency not in state:
                found = visit(dependency)
                if found:
                    return found
        trail.pop()
        state[number] = "closed"
        return None

    for number in sorted(phases):
        if number not in state:
            found = visit(number)
            if found:
                return found
    return None


def ancestors(plan: Plan, number: int) -> set[int]:
    seen: set[int] = set()
    pending = list(plan.phases[number].depends_on)
    while pending:
        current = pending.pop()
        if current not in seen:
            seen.add(current)
            pending.extend(plan.phases[current].depends_on)
    return seen


def overlap_warnings(plan: Plan) -> list[str]:
    """
    Two phases with no path between them are claimed parallel-safe; editing the
    same target, they are not, and two sessions would collide on the file.
    """
    by_target: dict[str, list[int]] = {}
    for phase in plan.phases.values():
        for target in {step.target for step in phase.steps if step.target}:
            by_target.setdefault(target, []).append(phase.number)

    warnings = []
    for target, numbers in sorted(by_target.items()):
        numbers = sorted(numbers)
        for index, first in enumerate(numbers):
            for second in numbers[index + 1 :]:
                if first not in ancestors(plan, second) and second not in ancestors(
                    plan, first
                ):
                    warnings.append(
                        f"phases {first} and {second} both target {target} with no "
                        "dependency between them; add one, or merge them"
                    )
    return warnings


# --- the generated block ----------------------------------------------------


def hours(value: float) -> str:
    return f"{value:g}"


def status_cell(phase: Phase) -> str:
    cell = STATUS_CELLS[phase.status]
    if phase.status == "Blocked":
        blocked = [step.id for step in phase.steps if step.status == "Blocked"]
        cell += f" ({', '.join(blocked)})"
    elif phase.status == "In Progress":
        done = sum(1 for step in phase.steps if step.status == "Done")
        cell += f" ({done} / {len(phase.steps)} steps)"
    return cell


def mermaid_label(phase: Phase) -> str:
    title = phase.title.replace('"', "#quot;")
    return (
        f'p{phase.number}["{phase.number} · {title}<br/>~{hours(phase.estimate)} hrs"]'
    )


def mermaid_class(plan: Plan, phase: Phase) -> str:
    if phase.status == "Done":
        return "done"
    if phase.status == "Blocked":
        return "blocked"
    if phase.status == "In Progress":
        return "progress"
    return "ready" if plan.readiness(phase)[0] else "waiting"


def render_block(plan: Plan) -> str:
    phases = plan.ordered()
    total = sum(phase.estimate for phase in phases)
    done = sum(1 for phase in phases if phase.status == "Done")
    ready = sum(1 for phase in phases if plan.readiness(phase)[0])
    chain, chain_hours = plan.critical_path()

    rows = [
        "| Phase | Depends on | Activity | Estimate | Status | Ready |",
        "| ----- | ---------- | -------- | -------- | ------ | ----- |",
    ]
    for phase in phases:
        depends = ", ".join(str(number) for number in phase.depends_on) or "—"
        rows.append(
            f"| [Phase {phase.number}: {phase.title}]({phase.filename}) | {depends} "
            f"| {phase.activity} | ~{hours(phase.estimate)} hrs | {status_cell(phase)} "
            f"| {plan.readiness(phase)[1]} |"
        )
    rows.append(
        f"| **Total** | | | **~{hours(total)} hrs** | {done} / {len(phases)} phases done "
        f"| {ready} ready |"
    )

    graph = ["```mermaid", "flowchart LR"]
    graph += [f"    {mermaid_label(phase)}" for phase in phases]
    graph += [
        f"    p{dependency} --> p{phase.number}"
        for phase in phases
        for dependency in phase.depends_on
    ]
    graph += [
        f"    class p{phase.number} {mermaid_class(plan, phase)}" for phase in phases
    ]
    graph += [
        "    classDef done fill:#d4edda,stroke:#28a745",
        "    classDef progress fill:#fff3cd,stroke:#e0a800",
        "    classDef blocked fill:#f8d7da,stroke:#dc3545",
        "    classDef ready fill:#cce5ff,stroke:#0069d9",
        "    classDef waiting fill:#f8f9fa,stroke:#adb5bd",
        "```",
    ]

    path = " → ".join(str(number) for number in chain)
    return "\n".join(
        [
            BLOCK_START,
            "",
            "## Progress",
            "",
            *rows,
            "",
            (
                f"**Critical path:** {path} (~{hours(chain_hours)} hrs) — the shortest this "
                "plan can take, however many phases run in parallel."
            ),
            "",
            "## Dependency graph",
            "",
            *graph,
            "",
            BLOCK_END,
        ]
    )


def report(plan: Plan) -> dict:
    chain, chain_hours = plan.critical_path()
    phases = []
    for phase in plan.ordered():
        is_ready, reason = plan.readiness(phase)
        phases.append(
            {
                "number": phase.number,
                "title": phase.title,
                "file": str(phase.path),
                "activity": phase.activity,
                "estimate": phase.estimate,
                "depends_on": phase.depends_on,
                "projects": phase.projects,
                "status": phase.status,
                "ready": is_ready,
                "ready_reason": reason,
                "open_prerequisites": phase.open_prerequisites,
                "steps": [step.as_dict() for step in phase.steps],
            }
        )

    return {
        "plan": str(plan.index),
        "plan_dir": str(plan.directory),
        "phases": phases,
        "ready": [phase["number"] for phase in phases if phase["ready"]],
        "in_flight": [
            phase["number"]
            for phase in phases
            if phase["status"] in ("In Progress", "Blocked")
        ],
        "done": sum(1 for phase in phases if phase["status"] == "Done"),
        "total_hours": sum(phase.estimate for phase in plan.phases.values()),
        "critical_path": {"phases": chain, "hours": chain_hours},
        "warnings": plan.warnings,
    }


def sync(plan_dir: Path, dry_run: bool = False) -> dict:
    """Rewrite plan.md's generated block from the phase files, and report the plan."""
    plan = load(plan_dir)
    with plan.index.open(encoding="utf-8", newline="") as handle:
        text = handle.read()

    if not BLOCK_PATTERN.search(text):
        raise TicketError(
            f"{plan.index} has no generated block",
            EXIT_ERROR,
            f"Add a line holding `{BLOCK_START}` and one holding `{BLOCK_END}` "
            "where the Progress table belongs, then run this again.",
        )

    newline = "\r\n" if "\r\n" in text else "\n"
    block = render_block(plan).replace("\n", newline)
    updated = BLOCK_PATTERN.sub(lambda _: block, text, count=1)
    stale = updated != text

    if stale and not dry_run:
        with plan.index.open("w", encoding="utf-8", newline="") as handle:
            handle.write(updated)

    result = report(plan)
    result.update({"stale": stale, "written": stale and not dry_run})
    return result


# --- renumbering ------------------------------------------------------------


def topological_order(plan: Plan, requested: list[int] | None) -> list[int]:
    """
    The phases after phase 0, in the order they will be numbered.

    Without a requested order, a stable topological sort: the current numbers
    already encode the planner's tie-breaks, so they are kept wherever the
    graph allows. Lifecycle and estimate are judgments the planner makes and
    passes in as `requested`; this only checks the graph agrees.
    """
    numbered = [
        number for number in sorted(plan.phases) if number != PREREQUISITES_PHASE
    ]

    if requested is not None:
        if sorted(requested) != numbered:
            raise TicketError(
                "--order must list every phase after 0 exactly once",
                EXIT_ERROR,
                "The phases are " + ", ".join(str(number) for number in numbered) + ".",
            )
        placed: set[int] = {PREREQUISITES_PHASE}
        for number in requested:
            missing = [
                dependency
                for dependency in plan.phases[number].depends_on
                if dependency not in placed
            ]
            if missing:
                raise TicketError(
                    f"--order puts phase {number} before "
                    + ", ".join(str(dependency) for dependency in missing)
                    + ", which it depends on",
                    EXIT_ERROR,
                )
            placed.add(number)
        return requested

    order: list[int] = []
    placed = {PREREQUISITES_PHASE}
    remaining = list(numbered)
    while remaining:
        number = next(
            candidate
            for candidate in remaining
            if all(
                dependency in placed for dependency in plan.phases[candidate].depends_on
            )
        )
        order.append(number)
        placed.add(number)
        remaining.remove(number)
    return order


def step_directories(artifacts_dir: Path) -> dict[int, list[Path]]:
    found: dict[int, list[Path]] = {}
    if not artifacts_dir.is_dir():
        return found
    for path in artifacts_dir.iterdir():
        match = re.fullmatch(r"step-(\d+)\.(\d+)", path.name)
        if path.is_dir() and match:
            found.setdefault(int(match.group(1)), []).append(path)
    return found


def reference_rewriter(mapping: dict[int, int], slugs: dict[int, str]):
    """
    One pass, every reference at once: a sequential pass would turn 1 → 2 and
    then that same 2 → 3.
    """
    slug_alternatives = "|".join(
        re.escape(slug) for slug in sorted(set(slugs.values()))
    )
    patterns = [
        re.compile(r"(?<![\w.])([Ss]tep[ -])(\d+)(\.\d+)(?!\d)"),
        re.compile(r"\b(Phase )(\d+)\b()"),
    ]
    file_pattern = (
        re.compile(rf"(?<![\w-])()(\d+)(-(?:{slug_alternatives})\.md)")
        if slug_alternatives
        else None
    )

    def renumber(match: re.Match) -> str:
        number = int(match.group(2))
        if number not in mapping:
            return match.group(0)
        return f"{match.group(1)}{mapping[number]}{match.group(3)}"

    def renumber_file(match: re.Match) -> str:
        number = int(match.group(2))
        if number not in mapping or f"-{slugs.get(number)}.md" != match.group(3):
            return match.group(0)
        return f"{mapping[number]}{match.group(3)}"

    def rewrite(text: str) -> str:
        for pattern in patterns:
            text = pattern.sub(renumber, text)
        if file_pattern:
            text = file_pattern.sub(renumber_file, text)
        return text

    return rewrite


def rewrite_frontmatter(text: str, mapping: dict[int, int]) -> str:
    def replace(match: re.Match) -> str:
        key, value, carriage_return = match.group(1), match.group(2), match.group(3)
        if key == "number":
            number = int(value)
            return f"{key}: {mapping.get(number, number)}{carriage_return}"
        items = [item.strip() for item in value.strip("[] ").split(",") if item.strip()]
        renumbered = sorted(
            mapping.get(int(item), int(item)) for item in items if item.isdigit()
        )
        return (
            f"{key}: [{', '.join(str(item) for item in renumbered)}]{carriage_return}"
        )

    head, fence, rest = text.partition("\n---")
    head = re.sub(
        r"^(number|depends_on):[ \t]*(.*?)[ \t]*(\r?)$",
        replace,
        head,
        flags=re.MULTILINE,
    )
    return head + fence + rest


def read_text(path: Path) -> str | None:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return handle.read()
    except (UnicodeDecodeError, OSError):
        return None


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def renumber(
    plan_dir: Path, artifacts_dir: Path, requested: list[int] | None, dry_run: bool
) -> dict:
    """
    Number the phases in topological order, and finish the whole rename in one pass.

    Refused while any phase is In Progress: another session may be writing
    into one of the `artifacts/step-{N}.{M}/` directories this would rename.
    """
    plan = load(plan_dir)

    in_progress = [
        phase.number for phase in plan.ordered() if phase.status == "In Progress"
    ]
    if in_progress:
        raise TicketError(
            "cannot renumber while phase "
            + ", ".join(str(number) for number in in_progress)
            + " is In Progress",
            EXIT_ERROR,
            "Another session may be writing into its artifacts directory. Keep the "
            "current numbers until no phase is In Progress — gaps and out-of-order "
            "numbers are tolerated until then.",
        )

    order = topological_order(plan, requested)
    mapping = {old: new for new, old in enumerate(order, start=1) if old != new}
    if not mapping:
        return {"changed": False, "mapping": {}, "plan": str(plan.index)}

    slugs = {number: phase.slug for number, phase in plan.phases.items()}
    file_renames = [
        (plan.phases[old].path, plan_dir / f"{new}-{slugs[old]}.md")
        for old, new in mapping.items()
    ]

    directories = step_directories(artifacts_dir)
    directory_renames = [
        (path, path.with_name("step-" + str(new) + path.name[len(f"step-{old}") :]))
        for old, new in mapping.items()
        for path in directories.get(old, [])
    ]

    moving_away = {source for source, _ in directory_renames}
    collisions = [
        str(destination)
        for _, destination in directory_renames
        if destination.exists() and destination not in moving_away
    ]
    if collisions:
        raise TicketError(
            "renumbering would overwrite an artifacts directory no phase owns: "
            + ", ".join(collisions),
            EXIT_ERROR,
            "Rename or remove the orphaned directory first — artifacts are never overwritten.",
        )

    rewrite = reference_rewriter(mapping, slugs)
    text_files = [path for path in sorted(plan_dir.glob("*.md"))]
    if artifacts_dir.is_dir():
        text_files += [
            path
            for path in sorted(artifacts_dir.rglob("*"))
            if path.is_file() and not CAPTURE_FILE.search(path.name)
        ]

    edits: dict[Path, str] = {}
    phase_files = {phase.path for phase in plan.phases.values()}
    for path in text_files:
        text = read_text(path)
        if text is None:
            continue
        updated = rewrite(text)
        if path in phase_files:
            updated = rewrite_frontmatter(updated, mapping)
        if updated != text:
            edits[path] = updated

    result = {
        "changed": True,
        "dry_run": dry_run,
        "mapping": {str(old): new for old, new in sorted(mapping.items())},
        "renamed_files": [
            {"from": source.name, "to": destination.name}
            for source, destination in file_renames
        ],
        "renamed_directories": [
            {"from": source.name, "to": destination.name}
            for source, destination in directory_renames
        ],
        "edited_files": [str(path) for path in edits],
    }
    if dry_run:
        return result

    for path, text in edits.items():
        write_text(path, text)

    # Two passes through temporary names, so swapping 1 and 2 never collides.
    for renames in (file_renames, directory_renames):
        staged = []
        for source, destination in renames:
            temporary = source.with_name(f".renumber-{os.getpid()}-{source.name}")
            source.rename(temporary)
            staged.append((temporary, destination))
        for temporary, destination in staged:
            temporary.rename(destination)

    result["sync"] = sync(plan_dir)
    return result
