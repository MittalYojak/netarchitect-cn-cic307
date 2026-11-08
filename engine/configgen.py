"""Generate Cisco IOS switch configurations from a NetArchitect Plan."""

from engine.errors import InvalidParameterError
from engine.planner import Plan
from engine.vlsm import Subnet, ip_to_int, int_to_ip


def generate_switch_configs(plan: Plan) -> dict[str, str]:
    """Generate CORE-SW1 and ACCESS-SW1 Cisco IOS configurations.

    LAN subnets are mapped to VLAN IDs in increments of 10, preserving
    their order in the original parameter dictionary.

    Args:
        plan: A validated NetArchitect Plan containing parameters and
            allocated subnet objects.

    Returns:
        A dictionary containing exactly two complete IOS configurations:
        CORE-SW1 and ACCESS-SW1.

    Raises:
        InvalidParameterError: If there are no LAN subnets, more than
            20 LAN subnets, a required subnet is missing, or the
            management subnet has insufficient usable hosts.
    """
    params = plan.params
    subnet_requests = params["subnets"]

    # Identify LAN subnets while preserving their original order.
    lan_requests = [
        request
        for request in subnet_requests
        if not request["name"].startswith(("P2P-", "Tunnel-"))
    ]

    if not lan_requests:
        raise InvalidParameterError(
            "At least one LAN subnet is required to generate switch configs."
        )

    if len(lan_requests) > 20:
        raise InvalidParameterError(
            f"Cannot generate more than 20 LAN VLANs; "
            f"received {len(lan_requests)}."
        )

    # Index allocated subnet objects by name.
    allocated_subnets: dict[str, Subnet] = {
        subnet.name: subnet for subnet in plan.subnets
    }

    lan_subnets: list[tuple[int, Subnet]] = []

    for index, request in enumerate(lan_requests):
        name = request["name"]
        subnet = allocated_subnets.get(name)

        if subnet is None:
            raise InvalidParameterError(
                f"Allocated subnet not found for LAN subnet {name!r}."
            )

        vlan_id = 10 * (index + 1)
        lan_subnets.append((vlan_id, subnet))

    vlan_list = ",".join(
        str(vlan_id) for vlan_id, _ in lan_subnets
    )

    management = next(
        (
            (vlan_id, subnet)
            for vlan_id, subnet in lan_subnets
            if subnet.name == "Management"
        ),
        None,
    )

    # Build the shared trunk configuration.
    trunk_lines = [
        "interface GigabitEthernet0/1",
        " description Trunk uplink to distribution/core switch",
        " switchport trunk encapsulation dot1q",
        " switchport mode trunk",
        f" switchport trunk allowed vlan {vlan_list}",
        " switchport trunk native vlan 999",
        " switchport nonegotiate",
        " no shutdown",
    ]

    # ---------------------------------------------------------
    # CORE-SW1: Layer 3 switch configuration
    # ---------------------------------------------------------
    core_blocks: list[list[str]] = [
        [
            "hostname CORE-SW1",
            "no ip domain-lookup",
            "ip routing",
        ],
        [
            "spanning-tree mode rapid-pvst",
            f"spanning-tree vlan {vlan_list} priority 4096",
        ],
        [
            "vlan 999",
            " name BLACKHOLE-NATIVE",
        ],
    ]

    # VLAN definitions.
    for vlan_id, subnet in lan_subnets:
        core_blocks.append(
            [
                f"vlan {vlan_id}",
                f" name {subnet.name}",
            ]
        )

    # Layer 3 switched virtual interfaces.
    for vlan_id, subnet in lan_subnets:
        svi_lines = [
            f"interface Vlan{vlan_id}",
            f" description Gateway for {subnet.name}",
            f" ip address {subnet.gateway} {subnet.mask}",
        ]

        if management is not None and subnet.name != "Management":
            svi_lines.append(" ip access-group PROTECT-MGMT in")

        svi_lines.append(" no shutdown")
        core_blocks.append(svi_lines)

    core_blocks.append(trunk_lines)

    # Management access-control list.
    if management is not None:
        _, mgmt_subnet = management

        core_blocks.append(
            [
                "ip access-list extended PROTECT-MGMT",
                " remark Restrict access to the management subnet",
                f" deny ip any {mgmt_subnet.network} {mgmt_subnet.wildcard}",
                " permit ip any any",
            ]
        )

    # OSPF routing configuration.
    ospf_lines = [
        "router ospf 1",
        " router-id 1.1.1.1",
        " passive-interface default",
    ]

    for _, subnet in lan_subnets:
        ospf_lines.append(
            f" network {subnet.network} {subnet.wildcard} area 0"
        )

    core_blocks.append(ospf_lines)
    core_blocks.append(["end"])

    core_config = "\n!\n".join(
        "\n".join(block) for block in core_blocks
    ) + "\n"

    # ---------------------------------------------------------
    # ACCESS-SW1: Layer 2 switch configuration
    # ---------------------------------------------------------
    access_blocks: list[list[str]] = [
        [
            "hostname ACCESS-SW1",
            "no ip domain-lookup",
        ],
        [
            "spanning-tree mode rapid-pvst",
        ],
        [
            "vlan 999",
            " name BLACKHOLE-NATIVE",
        ],
    ]

    # VLAN definitions.
    for vlan_id, subnet in lan_subnets:
        access_blocks.append(
            [
                f"vlan {vlan_id}",
                f" name {subnet.name}",
            ]
        )

    # Management SVI and default gateway.
    if management is not None:
        mgmt_vlan_id, mgmt_subnet = management

        if mgmt_subnet.usable_hosts < 3:
            raise InvalidParameterError(
                f"Management subnet {mgmt_subnet.name!r} has only "
                f"{mgmt_subnet.usable_hosts} usable hosts; at least "
                "3 are required for switch management."
            )

        gateway_int = ip_to_int(mgmt_subnet.gateway)
        second_host = int_to_ip(gateway_int + 1)

        access_blocks.append(
            [
                f"interface Vlan{mgmt_vlan_id}",
                f" ip address {second_host} {mgmt_subnet.mask}",
                " no shutdown",
            ]
        )

        access_blocks.append(
            [
                f"ip default-gateway {mgmt_subnet.gateway}",
            ]
        )

    # Uplink trunk.
    access_blocks.append(trunk_lines)

    # Access ports, one per LAN subnet.
    for index, (vlan_id, subnet) in enumerate(lan_subnets, start=1):
        access_blocks.append(
            [
                f"interface FastEthernet0/{index}",
                f" description Access port for {subnet.name}",
                " switchport mode access",
                f" switchport access vlan {vlan_id}",
                " spanning-tree portfast",
                " spanning-tree bpduguard enable",
                " no shutdown",
            ]
        )

    access_blocks.append(["end"])

    access_config = "\n!\n".join(
        "\n".join(block) for block in access_blocks
    ) + "\n"

    configs = {
        "CORE-SW1": core_config,
        "ACCESS-SW1": access_config,
    }

    # Ensure generated configurations are ASCII-only.
    for hostname, config in configs.items():
        try:
            config.encode("ascii")
        except UnicodeEncodeError as exc:
            raise InvalidParameterError(
                f"Generated configuration for {hostname} contains "
                "non-ASCII characters."
            ) from exc

    return configs
