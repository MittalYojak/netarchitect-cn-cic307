import copy
import ipaddress
import pytest
from engine.errors import AddressSpaceExhaustedError, InvalidParameterError
from engine.explain import Decision
from engine.params import load_preset
from engine.planner import build_plan, render_report, all_decisions

PRESETS = ["campus_lan", "metro_man", "global_wan"]
EXPECTED = {
    "campus_lan": ("Single-Area", "Three-tier"),
    "metro_man": ("Multi-Area", "Full-mesh"),
    "global_wan": ("eBGP", "Hub-and-spoke"),
}


def custom():
    return {
        "profile": 1, "name": "Test Office", "endpoints": 200,
        "root_cidr": "192.168.0.0/24", "resiliency": "none",
        "routing": {"num_sites": 1, "multi_cloud": False, "num_autonomous_systems": 1},
        "links": [{"name": "L1", "distance_m": 50}, {"name": "L2", "distance_m": 300}],
        "subnets": [{"name": "Users", "hosts": 100}, {"name": "Servers", "hosts": 20},
                    {"name": "P2P", "hosts": 2}],
    }


@pytest.mark.parametrize("name", PRESETS)
def test_expected_protocol_and_topology(name):
    plan = build_plan(load_preset(name))
    proto, topo = EXPECTED[name]
    assert proto in plan.routing.choice
    assert topo in plan.topology.choice


@pytest.mark.parametrize("name", PRESETS)
def test_link_plans_match_input_links_in_order(name):
    p = load_preset(name)
    plan = build_plan(p)
    assert [(l.name, l.distance_m) for l in plan.link_plans] == \
           [(l["name"], l["distance_m"]) for l in p["links"]]


@pytest.mark.parametrize("name", PRESETS)
def test_every_decision_is_explained(name):
    plan = build_plan(load_preset(name))
    ds = all_decisions(plan)
    assert len(ds) == len(plan.link_plans) + 3
    for d in ds:
        assert isinstance(d, Decision)
        assert len(d.justification) > 40
        assert any(ch.isdigit() for ch in d.justification), d.choice


@pytest.mark.parametrize("name", PRESETS)
def test_media_choice_matches_distance_band(name):
    for lp in build_plan(load_preset(name)).link_plans:
        c = lp.decision.choice
        if lp.distance_m <= 100:
            assert "Cat6a" in c
        elif lp.distance_m <= 400:
            assert "OM4" in c
        else:
            assert "OS2" in c or "Carrier" in c


@pytest.mark.parametrize("name", PRESETS)
def test_address_plan_has_no_overlap_and_stays_inside_root(name):
    p = load_preset(name)
    plan = build_plan(p)
    root = ipaddress.ip_network(p["root_cidr"])
    assert [s.name for s in plan.subnets].sort() == [s["name"] for s in p["subnets"]].sort()
    nets = [ipaddress.ip_network(f"{s.network}/{s.prefix}") for s in plan.subnets]
    assert all(n.subnet_of(root) for n in nets)
    for i in range(len(nets)):
        for j in range(i + 1, len(nets)):
            assert not nets[i].overlaps(nets[j])


@pytest.mark.parametrize("name", PRESETS)
def test_report_contains_every_decision_link_and_subnet(name):
    plan = build_plan(load_preset(name))
    report = render_report(plan)
    for d in all_decisions(plan):
        assert d.justification in report
        assert d.choice in report
    for lp in plan.link_plans:
        assert lp.name in report
    for s in plan.subnets:
        assert s.name in report
        assert f"{s.network}/{s.prefix}" in report
        assert s.wildcard in report
        assert s.gateway in report


@pytest.mark.parametrize("name", PRESETS)
def test_report_is_deterministic_and_ascii(name):
    p = load_preset(name)
    a, b = render_report(build_plan(p)), render_report(build_plan(copy.deepcopy(p)))
    assert a == b
    a.encode("ascii")


@pytest.mark.parametrize("name", PRESETS)
def test_build_plan_does_not_mutate_input(name):
    p = load_preset(name)
    snap = copy.deepcopy(p)
    build_plan(p)
    assert p == snap


def test_metro_22km_link_is_er_with_distance_in_text():
    plan = build_plan(load_preset("metro_man"))
    lp = next(l for l in plan.link_plans if l.distance_m == 22000)
    assert "10GBASE-ER" in lp.decision.choice
    assert "22000" in lp.decision.justification


def test_custom_scenario_end_to_end():
    plan = build_plan(custom())
    report = render_report(plan)
    assert "Two-tier" in plan.topology.choice
    assert "Single-Area" in plan.routing.choice
    assert "single point of failure" in plan.topology.justification.lower()
    assert "Users" in report and "192.168.0.0/25" in report


def test_invalid_parameters_propagate():
    for mutate in (lambda p: p.update(endpoints=-1),
                   lambda p: p["links"][0].update(distance_m=float("nan")),
                   lambda p: p["subnets"][0].update(hosts=0)):
        p = custom()
        mutate(p)
        with pytest.raises(InvalidParameterError):
            build_plan(p)


def test_address_space_exhaustion_propagates():
    p = load_preset("campus_lan")
    p["root_cidr"] = "10.10.0.0/24"
    with pytest.raises(AddressSpaceExhaustedError):
        build_plan(p)
