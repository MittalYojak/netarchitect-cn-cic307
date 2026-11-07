import re
import pytest
from engine.errors import InvalidParameterError
from engine.topology import select_topology

NAN = float("nan")
INF = float("inf")


def tier(endpoints, sites=1, res="dual-homed"):
    return select_topology(endpoints, sites, res)


@pytest.mark.parametrize("endpoints,expected", [(1, "Two-tier"), (500, "Two-tier"),
                                                (501, "Three-tier"), (1600, "Three-tier")])
def test_single_site_tier_boundary(endpoints, expected):
    assert expected in tier(endpoints).choice


@pytest.mark.parametrize("sites,expected", [(2, "Full-mesh"), (3, "Full-mesh"),
                                            (4, "Full-mesh"), (5, "Hub-and-spoke"),
                                            (8, "Hub-and-spoke")])
def test_multi_site_topology_boundary(sites, expected):
    assert expected in tier(450, sites).choice


@pytest.mark.parametrize("sites,links", [(2, 1), (3, 3), (4, 6)])
def test_full_mesh_link_count_in_text(sites, links):
    assert re.search(rf"\b{links}\b[^.]*link", tier(450, sites).justification)


@pytest.mark.parametrize("sites,links", [(5, 4), (8, 7)])
def test_hub_and_spoke_link_count_in_text(sites, links):
    assert re.search(rf"\b{links}\b[^.]*link", tier(450, sites).justification)


def test_justification_includes_input_numbers():
    j = tier(1600, 1).justification
    assert "1600" in j
    assert re.search(r"\b3\b", tier(450, 3).justification)


@pytest.mark.parametrize("endpoints,sites", [(300, 1), (1600, 1), (450, 3), (2000, 5)])
def test_dual_homed_text_mentions_redundant(endpoints, sites):
    assert "redundant" in tier(endpoints, sites, "dual-homed").justification.lower()


@pytest.mark.parametrize("endpoints,sites", [(300, 1), (1600, 1), (450, 3), (2000, 5)])
def test_none_resiliency_text_names_single_point_of_failure(endpoints, sites):
    assert "single point of failure" in tier(endpoints, sites, "none").justification.lower()


def test_domain_is_topology_tier():
    assert tier(1600).domain == "Topology tier"


def test_preset_parameters_give_expected_topologies():
    assert "Three-tier" in tier(1600, 1, "dual-homed").choice   # campus_lan
    assert "Full-mesh" in tier(450, 3, "dual-homed").choice     # metro_man
    assert "Hub-and-spoke" in tier(2000, 5, "none").choice      # global_wan


BAD_POS_INT = [0, -1, True, False, 1.5, "10", None, NAN, INF]


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_endpoints_rejected(v):
    with pytest.raises(InvalidParameterError):
        select_topology(v, 1, "none")


@pytest.mark.parametrize("v", BAD_POS_INT)
def test_bad_num_sites_rejected(v):
    with pytest.raises(InvalidParameterError):
        select_topology(100, v, "none")


@pytest.mark.parametrize("v", ["maybe", "", None, "Dual-Homed", 1, True])
def test_bad_resiliency_rejected(v):
    with pytest.raises(InvalidParameterError):
        select_topology(100, 1, v)
