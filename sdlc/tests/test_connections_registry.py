"""The optional `connections` registry in `namespace.json` and `product.json`, validated through `resolve`."""

import pytest

REGISTRY = [{"profile": "qa"}, {"profile": "edx-prod", "production": True}]
REFERENCE = "acme/billing-app/local:fix-it"


@pytest.mark.parametrize(
    "relative", ["acme/namespace.json", "acme/billing-app/product.json"]
)
def test_a_registry_in_either_level_appears_in_the_effective_config(
    run_cli, write_config, relative
):
    write_config("acme/billing-app/product.json", {})
    write_config(relative, {"connections": REGISTRY})

    result = run_cli("resolve", REFERENCE)

    assert result.code == 0, result.err
    assert result.json["config"]["connections"] == REGISTRY


def test_no_registry_at_all_is_valid(run_cli, write_config):
    write_config("acme/billing-app/product.json", {})

    result = run_cli("resolve", REFERENCE)

    assert result.code == 0, result.err
    assert "connections" not in result.json["config"]


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        ({"connections": "qa"}, "'connections' must be a list"),
        ({"connections": ["qa"]}, "each connection must be an object"),
        ({"connections": [{}]}, "every connection needs a 'profile'"),
        (
            {"connections": [{"profile": "Not A Slug"}]},
            "'Not A Slug' is not a valid profile name",
        ),
        (
            {"connections": [{"profile": "qa", "colour": "red"}]},
            "'colour' is not a connection key",
        ),
        (
            {"connections": [{"profile": "qa", "production": "yes"}]},
            "connection 'qa' needs a boolean 'production'",
        ),
        (
            {"connections": [{"profile": "qa"}, {"profile": "qa"}]},
            "connection 'qa' is listed twice",
        ),
    ],
)
def test_an_invalid_registry_is_an_error_naming_the_file(
    run_cli, write_config, content, problem
):
    path = write_config("acme/billing-app/product.json", content)

    result = run_cli("resolve", REFERENCE)

    assert result.code == 1
    assert str(path) in result.err
    assert problem in result.err


def test_the_machine_level_has_no_registry(run_cli, write_config):
    write_config("acme/billing-app/product.json", {})
    path = write_config("sdlc.json", {"connections": REGISTRY})

    result = run_cli("resolve", REFERENCE)

    assert result.code == 1
    assert str(path) in result.err
    assert "'connections' is not a sdlc setting" in result.err


def test_a_product_registry_may_link_an_environment_it_lists(run_cli, write_config):
    write_config(
        "acme/billing-app/product.json",
        {
            "environments": [{"name": "qa", "production": False}],
            "connections": [{"profile": "qa-db", "environment": "QA"}],
        },
    )

    result = run_cli("resolve", REFERENCE)

    assert result.code == 0, result.err
    assert result.json["config"]["connections"] == [
        {"profile": "qa-db", "environment": "QA"}
    ]


@pytest.mark.parametrize("environments", [[], [{"name": "dev", "production": False}]])
def test_a_link_to_an_environment_the_product_does_not_list_is_an_error(
    run_cli, write_config, environments
):
    path = write_config(
        "acme/billing-app/product.json",
        {
            "environments": environments,
            "connections": [{"profile": "qa-db", "environment": "qa"}],
        },
    )

    result = run_cli("resolve", REFERENCE)

    assert result.code == 1
    assert str(path) in result.err
    assert (
        "connection 'qa-db' links environment 'qa', which the product does not list"
        in result.err
    )


@pytest.mark.parametrize("environment", ["", " ", 1])
def test_an_environment_link_must_be_a_non_empty_string(
    run_cli, write_config, environment
):
    path = write_config(
        "acme/billing-app/product.json",
        {"connections": [{"profile": "qa-db", "environment": environment}]},
    )

    result = run_cli("resolve", REFERENCE)

    assert result.code == 1
    assert str(path) in result.err
    assert "'environment' must be a non-empty string" in result.err


def test_an_environment_link_in_a_namespace_file_is_an_error(run_cli, write_config):
    write_config("acme/billing-app/product.json", {})
    path = write_config(
        "acme/namespace.json",
        {"connections": [{"profile": "qa-db", "environment": "qa"}]},
    )

    result = run_cli("resolve", REFERENCE)

    assert result.code == 1
    assert str(path) in result.err
    assert "environment links belong in a product file" in result.err


def test_a_product_registry_replaces_the_namespace_one(run_cli, write_config):
    write_config("acme/namespace.json", {"connections": [{"profile": "a"}]})
    write_config("acme/billing-app/product.json", {"connections": [{"profile": "b"}]})

    config = run_cli("resolve", REFERENCE).json["config"]

    assert config["connections"] == [{"profile": "b"}]


def test_an_empty_product_registry_clears_the_namespace_one(run_cli, write_config):
    write_config("acme/namespace.json", {"connections": [{"profile": "a"}]})
    write_config("acme/billing-app/product.json", {"connections": []})

    config = run_cli("resolve", REFERENCE).json["config"]

    assert config["connections"] == []


def test_a_product_without_a_registry_inherits_the_namespace_one(run_cli, write_config):
    write_config("acme/namespace.json", {"connections": [{"profile": "a"}]})
    write_config("acme/billing-app/product.json", {})

    config = run_cli("resolve", REFERENCE).json["config"]

    assert config["connections"] == [{"profile": "a"}]


PRODUCT_WITH_REGISTRY = {
    "environments": [
        {"name": "live", "production": True},
        {"name": "qa", "production": False},
    ],
    "connections": [
        {"profile": "qa-db", "environment": "live"},
        {"profile": "plain", "production": True},
        {"profile": "flagged", "production": False},
        {"profile": "linked-qa", "environment": "qa"},
        {"profile": "ghost"},
    ],
}


def listed(run_cli, *argv):
    result = run_cli("connection", "list", *argv)
    assert result.code == 0, result.err
    return {entry["profile"]: entry for entry in result.json["connections"]}


def test_list_applies_the_registry_when_given_a_context(
    run_cli, write_config, write_profile
):
    write_config("acme/billing-app/product.json", PRODUCT_WITH_REGISTRY)
    write_profile("qa-db", "CONNECTION_KIND=rest\n")
    write_profile("plain", "CONNECTION_KIND=rest\n")
    write_profile("flagged", "CONNECTION_KIND=rest\nCONNECTION_PRODUCTION=true\n")
    write_profile("linked-qa", "CONNECTION_KIND=rest\nCONNECTION_PRODUCTION=true\n")
    write_profile("unlisted", "CONNECTION_KIND=rest\n")

    entries = listed(run_cli, "--context", "acme/billing-app")

    assert {
        name: (entry["production"], entry["production_source"])
        for name, entry in entries.items()
    } == {
        "qa-db": (True, "environment"),
        "plain": (True, "registry"),
        "flagged": (True, "profile"),
        "linked-qa": (False, "environment"),
        "unlisted": (True, "default"),
        "ghost": (True, "default"),
    }
    assert entries["qa-db"]["environment"] == "live"
    assert entries["ghost"]["registered"] is True
    assert entries["ghost"]["file"] is False
    assert entries["unlisted"]["registered"] is False
    assert entries["unlisted"]["file"] is True


def test_list_ignores_the_registry_without_a_context(
    run_cli, write_config, write_profile
):
    write_config("acme/billing-app/product.json", PRODUCT_WITH_REGISTRY)
    write_profile("qa-db", "CONNECTION_KIND=rest\n")

    entries = listed(run_cli)

    assert list(entries) == ["qa-db"]
    assert entries["qa-db"]["production"] is False
    assert entries["qa-db"]["production_source"] == "name"
    assert entries["qa-db"]["registered"] is False
