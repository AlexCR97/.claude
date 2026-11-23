from pathlib import Path


def test_a_new_ticket_is_reported_under_the_default_namespace_and_product(
    run_cli, sdlc_home: Path
):
    result = run_cli("resolve", "--new", "--title", "Cache the authorization lookup")

    assert result.code == 0
    report = result.json
    expected = (
        sdlc_home / "default" / "default" / "local" / "cache-the-authorization-lookup"
    )
    assert report["source"] == "local"
    assert report["id"] == "cache-the-authorization-lookup"
    assert report["namespace"] == "default"
    assert report["product"] == "default/default"
    assert report["exists"] is False
    assert report["paths"]["ticket_dir"] == str(expected)
    assert report["paths"]["ticket_json"] == str(expected / "ticket.json")
    assert report["paths"]["ticket_file"] == str(expected / "raw" / "ticket.md")


def test_resolving_creates_nothing_in_the_store(run_cli, sdlc_home: Path):
    run_cli("resolve", "--new", "--title", "Cache the authorization lookup")
    run_cli("resolve", "local:anything")

    assert not sdlc_home.exists()


def test_the_slug_is_deterministic_and_drops_punctuation(run_cli):
    first = run_cli(
        "resolve", "--new", "--title", "Fix: the  `login` bug (again!)"
    ).json
    second = run_cli(
        "resolve", "--new", "--title", "Fix: the  `login` bug (again!)"
    ).json

    assert first["id"] == "fix-the-login-bug-again"
    assert second["id"] == first["id"]


def test_a_long_title_is_cut_to_eight_words(run_cli):
    title = "one two three four five six seven eight nine ten"

    assert run_cli("resolve", "--new", "--title", title).json["id"] == (
        "one-two-three-four-five-six-seven-eight"
    )


def test_a_title_with_no_letters_or_digits_is_an_error(run_cli):
    result = run_cli("resolve", "--new", "--title", "!!!")

    assert result.code == 1
    assert "no letters or digits" in result.err


def test_a_filed_ticket_resolves_to_its_directory_by_any_spelling(
    run_cli, sdlc_home: Path
):
    ticket_dir = sdlc_home / "default" / "default" / "local" / "cache-lookup"
    ticket_dir.mkdir(parents=True)

    for reference in ("cache-lookup", "local:cache-lookup", "l:cache-lookup"):
        report = run_cli("resolve", reference).json
        assert report["exists"] is True
        assert report["ref"] == "local:cache-lookup"
        assert report["paths"]["ticket_dir"] == str(ticket_dir)


def test_a_reference_not_on_disk_reports_where_it_would_be_without_failing(run_cli):
    result = run_cli("resolve", "local:not-there")

    assert result.code == 0
    assert result.json["exists"] is False


def test_a_new_ticket_cannot_take_the_place_of_an_existing_one(
    run_cli, sdlc_home: Path
):
    (sdlc_home / "default" / "default" / "local" / "cache-lookup").mkdir(parents=True)

    result = run_cli("resolve", "--new", "--title", "Cache lookup")

    assert result.code == 1
    assert "already exists" in result.err


def test_a_reference_that_could_leave_the_store_is_rejected(run_cli):
    for reference in ("../escape", "local:../escape", "a/b", "Upper"):
        result = run_cli("resolve", reference)
        assert result.code == 1, reference
        assert "not a valid" in result.err or "not available" in result.err


def test_a_source_nothing_is_bound_to_cannot_be_filed(run_cli):
    result = run_cli("resolve", "ado:1234")

    assert result.code == 1
    assert "not bound in any product" in result.err


def test_an_unknown_source_prefix_is_not_available(run_cli):
    result = run_cli("resolve", "jira:1234")

    assert result.code == 1
    assert "not available" in result.err
