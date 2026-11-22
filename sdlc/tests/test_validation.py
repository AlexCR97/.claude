"""`resolve` validates every config file on every call and names the file at fault."""

import pytest

ACME = {"sources": {"ado": {"organization": "Acme"}}}


def resolve_anything(run_cli):
    return run_cli("resolve", "--new", "--title", "Cache lookup")


@pytest.mark.parametrize(
    "relative",
    ["sdlc.json", "acme/namespace.json", "acme/billing-app/product.json"],
)
def test_invalid_json_in_any_level_is_an_error_naming_the_file(
    run_cli, write_config, relative
):
    write_config("acme/billing-app/product.json", {})
    path = write_config(relative, "{ not json")

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert "not valid JSON" in result.err


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        ('["a list"]', "JSON object"),
        ({"scan_root": []}, "'scan_root' is not a namespace setting"),
        ({"scan_roots": "/code"}, "'scan_roots' must be a list"),
        ({"default_source": "jira"}, "'default_source' must be one of"),
        ({"default_product": "Billing App"}, "must be a lowercase slug"),
        ({"sources": {"ado": {"team": "x"}}}, "'team' is not a ado coordinate"),
        ({"sources": {"ado": {"project": "Billing"}}}, "bound at the product level"),
        ({"sources": {"ado": {"organization": ""}}}, "non-empty string"),
        ({"sources": {"jira": {}}}, "not an available source"),
        ({"default_namespace": "acme"}, "not a namespace setting"),
    ],
)
def test_an_invalid_shape_is_an_error_naming_the_file(
    run_cli, write_config, content, problem
):
    path = write_config("acme/namespace.json", content)

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert problem in result.err


def test_a_default_product_that_does_not_exist_is_an_error(run_cli, write_config):
    path = write_config("acme/namespace.json", {"default_product": "billing-app"})

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert "does not exist" in result.err


def test_a_default_namespace_that_does_not_exist_is_an_error(run_cli, write_config):
    path = write_config("sdlc.json", {"default_namespace": "acme"})

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err


def test_two_products_bound_to_the_same_coordinates_are_an_error(run_cli, write_config):
    write_config("acme/namespace.json", ACME)
    write_config(
        "acme/billing-app/product.json", {"sources": {"ado": {"project": "Billing"}}}
    )
    second = write_config(
        "acme/invoices/product.json", {"sources": {"ado": {"project": "billing"}}}
    )

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert "already bound in" in result.err
    assert str(second) in result.err or "billing-app" in result.err


def test_two_namespaces_bound_to_the_same_organization_are_an_error(
    run_cli, write_config
):
    write_config("acme/namespace.json", ACME)
    write_config(
        "globex/namespace.json", {"sources": {"ado": {"organization": "ACME"}}}
    )

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert "already bound in" in result.err


def test_a_product_binding_without_its_namespace_half_is_an_error(
    run_cli, write_config
):
    path = write_config(
        "acme/billing-app/product.json", {"sources": {"ado": {"project": "Billing"}}}
    )

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert "organization is not bound by namespace acme" in result.err


def test_a_fallback_product_is_never_bound(run_cli, write_config):
    write_config("acme/namespace.json", ACME)
    path = write_config(
        "acme/default/product.json", {"sources": {"ado": {"project": "Billing"}}}
    )

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert "reserved for the fallback product" in result.err


def test_the_fallback_namespace_is_never_bound(run_cli, write_config):
    path = write_config("default/namespace.json", ACME)

    result = resolve_anything(run_cli)

    assert result.code == 1
    assert str(path) in result.err
    assert "reserved for the fallback namespace" in result.err


def test_a_context_that_is_not_a_slug_or_does_not_exist_is_an_error(
    run_cli, write_config
):
    write_config("acme/billing-app/product.json", {})

    bad_name = run_cli("resolve", "--new", "--title", "x", "--context", "Acme")
    missing = run_cli("resolve", "--new", "--title", "x", "--context", "acme/ledger")

    assert bad_name.code == 1
    assert "not a valid namespace name" in bad_name.err
    assert missing.code == 1
    assert "does not exist" in missing.err


def test_valid_config_is_accepted(run_cli, write_config):
    write_config("sdlc.json", {"default_source": "local", "scan_roots": []})
    write_config("acme/namespace.json", ACME)
    write_config(
        "acme/billing-app/product.json", {"sources": {"ado": {"project": "Billing"}}}
    )

    assert resolve_anything(run_cli).code == 0
