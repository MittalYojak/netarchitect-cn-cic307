import ipaddress
import random
import pytest
from engine.errors import AddressSpaceExhaustedError, InvalidParameterError
from engine.explain import Decision
from engine.vlsm import (allocate_vlsm, ip_to_int, int_to_ip, prefix_to_mask,
                         mask_to_wildcard, utilization_report)


# ---------- helpers ----------
@pytest.mark.parametrize("ip,val", [("0.0.0.0", 0), ("10.0.0.1", 167772161),
                                    ("192.168.1.1", 3232235777),
                                    ("255.255.255.255", 4294967295)])
def test_ip_int_roundtrip(ip, val):
    assert ip_to_int(ip) == val
    assert int_to_ip(val) == ip


@pytest.mark.parametrize("p,mask", [(0, "0.0.0.0"), (8, "255.0.0.0"),
                                    (16, "255.255.0.0"), (23, "255.255.254.0"),
                                    (24, "255.255.255.0"), (25, "255.255.255.128"),
                                    (27, "255.255.255.224"), (30, "255.255.255.252"),
                                    (31, "255.255.255.254"), (32, "255.255.255.255")])
def test_prefix_to_mask(p, mask):
    assert prefix_to_mask(p) == mask


@pytest.mark.parametrize("p", [-1, 33])
def test_prefix_to_mask_invalid(p):
    with pytest.raises(InvalidParameterError):
        prefix_to_mask(p)


@pytest.mark.parametrize("mask,wc", [("255.255.255.0", "0.0.0.255"),
                                     ("255.255.254.0", "0.0.1.255"),
                                     ("255.255.255.128", "0.0.0.127"),
                                     ("255.255.255.192", "0.0.0.63"),
                                     ("255.255.255.252", "0.0.0.3"),
                                     ("255.255.255.254", "0.0.0.1"),
                                     ("255.255.255.255", "0.0.0.0"),
                                     ("0.0.0.0", "255.255.255.255")])
def test_mask_to_wildcard_known_values(mask, wc):
    assert mask_to_wildcard(mask) == wc


def test_mask_to_wildcard_all_33_prefixes_vs_oracle():
    for p in range(0, 33):
        expected = str(ipaddress.ip_network(f"0.0.0.0/{p}").hostmask)
        assert mask_to_wildcard(prefix_to_mask(p)) == expected, f"/{p}"


@pytest.mark.parametrize("bad", ["255.0.255.0", "255.255.255.1", "0.255.255.255"])
def test_mask_to_wildcard_rejects_non_contiguous_masks(bad):
    with pytest.raises(InvalidParameterError):
        mask_to_wildcard(bad)


# ---------- allocation ----------
def test_sample_allocation_exact_values():
    reqs = [{"name": "A", "hosts": 500}, {"name": "B", "hosts": 100},
            {"name": "C", "hosts": 30}]
    got = [(s.name, s.network, s.prefix, s.mask, s.wildcard, s.first_host,
            s.last_host, s.broadcast, s.gateway, s.usable_hosts)
           for s in allocate_vlsm("10.0.0.0/16", reqs)]
    assert got == [
        ("A", "10.0.0.0", 23, "255.255.254.0", "0.0.1.255", "10.0.0.1",
         "10.0.1.254", "10.0.1.255", "10.0.0.1", 510),
        ("B", "10.0.2.0", 25, "255.255.255.128", "0.0.0.127", "10.0.2.1",
         "10.0.2.126", "10.0.2.127", "10.0.2.1", 126),
        ("C", "10.0.2.128", 27, "255.255.255.224", "0.0.0.31", "10.0.2.129",
         "10.0.2.158", "10.0.2.159", "10.0.2.129", 30),
    ]


def test_output_is_sorted_largest_first():
    reqs = [{"name": "small", "hosts": 10}, {"name": "big", "hosts": 300},
            {"name": "mid", "hosts": 60}]
    names = [s.name for s in allocate_vlsm("10.0.0.0/16", reqs)]
    assert names == ["big", "mid", "small"]


@pytest.mark.parametrize("hosts,prefix", [(1, 30), (2, 30), (3, 29), (6, 29),
                                          (7, 28), (14, 28), (15, 27), (30, 27),
                                          (31, 26), (62, 26), (63, 25), (126, 25),
                                          (127, 24), (254, 24), (255, 23),
                                          (510, 23), (511, 22)])
def test_smallest_prefix_boundaries(hosts, prefix):
    s = allocate_vlsm("10.0.0.0/16", [{"name": "X", "hosts": hosts}])[0]
    assert s.prefix == prefix


def test_exact_fill_of_root_prefix():
    reqs = [{"name": "A", "hosts": 126}, {"name": "B", "hosts": 126}]
    subs = allocate_vlsm("192.168.1.0/24", reqs)
    assert [s.network for s in subs] == ["192.168.1.0", "192.168.1.128"]


def test_exhaustion_one_block_too_many():
    reqs = [{"name": "A", "hosts": 126}, {"name": "B", "hosts": 126},
            {"name": "C", "hosts": 2}]
    with pytest.raises(AddressSpaceExhaustedError):
        allocate_vlsm("192.168.1.0/24", reqs)


def test_exhaustion_single_request_larger_than_root():
    with pytest.raises(AddressSpaceExhaustedError):
        allocate_vlsm("10.0.0.0/24", [{"name": "A", "hosts": 300}])


def test_exhaustion_tiny_root():
    with pytest.raises(AddressSpaceExhaustedError):
        allocate_vlsm("10.0.0.0/30", [{"name": "A", "hosts": 3}])


@pytest.mark.parametrize("bad", ["10.0.0.0/33", "10.0.0/16", "abc",
                                 "256.0.0.0/8", "10.0.0.0/-1", None])
def test_invalid_root_cidr(bad):
    with pytest.raises(InvalidParameterError):
        allocate_vlsm(bad, [{"name": "A", "hosts": 10}])


@pytest.mark.parametrize("hosts", [0, -1, -100])
def test_invalid_host_count(hosts):
    with pytest.raises(InvalidParameterError):
        allocate_vlsm("10.0.0.0/16", [{"name": "A", "hosts": hosts}])


def test_randomized_against_ipaddress_oracle():
    """200 random scenarios checked against Python's ipaddress module (tests only)."""
    rng = random.Random(1234)
    root = ipaddress.ip_network("10.0.0.0/16")
    for _ in range(200):
        reqs = [{"name": f"S{i}", "hosts": rng.randint(1, 800)}
                for i in range(rng.randint(1, 8))]
        subs = allocate_vlsm("10.0.0.0/16", reqs)
        assert len(subs) == len(reqs)
        nets = []
        for s in subs:
            net = ipaddress.ip_network(f"{s.network}/{s.prefix}")  # strict: fails if misaligned
            nets.append(net)
            assert net.subnet_of(root)
            assert str(net.netmask) == s.mask
            assert str(net.hostmask) == s.wildcard
            assert str(net.broadcast_address) == s.broadcast
            assert str(net[1]) == s.first_host
            assert str(net[-2]) == s.last_host
            assert s.gateway == s.first_host
            assert s.usable_hosts == net.num_addresses - 2
            assert s.usable_hosts >= s.requested_hosts
            assert net.num_addresses // 2 - 2 < s.requested_hosts   # smallest block that fits
            assert abs(s.efficiency_pct - round(100 * s.requested_hosts / s.usable_hosts, 2)) < 0.01
        for i in range(len(nets)):
            for j in range(i + 1, len(nets)):
                assert not nets[i].overlaps(nets[j]), (reqs, nets[i], nets[j])


def test_utilization_report_is_a_vlsm_decision():
    reqs = [{"name": "A", "hosts": 500}, {"name": "B", "hosts": 100}]
    subs = allocate_vlsm("10.0.0.0/16", reqs)
    rep = utilization_report(subs, "10.0.0.0/16")
    assert isinstance(rep, Decision)
    assert rep.domain == "VLSM"
    assert "%" in rep.justification
