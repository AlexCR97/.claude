"""
Reading, validating and merging the three config levels.

`sdlc.json` at the SDLC home, `namespace.json` in a namespace and
`product.json` in a product. The effective config is the three merged, the
inner level winning, so a product records only what differs from its namespace
and a namespace only what differs from the machine. Objects merge key by key,
which is how a namespace's `sources.ado.organization` and a product's
`sources.ado.project` combine into one binding; anything else replaces what an
outer level set, so `"scan_roots": []` clears an inherited list.

The model writes these files, so every call validates all of them and fails
loudly, naming the file: a config read as empty would quietly file tickets in
the wrong place.

No credential lives in any of these files: `az` and `gh` hold them.
"""

import copy
from dataclasses import dataclass
from pathlib import Path

from . import layout, paths, providers
from .errors import SdlcError
from .layout import Product

LIST_KEYS = frozenset({"scan_roots", "protected_branches", "sensitive"})
# Directories on one machine, which mean nothing on another.
MACHINE_KEYS = frozenset({"scan_roots", "worktree_root"})
SHARED_KEYS = {"default_source", *LIST_KEYS, *MACHINE_KEYS}

# A key describing a level's relationship to what is inside it belongs to that
# level alone: a product inheriting `default_product` would name a product that
# is not there, so each such key is allowed in one file only.
ALLOWED_KEYS = {
    "sdlc": {"default_namespace", *SHARED_KEYS},
    "namespace": {"default_product", "sources", "connections", *SHARED_KEYS},
    "product": {"sources", "environments", "connections", *SHARED_KEYS},
}
LEVEL_ONLY_KEYS = frozenset({"default_namespace", "default_product"})
ENVIRONMENT_KEYS = frozenset({"name", "production"})
CONNECTION_KEYS = frozenset({"profile", "environment", "production"})


FIX_HINT = "Fix the file by hand, or rewrite it with `/sdlc:setup`."


def invalid(path: Path, problem: str) -> SdlcError:
    return SdlcError(f"{path}: {problem}", hint=FIX_HINT)


def read_level(path: Path, level: str) -> dict:
    """An absent file reads as empty; one that exists must be a valid object of known keys."""
    data = layout.read_json_object(path, FIX_HINT)
    for key, value in data.items():
        if key not in ALLOWED_KEYS[level]:
            allowed = ", ".join(sorted(ALLOWED_KEYS[level]))
            raise invalid(
                path, f"'{key}' is not a {level} setting (allowed: {allowed})"
            )
        check_value(path, level, key, value)
    return data


def check_value(path: Path, level: str, key: str, value: object) -> None:
    if key in ("default_namespace", "default_product"):
        if not isinstance(value, str) or not layout.is_name(value):
            raise invalid(path, f"'{key}' must be a lowercase slug")
    elif key == "default_source":
        if not isinstance(value, str) or value not in providers.list_sources():
            sources = ", ".join(providers.list_sources())
            raise invalid(path, f"'default_source' must be one of: {sources}")
    elif key == "worktree_root":
        if not isinstance(value, str) or not value.strip():
            raise invalid(path, "'worktree_root' must be a non-empty string")
    elif key in LIST_KEYS:
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise invalid(path, f"'{key}' must be a list of non-empty strings")
    elif key == "sources":
        check_sources(path, level, value)
    elif key == "environments":
        check_environments(path, value)
    elif key == "connections":
        check_connections(path, level, value)


def check_connections(path: Path, level: str, value: object) -> None:
    """A registry of connections by profile name: never a credential, which lives in the profile."""
    if not isinstance(value, list):
        raise invalid(path, "'connections' must be a list of objects, one per profile")
    seen: set[str] = set()
    for connection in value:
        if not isinstance(connection, dict):
            raise invalid(path, "each connection must be an object")
        profile = connection.get("profile")
        if not isinstance(profile, str) or not profile.strip():
            raise invalid(
                path, "every connection needs a 'profile', a non-empty string"
            )
        if not layout.is_profile_name(profile):
            raise invalid(
                path,
                f"'{profile}' is not a valid profile name "
                "(lowercase letters, digits, '.', '_' and '-')",
            )
        for key in connection:
            if key not in CONNECTION_KEYS:
                raise invalid(
                    path,
                    f"'{key}' is not a connection key ({', '.join(sorted(CONNECTION_KEYS))})",
                )
        if "environment" in connection:
            # Environments are listed in a product file alone, so only a product can name one.
            if level != "product":
                raise invalid(
                    path,
                    f"connection '{profile}' links an environment, but environment links belong in a product file",
                )
            environment = connection["environment"]
            if not isinstance(environment, str) or not environment.strip():
                raise invalid(
                    path,
                    f"connection '{profile}': 'environment' must be a non-empty string",
                )
        if "production" in connection and not isinstance(
            connection["production"], bool
        ):
            raise invalid(path, f"connection '{profile}' needs a boolean 'production'")
        if profile in seen:
            raise invalid(path, f"connection '{profile}' is listed twice")
        seen.add(profile)


def check_environments(path: Path, value: object) -> None:
    """A product's environments: objects of a unique name and a boolean `production`."""
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise invalid(
            path,
            "'environments' must be a list of objects, each a 'name' and a boolean 'production'",
        )
    seen: set[str] = set()
    for environment in value:
        name = environment.get("name")
        if not isinstance(name, str) or not name.strip():
            raise invalid(path, "every environment needs a 'name', a non-empty string")
        for key in environment:
            if key not in ENVIRONMENT_KEYS:
                raise invalid(
                    path,
                    f"'{key}' is not an environment key ({', '.join(sorted(ENVIRONMENT_KEYS))})",
                )
        if not isinstance(environment.get("production"), bool):
            raise invalid(path, f"environment '{name}' needs a boolean 'production'")
        # Environment names are matched case-insensitively when a skill is asked
        # to deploy, so `QA` and `qa` would name the same place twice.
        folded = name.casefold()
        if folded in seen:
            raise invalid(path, f"environment '{folded}' is listed twice")
        seen.add(folded)


def check_sources(path: Path, level: str, value: object) -> None:
    if not isinstance(value, dict):
        raise invalid(path, "'sources' must be an object keyed by source")
    for source, coordinates in value.items():
        if source not in providers.list_sources():
            available = ", ".join(providers.list_sources())
            raise invalid(
                path, f"'sources.{source}' is not an available source ({available})"
            )
        if not isinstance(coordinates, dict):
            raise invalid(path, f"'sources.{source}' must be an object of coordinates")
        declared = providers.coordinates(source)
        for name, coordinate in coordinates.items():
            if name not in declared:
                raise invalid(
                    path,
                    f"'{name}' is not a {source} coordinate ({', '.join(declared) or 'none'})",
                )
            if declared[name] != level:
                raise invalid(
                    path,
                    f"{source} {name} is bound at the {declared[name]} level, not in a {level} file",
                )
            if not isinstance(coordinate, str) or not coordinate.strip():
                raise invalid(
                    path, f"'sources.{source}.{name}' must be a non-empty string"
                )


def same(left: object, right: object) -> bool:
    """Providers treat organizations, projects and repositories case-insensitively."""
    return str(left).casefold() == str(right).casefold()


def merge_into(target: dict, layer: dict) -> None:
    for key, value in layer.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            merge_into(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


@dataclass(frozen=True)
class Config:
    root: dict
    namespaces: dict[str, dict]
    products: dict[Product, dict]

    def effective(
        self, namespace: str | None = None, product: str | None = None
    ) -> dict:
        layers = [self.root]
        if namespace:
            layers.append(self.namespaces.get(namespace, {}))
        if namespace and product:
            layers.append(self.products.get(Product(namespace, product), {}))
        merged: dict = {}
        for layer in layers:
            merge_into(
                merged,
                {
                    key: value
                    for key, value in layer.items()
                    if key not in LEVEL_ONLY_KEYS
                },
            )
        return merged

    def binding(self, source: str, product: Product) -> dict:
        sources = self.effective(product.namespace, product.name).get("sources", {})
        return dict(sources.get(source, {}))

    def namespace_binding(self, source: str, namespace: str) -> dict:
        sources = self.effective(namespace).get("sources", {})
        return dict(sources.get(source, {}))

    def own_scan_roots(
        self, namespace: str, product: str | None = None
    ) -> list[str] | None:
        level = (
            self.products.get(Product(namespace, product), {})
            if product
            else self.namespaces.get(namespace, {})
        )
        return level.get("scan_roots")

    def default_namespace(self) -> str:
        return self.root.get("default_namespace", paths.DEFAULT_NAME)

    def default_product(self, namespace: str) -> str:
        return self.namespaces.get(namespace, {}).get(
            "default_product", paths.DEFAULT_NAME
        )

    def default_source(self, namespace: str, product: str | None = None) -> str | None:
        return self.effective(namespace, product).get("default_source")


def load() -> Config:
    root = read_level(paths.root_config_path(), "sdlc")

    namespaces: dict[str, dict] = {}
    for namespace in layout.namespaces():
        path = paths.namespace_config_path(namespace)
        namespaces[namespace] = read_level(path, "namespace")
        if namespaces[namespace].get("sources") and namespace == paths.DEFAULT_NAME:
            raise invalid(path, fallback_bound_problem("namespace"))

    products: dict[Product, dict] = {}
    for product in layout.products():
        path = paths.product_config_path(product.namespace, product.name)
        products[product] = read_level(path, "product")
        if products[product].get("sources") and product.is_fallback:
            raise invalid(path, fallback_bound_problem("product"))

    config = Config(root, namespaces, products)
    check_defaults(config)
    check_bindings(config)
    check_environment_links(config)
    return config


def check_environment_links(config: Config) -> None:
    """A connection may only link an environment its own product lists, matched case-insensitively."""
    for product, level in config.products.items():
        listed = {
            environment["name"].casefold()
            for environment in level.get("environments", [])
        }
        for connection in level.get("connections", []):
            environment = connection.get("environment")
            if environment is not None and environment.casefold() not in listed:
                raise invalid(
                    paths.product_config_path(product.namespace, product.name),
                    f"connection '{connection['profile']}' links environment '{environment}', "
                    "which the product does not list",
                )


def fallback_bound_problem(kind: str) -> str:
    return (
        f"'{paths.DEFAULT_NAME}' is reserved for the fallback {kind}, which receives "
        "what no binding fits and is never bound"
    )


def check_defaults(config: Config) -> None:
    default_namespace = config.default_namespace()
    if (
        default_namespace != paths.DEFAULT_NAME
        and default_namespace not in config.namespaces
    ):
        raise invalid(
            paths.root_config_path(),
            f"'default_namespace' names '{default_namespace}', which does not exist",
        )
    for namespace in config.namespaces:
        default_product = config.default_product(namespace)
        if (
            default_product != paths.DEFAULT_NAME
            and Product(namespace, default_product) not in config.products
        ):
            raise invalid(
                paths.namespace_config_path(namespace),
                f"'default_product' names '{default_product}', which does not exist in {namespace}",
            )


def check_bindings(config: Config) -> None:
    """A binding must be complete, and belong to exactly one namespace or product."""
    holders: dict[tuple, Path] = {}

    def claim(key: tuple, path: Path, what: str) -> None:
        if key in holders:
            raise invalid(path, f"{what} is already bound in {holders[key]}")
        holders[key] = path

    for namespace, level in config.namespaces.items():
        for source, own in level.get("sources", {}).items():
            if own:
                claim(
                    (source, "namespace", *coordinate_key(own)),
                    paths.namespace_config_path(namespace),
                    f"{source} {describe(own)}",
                )

    for product, level in config.products.items():
        path = paths.product_config_path(product.namespace, product.name)
        for source, own in level.get("sources", {}).items():
            if not own:
                continue
            effective = config.binding(source, product)
            missing = [
                name for name in providers.coordinates(source) if name not in effective
            ]
            if missing:
                raise invalid(
                    path,
                    f"binds {source} {describe(own)} but {', '.join(missing)} is not "
                    f"bound by namespace {product.namespace}",
                )
            claim(
                (source, "product", *coordinate_key(effective)),
                path,
                f"{source} {describe(effective)}",
            )


def coordinate_key(binding: dict) -> tuple:
    return tuple(
        sorted((name, str(value).casefold()) for name, value in binding.items())
    )


def describe(coordinates: dict) -> str:
    return ", ".join(f"{name} '{value}'" for name, value in coordinates.items())
