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


# ---------- explanation accuracy (added after reviewing the AI's v2 text) ----------
def _loss_db(d):
    j = select_media(d).justification
    m = re.search(r"(?:approximately|about|roughly|~)\s*([\d.]+)\s*dB", j)
    assert m, "justification must state the fibre loss in dB"
    return float(m.group(1))


@pytest.mark.parametrize("d,budget", [(10000, 6.2), (40000, 11.0), (80000, 24.0)])
def test_stated_fibre_loss_fits_transceiver_budget_at_max_reach(d, budget):
    assert _loss_db(d) <= budget


def test_zr_is_not_attributed_to_ieee_802_3ae():
    r = select_media(60000)
    assert "802.3ae" not in " ".join(r.references)
    j = r.justification.lower()
    assert any(w in j for w in ("vendor", "non-standard", "not part of ieee", "not an ieee", "msa"))


def test_carrier_circuit_is_not_attributed_to_802_3ae():
    assert "802.3ae" not in " ".join(select_media(200000).references)


@pytest.mark.parametrize("d", [8000, 22000])
def test_lr_and_er_cite_802_3ae(d):
    assert "802.3ae" in " ".join(select_media(d).references)


@pytest.mark.parametrize("d", [60000, 200000])
def test_justification_states_engineering_facts_not_the_request(d):
    assert "requested" not in select_media(d).justification.lower()
