"""The three config levels, through `resolve`'s report of where a new ticket is filed."""


def test_the_default_namespace_and_product_receive_a_new_ticket(run_cli, write_config):
    write_config("sdlc.json", {"default_namespace": "acme"})
    write_config("acme/namespace.json", {"default_product": "billing-app"})
    write_config("acme/billing-app/product.json", {})

    report = run_cli("resolve", "--new", "--title", "Cache lookup").json

    assert report["product"] == "acme/billing-app"
    assert report["filing"]["rule"] == "default"


def test_an_inner_level_wins_and_bindings_combine_across_levels(run_cli, write_config):
    write_config(
        "sdlc.json",
        {
            "default_source": "github",
            "scan_roots": ["/code"],
            "protected_branches": ["main"],
        },
    )
    write_config(
        "acme/namespace.json",
        {
            "default_source": "ado",
            "scan_roots": [],
            "sources": {"ado": {"organization": "Acme"}},
        },
    )
    write_config(
        "acme/billing-app/product.json",
        {
            "default_source": "local",
            "sources": {"ado": {"project": "Billing.App"}},
        },
    )

    effective = run_cli("resolve", "acme/billing-app/ado:1234").json["config"]

    assert effective["default_source"] == "local"
    assert effective["scan_roots"] == []
    assert effective["protected_branches"] == ["main"]
    assert effective["sources"] == {
        "ado": {"organization": "Acme", "project": "Billing.App"}
    }


def test_a_namespace_inherits_the_machine_level_and_not_its_products(
    run_cli, write_config
):
    write_config("sdlc.json", {"protected_branches": ["main", "release/*"]})
    write_config("acme/namespace.json", {"scan_roots": ["/code/acme"]})
    write_config("acme/billing-app/product.json", {"scan_roots": ["/code/billing"]})
    write_config("acme/ledger/product.json", {})

    ledger = run_cli("resolve", "acme/ledger/local:fix-it").json["config"]
    billing = run_cli("resolve", "acme/billing-app/local:fix-it").json["config"]

    assert ledger["scan_roots"] == ["/code/acme"]
    assert ledger["protected_branches"] == ["main", "release/*"]
    assert billing["scan_roots"] == ["/code/billing"]
