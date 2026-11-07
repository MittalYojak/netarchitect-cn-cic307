"""Load and validate NetArchitect network parameter profiles."""

import json
import math
from pathlib import Path
from typing import Any

from engine.errors import InvalidParameterError


VALID_PRESETS = ("campus_lan", "metro_man", "global_wan")

REQUIRED_KEYS = {
    "profile",
    "name",
    "endpoints",
    "root_cidr",
    "resiliency",
    "routing",
    "links",
    "subnets",
}

ROUTING_KEYS = {
    "num_sites",
    "multi_cloud",
    "num_autonomous_systems",
}

LINK_KEYS = {"name", "distance_m"}
SUBNET_KEYS = {"name", "hosts"}

VALID_RESILIENCY = {"none", "dual-homed"}


def _validate_keys(
    data: dict,
    required: set[str],
    context: str,
) -> None:
    """Ensure an object contains exactly the required keys."""
    missing = required - data.keys()
    extra = data.keys() - required

    if missing:
        raise InvalidParameterError(
            f"{context}: missing required key(s): "
            f"{', '.join(sorted(missing))}."
        )

    if extra:
        raise InvalidParameterError(
            f"{context}: unknown key(s): "
            f"{', '.join(sorted(str(key) for key in extra))}."
        )


def _validate_string(value: Any, key: str) -> None:
    """Validate a non-empty string parameter."""
    if not isinstance(value, str) or not value.strip():
        raise InvalidParameterError(
            f"{key} must be a non-empty string, received {value!r}."
        )


def _validate_positive_int(value: Any, key: str) -> None:
    """Validate a strictly positive integer, excluding booleans."""
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
    ):
        raise InvalidParameterError(
            f"{key} must be a positive integer, received {value!r}."
        )


def _validate_positive_number(value: Any, key: str) -> None:
    """Validate a finite, strictly positive real number."""
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        raise InvalidParameterError(
            f"{key} must be a positive real number, received {value!r}."
        )

    try:
        finite = math.isfinite(value)
    except (OverflowError, TypeError, ValueError):
        finite = False

    if not finite or value <= 0:
        raise InvalidParameterError(
            f"{key} must be finite and greater than zero, "
            f"received {value!r}."
        )


def validate_params(params: dict) -> dict:
    """Validate a complete NetArchitect parameter dictionary.

    Validation covers required fields, unexpected fields, data types,
    numeric ranges, routing settings, link definitions, and subnet
    definitions.

    CIDR syntax is intentionally not checked here because address
    validation belongs to the VLSM engine.

    Args:
        params: Dictionary containing network design parameters.

    Returns:
        The original validated parameter dictionary.

    Raises:
        InvalidParameterError: If any parameter is missing, unexpected,
            incorrectly typed, or outside its permitted range.
    """
    if not isinstance(params, dict):
        raise InvalidParameterError(
            f"params must be a dictionary, received {type(params).__name__}."
        )

    _validate_keys(params, REQUIRED_KEYS, "params")

    # General profile parameters.
    _validate_positive_int(params["profile"], "profile")
    _validate_string(params["name"], "name")
    _validate_positive_int(params["endpoints"], "endpoints")

    # CIDR syntax is validated separately by engine.vlsm.
    if not isinstance(params["root_cidr"], str):
        raise InvalidParameterError(
            "root_cidr must be a string, "
            f"received {params['root_cidr']!r}."
        )

    # Resiliency configuration.
    resiliency = params["resiliency"]

    if (
        not isinstance(resiliency, str)
        or resiliency not in VALID_RESILIENCY
    ):
        raise InvalidParameterError(
            "resiliency must be either 'none' or 'dual-homed', "
            f"received {resiliency!r}."
        )

    # Routing configuration.
    routing = params["routing"]

    if not isinstance(routing, dict):
        raise InvalidParameterError(
            f"routing must be an object, received {routing!r}."
        )

    _validate_keys(routing, ROUTING_KEYS, "routing")

    _validate_positive_int(
        routing["num_sites"],
        "routing.num_sites",
    )

    _validate_positive_int(
        routing["num_autonomous_systems"],
        "routing.num_autonomous_systems",
    )

    if not isinstance(routing["multi_cloud"], bool):
        raise InvalidParameterError(
            "routing.multi_cloud must be a boolean, "
            f"received {routing['multi_cloud']!r}."
        )

    # Physical link definitions.
    links = params["links"]

    if not isinstance(links, list) or not links:
        raise InvalidParameterError(
            "links must be a non-empty list of objects."
        )

    for index, link in enumerate(links):
        context = f"links[{index}]"

        if not isinstance(link, dict):
            raise InvalidParameterError(
                f"{context} must be an object, received {link!r}."
            )

        _validate_keys(link, LINK_KEYS, context)

        _validate_string(
            link["name"],
            f"{context}.name",
        )

        _validate_positive_number(
            link["distance_m"],
            f"{context}.distance_m",
        )

    # Subnet allocation requests.
    subnets = params["subnets"]

    if not isinstance(subnets, list) or not subnets:
        raise InvalidParameterError(
            "subnets must be a non-empty list of objects."
        )

    seen_names: set[str] = set()

    for index, subnet in enumerate(subnets):
        context = f"subnets[{index}]"

        if not isinstance(subnet, dict):
            raise InvalidParameterError(
                f"{context} must be an object, received {subnet!r}."
            )

        _validate_keys(subnet, SUBNET_KEYS, context)

        _validate_string(
            subnet["name"],
            f"{context}.name",
        )

        _validate_positive_int(
            subnet["hosts"],
            f"{context}.hosts",
        )

        name = subnet["name"].strip()

        if name in seen_names:
            raise InvalidParameterError(
                f"{context}.name contains duplicate subnet name {name!r}. "
                "Subnet names must be unique."
            )

        seen_names.add(name)

    return params


def _read_json(path: Path) -> dict:
    """Read a JSON file and validate its parameter structure.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        A validated parameter dictionary.

    Raises:
        InvalidParameterError: If the file cannot be read, contains
            invalid JSON, or fails parameter validation.
    """
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

    except OSError as exc:
        raise InvalidParameterError(
            f"Unable to read configuration file {str(path)!r}: {exc}"
        ) from exc

    except (json.JSONDecodeError, UnicodeError, ValueError) as exc:
        raise InvalidParameterError(
            f"Invalid JSON in configuration file {str(path)!r}: {exc}"
        ) from exc

    return validate_params(data)


def load_preset(name: str) -> dict:
    """Load and validate a predefined NetArchitect network profile.

    Presets are resolved relative to the repository root rather than
    the current working directory.

    Expected repository structure:

        NetArchitect/
            engine/
                params.py
            presets/
                campus_lan.json
                metro_man.json
                global_wan.json

    Args:
        name: One of 'campus_lan', 'metro_man', or 'global_wan'.

    Returns:
        A validated dictionary containing the preset parameters.

    Raises:
        InvalidParameterError: If the preset name is unknown, the file
            cannot be read, or its contents fail validation.
    """
    if not isinstance(name, str) or name not in VALID_PRESETS:
        valid_names = ", ".join(VALID_PRESETS)

        raise InvalidParameterError(
            f"Unknown preset {name!r}. Valid preset names: {valid_names}."
        )

    repository_root = Path(__file__).resolve().parent.parent
    preset_path = repository_root / "presets" / f"{name}.json"

    return _read_json(preset_path)


def load_custom(path: str) -> dict:
    """Load and validate a custom JSON network configuration.

    Relative paths are resolved against the current working directory.
    Absolute paths are supported.

    Args:
        path: Filesystem path to a JSON configuration file.

    Returns:
        A validated dictionary containing the custom parameters.

    Raises:
        InvalidParameterError: If the path is invalid, the file cannot
            be read, or its contents fail validation.
    """
    if not isinstance(path, str) or not path.strip():
        raise InvalidParameterError(
            f"path must be a non-empty string, received {path!r}."
        )

    try:
        config_path = Path(path).expanduser()
    except (TypeError, ValueError, OSError) as exc:
        raise InvalidParameterError(
            f"Invalid configuration path {path!r}: {exc}"
        ) from exc

    return _read_json(config_path)
