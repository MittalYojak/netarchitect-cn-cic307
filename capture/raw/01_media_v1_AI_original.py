"""Select an appropriate physical transmission medium based on cable distance."""

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
        InvalidParameterError: If distance_m is non-numeric, zero, or negative.
        PhysicalDistanceViolationError: If copper is requested beyond 100 m.
    """
    if isinstance(distance_m, bool) or not isinstance(distance_m, (int, float)):
        raise InvalidParameterError(
            f"Distance must be a numeric value, received {distance_m!r}."
        )

    if distance_m <= 0:
        raise InvalidParameterError(
            f"Distance must be greater than zero, received {distance_m!r}."
        )

    if requested_media is not None and not isinstance(requested_media, str):
        raise InvalidParameterError(
            f"Requested media must be a string or None, received {requested_media!r}."
        )

    distance = float(distance_m)
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
                "for LAN access connectivity at this distance."
            ),
            references=["IEEE 802.3an"],
        )

    if distance <= 400:
        return Decision(
            domain="L1 media",
            choice="OM4 Multimode Fiber (10GBASE-SR)",
            justification=(
                f"The {distance_m} m run is suitable for OM4 multimode "
                "fiber in a backbone application. Its optimized 850 nm "
                "laser-optimized bandwidth reduces modal dispersion "
                "effects and supports 10GBASE-SR transmission over "
                "distances up to 400 m."
            ),
            references=["IEEE 802.3ae"],
        )

    return Decision(
        domain="L1 media",
        choice="OS2 Single-Mode Fiber (10GBASE-LR/ER)",
        justification=(
            f"The {distance_m} m run exceeds the practical 400 m "
            "multimode backbone range and is better served by OS2 "
            "single-mode fiber. Its small core minimizes modal dispersion, "
            "while the optical power budget provides sufficient allowance "
            "for fiber attenuation, connector losses, and transmission "
            "distance in MAN/WAN deployments."
        ),
        references=["IEEE 802.3ae"],
    )