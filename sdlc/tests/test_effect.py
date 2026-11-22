"""The `effect` verb: whether a script may run without asking, through the command line."""

import pytest

READ_ONLY_SQL = (
    "-- effect: read-only\nSELECT COUNT(*) FROM Invoices WHERE Active = 1;\n"
)
READ_ONLY_PY = (
    "#!/usr/bin/env python3\n# effect: read-only\nimport json\n"
    "print(json.dumps({'count': 3}))\n"
)


def check(run_cli, tmp_path, text, name="probe.py"):
    script = tmp_path / name
    script.write_text(text, encoding="utf-8")
    result = run_cli("effect", str(script))
    assert result.code == 0, result.err
    return result.json


def check_in_context(run_cli, tmp_path, text, context):
    script = tmp_path / "probe.py"
    script.write_text(text, encoding="utf-8")
    result = run_cli("effect", str(script), "--context", context)
    assert result.code == 0, result.err
    return result.json


def test_a_verified_read_only_script_runs_without_asking(run_cli, tmp_path):
    verdict = check(run_cli, tmp_path, READ_ONLY_PY)

    assert verdict["run_without_asking"] is True
    assert verdict["declared_effect"] == "read-only"
    assert verdict["reasons"] == []


def test_a_read_only_sql_header_is_accepted(run_cli, tmp_path):
    assert check(run_cli, tmp_path, READ_ONLY_SQL, "probe.sql")["run_without_asking"]


def test_a_script_declaring_writes_asks(run_cli, tmp_path):
    verdict = check(
        run_cli, tmp_path, "# effect: writes\nopen('x.txt', 'w').write('1')\n"
    )

    assert verdict["run_without_asking"] is False
    assert verdict["declared_effect"] == "writes"


def test_a_script_with_no_header_asks(run_cli, tmp_path):
    verdict = check(run_cli, tmp_path, "print('hi')\n")

    assert verdict["run_without_asking"] is False
    assert "no `effect:`" in verdict["reasons"][0]


@pytest.mark.parametrize(
    "body",
    [
        "open('out.txt', 'w').write('x')",
        "from pathlib import Path\nPath('a').write_text('x')",
        "import os\nos.remove('a')",
        "import shutil\nshutil.rmtree('a')",
        "import subprocess\nsubprocess.run(['ls'])",
        "import requests\nrequests.post('https://x', json={})",
        "print(1)\n# next line\nos.system('rm -rf x')",
        "subprocess.run(['git', 'commit', '-m', 'x'])",
        "run('pip install requests')",
    ],
)
def test_a_header_that_disagrees_with_the_code_falls_back_to_asking(
    run_cli, tmp_path, body
):
    verdict = check(run_cli, tmp_path, f"# effect: read-only\n{body}\n")

    assert verdict["run_without_asking"] is False
    assert "header says read-only but the code" in verdict["reasons"][0]


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO t VALUES (1);",
        "UPDATE t SET a = 1;",
        "DELETE FROM t;",
        "DROP TABLE t;",
    ],
)
def test_a_mutating_statement_contradicts_a_read_only_sql_header(
    run_cli, tmp_path, statement
):
    verdict = check(run_cli, tmp_path, f"-- effect: read-only\n{statement}\n", "p.sql")

    assert verdict["run_without_asking"] is False


def test_a_comment_mentioning_a_write_is_not_a_write(run_cli, tmp_path):
    text = "# effect: read-only\n# never DELETE FROM anything here\nprint(1)\n"

    assert check(run_cli, tmp_path, text)["run_without_asking"] is True


def test_a_read_only_script_declared_heavy_still_asks(run_cli, tmp_path):
    verdict = check(run_cli, tmp_path, "# effect: read-only\n# cost: heavy\nprint(1)\n")

    assert verdict["run_without_asking"] is False
    assert verdict["cost"] == "heavy"


def test_a_sensitive_target_still_asks(run_cli, write_config, tmp_path):
    write_config("sdlc.json", {"sensitive": ["prod-db.internal"]})

    verdict = check(
        run_cli,
        tmp_path,
        "# effect: read-only\nCONNECTION = 'Server=prod-db.internal;Db=x'\nprint(1)\n",
    )

    assert verdict["run_without_asking"] is False
    assert "sensitive" in verdict["reasons"][0]


def test_no_sensitive_list_ships_by_default(run_cli, tmp_path):
    verdict = check(run_cli, tmp_path, "# effect: read-only\nprint('prod')\n")

    assert verdict["run_without_asking"] is True


def test_a_header_below_the_first_lines_is_not_a_header(run_cli, tmp_path):
    filler = "\n".join("x = 1" for _ in range(30))
    verdict = check(run_cli, tmp_path, f"{filler}\n# effect: read-only\n")

    assert verdict["run_without_asking"] is False


def test_an_unreadable_script_asks(run_cli, tmp_path):
    script = tmp_path / "probe.bin"
    script.write_bytes(b"\xff\xfe\x00\x01")

    result = run_cli("effect", str(script))

    assert result.json["run_without_asking"] is False


def test_a_missing_script_is_an_error(run_cli, tmp_path):
    assert run_cli("effect", str(tmp_path / "nope.py")).code == 1


SENSITIVE_SCRIPT = "# effect: read-only\nHOST = 'prod-db.internal'\nprint(HOST)\n"


def test_a_sensitive_target_listed_at_the_product_level_asks_in_that_context(
    run_cli, write_config, tmp_path
):
    write_config("acme/billing-app/product.json", {"sensitive": ["prod-db.internal"]})

    verdict = check_in_context(run_cli, tmp_path, SENSITIVE_SCRIPT, "acme/billing-app")

    assert verdict["run_without_asking"] is False
    assert "prod-db.internal" in verdict["reasons"][0]


def test_a_sensitive_target_of_another_product_does_not_apply(
    run_cli, write_config, tmp_path
):
    write_config("acme/billing-app/product.json", {"sensitive": ["prod-db.internal"]})
    write_config("acme/notes-app/product.json", {})

    verdict = check_in_context(run_cli, tmp_path, SENSITIVE_SCRIPT, "acme/notes-app")

    assert verdict["run_without_asking"] is True


def test_a_product_list_replaces_the_inherited_one(run_cli, write_config, tmp_path):
    write_config("sdlc.json", {"sensitive": ["prod-db.internal"]})
    write_config("acme/billing-app/product.json", {"sensitive": ["other-host"]})

    verdict = check_in_context(run_cli, tmp_path, SENSITIVE_SCRIPT, "acme/billing-app")

    assert verdict["run_without_asking"] is True


def test_a_sensitive_setting_must_be_a_list_of_strings(run_cli, write_config, tmp_path):
    write_config("sdlc.json", {"sensitive": "prod-db.internal"})
    script = tmp_path / "probe.py"
    script.write_text(SENSITIVE_SCRIPT, encoding="utf-8")

    result = run_cli("effect", str(script))

    assert result.code == 1
    assert "sensitive" in result.err


def test_a_context_naming_nothing_on_disk_is_an_error_like_every_other_verb(
    run_cli, write_config, tmp_path
):
    write_config("acme/billing-app/product.json", {})
    script = tmp_path / "probe.py"
    script.write_text(READ_ONLY_PY, encoding="utf-8")

    result = run_cli("effect", str(script), "--context", "ghost")

    assert result.code == 1
    assert "ghost" in result.err
