import re
import pytest
from engine.errors import PhysicalDistanceViolationError, InvalidParameterError
from engine.media import select_media


def transceiver(choice: str) -> str:
    """Extract the 10GBASE-xx token from a choice string."""
    m = re.search(r"10GBASE-[A-Z]+(?:/[A-Z]+)?", choice)
    return m.group(0) if m else ""


@pytest.mark.parametrize("d", [1, 50, 100])
def test_access_run_uses_cat6a(d):
    assert "Cat6a" in select_media(d).choice


@pytest.mark.parametrize("d", [101, 250, 400])
def test_backbone_uses_om4_sr(d):
    r = select_media(d)
    assert "OM4" in r.choice
    assert transceiver(r.choice) == "10GBASE-SR"


@pytest.mark.parametrize("d", [401, 5000])
def test_over_400m_is_os2(d):
    assert "OS2" in select_media(d).choice


@pytest.mark.parametrize("d", [401, 5000, 10000])
def test_lr_up_to_10km(d):
    assert transceiver(select_media(d).choice) == "10GBASE-LR"


@pytest.mark.parametrize("d", [10001, 22000, 35000, 40000])
def test_er_between_10_and_40km(d):
    assert transceiver(select_media(d).choice) == "10GBASE-ER"


@pytest.mark.parametrize("d", [40001, 60000, 80000])
def test_zr_between_40_and_80km(d):
    assert "ZR" in select_media(d).choice


@pytest.mark.parametrize("d", [80001, 150000, 1150000])
def test_beyond_80km_needs_carrier_or_dwdm(d):
    c = select_media(d).choice.lower()
    assert "carrier" in c or "dwdm" in c


def test_justification_contains_distance():
    j = select_media(22000).justification
    assert any(tok in j for tok in ("22000", "22 km", "22.0 km"))


@pytest.mark.parametrize("media,d", [("cat6a", 101), ("copper", 150),
                                     ("cat5e", 500), ("cat6", 1000)])
def test_copper_over_100m_raises(media, d):
    with pytest.raises(PhysicalDistanceViolationError, match="(?i)attenuat"):
        select_media(d, media)


def test_copper_at_exactly_100m_is_allowed():
    assert "Cat6a" in select_media(100, "cat6a").choice


@pytest.mark.parametrize("d", [0, -5, "abc", None, float("nan"), float("inf")])
def test_invalid_distance_raises(d):
    with pytest.raises(InvalidParameterError):
        select_media(d)
