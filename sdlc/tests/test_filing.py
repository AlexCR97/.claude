"""Where a ticket not yet on disk is filed: coordinates, context, invocation directory, default."""

from pathlib import Path

import pytest


@pytest.fixture
def two_products(write_config):
    """acme holds billing-app and ledger; the default is billing-app."""
    write_config("sdlc.json", {"default_namespace": "acme"})
    write_config("acme/namespace.json", {"default_product": "billing-app"})
    write_config("acme/billing-app/product.json", {})
    write_config("acme/ledger/product.json", {})


def file_new(run_cli, *extra: str, cwd: Path | None = None) -> dict:
    return run_cli("resolve", "--new", "--title", "Cache lookup", *extra, cwd=cwd).json


def test_without_anything_else_the_default_product_receives_the_ticket(
    run_cli, two_products
):
    filing = file_new(run_cli)

    assert filing["product"] == "acme/billing-app"
    assert filing["filing"]["rule"] == "default"


def test_a_home_with_nothing_configured_files_under_the_fallback_product(run_cli):
    filing = file_new(run_cli)

    assert filing["product"] == "default/default"
    assert filing["filing"]["rule"] == "only-candidate"


def test_the_session_context_beats_the_default(run_cli, two_products):
    filing = file_new(run_cli, "--context", "acme/ledger")

    assert filing["product"] == "acme/ledger"
    assert filing["filing"]["rule"] == "context"


def test_a_namespace_context_files_under_that_namespace_default_product(
    run_cli, two_products, write_config
):
    write_config("globex/namespace.json", {"default_product": "payroll"})
    write_config("globex/payroll/product.json", {})

    filing = file_new(run_cli, "--context", "globex")

    assert filing["product"] == "globex/payroll"


def test_the_invocation_directory_beats_the_default(
    run_cli, two_products, write_config, tmp_path
):
    code = tmp_path / "code" / "ledger"
    code.mkdir(parents=True)
    write_config("acme/ledger/product.json", {"scan_roots": [str(code)]})

    filing = file_new(run_cli, cwd=code)

    assert filing["product"] == "acme/ledger"
    assert filing["filing"]["rule"] == "invocation-directory"


def test_the_session_context_beats_the_invocation_directory(
    run_cli, two_products, write_config, tmp_path
):
    code = tmp_path / "code" / "ledger"
    code.mkdir(parents=True)
    write_config("acme/ledger/product.json", {"scan_roots": [str(code)]})

    filing = file_new(run_cli, "--context", "acme/billing-app", cwd=code)

    assert filing["product"] == "acme/billing-app"
    assert filing["filing"]["rule"] == "context"


def test_an_inherited_scan_root_does_not_say_which_product_a_directory_belongs_to(
    run_cli, two_products, write_config, tmp_path
):
    code = tmp_path / "code"
    code.mkdir()
    write_config("sdlc.json", {"default_namespace": "acme", "scan_roots": [str(code)]})

    filing = file_new(run_cli, cwd=code)

    assert filing["filing"]["rule"] == "default"


@pytest.fixture
def bound(write_config):
    write_config("sdlc.json", {"default_namespace": "acme"})
    write_config(
        "acme/namespace.json",
        {
            "default_product": "billing-app",
            "sources": {"ado": {"organization": "Acme"}},
        },
    )
    write_config(
        "acme/billing-app/product.json",
        {"sources": {"ado": {"project": "Billing.App"}}},
    )
    write_config(
        "acme/ledger/product.json", {"sources": {"ado": {"project": "Ledger"}}}
    )
    write_config("acme/default/product.json", {})


def coordinates(organization: str, project: str) -> list[str]:
    return [
        "--coordinate",
        f"organization={organization}",
        "--coordinate",
        f"project={project}",
    ]


def test_a_ticket_with_coordinates_is_filed_where_they_are_bound(run_cli, bound):
    report = run_cli(
        "resolve",
        "ado:1234",
        *coordinates("acme", "LEDGER"),
        "--context",
        "acme/billing-app",
    ).json

    assert report["product"] == "acme/ledger"
    assert report["filing"]["rule"] == "coordinates"
    assert report["exists"] is False
    assert report["outside_context"] is True


def test_coordinates_matching_only_the_namespace_file_under_its_fallback_product(
    run_cli, bound
):
    report = run_cli("resolve", "ado:1234", *coordinates("Acme", "Payroll")).json

    assert report["product"] == "acme/default"


def test_coordinates_nothing_is_bound_to_are_an_error(run_cli, bound):
    result = run_cli("resolve", "ado:1234", *coordinates("Globex", "Billing.App"))

    assert result.code == 1
    assert "no namespace or product is bound" in result.err


def test_a_remote_ticket_without_coordinates_is_filed_by_the_same_order(run_cli, bound):
    by_context = run_cli("resolve", "ado:1234", "--context", "acme/ledger").json
    by_default = run_cli("resolve", "ado:1234").json

    assert by_context["product"] == "acme/ledger"
    assert by_default["product"] == "acme/billing-app"


def test_a_fallback_product_is_never_a_candidate_for_a_bound_source(run_cli, bound):
    report = run_cli("resolve", "ado:1234", "--context", "acme/default")

    assert report.code == 0
    assert report.json["product"] == "acme/billing-app"


def test_a_coordinate_the_source_does_not_declare_is_an_error(run_cli, bound):
    result = run_cli("resolve", "ado:1234", "--coordinate", "owner=acme")

    assert result.code == 1
    assert "not a ado coordinate" in result.err


def test_a_named_product_bound_to_other_coordinates_refuses_the_ticket(run_cli, bound):
    result = run_cli(
        "resolve", "acme/ledger/ado:1234", *coordinates("acme", "Billing.App")
    )

    assert result.code == 1
    assert "bound to other ado coordinates" in result.err


def test_a_bare_id_not_on_disk_takes_the_default_source(run_cli, bound, write_config):
    write_config(
        "acme/namespace.json",
        {
            "default_source": "ado",
            "default_product": "billing-app",
            "sources": {"ado": {"organization": "Acme"}},
        },
    )

    assert run_cli("resolve", "1234").json["ref"] == "ado:1234"


def test_a_bare_id_not_on_disk_and_no_default_source_is_an_error(run_cli, bound):
    result = run_cli("resolve", "1234")

    assert result.code == 1
    assert "no default_source" in result.err
