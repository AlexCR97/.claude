"""The `connection` verb: profiles in the connections home, listed and checked through the command line."""

import zipfile
from pathlib import Path

import pytest


def test_list_shows_a_profile_without_any_of_its_values(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=abc123456\n")

    result = run_cli("connection", "list")

    assert result.code == 0, result.err
    connections = result.json["connections"]
    assert [(entry["profile"], entry["kind"]) for entry in connections] == [
        ("qa", "rest")
    ]
    assert "abc123456" not in result.out + result.err


def test_list_is_empty_when_there_is_no_connections_home(run_cli):
    result = run_cli("connection", "list")

    assert result.code == 0, result.err
    assert result.json["connections"] == []


def test_check_reports_a_valid_profile_by_key_names_alone(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=abc123456\n")

    result = run_cli("connection", "check")

    assert result.code == 0, result.err
    assert result.json["ok"] is True
    [report] = result.json["profiles"]
    assert report["profile"] == "qa"
    assert report["problems"] == []
    assert report["keys"] == ["CONNECTION_KIND", "TOKEN"]
    assert "abc123456" not in result.out + result.err


def test_check_names_a_missing_kind(run_cli, write_profile):
    write_profile("qa", "TOKEN=abc123456\n")

    result = run_cli("connection", "check")

    assert result.code == 1
    [report] = result.json["profiles"]
    assert report["ok"] is False
    assert any("CONNECTION_KIND" in problem for problem in report["problems"])


def test_check_names_a_reference_to_an_undefined_variable_without_any_value(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=tok-${MISSING_VARIABLE}-end\n")

    result = run_cli("connection", "check")

    assert result.code == 1
    [problem] = result.json["profiles"][0]["problems"]
    assert "TOKEN" in problem
    assert "MISSING_VARIABLE" in problem
    assert "tok-" not in result.out + result.err


def test_check_names_the_line_that_is_not_an_assignment(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nthis is not an assignment\n")

    result = run_cli("connection", "check")

    assert result.code == 1
    [problem] = result.json["profiles"][0]["problems"]
    assert "line 2" in problem
    assert "this is not" not in result.out + result.err


def test_check_resolves_a_reference_from_the_process_environment(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=tok-${SCRATCH_SECRET}\n")

    result = run_cli("connection", "check", env={"SCRATCH_SECRET": "abcd1234"})

    assert result.code == 0, result.err
    assert result.json["profiles"][0]["problems"] == []
    assert "abcd1234" not in result.out + result.err


def test_check_resolves_a_reference_to_an_earlier_key_of_the_same_file(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nBASE=base-value\nURL=${BASE}/v1\n")

    result = run_cli("connection", "check")

    assert result.code == 0, result.err
    assert result.json["profiles"][0]["problems"] == []


def test_a_reference_to_a_later_key_is_not_defined_yet(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nURL=${BASE}/v1\nBASE=base-value\n")

    result = run_cli("connection", "check")

    assert result.code == 1
    assert "BASE" in result.json["profiles"][0]["problems"][0]


def test_check_lists_the_keys_of_the_referenced_env_file(
    run_cli, write_profile, sdlc_home, tmp_path
):
    project_env = tmp_path / "project.env"
    project_env.write_text("API_KEY=key-value-1\nTOKEN=from-file\n", encoding="utf-8")
    nested = sdlc_home / ".connections" / "refs"
    nested.mkdir(parents=True)
    (nested / "relative.env").write_text("DB_PASSWORD=pw-value-1\n", encoding="utf-8")
    write_profile(
        "absolute",
        f"CONNECTION_KIND=rest\nCONNECTION_ENV_FILE={project_env}\nTOKEN=own-token\n",
    )
    write_profile(
        "relative", "CONNECTION_KIND=rest\nCONNECTION_ENV_FILE=refs/relative.env\n"
    )

    result = run_cli("connection", "check")

    assert result.code == 0, result.err
    reports = {report["profile"]: report for report in result.json["profiles"]}
    assert reports["absolute"]["keys"] == [
        "CONNECTION_KIND",
        "CONNECTION_ENV_FILE",
        "TOKEN",
        "API_KEY",
    ]
    assert reports["relative"]["keys"] == [
        "CONNECTION_KIND",
        "CONNECTION_ENV_FILE",
        "DB_PASSWORD",
    ]
    assert "key-value-1" not in result.out + result.err
    assert "pw-value-1" not in result.out + result.err


def test_check_names_a_referenced_env_file_that_is_missing(run_cli, write_profile):
    write_profile(
        "qa", "CONNECTION_KIND=rest\nCONNECTION_ENV_FILE=nowhere/project.env\n"
    )

    result = run_cli("connection", "check")

    assert result.code == 1
    [problem] = result.json["profiles"][0]["problems"]
    assert "nowhere" in problem
    assert "project.env" in problem


def test_check_warns_that_a_short_value_will_not_be_masked(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nPIN=12\n")

    result = run_cli("connection", "check")

    assert result.code == 0, result.err
    report = result.json["profiles"][0]
    assert report["ok"] is True
    [warning] = report["warnings"]
    assert "PIN" in warning
    assert "12" not in warning


@pytest.mark.parametrize(
    ("profile", "production", "source"),
    [
        ("edx-prod", True, "name"),
        ("edgraph-prod-usc", True, "name"),
        ("dev-prod-mirror", True, "name"),
        ("production", True, "name"),
        ("edx-preprod", False, "name"),
        ("edx-pre-prod", False, "name"),
        ("qa", False, "name"),
        ("localhost", False, "name"),
        ("edx-int", False, "name"),
        ("acme", True, "default"),
    ],
)
def test_list_marks_production_by_the_profile_name(
    run_cli, write_profile, profile, production, source
):
    write_profile(profile, "CONNECTION_KIND=rest\n")

    result = run_cli("connection", "list")

    [entry] = result.json["connections"]
    assert entry["production"] is production
    assert entry["production_source"] == source


@pytest.mark.parametrize(
    ("profile", "flag", "production"),
    [
        ("qa", "true", True),
        ("acme", "false", False),
        ("qa", "maybe", True),
    ],
)
def test_the_profile_flag_beats_the_name_and_an_unreadable_flag_is_production(
    run_cli, write_profile, profile, flag, production
):
    write_profile(profile, f"CONNECTION_KIND=rest\nCONNECTION_PRODUCTION={flag}\n")

    result = run_cli("connection", "list")

    [entry] = result.json["connections"]
    assert entry["production"] is production
    assert entry["production_source"] == "profile"


def test_check_names_an_unreadable_production_flag(run_cli, write_profile):
    write_profile("qa", "CONNECTION_KIND=rest\nCONNECTION_PRODUCTION=maybe\n")

    result = run_cli("connection", "check")

    assert result.code == 1
    [problem] = result.json["profiles"][0]["problems"]
    assert "CONNECTION_PRODUCTION" in problem
    assert "true or false" in problem


def test_the_connections_home_never_reaches_an_export_or_a_namespace_listing(
    run_cli, write_profile, write_config, make_ticket, tmp_path: Path
):
    write_config("acme/namespace.json", {"sources": {"github": {"owner": "acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"github": {"repository": "billing-app"}}},
    )
    (make_ticket("acme", "billing-app", "github", "1234") / "ticket.json").write_text(
        "{}", encoding="utf-8"
    )
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=export-leak-canary\n")

    exported = run_cli("archive", "export", cwd=tmp_path)
    listed = run_cli("archive", "export", ".connections", cwd=tmp_path)

    assert exported.code == 0, exported.err
    with zipfile.ZipFile(exported.json["archive"]) as archive:
        assert not [name for name in archive.namelist() if ".connections" in name]
        assert all(
            b"export-leak-canary" not in archive.read(name)
            for name in archive.namelist()
        )
    assert listed.code == 1
    assert "not a valid namespace name" in listed.err
