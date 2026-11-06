"""Variable Length Subnet Masking (VLSM) allocation engine."""

from dataclasses import dataclass
import math

from engine.errors import AddressSpaceExhaustedError, InvalidParameterError
from engine.explain import Decision


@dataclass
class Subnet:
    """Represent an allocated IPv4 subnet and its addressing details."""

    name: str
    network: str
    prefix: int
    mask: str
    wildcard: str
    first_host: str
    last_host: str
    broadcast: str
    gateway: str
    requested_hosts: int
    usable_hosts: int
    efficiency_pct: float


def ip_to_int(address: str) -> int:
    """Convert a dotted-quad IPv4 address into a 32-bit integer."""
    if not isinstance(address, str):
        raise InvalidParameterError("IPv4 address must be a string.")

    octets = address.split(".")

    if len(octets) != 4:
        raise InvalidParameterError(f"Malformed IPv4 address: {address!r}")

    result = 0

    for octet in octets:
        if not octet.isdigit() or len(octet) > 3:
            raise InvalidParameterError(f"Malformed IPv4 address: {address!r}")

        value = int(octet)

        if value > 255:
            raise InvalidParameterError(f"IPv4 octet out of range: {address!r}")

        result = (result << 8) | value

    return result


def int_to_ip(value: int) -> str:
    """Convert a 32-bit integer into a dotted-quad IPv4 address."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidParameterError("IPv4 integer must be an integer.")

    if not 0 <= value <= 0xFFFFFFFF:
        raise InvalidParameterError(
            f"IPv4 integer is outside the 32-bit range: {value}"
        )

    octets = [
        str((value >> 24) & 0xFF),
        str((value >> 16) & 0xFF),
        str((value >> 8) & 0xFF),
        str(value & 0xFF),
    ]

    return ".".join(octets)


def prefix_to_mask(prefix: int) -> str:
    """Convert a CIDR prefix length into a dotted-decimal subnet mask."""
    if isinstance(prefix, bool) or not isinstance(prefix, int):
        raise InvalidParameterError("Prefix must be an integer.")

    if not 0 <= prefix <= 32:
        raise InvalidParameterError(
            f"Prefix length must be between 0 and 32, received {prefix}."
        )

    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return int_to_ip(mask)


def mask_to_wildcard(mask: str) -> str:
    """Convert a dotted-decimal subnet mask into its wildcard mask."""
    mask_int = ip_to_int(mask)
    inverse = (~mask_int) & 0xFFFFFFFF

    # A valid subnet mask must contain contiguous leading one bits.
    inverse_bits = format(inverse, "032b")

    if "01" in inverse_bits:
        raise InvalidParameterError(f"Invalid subnet mask: {mask!r}")

    return int_to_ip(inverse)


def _parse_cidr(cidr: str) -> tuple[int, int]:
    """Validate and parse a CIDR network into its address and prefix."""
    if not isinstance(cidr, str):
        raise InvalidParameterError("Root CIDR must be a string.")

    parts = cidr.split("/")

    if len(parts) != 2:
        raise InvalidParameterError(f"Malformed CIDR notation: {cidr!r}")

    address = ip_to_int(parts[0])

    try:
        prefix = int(parts[1])
    except (ValueError, TypeError):
        raise InvalidParameterError(f"Invalid CIDR prefix: {cidr!r}") from None

    if not 0 <= prefix <= 32:
        raise InvalidParameterError(
            f"CIDR prefix must be between 0 and 32: {cidr!r}"
        )

    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network = address & mask

    if network != address:
        raise InvalidParameterError(
            f"Root CIDR contains host bits; use {int_to_ip(network)}/{prefix}."
        )

    return network, prefix


def _required_prefix(hosts: int) -> int:
    """Calculate the smallest prefix accommodating the requested hosts."""
    required_addresses = hosts + 2
    host_bits = math.ceil(math.log2(required_addresses))

    if host_bits > 32:
        raise AddressSpaceExhaustedError(
            f"Request for {hosts} hosts exceeds the IPv4 address space."
        )

    return 32 - host_bits


def allocate_vlsm(root_cidr: str, requests: list[dict]) -> list[Subnet]:
    """Allocate non-overlapping IPv4 subnets using VLSM.

    Requests are processed in descending order of host requirements.
    Each subnet is allocated sequentially from the beginning of the root
    network, respecting the block-size alignment requirement.

    Args:
        root_cidr: Root IPv4 network in CIDR notation.
        requests: List of dictionaries containing subnet names and host counts.

    Returns:
        A list of allocated Subnet objects.

    Raises:
        InvalidParameterError: If the CIDR or host requests are invalid.
        AddressSpaceExhaustedError: If the root network cannot accommodate
            all requested subnets.
    """
    root_network, root_prefix = _parse_cidr(root_cidr)

    if not isinstance(requests, list):
        raise InvalidParameterError("Requests must be provided as a list.")

    root_size = 1 << (32 - root_prefix)
    root_end = root_network + root_size

    validated_requests = []

    for request in requests:
        if not isinstance(request, dict):
            raise InvalidParameterError("Each subnet request must be a dictionary.")

        name = request.get("name")
        hosts = request.get("hosts")

        if not isinstance(name, str) or not name.strip():
            raise InvalidParameterError("Each subnet must have a non-empty name.")

        if isinstance(hosts, bool) or not isinstance(hosts, int) or hosts <= 0:
            raise InvalidParameterError(
                f"Invalid host count for subnet {name!r}: {hosts!r}"
            )

        validated_requests.append((name, hosts))

    validated_requests.sort(key=lambda item: item[1], reverse=True)

    subnets = []
    current_address = root_network

    for name, hosts in validated_requests:
        prefix = _required_prefix(hosts)
        block_size = 1 << (32 - prefix)

        # Align the next allocation to the required subnet block boundary.
        current_address = (
            (current_address + block_size - 1) // block_size
        ) * block_size

        broadcast_int = current_address + block_size - 1

        if current_address < root_network or broadcast_int >= root_end:
            raise AddressSpaceExhaustedError(
                f"Root network {root_cidr} cannot accommodate subnet "
                f"{name!r} requiring {hosts} hosts."
            )

        usable_hosts = max(block_size - 2, 0)
        mask = prefix_to_mask(prefix)
        wildcard = mask_to_wildcard(mask)

        if prefix <= 30:
            first_host_int = current_address + 1
            last_host_int = broadcast_int - 1
            gateway_int = first_host_int
        else:
            # /31 and /32 are not suitable for traditional LAN host
            # allocation with separate network and broadcast addresses.
            raise InvalidParameterError(
                f"Subnet {name!r} requires a prefix of /31 or /32, "
                "which cannot provide traditional usable host addresses."
            )

        efficiency = (hosts / usable_hosts) * 100

        subnets.append(
            Subnet(
                name=name,
                network=int_to_ip(current_address),
                prefix=prefix,
                mask=mask,
                wildcard=wildcard,
                first_host=int_to_ip(first_host_int),
                last_host=int_to_ip(last_host_int),
                broadcast=int_to_ip(broadcast_int),
                gateway=int_to_ip(gateway_int),
                requested_hosts=hosts,
                usable_hosts=usable_hosts,
                efficiency_pct=round(efficiency, 2),
            )
        )

        current_address = broadcast_int + 1

    return subnets


def utilization_report(
    subnets: list[Subnet],
    root_cidr: str,
) -> Decision:
    """Generate a Decision describing overall VLSM address-space efficiency.

    Efficiency is calculated using requested host addresses divided by
    the total usable host addresses allocated across all subnets.

    Args:
        subnets: Previously allocated subnet objects.
        root_cidr: Root network used for the allocation.

    Returns:
        A VLSM Decision containing allocation efficiency and reasoning.
    """
    _, root_prefix = _parse_cidr(root_cidr)

    root_total_addresses = 1 << (32 - root_prefix)
    root_usable_addresses = max(root_total_addresses - 2, 0)

    total_requested = sum(subnet.requested_hosts for subnet in subnets)
    total_allocated = sum(
        1 << (32 - subnet.prefix) for subnet in subnets
    )
    total_usable = sum(subnet.usable_hosts for subnet in subnets)

    efficiency = (
        (total_requested / total_usable) * 100
        if total_usable
        else 0.0
    )

    allocation_pct = (
        (total_allocated / root_total_addresses) * 100
        if root_total_addresses
        else 0.0
    )

    remaining_addresses = root_total_addresses - total_allocated

    justification = (
        f"Root network {root_cidr} contains {root_total_addresses} total "
        f"addresses ({root_usable_addresses} traditionally usable host "
        f"addresses). The allocation contains {len(subnets)} subnets, "
        f"requesting {total_requested} hosts and consuming "
        f"{total_allocated} addresses ({allocation_pct:.2f}% of the root "
        f"address space). Overall host utilization is {efficiency:.2f}% "
        f"of allocated usable addresses, with {total_usable - total_requested} "
        f"allocated usable addresses remaining unused and "
        f"{remaining_addresses} root addresses unallocated."
    )

    return Decision(
        domain="VLSM",
        choice=f"{efficiency:.2f}% host utilization",
        justification=justification,
        references=["RFC 4632"],
    )
