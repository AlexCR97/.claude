"""`connection run`: a child gets a profile's variables, and the caller never sees a value."""

import sys

PYTHON = sys.executable


def run_child(run_cli, profile, code, *arguments, **options):
    return run_cli(
        "connection", "run", profile, "--", PYTHON, "-c", code, *arguments, **options
    )


def test_the_child_receives_the_values_and_the_caller_never_sees_them(
    run_cli, write_profile, tmp_path
):
    seen = tmp_path / "seen.txt"
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")
    code = (
        "import os, sys\n"
        "value = os.environ['TOKEN']\n"
        "open(sys.argv[1], 'w').write(value)\n"
        "print(value)\n"
        "print(value, file=sys.stderr)\n"
    )

    result = run_child(run_cli, "qa", code, str(seen))

    assert result.code == 0, result.err
    assert seen.read_text(encoding="utf-8") == "s3cret-value"
    assert "s3cret-value" not in result.out + result.err
    envelope = result.json
    assert envelope["exit_code"] == 0
    assert envelope["stdout"].strip() == "***"
    assert envelope["stderr"].strip() == "***"


def test_the_reserved_connection_keys_are_not_passed_to_the_child(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_child(
        run_cli,
        "qa",
        "import os; print(os.environ.get('CONNECTION_KIND', 'absent'))",
    )

    assert result.code == 0, result.err
    assert result.json["stdout"].strip() == "absent"


def test_a_failing_child_still_exits_zero_and_reports_its_own_code(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_child(
        run_cli,
        "qa",
        "import os, sys; print(os.environ['TOKEN'], file=sys.stderr); sys.exit(3)",
    )

    assert result.code == 0, result.err
    envelope = result.json
    assert envelope["exit_code"] == 3
    assert envelope["stderr"].strip() == "***"


def test_values_reached_through_expansion_and_an_env_file_are_masked(
    run_cli, write_profile, tmp_path
):
    project_env = tmp_path / "project.env"
    project_env.write_text("API_KEY=file-key-9999\n", encoding="utf-8")
    write_profile(
        "qa",
        "CONNECTION_KIND=rest\n"
        f"CONNECTION_ENV_FILE={project_env}\n"
        "BASE=base-value-1\n"
        "URL=https://${BASE}/v1\n"
        "TOKEN=tok-${SCRATCH_SECRET}\n",
    )
    code = (
        "import os\n"
        "for name in ('URL', 'API_KEY', 'TOKEN'):\n"
        "    print(os.environ[name])\n"
    )

    result = run_child(run_cli, "qa", code, env={"SCRATCH_SECRET": "abcd1234"})

    assert result.code == 0, result.err
    assert result.json["stdout"].split() == ["***", "***", "***"]
    assert "file-key-9999" not in result.out
    assert "abcd1234" not in result.out


def test_a_value_shorter_than_four_characters_reaches_the_child_but_is_not_masked(
    run_cli, write_profile
):
    write_profile("qa", "CONNECTION_KIND=rest\nPIN=12\n")

    result = run_child(run_cli, "qa", "import os; print(os.environ['PIN'])")

    assert result.json["stdout"].strip() == "12"


def test_a_profile_with_problems_is_refused_and_the_child_does_not_run(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=tok-${MISSING_VARIABLE}\n")

    result = run_child(run_cli, "qa", "open(__import__('sys').argv[1], 'w')", str(ran))

    assert result.code == 1
    assert "connection check" in result.err
    assert not ran.exists()


def test_an_unknown_profile_is_an_error_naming_it(run_cli):
    result = run_cli("connection", "run", "nowhere", "--", PYTHON, "-c", "pass")

    assert result.code == 1
    assert "nowhere" in result.err


def touch_command(marker):
    return (PYTHON, "-c", "open(__import__('sys').argv[1], 'w')", str(marker))


def test_a_production_profile_is_refused_until_it_is_approved(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile("edx-prod", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    refused = run_cli("connection", "run", "edx-prod", "--", *touch_command(ran))

    assert refused.code == 4
    assert "production" in refused.json["reason"]
    assert "s3cret-value" not in refused.out + refused.err
    assert not ran.exists()

    approved = run_cli(
        "connection", "run", "--approved", "edx-prod", "--", *touch_command(ran)
    )

    assert approved.code == 0, approved.err
    assert approved.json["production"] is True
    assert ran.exists()


def test_an_unrecognised_profile_name_is_treated_as_production(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile("acme", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_cli("connection", "run", "acme", "--", *touch_command(ran))

    assert result.code == 4
    assert not ran.exists()


def test_a_non_production_profile_runs_without_approval(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_cli("connection", "run", "qa", "--", *touch_command(ran))

    assert result.code == 0, result.err
    assert result.json["production"] is False
    assert ran.exists()


def test_a_linked_production_environment_refuses_whatever_the_name_says(
    run_cli, write_config, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_config(
        "acme/billing-app/product.json",
        {
            "environments": [{"name": "live", "production": True}],
            "connections": [{"profile": "qa-db", "environment": "live"}],
        },
    )
    write_profile("qa-db", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_cli(
        "connection",
        "run",
        "--context",
        "acme/billing-app",
        "qa-db",
        "--",
        *touch_command(ran),
    )

    assert result.code == 4
    assert "environment" in result.json["reason"]
    assert not ran.exists()


def test_a_sensitive_profile_is_refused_until_it_is_approved(
    run_cli, write_config, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_config("acme/billing-app/product.json", {"sensitive": ["edx-int"]})
    write_profile("edx-int", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")
    context = ("--context", "acme/billing-app")

    refused = run_cli(
        "connection", "run", *context, "edx-int", "--", *touch_command(ran)
    )

    assert refused.code == 4
    assert "sensitive" in refused.json["reason"]
    assert not ran.exists()

    approved = run_cli(
        "connection",
        "run",
        *context,
        "--approved",
        "edx-int",
        "--",
        *touch_command(ran),
    )

    assert approved.code == 0, approved.err
    assert ran.exists()


def test_a_sensitive_pattern_in_the_command_line_is_refused(
    run_cli, write_config, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_config("sdlc.json", {"sensitive": ["ledger-db.example.com"]})
    write_profile("qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_cli(
        "connection",
        "run",
        "qa",
        "--",
        *touch_command(ran),
        "https://ledger-db.example.com/accounts",
    )

    assert result.code == 4
    assert "ledger-db.example.com" in result.json["reason"]
    assert not ran.exists()


def test_a_dry_run_runs_nothing_and_reports_names_never_values(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile(
        "qa", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\nAPI_KEY=key-value-1\n"
    )

    result = run_cli(
        "connection",
        "run",
        "--dry-run",
        "qa",
        "--",
        *touch_command(ran),
        "Bearer s3cret-value",
    )

    assert result.code == 0, result.err
    assert not ran.exists()
    report = result.json
    assert report["dry_run"] is True
    assert report["variables"] == ["TOKEN", "API_KEY"]
    assert report["would_refuse"] is False
    assert report["command"][-1] == "Bearer ***"
    assert "s3cret-value" not in result.out + result.err
    assert "key-value-1" not in result.out + result.err


def test_a_dry_run_reports_a_refusal_instead_of_exiting_4(
    run_cli, write_profile, tmp_path
):
    ran = tmp_path / "ran.txt"
    write_profile("edx-prod", "CONNECTION_KIND=rest\nTOKEN=s3cret-value\n")

    result = run_cli(
        "connection", "run", "--dry-run", "edx-prod", "--", *touch_command(ran)
    )

    assert result.code == 0, result.err
    assert result.json["would_refuse"] is True
    assert "production" in result.json["reason"]
    assert not ran.exists()


def test_a_connection_string_key_reaches_the_child_and_is_masked(
    run_cli, write_profile
):
    write_profile(
        "qa",
        "CONNECTION_KIND=database\n"
        "CONNECTION_STRING=postgres://app:s3cret-pw@db.example.com/orders\n",
    )

    result = run_child(
        run_cli, "qa", "import os; print(os.environ['CONNECTION_STRING'])"
    )

    assert result.code == 0, result.err
    assert result.json["stdout"].strip() == "***"
    assert "s3cret-pw" not in result.out + result.err


def test_only_the_three_reserved_keys_are_withheld_from_the_child(
    run_cli, write_profile, tmp_path
):
    project_env = tmp_path / "project.env"
    project_env.write_text("API_KEY=file-key-9999\n", encoding="utf-8")
    write_profile(
        "qa",
        "CONNECTION_KIND=rest\n"
        "CONNECTION_PRODUCTION=false\n"
        f"CONNECTION_ENV_FILE={project_env}\n"
        "CONNECTION_STRING=postgres://app:s3cret-pw@db.example.com/orders\n",
    )

    result = run_child(
        run_cli,
        "qa",
        "import os; print(sorted(k for k in os.environ if k.startswith('CONNECTION_')))",
    )

    assert result.code == 0, result.err
    assert result.json["stdout"].strip() == "['CONNECTION_STRING']"
