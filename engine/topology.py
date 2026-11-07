"""Select an appropriate enterprise network topology based on scale and resiliency."""


from engine.errors import InvalidParameterError
from engine.explain import Decision


def select_topology(
    endpoints: int,
    num_sites: int,
    resiliency: str,
) -> Decision:
    """Recommend a network topology based on endpoints, sites, and resiliency.

    Args:
        endpoints: Total number of network endpoints.
        num_sites: Number of geographically distinct network sites.
        resiliency: Required resiliency level, either "dual-homed" or "none".

    Returns:
        A Decision containing the recommended topology and its justification.

    Raises:
        InvalidParameterError: If endpoints or num_sites are not positive
            integers, or resiliency is not a supported value.
    """
    for parameter, value in (
        ("endpoints", endpoints),
        ("num_sites", num_sites),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise InvalidParameterError(
                f"{parameter} must be a positive integer, received {value!r}."
            )

    if resiliency not in ("dual-homed", "none") or not isinstance(
        resiliency, str
    ):
        raise InvalidParameterError(
            "resiliency must be exactly 'dual-homed' or 'none', "
            f"received {resiliency!r}."
        )

    # Select the topology according to the number of sites and endpoints.
    if num_sites == 1 and endpoints <= 500:
        choice = (
            "Two-tier collapsed core (access + collapsed core/distribution)"
        )
        topology_reason = (
            f"A single-site network with {endpoints} endpoints is within "
            "the 500-endpoint threshold for a two-tier architecture. "
            "Combining the core and distribution layers reduces hardware "
            "complexity and cost while keeping access connectivity separate."
        )
        failure_domain_reason = (
            "The collapsed core/distribution layer provides a compact "
            "architecture, but its failure can affect multiple access "
            "segments."
        )

    elif num_sites == 1:
        choice = "Three-tier hierarchical (access, distribution, core)"
        topology_reason = (
            f"A single-site network with {endpoints} endpoints exceeds "
            "the 500-endpoint threshold for a collapsed-core design. "
            "Separating access, distribution, and core layers improves "
            "scalability, traffic aggregation, and failure-domain isolation."
        )
        failure_domain_reason = (
            "Separate distribution and core layers help contain failures "
            "and simplify network expansion."
        )

    elif num_sites <= 4:
        choice = "Full-mesh site interconnect"
        inter_site_links = num_sites * (num_sites - 1) // 2

        topology_reason = (
            f"A network with {endpoints} endpoints across {num_sites} sites "
            f"requires {inter_site_links} inter-site links in a full mesh. "
            "This topology provides direct connectivity between every pair "
            "of sites, reducing dependence on intermediate sites and "
            "supporting efficient inter-site communication."
        )
        failure_domain_reason = (
            "Direct inter-site connections improve path diversity and "
            "limit the impact of an individual inter-site link failure."
        )

    else:
        choice = "Hub-and-spoke WAN"
        spoke_links = num_sites - 1

        topology_reason = (
            f"A network with {endpoints} endpoints across {num_sites} sites "
            f"requires {spoke_links} spoke links connecting remote sites "
            "to a central hub. This architecture reduces WAN connectivity "
            "complexity and centralizes routing, security, and network "
            "management as the number of sites grows."
        )
        failure_domain_reason = (
            "Centralizing connectivity simplifies administration, although "
            "the hub becomes a critical failure domain."
        )

    # Apply the selected resiliency requirement.
    if resiliency == "dual-homed":
        resiliency_reason = (
            " Dual-homed resiliency provides redundant uplinks or network "
            "paths. Access switches should connect to independent "
            "distribution or collapsed-core devices where applicable. "
            "For multi-site topologies, redundant inter-site or WAN paths "
            "should be provisioned to maintain connectivity during "
            "individual link or device failures."
        )
    else:
        resiliency_reason = (
            " With no additional resiliency, the architecture may contain "
            "a single point of failure. A failure of a critical device, "
            "uplink, inter-site connection, or central hub can interrupt "
            "connectivity for dependent network segments."
        )

    justification = (
        f"The network has {endpoints} endpoints across {num_sites} "
        f"{'site' if num_sites == 1 else 'sites'}. "
        f"{topology_reason} {failure_domain_reason}"
        f"{resiliency_reason}"
        f" The selected resiliency level is '{resiliency}'."
    )

    return Decision(
        domain="Topology tier",
        choice=choice,
        justification=justification,
        references=[],
    )
