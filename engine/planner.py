"""Orchestrate NetArchitect engines into a unified explainable network plan."""

from dataclasses import dataclass
from typing import Any

from engine.errors import InvalidParameterError
from engine.explain import Decision
from engine.media import select_media
from engine.params import validate_params
from engine.routing import select_routing
from engine.topology import select_topology
from engine.vlsm import Subnet, allocate_vlsm, utilization_report


@dataclass
class LinkPlan:
    """Represent the physical media recommendation for one network link."""

    name: str
    distance_m: float
    decision: Decision


@dataclass
class Plan:
    """Represent the complete validated network architecture plan."""

    params: dict
    link_plans: list[LinkPlan]
    topology: Decision
    routing: Decision
    subnets: list[Subnet]
    vlsm_report: Decision


def build_plan(params: dict) -> Plan:
    """Build a complete network architecture plan from input parameters.

    The existing validation and engineering engines are called in sequence.
    The original input dictionary is not modified.

    Args:
        params: Network configuration parameter dictionary.

    Returns:
        A Plan containing physical media, topology, routing, and VLSM
        recommendations with their explanations.

    Raises:
        InvalidParameterError: If the input parameters are invalid.
        AddressSpaceExhaustedError: If the root network cannot accommodate
            the requested subnets.
        PhysicalDistanceViolationError: If a requested medium violates
            its physical reach.
    """
    validated_params = validate_params(params)

    routing_params = validated_params["routing"]

    # Physical media recommendations, preserving link order.
    link_plans = [
        LinkPlan(
            name=link["name"],
            distance_m=link["distance_m"],
            decision=select_media(link["distance_m"]),
        )
        for link in validated_params["links"]
    ]

    # Select the logical network topology.
    topology = select_topology(
        endpoints=validated_params["endpoints"],
        num_sites=routing_params["num_sites"],
        resiliency=validated_params["resiliency"],
    )

    # Select the routing architecture.
    routing = select_routing(
        num_subnets=len(validated_params["subnets"]),
        num_sites=routing_params["num_sites"],
        multi_cloud=routing_params["multi_cloud"],
        num_autonomous_systems=routing_params["num_autonomous_systems"],
    )

    # Allocate the requested IPv4 subnets.
    subnets = allocate_vlsm(
        root_cidr=validated_params["root_cidr"],
        requests=validated_params["subnets"],
    )

    # Calculate overall address-space utilization.
    vlsm_report = utilization_report(
        subnets=subnets,
        root_cidr=validated_params["root_cidr"],
    )

    return Plan(
        params=validated_params,
        link_plans=link_plans,
        topology=topology,
        routing=routing,
        subnets=subnets,
        vlsm_report=vlsm_report,
    )


def all_decisions(plan: Plan) -> list[Decision]:
    """Collect every engineering decision in a deterministic order.

    The order is physical media recommendations, topology, routing,
    and finally VLSM utilization.

    Args:
        plan: Previously generated network architecture plan.

    Returns:
        Ordered list of all Decision objects.
    """
    return [
        *(link_plan.decision for link_plan in plan.link_plans),
        plan.topology,
        plan.routing,
        plan.vlsm_report,
    ]


def render_report(plan: Plan) -> str:
    """Render a complete ASCII plain-text network architecture report.

    Justification strings are preserved exactly as stored in their
    respective Decision objects. No wrapping, truncation, or rewriting
    is performed.

    Args:
        plan: Previously generated network architecture plan.

    Returns:
        Deterministic ASCII plain-text engineering report.

    Raises:
        InvalidParameterError: If report content contains non-ASCII
            characters.
    """
    params = plan.params
    routing_params = params["routing"]

    lines: list[str] = []

    def add_decision_details(decision: Decision) -> None:
        """Append a decision's choice, justification, and references."""
        lines.append(f"Choice: {decision.choice}")
        lines.append(f"Justification: {decision.justification}")

        if decision.references:
            lines.append(f"References: {', '.join(decision.references)}")
        else:
            lines.append("References: None")

    # Section 1: Scenario summary.
    lines.extend(
        [
            "1. Scenario summary",
            "-------------------",
            f"Name: {params['name']}",
            f"Profile: {params['profile']}",
            f"Endpoints: {params['endpoints']}",
            f"Root prefix: {params['root_cidr']}",
            f"Resiliency: {params['resiliency']}",
            f"Sites: {routing_params['num_sites']}",
            "",
        ]
    )

    # Section 2: Physical media per link.
    lines.extend(
        [
            "2. Physical media per link",
            "--------------------------",
        ]
    )

    for index, link_plan in enumerate(plan.link_plans, start=1):
        lines.extend(
            [
                f"Link {index}: {link_plan.name}",
                f"Distance: {link_plan.distance_m} m",
            ]
        )
        add_decision_details(link_plan.decision)
        lines.append("")

    # Section 3: Topology tier.
    lines.extend(
        [
            "3. Topology tier",
            "----------------",
        ]
    )
    add_decision_details(plan.topology)
    lines.append("")

    # Section 4: Routing protocol.
    lines.extend(
        [
            "4. Routing protocol",
            "-------------------",
        ]
    )
    add_decision_details(plan.routing)
    lines.append("")

    # Section 5: Address plan.
    lines.extend(
        [
            "5. Address plan",
            "---------------",
            (
                f"{'Name':<20} "
                f"{'Network/Prefix':<22} "
                f"{'Mask':<16} "
                f"{'Wildcard':<16} "
                f"{'Gateway':<16} "
                f"{'First-Last Host':<32} "
                f"{'Broadcast':<16} "
                f"{'Hosts (Req/Usable)':<20} "
                f"{'Efficiency %':<13}"
            ),
            "-" * 175,
        ]
    )

    for subnet in plan.subnets:
        host_range = f"{subnet.first_host}-{subnet.last_host}"
        requested_vs_usable = (
            f"{subnet.requested_hosts}/{subnet.usable_hosts}"
        )

        lines.append(
            f"{subnet.name:<20} "
            f"{f'{subnet.network}/{subnet.prefix}':<22} "
            f"{subnet.mask:<16} "
            f"{subnet.wildcard:<16} "
            f"{subnet.gateway:<16} "
            f"{host_range:<32} "
            f"{subnet.broadcast:<16} "
            f"{requested_vs_usable:<20} "
            f"{subnet.efficiency_pct:.2f}%"
        )

    lines.extend(
        [
            "",
            "VLSM justification:",
            plan.vlsm_report.justification,
            "",
            f"VLSM choice: {plan.vlsm_report.choice}",
        ]
    )

    if plan.vlsm_report.references:
        lines.append(
            f"References: {', '.join(plan.vlsm_report.references)}"
        )
    else:
        lines.append("References: None")

    lines.append("")

    # Section 6: Complete architectural rationale log.
    lines.extend(
        [
            "6. Architectural rationale log",
            "------------------------------",
        ]
    )

    for index, decision in enumerate(all_decisions(plan), start=1):
        lines.extend(
            [
                f"{index}. [{decision.domain}] {decision.choice}",
                decision.justification,
            ]
        )

    report = "\n".join(lines)

    try:
        report.encode("ascii")
    except UnicodeEncodeError as exc:
        raise InvalidParameterError(
            "Report contains non-ASCII characters and cannot be rendered "
            "as an ASCII-only report."
        ) from exc

    return report
