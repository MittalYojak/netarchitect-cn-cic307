import pytest
from engine.errors import InvalidParameterError
from engine.routing import select_routing


@pytest.mark.parametrize("subnets,sites,cloud,ases,expected", [
    (49, 1, False, 1, "Single-Area"),
    (50, 1, False, 1, "Multi-Area"),
    (20, 4, False, 1, "Multi-Area"),
    (20, 1, True, 1, "Multi-Area"),
    (20, 1, False, 2, "eBGP"),
    (20, 4, False, 3, "eBGP"),
    (20, 4, True, 2, "eBGP"),
])
def test_protocol_selection(subnets, sites, cloud, ases, expected):
    assert expected in select_routing(subnets, sites, cloud, ases).choice


@pytest.mark.parametrize("args", [(0, 1, False, 1), (-1, 1, False, 1),
                                  (20, 0, False, 1), (20, 1, False, 0),
                                  ("abc", 1, False, 1), (20.5, 1, False, 1),
                                  (True, 1, False, 1)])
def test_invalid_inputs_raise(args):
    with pytest.raises(InvalidParameterError):
        select_routing(*args)


def test_justification_contains_input_numbers():
    j = select_routing(20, 4, False).justification
    assert "20" in j and "4" in j
