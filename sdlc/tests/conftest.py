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
    def run(*argv: str) -> Result:
        completed = subprocess.run(
            [sys.executable, str(SDLC), *argv],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "SDLC_HOME": str(sdlc_home)},
        )
        return Result(completed.returncode, completed.stdout, completed.stderr)

    return run
