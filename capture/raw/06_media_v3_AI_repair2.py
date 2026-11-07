"""Select an appropriate physical transmission medium based on cable distance."""

import math

from engine.errors import (
    InvalidParameterError,
    PhysicalDistanceViolationError,
)
from engine.explain import Decision


def select_media(
    distance_m: float,
    requested_media: str | None = None,
) -> Decision:
    """Recommend a network transmission medium based on physical distance.

    Args:
        distance_m: Physical cable run length in metres.
        requested_media: Optional user-requested medium type.

    Returns:
        A Decision containing the recommended medium and justification.

    Raises:
        InvalidParameterError: If distance_m is non-numeric, non-finite,
            zero, or negative.
        PhysicalDistanceViolationError: If copper is requested beyond 100 m.
    """
    if isinstance(distance_m, bool) or not isinstance(distance_m, (int, float)):
        raise InvalidParameterError(
            f"Distance must be numeric, received {distance_m!r}."
        )

    distance = float(distance_m)

    if not math.isfinite(distance):
        raise InvalidParameterError(
            f"Distance must be finite, received {distance_m!r}."
        )

    if distance <= 0:
        raise InvalidParameterError(
            f"Distance must be greater than zero, received {distance_m!r}."
        )

    if requested_media is not None and not isinstance(requested_media, str):
        raise InvalidParameterError(
            f"Requested media must be a string or None, "
            f"received {requested_media!r}."
        )

    copper_types = {"copper", "cat6a", "cat6", "cat5e"}

    if (
        requested_media is not None
        and requested_media.strip().lower() in copper_types
        and distance > 100
    ):
        raise PhysicalDistanceViolationError(
            f"Copper media was requested for a {distance_m} m run, "
            "exceeding the 100 m Ethernet copper channel limit. "
            "Signal attenuation can degrade transmission quality and "
            "cause unreliable network connectivity. Consider fiber instead."
        )

    if distance <= 100:
        return Decision(
            domain="L1 media",
            choice="Cat6a Copper (10GBASE-T)",
            justification=(
                f"The {distance_m} m run falls within the 100 m Ethernet "
                "copper channel distance limit specified by IEEE 802.3an "
                "(10GBASE-T). Cat6a provides a cost-effective solution "
                "for LAN access connectivity."
            ),
            references=["IEEE 802.3an"],
        )

    if distance <= 400:
        return Decision(
            domain="L1 media",
            choice="OM4 Multimode Fiber (10GBASE-SR)",
            justification=(
                f"The {distance_m} m run falls within the 400 m reach "
                "limit of OM4 multimode fiber using 10GBASE-SR. Its "
                "850 nm laser-optimized bandwidth controls modal "
                "dispersion and supports high-speed backbone connectivity."
            ),
            references=["IEEE 802.3ae"],
        )

    if distance <= 10_000:
        fiber_loss = distance / 1000 * 0.4
        power_budget = 6.2
        margin = power_budget - fiber_loss

        return Decision(
            domain="L1 media",
            choice="OS2 Single-Mode Fiber (10GBASE-LR)",
            justification=(
                f"The {distance_m} m run exceeds the 400 m multimode "
                "reach limit but remains within the 10,000 m reach limit "
                "of 10GBASE-LR over OS2 single-mode fiber. At 1310 nm, "
                "the assumed fiber attenuation is 0.4 dB/km. The fiber "
                f"loss is approximately {fiber_loss:.2f} dB. Against "
                f"the 6.2 dB transceiver power budget, the remaining "
                f"margin is {margin:.2f} dB. Connector, splice, and "
                "engineering-margin losses must also be considered."
            ),
            references=["IEEE 802.3ae"],
        )

    if distance <= 40_000:
        fiber_loss = distance / 1000 * 0.25
        power_budget = 10.9
        margin = power_budget - fiber_loss

        return Decision(
            domain="L1 media",
            choice="OS2 Single-Mode Fiber (10GBASE-ER)",
            justification=(
                f"The {distance_m} m run exceeds the 10,000 m reach "
                "limit of 10GBASE-LR but remains within the 40,000 m "
                "reach limit of 10GBASE-ER. At 1550 nm, the assumed fiber "
                "attenuation is 0.25 dB/km. The fiber loss is "
                f"approximately {fiber_loss:.2f} dB. Against the "
                f"10.9 dB transceiver power budget, the remaining "
                f"margin is {margin:.2f} dB. Connector, splice, and "
                "engineering-margin losses must also be considered."
            ),
            references=["IEEE 802.3ae"],
        )

    if distance <= 80_000:
        fiber_loss = distance / 1000 * 0.25
        power_budget = 24.0
        margin = power_budget - fiber_loss

        return Decision(
            domain="L1 media",
            choice="OS2 Single-Mode Fiber (10GBASE-ZR)",
            justification=(
                f"The {distance_m} m run exceeds the 40,000 m reach "
                "limit of 10GBASE-ER but remains within the 80,000 m "
                "reach limit of vendor-defined 10GBASE-ZR, a non-IEEE "
                "optical interface. At 1550 nm, the assumed fiber "
                "attenuation is 0.25 dB/km. The fiber loss is "
                f"approximately {fiber_loss:.2f} dB. Against the "
                f"24.0 dB vendor-defined transceiver power budget, "
                f"the remaining margin is {margin:.2f} dB. Connector, "
                "splice, and engineering-margin losses must also be "
                "considered. Dispersion compensation and intermediate "
                "amplification may be necessary depending on the equipment."
            ),
            references=["Vendor-defined 10GBASE-ZR specifications"],
        )

    fiber_loss = distance / 1000 * 0.25

    return Decision(
        domain="L1 media",
        choice="Carrier-Provided WAN Circuit or DWDM with Optical Amplification",
        justification=(
            f"The {distance_m} m run exceeds the 80,000 m reach limit "
            "of vendor-defined 10GBASE-ZR. At 1550 nm, using an assumed "
            "fiber attenuation of 0.25 dB/km, the estimated fiber loss "
            f"is approximately {fiber_loss:.2f} dB, excluding connector, "
            "splice, and engineering-margin losses. This exceeds the "
            "24.0 dB vendor-defined ZR transceiver power budget. A "
            "carrier-provided WAN circuit or DWDM architecture with "
            "optical amplification is therefore appropriate. The optical "
            "link requires an engineered power budget and suitable "
            "amplification to compensate for accumulated transmission losses."
        ),
        references=["ITU-T G.652", "ITU-T G.694.1"],
    )
