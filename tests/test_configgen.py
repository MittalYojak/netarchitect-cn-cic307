import copy
import ipaddress
import re
import pytest
from engine.errors import InvalidParameterError
from engine.params import load_preset
from engine.planner import build_plan
from engine.configgen import generate_switch_configs

PRESETS = ["campus_lan", "metro_man", "global_wan"]


def blocks(text):
    """Split IOS text into (header, [children]) blocks; '!' ends a block."""
    out, cur = [], None
    for line in text.splitlines():
        if not line.strip() or line.strip() == "!":
            cur = None
            continue
        if line.startswith(" "):
            if cur is not None:
                cur[1].append(line.strip())
        else:
            cur = (line.strip(), [])
            out.append(cur)
    return out


def find(text, header):
    for h, kids in blocks(text):
        if h == header:
            return kids
    raise AssertionError(f"missing block: {header}")


def has(text, header):
    return any(h == header for h, _ in blocks(text))


def lan_entries(params):
    lan = [s for s in params["subnets"] if not s["name"].startswith(("P2P-", "Tunnel-"))]
    return [(10 * (i + 1), s["name"]) for i, s in enumerate(lan)]


def csv(ids):
    return ",".join(str(i) for i in ids)


def setup(name):
    p = load_preset(name)
    plan = build_plan(p)
    return p, plan, generate_switch_configs(plan), {s.name: s for s in plan.subnets}


def custom_plan(subnets, root="10.0.0.0/16"):
    return build_plan({
        "profile": 1, "name": "T", "endpoints": 100, "root_cidr": root,
        "resiliency": "none",
        "routing": {"num_sites": 1, "multi_cloud": False, "num_autonomous_systems": 1},
        "links": [{"name": "L", "distance_m": 50}],
        "subnets": subnets})


@pytest.mark.parametrize("name", PRESETS)
def test_two_devices_ascii_and_terminated(name):
    _, _, cfgs, _ = setup(name)
    assert set(cfgs) == {"CORE-SW1", "ACCESS-SW1"}
    for text in cfgs.values():
        text.encode("ascii")
        assert text.endswith("end\n")
        assert not any(l != l.rstrip() for l in text.splitlines()), "trailing spaces"


@pytest.mark.parametrize("name", PRESETS)
def test_core_global_settings(name):
    _, _, cfgs, _ = setup(name)
    core = cfgs["CORE-SW1"]
    assert has(core, "hostname CORE-SW1")
    assert has(core, "ip routing")
    assert has(core, "spanning-tree mode rapid-pvst")
    assert has(cfgs["ACCESS-SW1"], "spanning-tree mode rapid-pvst")


@pytest.mark.parametrize("name", PRESETS)
def test_vlans_defined_with_names_on_both_switches(name):
    p, _, cfgs, _ = setup(name)
    for text in cfgs.values():
        assert find(text, "vlan 999") == ["name BLACKHOLE-NATIVE"]
        for vid, sname in lan_entries(p):
            assert find(text, f"vlan {vid}") == [f"name {sname}"]


@pytest.mark.parametrize("name", PRESETS)
def test_svi_addresses_match_the_plan(name):
    p, _, cfgs, subs = setup(name)
    for vid, sname in lan_entries(p):
        s = subs[sname]
        kids = find(cfgs["CORE-SW1"], f"interface Vlan{vid}")
        assert f"ip address {s.gateway} {s.mask}" in kids
        assert "no shutdown" in kids
        iface = ipaddress.ip_interface(f"{s.gateway}/{s.mask}")
        assert iface.network == ipaddress.ip_network(f"{s.network}/{s.prefix}")


@pytest.mark.parametrize("name", PRESETS)
def test_every_trunk_is_constrained(name):
    p, _, cfgs, _ = setup(name)
    ids = [v for v, _ in lan_entries(p)]
    for dev, text in cfgs.items():
        trunks = [(h, k) for h, k in blocks(text)
                  if h.startswith("interface ") and "switchport mode trunk" in k]
        assert trunks, f"{dev} has no trunk"
        for h, kids in trunks:
            allowed = [k for k in kids if k.startswith("switchport trunk allowed vlan")]
            assert allowed == [f"switchport trunk allowed vlan {csv(ids)}"], (dev, h)
            assert "switchport trunk native vlan 999" in kids
            assert "switchport nonegotiate" in kids
            assert 999 not in ids


@pytest.mark.parametrize("name", PRESETS)
def test_core_is_stp_root_for_all_lan_vlans(name):
    p, _, cfgs, _ = setup(name)
    ids = [v for v, _ in lan_entries(p)]
    heads = [h for h, _ in blocks(cfgs["CORE-SW1"]) if h.startswith("spanning-tree vlan")]
    assert len(heads) == 1
    m = re.fullmatch(r"spanning-tree vlan ([\d,]+) priority 4096", heads[0])
    assert m, heads[0]
    assert [int(x) for x in m.group(1).split(",")] == ids


@pytest.mark.parametrize("name", PRESETS)
def test_ospf_uses_wildcards_for_every_lan_subnet(name):
    p, _, cfgs, subs = setup(name)
    kids = find(cfgs["CORE-SW1"], "router ospf 1")
    nets = {k for k in kids if k.startswith("network ")}
    expected = {f"network {subs[n].network} {subs[n].wildcard} area 0" for _, n in lan_entries(p)}
    assert nets == expected
    assert "passive-interface default" in kids
    for _, n in lan_entries(p):
        assert subs[n].wildcard != subs[n].mask


@pytest.mark.parametrize("name", PRESETS)
def test_management_acl_blocks_then_permits(name):
    p, _, cfgs, subs = setup(name)
    mgmt = subs["Management"]
    kids = find(cfgs["CORE-SW1"], "ip access-list extended PROTECT-MGMT")
    rules = [k for k in kids if not k.startswith("remark")]
    assert rules[0] == f"deny ip any {mgmt.network} {mgmt.wildcard}"
    assert rules[-1] == "permit ip any any"
    assert len(rules) == 2
    mgmt_id = next(v for v, n in lan_entries(p) if n == "Management")
    for vid, _ in lan_entries(p):
        applied = "ip access-group PROTECT-MGMT in" in find(cfgs["CORE-SW1"], f"interface Vlan{vid}")
        assert applied == (vid != mgmt_id)


@pytest.mark.parametrize("name", PRESETS)
def test_access_ports_are_safe_and_complete(name):
    p, _, cfgs, _ = setup(name)
    lan = lan_entries(p)
    ports = [(h, k) for h, k in blocks(cfgs["ACCESS-SW1"])
             if h.startswith("interface ") and "switchport mode access" in k]
    assert [h for h, _ in ports] == [f"interface FastEthernet0/{i}" for i in range(1, len(lan) + 1)]
    for (h, kids), (vid, _) in zip(ports, lan):
        assert f"switchport access vlan {vid}" in kids
        assert "spanning-tree portfast" in kids
        assert "spanning-tree bpduguard enable" in kids
        assert "no shutdown" in kids


@pytest.mark.parametrize("name", PRESETS)
def test_access_switch_management_address(name):
    p, _, cfgs, subs = setup(name)
    mgmt = subs["Management"]
    mgmt_id = next(v for v, n in lan_entries(p) if n == "Management")
    kids = find(cfgs["ACCESS-SW1"], f"interface Vlan{mgmt_id}")
    m = next(re.fullmatch(r"ip address (\S+) (\S+)", k) for k in kids if k.startswith("ip address"))
    ip = ipaddress.ip_address(m.group(1))
    net = ipaddress.ip_network(f"{mgmt.network}/{mgmt.prefix}")
    assert ip in net and m.group(2) == mgmt.mask
    assert str(ip) not in (mgmt.gateway, mgmt.broadcast, mgmt.network)
    assert has(cfgs["ACCESS-SW1"], f"ip default-gateway {mgmt.gateway}")


@pytest.mark.parametrize("name", PRESETS)
def test_deterministic_and_input_not_mutated(name):
    p = load_preset(name)
    plan = build_plan(p)
    snap = copy.deepcopy(plan.params)
    a = generate_switch_configs(plan)
    b = generate_switch_configs(build_plan(copy.deepcopy(p)))
    assert a == b
    assert plan.params == snap


def test_without_management_subnet_no_acl_no_gateway():
    plan = custom_plan([{"name": "Users", "hosts": 100}, {"name": "Servers", "hosts": 20},
                        {"name": "P2P-Link", "hosts": 2}])
    cfgs = generate_switch_configs(plan)
    core, acc = cfgs["CORE-SW1"], cfgs["ACCESS-SW1"]
    assert "PROTECT-MGMT" not in core
    assert "ip default-gateway" not in acc
    assert find(core, "vlan 10") == ["name Users"] and find(core, "vlan 20") == ["name Servers"]
    assert not has(core, "vlan 30")
    assert "switchport trunk allowed vlan 10,20" in core


def test_p2p_and_tunnel_subnets_are_not_vlans():
    plan = custom_plan([{"name": "Users", "hosts": 50}, {"name": "P2P-A-B", "hosts": 2},
                        {"name": "Tunnel-X", "hosts": 2}])
    core = generate_switch_configs(plan)["CORE-SW1"]
    assert "P2P-A-B" not in core and "Tunnel-X" not in core


def test_twenty_lan_subnets_allowed_twenty_one_rejected():
    ok = custom_plan([{"name": f"S{i}", "hosts": 10} for i in range(1, 21)])
    assert generate_switch_configs(ok)["ACCESS-SW1"].count("switchport mode access") == 20
    too_many = custom_plan([{"name": f"S{i}", "hosts": 10} for i in range(1, 22)])
    with pytest.raises(InvalidParameterError):
        generate_switch_configs(too_many)


def test_only_point_to_point_subnets_rejected():
    plan = custom_plan([{"name": "P2P-A-B", "hosts": 2}])
    with pytest.raises(InvalidParameterError):
        generate_switch_configs(plan)


def test_management_subnet_too_small_rejected():
    plan = custom_plan([{"name": "Users", "hosts": 50}, {"name": "Management", "hosts": 1}])
    with pytest.raises(InvalidParameterError):
        generate_switch_configs(plan)
