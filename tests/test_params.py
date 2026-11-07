import copy
import json
import pytest
from engine.errors import InvalidParameterError
from engine.params import load_preset, load_custom, validate_params

_DEL = object()
NAN = float("nan")
INF = float("inf")
TOP_KEYS = ["profile", "name", "endpoints", "root_cidr", "resiliency",
            "routing", "links", "subnets"]


def base():
    return copy.deepcopy(load_preset("metro_man"))


def change(path, value):
    """Return a valid params dict with one nested value replaced (or deleted)."""
    p = base()
    target = p
    for k in path[:-1]:
        target = target[k]
    if value is _DEL:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return p


def rejects(params):
    with pytest.raises(InvalidParameterError):
        validate_params(params)


# ---------- presets ----------
@pytest.mark.parametrize("name", ["campus_lan", "metro_man", "global_wan"])
def test_presets_load_and_validate(name):
    p = load_preset(name)
    assert validate_params(copy.deepcopy(p)) == p


def test_unknown_preset_lists_valid_names():
    with pytest.raises(InvalidParameterError) as e:
        load_preset("nope")
    for n in ("campus_lan", "metro_man", "global_wan"):
        assert n in str(e.value)


def test_preset_loads_regardless_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_preset("campus_lan")["name"] == "Campus LAN"


# ---------- structure ----------
@pytest.mark.parametrize("bad", [None, [], "text", 5])
def test_non_dict_input_rejected(bad):
    rejects(bad)


@pytest.mark.parametrize("key", TOP_KEYS)
def test_missing_top_level_key_rejected(key):
    rejects(change((key,), _DEL))


def test_unknown_extra_key_rejected():
    p = base()
    p["surprise"] = 1
    rejects(p)


@pytest.mark.parametrize("key", ["num_sites", "multi_cloud", "num_autonomous_systems"])
def test_missing_routing_key_rejected(key):
    rejects(change(("routing", key), _DEL))


def test_missing_link_and_subnet_keys_rejected():
    rejects(change(("links", 0, "distance_m"), _DEL))
    rejects(change(("links", 0, "name"), _DEL))
    rejects(change(("subnets", 0, "hosts"), _DEL))
    rejects(change(("subnets", 0, "name"), _DEL))


@pytest.mark.parametrize("path,value", [
    (("routing",), []), (("links",), {}), (("subnets",), "x"),
    (("links",), []), (("subnets",), []),
    (("links", 0), "abc"), (("subnets", 0), 7),
])
def test_wrong_container_types_rejected(path, value):
    rejects(change(path, value))


# ---------- numeric fields: bool, NaN, inf, zero, negative, strings ----------
BAD_POS_INT = [0, -1, True, False, 1.5, "10", None, NAN, INF]


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_endpoints_rejected(v):
    rejects(change(("endpoints",), v))


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_hosts_rejected(v):
    rejects(change(("subnets", 0, "hosts"), v))


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_num_sites_rejected(v):
    rejects(change(("routing", "num_sites"), v))


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_num_autonomous_systems_rejected(v):
    rejects(change(("routing", "num_autonomous_systems"), v))


@pytest.mark.parametrize("v", [0, -5, True, False, "90", None, NAN, INF, -INF])
def test_bad_distance_rejected(v):
    rejects(change(("links", 0, "distance_m"), v))


@pytest.mark.parametrize("v", [True, "1", 1.5, None])
def test_bad_profile_rejected(v):
    rejects(change(("profile",), v))


def test_valid_numeric_values_accepted():
    assert validate_params(change(("links", 0, "distance_m"), 90.5))
    assert validate_params(change(("links", 0, "distance_m"), 90))
    assert validate_params(change(("endpoints",), 1))


# ---------- strings and enums ----------
@pytest.mark.parametrize("v", ["maybe", "", None, 1, "Dual-Homed"])
def test_bad_resiliency_rejected(v):
    rejects(change(("resiliency",), v))


@pytest.mark.parametrize("v", ["none", "dual-homed"])
def test_valid_resiliency_accepted(v):
    assert validate_params(change(("resiliency",), v))


@pytest.mark.parametrize("v", [5, None, ["10.0.0.0/8"]])
def test_non_string_root_cidr_rejected(v):
    rejects(change(("root_cidr",), v))


@pytest.mark.parametrize("v", ["yes", 1, 0, None, "false"])
def test_multi_cloud_must_be_a_real_bool(v):
    rejects(change(("routing", "multi_cloud"), v))


@pytest.mark.parametrize("v", [123, None])
def test_non_string_name_rejected(v):
    rejects(change(("name",), v))


# ---------- subnet names ----------
def test_duplicate_subnet_names_rejected():
    p = base()
    p["subnets"][1]["name"] = p["subnets"][0]["name"]
    rejects(p)


@pytest.mark.parametrize("v", ["", "   "])  # design rule: whitespace-only counts as empty
def test_empty_subnet_name_rejected(v):
    rejects(change(("subnets", 0, "name"), v))


# ---------- purity ----------
def test_validate_does_not_mutate_input():
    p = base()
    snapshot = copy.deepcopy(p)
    validate_params(p)
    assert p == snapshot


# ---------- load_custom ----------
def write(tmp_path, content):
    f = tmp_path / "custom.json"
    f.write_text(content if isinstance(content, str) else json.dumps(content),
                 encoding="utf-8")
    return str(f)


def test_custom_valid_file_roundtrips(tmp_path):
    p = base()
    assert load_custom(write(tmp_path, p)) == p


def test_custom_missing_file_is_invalid_parameter(tmp_path):  # design rule: one error family
    with pytest.raises(InvalidParameterError):
        load_custom(str(tmp_path / "does_not_exist.json"))


@pytest.mark.parametrize("text", ["", "{not json", "[]", "42", "null"])
def test_custom_bad_json_or_wrong_top_level_rejected(tmp_path, text):  # design rule
    with pytest.raises(InvalidParameterError):
        load_custom(write(tmp_path, text))


def test_custom_file_with_nan_literal_rejected(tmp_path):
    text = json.dumps(base()).replace('"distance_m": 80', '"distance_m": NaN')
    assert "NaN" in text
    with pytest.raises(InvalidParameterError):
        load_custom(write(tmp_path, text))


def test_custom_file_with_invalid_values_rejected(tmp_path):
    with pytest.raises(InvalidParameterError):
        load_custom(write(tmp_path, change(("endpoints",), -4)))
