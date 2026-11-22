"""One seam: the `sdlc.py` command line, run as a subprocess against a scratch SDLC_HOME."""

import json
import os
import subprocess
import sys
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
