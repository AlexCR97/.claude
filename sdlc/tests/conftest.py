"""One seam: the `sdlc.py` command line, run as a subprocess against a scratch SDLC_HOME."""

import base64
import json
import os
import subprocess
import sys
import textwrap
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

SDLC = Path(__file__).resolve().parents[1] / "shared" / "sdlc.py"


@dataclass
class Result:
    code: int
    out: str
    err: str

    @property
    def json(self) -> dict:
        return json.loads(self.out)


@pytest.fixture
def sdlc_home(tmp_path: Path) -> Path:
    return tmp_path / "sdlc-home"


@pytest.fixture
def run_cli(sdlc_home: Path):
    def run(*argv: str, cwd: Path | None = None) -> Result:
        completed = subprocess.run(
            [sys.executable, str(SDLC), *argv],
            check=False,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "SDLC_HOME": str(sdlc_home)},
        )
        return Result(completed.returncode, completed.stdout, completed.stderr)

    return run


@pytest.fixture
def write_config(sdlc_home: Path):
    """Write a config file at a path relative to the SDLC home; a dict becomes JSON, a string is written as is."""

    def write(relative: str, content: dict | str) -> Path:
        path = sdlc_home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = content if isinstance(content, str) else json.dumps(content)
        path.write_text(text, encoding="utf-8")
        return path

    return write


@pytest.fixture
def make_ticket(sdlc_home: Path):
    def make(namespace: str, product: str, source: str, ticket_id: str) -> Path:
        directory = sdlc_home / namespace / product / source / ticket_id
        directory.mkdir(parents=True)
        return directory

    return make


GH_STUB = textwrap.dedent(
    """
    import base64, json, sys
    from pathlib import Path

    here = Path(__file__).parent
    args = sys.argv[1:]
    calls = here / "calls.jsonl"
    with calls.open("a", encoding="utf-8") as log:
        log.write(json.dumps(args) + chr(10))

    routes = json.loads((here / "routes.json").read_text(encoding="utf-8"))

    def endpoint(arguments):
        rest = arguments[1:]
        skip = False
        for argument in rest:
            if skip:
                skip = False
            elif argument == "-H":
                skip = True
            elif not argument.startswith("-"):
                return argument
        return ""

    if args[:2] == ["auth", "status"]:
        route = routes.get("auth status", {"stderr": "Logged in to github.com"})
    elif args[:1] == ["api"]:
        path = endpoint(args)
        route = routes.get(path, {"stderr": "stub has no route for " + path, "code": 1})
    else:
        route = {"stderr": "stub does not handle: " + " ".join(args), "code": 1}

    if isinstance(route, list):
        counter = here / "counter.json"
        seen = json.loads(counter.read_text()) if counter.exists() else {}
        key = endpoint(args)
        index = seen.get(key, 0)
        seen[key] = index + 1
        counter.write_text(json.dumps(seen))
        route = route[min(index, len(route) - 1)]

    body = route.get("stdout", "")
    if "--slurp" in args and body:
        body = json.dumps([json.loads(body)])
    if "stdout_b64" in route:
        sys.stdout.buffer.write(base64.b64decode(route["stdout_b64"]))
    else:
        sys.stdout.write(body)
    sys.stderr.write(route.get("stderr", ""))
    sys.exit(route.get("code", 0))
    """
)


class GhStub:
    """A fake `gh` on PATH: answers `api <path>` from registered routes and logs every call."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.routes: dict = {}
        directory.mkdir()
        (directory / "stub.py").write_text(GH_STUB, encoding="utf-8")
        python = f'"{sys.executable}" "{directory / "stub.py"}"'
        if sys.platform == "win32":
            script = f"@echo off\r\n{python} %*\r\n"
            (directory / "gh.cmd").write_bytes(script.encode("utf-8"))
        else:
            launcher = directory / "gh"
            launcher.write_text(f'#!/bin/sh\nexec {python} "$@"\n', encoding="utf-8")
            launcher.chmod(0o755)
        self.save()

    def save(self) -> None:
        (self.directory / "routes.json").write_text(
            json.dumps(self.routes), encoding="utf-8"
        )

    def respond(self, path: str, payload: object) -> None:
        self.routes[path] = {"stdout": json.dumps(payload)}
        self.save()

    def respond_bytes(self, path: str, content: bytes) -> None:
        self.routes[path] = {"stdout_b64": base64.b64encode(content).decode()}
        self.save()

    def fail(self, path: str, message: str, code: int = 1) -> None:
        self.routes[path] = {"stderr": message, "code": code}
        self.save()

    def fail_then_respond(self, path: str, message: str, payload: object) -> None:
        self.routes[path] = [
            {"stderr": message, "code": 1},
            {"stdout": json.dumps(payload)},
        ]
        self.save()

    @property
    def calls(self) -> list[list[str]]:
        log = self.directory / "calls.jsonl"
        if not log.is_file():
            return []
        return [json.loads(line) for line in log.read_text("utf-8").splitlines()]

    def asked_for(self, path: str) -> bool:
        return any(path in call for call in self.calls)


@pytest.fixture
def gh_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GhStub:
    stub = GhStub(tmp_path / "gh-bin")
    monkeypatch.setenv("PATH", str(stub.directory) + os.pathsep + os.environ["PATH"])
    return stub


@pytest.fixture
def stub_issue(gh_stub: GhStub):
    """Register a whole issue (no parent, no relations, no comments) and let a test change any part."""

    def register(
        owner: str = "acme",
        repository: str = "billing-app",
        number: int = 1234,
        **parts,
    ) -> str:
        base = f"repos/{owner}/{repository}/issues/{number}"
        issue = {
            "number": number,
            "title": "Cache the ledger lookup",
            "state": "open",
            "body": "Lookups are slow.",
            "html_url": f"https://github.com/{owner}/{repository}/issues/{number}",
            "labels": [{"name": "enhancement"}],
            **parts.pop("issue", {}),
        }
        gh_stub.respond(base, issue)
        gh_stub.respond(f"{base}/comments", parts.pop("comments", []))
        gh_stub.respond(f"{base}/sub_issues", parts.pop("sub_issues", []))
        gh_stub.respond(f"{base}/dependencies/blocked_by", parts.pop("blocked_by", []))
        gh_stub.respond(f"{base}/dependencies/blocking", parts.pop("blocking", []))
        if "parent" in parts:
            gh_stub.respond(f"{base}/parent", parts.pop("parent"))
        else:
            gh_stub.fail(f"{base}/parent", "gh: No parent issue found (HTTP 404)")
        return base

    return register


AZ_STUB = textwrap.dedent(
    """
    import base64, json, sys
    from pathlib import Path

    here = Path(__file__).parent
    args = sys.argv[1:]
    with (here / "calls.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(args) + chr(10))

    routes = json.loads((here / "routes.json").read_text(encoding="utf-8"))

    def values(flag):
        if flag not in args:
            return []
        found = []
        for argument in args[args.index(flag) + 1 :]:
            if argument.startswith("--"):
                break
            found.append(argument)
        return found

    if args[:1] != ["rest"]:
        sys.stderr.write("stub does not handle: " + " ".join(args))
        sys.exit(1)

    url = values("--url")[0]
    params = sorted(p for p in values("--url-parameters") if not p.startswith("api-version="))
    key = url + ("?" + "&".join(params) if params else "")
    route = routes.get(key, {"stderr": "stub has no route for " + key, "code": 1})

    if "stderr" in route:
        sys.stderr.write(route["stderr"])
    output = Path(values("--output-file")[0])
    if "json" in route:
        output.write_text(json.dumps(route["json"]), encoding="utf-8")
    if "b64" in route:
        output.write_bytes(base64.b64decode(route["b64"]))
    sys.exit(route.get("code", 0))
    """
)


class AzStub:
    """
    A fake `az` on PATH that answers `az rest` from registered routes and logs every call.

    A route is the URL plus its sorted `--url-parameters` (without `api-version`),
    written `url?a=1&b=2`; the answer is written to `--output-file`, as `az` does.
    """

    def __init__(self, directory: Path):
        self.directory = directory
        self.routes: dict = {}
        directory.mkdir()
        (directory / "stub.py").write_text(AZ_STUB, encoding="utf-8")
        python = f'"{sys.executable}" "{directory / "stub.py"}"'
        if sys.platform == "win32":
            script = f"@echo off\r\n{python} %*\r\n"
            (directory / "az.cmd").write_bytes(script.encode("utf-8"))
        else:
            launcher = directory / "az"
            launcher.write_text(f'#!/bin/sh\nexec {python} "$@"\n', encoding="utf-8")
            launcher.chmod(0o755)
        self.save()

    def save(self) -> None:
        (self.directory / "routes.json").write_text(
            json.dumps(self.routes), encoding="utf-8"
        )

    def respond(self, route: str, payload: object) -> None:
        self.routes[route] = {"json": payload}
        self.save()

    def respond_bytes(self, route: str, content: bytes) -> None:
        self.routes[route] = {"b64": base64.b64encode(content).decode()}
        self.save()

    def fail(self, route: str, message: str, code: int = 1) -> None:
        self.routes[route] = {"stderr": message, "code": code}
        self.save()

    @property
    def calls(self) -> list[list[str]]:
        log = self.directory / "calls.jsonl"
        if not log.is_file():
            return []
        return [json.loads(line) for line in log.read_text("utf-8").splitlines()]

    def asked_for(self, fragment: str) -> bool:
        return any(fragment in " ".join(call) for call in self.calls)


@pytest.fixture
def az_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AzStub:
    stub = AzStub(tmp_path / "az-bin")
    monkeypatch.setenv("PATH", str(stub.directory) + os.pathsep + os.environ["PATH"])
    return stub


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
def make_repository(tmp_path: Path) -> Callable[..., Repository]:
    """A repository on `main` whose `origin` is a local bare repository, with `origin/HEAD` set."""

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
def repository(make_repository: Callable[..., Repository]) -> Repository:
    return make_repository()
