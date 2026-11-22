"""Resolving a ticket already on disk: by the nearest level, and never moved by the context."""

import pytest


@pytest.fixture
def same_id_in_three_products(make_ticket):
    make_ticket("acme", "billing-app", "ado", "1234")
    make_ticket("acme", "ledger", "ado", "1234")
    make_ticket("globex", "ledger", "ado", "1234")


def test_two_equally_near_matches_are_an_error_that_lists_them(
    run_cli, same_id_in_three_products
):
    result = run_cli("resolve", "ado:1234")

    assert result.code == 3
    assert "acme/billing-app/ado:1234" in result.err
    assert "acme/ledger/ado:1234" in result.err
    assert "globex/ledger/ado:1234" in result.err


def test_a_qualified_reference_names_exactly_one_ticket(
    run_cli, same_id_in_three_products
):
    report = run_cli("resolve", "globex/ledger/ado:1234").json

    assert report["exists"] is True
    assert report["product"] == "globex/ledger"


def test_the_context_product_is_the_nearest_level(run_cli, same_id_in_three_products):
    report = run_cli("resolve", "ado:1234", "--context", "acme/ledger").json

    assert report["product"] == "acme/ledger"
    assert report["outside_context"] is False


def test_the_context_namespace_is_the_next_nearest_level(
    run_cli, same_id_in_three_products
):
    result = run_cli("resolve", "ado:1234", "--context", "acme")

    assert result.code == 3
    assert "globex" not in result.err
    assert "acme/billing-app/ado:1234" in result.err


def test_a_namespace_context_picks_the_only_match_inside_it(run_cli, make_ticket):
    make_ticket("acme", "ledger", "ado", "1234")
    make_ticket("globex", "ledger", "ado", "1234")

    report = run_cli("resolve", "ado:1234", "--context", "globex").json

    assert report["product"] == "globex/ledger"


def test_a_context_never_hides_a_ticket_filed_elsewhere(
    run_cli, make_ticket, write_config
):
    make_ticket("globex", "ledger", "ado", "1234")
    write_config("acme/billing-app/product.json", {})

    report = run_cli("resolve", "ado:1234", "--context", "acme/billing-app").json

    assert report["exists"] is True
    assert report["product"] == "globex/ledger"
    assert report["outside_context"] is True


def test_a_bare_id_matches_every_source_whose_id_shape_fits(run_cli, make_ticket):
    make_ticket("acme", "billing-app", "github", "1234")
    make_ticket("acme", "billing-app", "ado", "1234")

    result = run_cli("resolve", "1234")

    assert result.code == 3
    assert "github:1234" in result.err
    assert "ado:1234" in result.err


def test_a_bare_slug_is_found_wherever_it_is_filed(run_cli, make_ticket):
    make_ticket("acme", "billing-app", "local", "fix-login")

    report = run_cli("resolve", "fix-login").json

    assert report["ref"] == "local:fix-login"
    assert report["product"] == "acme/billing-app"


def test_a_ticket_recorded_with_other_coordinates_is_a_different_ticket(
    run_cli, make_ticket, write_config
):
    write_config("acme/namespace.json", {"sources": {"ado": {"organization": "Acme"}}})
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"ado": {"project": "Billing.App"}}},
    )
    make_ticket("acme", "billing-app", "ado", "1234")
    write_config(
        "acme/billing-app/ado/1234/ticket.json",
        {"coordinates": {"organization": "Acme", "project": "Billing.App"}},
    )
    own = ["--coordinate", "organization=acme", "--coordinate", "project=billing.app"]
    other = ["--coordinate", "organization=acme", "--coordinate", "project=Ledger"]

    mine = run_cli("resolve", "ado:1234", *own).json
    different = run_cli("resolve", "ado:1234", *other)

    assert mine["exists"] is True
    assert different.code == 0
    assert different.json["exists"] is False
    assert different.json["product"] == "acme/default"
