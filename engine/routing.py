"""Routing protocol selection engine for enterprise network architectures."""

from engine.errors import InvalidParameterError
from engine.explain import Decision


def select_routing(
    num_subnets: int,
    num_sites: int,
    multi_cloud: bool,
    num_autonomous_systems: int = 1,
) -> Decision:
    """Select an appropriate routing architecture based on network scale.

    Args:
        num_subnets: Total number of network subnets.
        num_sites: Number of geographically distinct network sites.
        multi_cloud: Whether the architecture spans multiple cloud providers.
        num_autonomous_systems: Number of autonomous systems in the network.

    Returns:
        A Decision containing the recommended routing architecture
        and its engineering justification.

    Raises:
        InvalidParameterError: If counts are non-integer, boolean, zero,
            or negative, or if multi_cloud is not a boolean.
    """
    counts = {
        "num_subnets": num_subnets,
        "num_sites": num_sites,
        "num_autonomous_systems": num_autonomous_systems,
    }

    for parameter, value in counts.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise InvalidParameterError(
                f"{parameter} must be a positive integer, received {value!r}."
            )

    if not isinstance(multi_cloud, bool):
        raise InvalidParameterError(
            f"multi_cloud must be a boolean, received {multi_cloud!r}."
        )

    if num_autonomous_systems > 1:
        return Decision(
            domain="L3 routing",
            choice="eBGP (External Border Gateway Protocol)",
            justification=(
                f"The network has {num_subnets} subnets across {num_sites} "
                f"sites, spans {'multiple cloud providers' if multi_cloud else 'a single cloud environment'}, "
                f"and contains {num_autonomous_systems} autonomous systems. "
                "eBGP is recommended for exchanging routes between different "
                "autonomous systems. It provides routing-domain isolation, "
                "policy-based inter-domain routing, and route summarization "
                "where appropriate."
            ),
            references=["RFC 4271"],
        )

    if num_sites > 1 or multi_cloud:
        return Decision(
            domain="L3 routing",
            choice="Multi-Area OSPF with Area 0 backbone",
            justification=(
                f"The network has {num_subnets} subnets across {num_sites} "
                f"sites, {'uses multiple cloud providers' if multi_cloud else 'does not use multiple cloud providers'}, "
                f"and operates within {num_autonomous_systems} autonomous system. "
                "Multi-area OSPF is recommended to isolate routing domains "
                "while maintaining connectivity through the Area 0 backbone. "
                "Area boundaries support route summarization, reduce routing "
                "overhead, and improve scalability."
            ),
            references=["RFC 2328"],
        )

    if num_subnets >= 50:
        return Decision(
            domain="L3 routing",
            choice="Multi-Area OSPF with Area 0 backbone",
            justification=(
                f"The network has {num_subnets} subnets across {num_sites} "
                f"site and {num_autonomous_systems} autonomous system. "
                "Since the subnet count is at least 50, multi-area OSPF "
                "is recommended for better scalability. Dividing the network "
                "into multiple areas reduces link-state advertisement "
                "overhead and enables route summarization. Area 0 acts "
                "as the backbone connecting the other areas."
            ),
            references=["RFC 2328"],
        )

    return Decision(
        domain="L3 routing",
        choice="OSPF Single-Area (Area 0)",
        justification=(
            f"The network has {num_subnets} subnets across {num_sites} site "
            f"and {num_autonomous_systems} autonomous system, with "
            f"multi-cloud set to {multi_cloud}. Since it is a single-site "
            "network with fewer than 50 subnets, single-area OSPF using "
            "Area 0 is appropriate. Its link-state architecture enables "
            "fast convergence through shortest-path recalculation, "
            "making it suitable for this relatively small enterprise network."
        ),
        references=["RFC 2328"],
    )
