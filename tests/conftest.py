"""
Fixtures for driving the ticket resolver the way a skill does.

Every test goes through `ticket.py`'s command line against a scratch tickets
home. Nothing here touches the network or a real credential: `gh` is a stub
process on the path, and Azure DevOps is stubbed where its HTTP leaves the
process.
"""

import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"
COMMON = SKILLS / "ticket-common"


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def json(self) -> dict:
        # A provider may print progress before the front door emits its report.
        lines = self.out.splitlines()
        start = max(i for i, line in enumerate(lines) if line == "{") if "{" in lines else 0
        return json.loads(os.linesep.join(lines[start:]))


def load_ticket_module():
    sys.path.insert(0, str(COMMON))
    spec = importlib.util.spec_from_file_location("ticket_cli", COMMON / "ticket.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def tickets_home(tmp_path, monkeypatch) -> Path:
    home = tmp_path / "tickets"
    home.mkdir()
    monkeypatch.setenv("TICKETS_HOME", str(home))
    return home


@pytest.fixture
def run_cli(tickets_home, capsys, monkeypatch) -> Callable[..., Result]:
    module = load_ticket_module()

    def run(*argv: str, cwd: Path | None = None) -> Result:
        monkeypatch.setattr(sys, "argv", ["ticket.py", *argv])
        if cwd:
            monkeypatch.chdir(cwd)
        capsys.readouterr()
        code = module.main()
        captured = capsys.readouterr()
        return Result(code, captured.out, captured.err)

    return run


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


@dataclass
class Repository:
    path: Path
    remote: Path

    def git(self, *args: str) -> str:
        return git(self.path, *args)

    def commit(self, name: str, text: str = "x") -> None:
        (self.path / name).write_text(text, encoding="utf-8")
        self.git("add", name)
        self.git("commit", "-m", f"add {name}")


@pytest.fixture
def make_repository(tmp_path) -> Callable[..., Repository]:
    """A repository with a local bare repository as its `origin`, on `main`."""

    def make(name: str = "repo") -> Repository:
        remote = tmp_path / f"{name}.git"
        path = tmp_path / name
        path.mkdir()
        git(tmp_path, "init", "--bare", "--initial-branch=main", str(remote))
        git(path, "init", "--initial-branch=main")
        git(path, "config", "user.email", "test@example.com")
        git(path, "config", "user.name", "Test")
        git(path, "config", "commit.gpgsign", "false")
        git(path, "remote", "add", "origin", str(remote))
        repository = Repository(path, remote)
        repository.commit("README.md")
        git(path, "push", "-u", "origin", "main")
        git(path, "remote", "set-head", "origin", "main")
        return repository

    return make


@pytest.fixture
def repository(make_repository) -> Repository:
    return make_repository()


@dataclass
class GhStub:
    """A `gh` on the path that answers from a script and records every call."""

    directory: Path
    log: Path
    responses: Path

    def respond(self, matcher: str, stdout: str = "", code: int = 0) -> None:
        table = json.loads(self.responses.read_text(encoding="utf-8"))
        table.insert(0, {"match": matcher, "stdout": stdout, "code": code})
        self.responses.write_text(json.dumps(table), encoding="utf-8")

    @property
    def calls(self) -> list[list[str]]:
        if not self.log.is_file():
            return []
        return [
            json.loads(line)
            for line in self.log.read_text(encoding="utf-8").splitlines()
        ]


GH_SCRIPT = """\
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
joined = " ".join(args)
if args[:2] == ["auth", "status"]:
    sys.stderr.write("Logged in to github.com as tester\\n")
    sys.exit(0)
with open(os.path.join(here, "responses.json"), encoding="utf-8") as handle:
    table = json.load(handle)
for entry in table:
    if entry["match"] in joined:
        sys.stdout.write(entry["stdout"])
        sys.exit(entry["code"])
sys.stderr.write("gh stub: no response for " + joined + "\\n")
sys.exit(1)
"""


@pytest.fixture
def gh_stub(tmp_path, monkeypatch) -> GhStub:
    directory = tmp_path / "gh-stub"
    directory.mkdir()
    (directory / "gh.py").write_text(GH_SCRIPT, encoding="utf-8")
    (directory / "responses.json").write_text("[]", encoding="utf-8")
    python = sys.executable
    if os.name == "nt":
        (directory / "gh.cmd").write_text(
            f'@echo off\r\n"{python}" "%~dp0gh.py" %*\r\n', encoding="utf-8"
        )
    else:
        launcher = directory / "gh"
        launcher.write_text(
            f'#!/bin/sh\nexec "{python}" "$(dirname "$0")/gh.py" "$@"\n',
            encoding="utf-8",
        )
        launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return GhStub(directory, directory / "calls.jsonl", directory / "responses.json")


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@dataclass
class AdoStub:
    """Azure DevOps as seen from the transport: URL substring in, JSON out."""

    routes: list[tuple[str, object]]
    requests: list[tuple[str, str]]

    def route(self, fragment: str, payload: object) -> None:
        self.routes.insert(0, (fragment, payload))


@pytest.fixture
def ado_stub(tickets_home, run_cli, monkeypatch) -> AdoStub:
    from ticketlib import tokencache

    stub = AdoStub(routes=[], requests=[])

    def urlopen(request, timeout=None):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        method = getattr(request, "method", None) or "GET"
        stub.requests.append((method, url))
        for fragment, payload in stub.routes:
            if fragment in url:
                body = payload(request) if callable(payload) else payload
                return _Response(json.dumps(body).encode())
        raise AssertionError(f"ado stub: no route for {method} {url}")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    token = {"accessToken": "fake", "expires_on": int(time.time()) + 3600}
    for organization in ("edwire", "contoso"):
        tokencache.save("ado", organization, token)
    return stub


def write_binding(
    home: Path,
    source: str,
    namespace: str,
    product: str,
    at_namespace: dict | None = None,
    at_product: dict | None = None,
) -> None:
    """Bind a source under a namespace and product by writing the config files."""
    for directory, values in (
        (home / namespace, at_namespace or {}),
        (home / namespace / product, at_product or {}),
    ):
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "config.json"
        existing = json.loads(path.read_text()) if path.is_file() else {}
        existing.setdefault("sources", {}).setdefault(source, {}).update(values)
        path.write_text(json.dumps(existing), encoding="utf-8")


@pytest.fixture
def ado_bound(tickets_home) -> None:
    """The `contoso/big-project` product bound to Azure DevOps."""
    write_binding(
        tickets_home,
        "ado",
        "contoso",
        "big-project",
        at_namespace={"organization": "contoso"},
        at_product={"project": "Big Project"},
    )
