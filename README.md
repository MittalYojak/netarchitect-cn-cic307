# NetArchitect — Network Architecture Recommendation & Configuration Engine

**Course:** Computer Networks (CIC-307)
**Language:** Python 3.10+
**Project type:** CLI-based network planning and configuration tool

NetArchitect is an algorithmic network planning tool that generates enterprise network architecture recommendations from validated network requirements.

It combines network parameter validation, topology planning, Variable Length Subnet Masking (VLSM), routing recommendations, physical media selection and Cisco IOS switch configuration generation. Its decision engine provides natural-language justifications and technical references alongside its recommendations.

## 1. Features

- **Network planning:** Generate architecture plans from predefined or custom network configurations.
- **VLSM subnetting:** Allocate IP subnets based on network requirements.
- **Topology recommendations:** Generate network topology recommendations.
- **Routing recommendations:** Evaluate routing requirements and recommend suitable approaches.
- **Physical media selection:** Recommend transmission media based on link distance and requested media.
- **Cisco IOS configuration generation:** Generate switch configurations for supported network profiles.
- **Explainable decisions:** Provide justifications and technical references for recommendations.
- **Input validation:** Validate network parameters and handle invalid configurations.

## 2. Available Network Presets

NetArchitect currently includes three predefined network configurations:

| Preset | Network type |
|---|---|
| `campus_lan` | Campus Local Area Network |
| `metro_man` | Metropolitan Area Network |
| `global_wan` | Global Wide Area Network |

Presets are stored as JSON files in the `presets/` directory.

## 3. Project Architecture

```text
netarchitect-cn-cic307/
│
├── engine/
│   ├── errors.py       # Project-specific exceptions
│   ├── params.py       # Parameter loading and validation
│   ├── vlsm.py         # IP subnet allocation
│   ├── topology.py     # Network topology planning
│   ├── routing.py      # Routing recommendations
│   ├── media.py        # Physical transmission media selection
│   ├── explain.py      # Decision explanations
│   ├── planner.py      # Architecture planning engine
│   └── configgen.py    # Cisco IOS switch configuration generation
│
├── presets/            # Predefined JSON configurations
├── exports/            # Generated configuration files
├── tests/              # Automated test suite
├── capture/
│   ├── raw/            # Test outputs, debugging and development evidence
│   └── screens/        # Packet Tracer verification screenshots
│
├── cli.py              # Command-line interface
├── requirements.txt    # Project dependencies
├── pytest.ini
├── ai_audit_log.md
└── README.md
```

The `engine/` directory contains the core planning and decision-making logic. The CLI acts as the interface between users and the engine.

## 4. Installation and Setup

### Prerequisites

- Python 3.10 or later
- Git
- pip

### Clone the repository

```bash
git clone https://github.com/MittalYojak/netarchitect-cn-cic307.git
cd netarchitect-cn-cic307
```

### Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Windows Git Bash:**

```bash
source .venv/Scripts/activate
```

**Windows Command Prompt:**

```cmd
.venv\Scripts\activate
```

### Install dependencies

```bash
python -m pip install -r requirements.txt
```

## 5. Command-Line Usage

Display available commands:

```bash
python cli.py --help
```

### A. List available presets

```bash
python cli.py list
```

Expected output:

```text
campus_lan
metro_man
global_wan
```

### B. Generate a network architecture plan

Using a predefined configuration:

```bash
python cli.py plan --preset campus_lan
```

Other available presets:

```bash
python cli.py plan --preset metro_man
python cli.py plan --preset global_wan
```

Save the generated report to a file:

```bash
python cli.py plan --preset campus_lan --out report.txt
```

Using a custom JSON configuration:

```bash
python cli.py plan --custom path/to/config.json
```

### C. Check physical link media

Evaluate a link based on its physical distance:

```bash
python cli.py check-link --distance 100
```

Specify a requested transmission medium:

```bash
python cli.py check-link --distance 100 --media "Cat6a Copper"
```

Example output for a 100-metre link:

```text
Choice: Cat6a Copper (10GBASE-T)
Justification: The 100.0 m run falls within the 100 m Ethernet copper channel distance limit specified by IEEE 802.3an (10GBASE-T). Cat6a provides a cost-effective solution for LAN access connectivity.
References: IEEE 802.3an
```

## 6. Cisco IOS Configuration and Network Verification

NetArchitect includes a Cisco IOS switch configuration generator in `engine/configgen.py`. It generates core and access switch configurations using the validated network plan produced by the planning engine.

### A. Generated Configuration Exports

Configurations are generated for all three predefined network profiles:

```text
exports/
├── campus_lan/
│   ├── CORE-SW1.cfg
│   ├── ACCESS-SW1.cfg
│   └── campus_lan.pkt
│
├── metro_man/
│   ├── CORE-SW1.cfg
│   └── ACCESS-SW1.cfg
│
└── global_wan/
    ├── CORE-SW1.cfg
    └── ACCESS-SW1.cfg
```

Each profile produces two Cisco IOS switch configuration files:

- **CORE-SW1:** Includes VLAN definitions, switched virtual interfaces (SVIs), inter-VLAN routing, management access-control lists (ACLs), trunk configuration and OSPF statements.
- **ACCESS-SW1:** Includes VLAN definitions, management interface configuration, trunk settings and access-port assignments.

The configurations are generated using the subnet allocations and network requirements of the selected preset.

### B. Configuration Scope and Limitations

The current configuration generator produces a common two-switch LAN configuration baseline for all three profiles.

Although the Metro MAN and Global WAN presets contain multi-site network requirements, their generated configurations do not yet implement complete WAN deployments.

The following capabilities remain outside the current configuration generator:

- Site-specific router configurations and WAN interfaces.
- eBGP and multi-area OSPF configuration.
- IPsec VPN tunnel configuration.
- EVPL service and WAN failover configuration.
- Complete inter-site routing and cloud connectivity.

The architecture planner independently evaluates routing and network requirements and provides recommendations. However, those recommendations should not be interpreted as fully deployed router configurations.

### C. Packet Tracer Verification

The Campus LAN configuration was tested in Cisco Packet Tracer using:

- One multilayer core switch (Catalyst 3560).
- One access switch (Catalyst 2960).
- Two end devices.

Verification included:

- VLAN creation and assignment.
- Trunk configuration and native VLAN verification.
- Switched virtual interface (SVI) status.
- Inter-VLAN connectivity.
- Management VLAN access restrictions.
- Access-control list (ACL) enforcement.
- End-to-end connectivity between PCs.

A platform compatibility issue involving the `switchport trunk encapsulation dot1q` command on Catalyst 2960 switches was identified during testing and corrected through device-specific capability handling.

The corrected configurations were accepted in Packet Tracer, and connectivity and ACL behaviour were verified.

Supporting screenshots and raw verification evidence are available in:

```text
capture/
├── raw/
└── screens/
```

## 7. Testing

The project uses pytest for automated testing.

Run the complete test suite:

```bash
python -m pytest -q
```

**Latest recorded test result:**

```text
377 passed in 0.65s
```

The test suite covers parameter validation, subnet allocation, routing, topology, physical media selection, planning, CLI behaviour and switch configuration generation.

Test outputs and debugging evidence are preserved in `capture/raw/`.

## 8. AI Usage and Development Transparency

AI tools were used during different stages of development.

- **Claude:** Initial project planning, problem framing, repository structure, architecture and development roadmap.
- **ChatGPT:** Implementation assistance, module generation and repair, debugging, testing support and configuration compatibility fixes.

AI-generated drafts, subsequent modifications, identified defects and their resolutions are documented in `ai_audit_log.md` and the repository's Git history.

All generated code was subjected to testing and verification. Packet Tracer was used to validate the Campus LAN implementation beyond unit testing.

## 9. Project Scope

The current implementation focuses on algorithmic network planning, explainable recommendations, VLSM subnetting, physical media selection and Cisco IOS switch configuration generation.

Router configuration generation and further integration of generated configurations across all network profiles remain areas for subsequent development.

---

**Repository:** https://github.com/MittalYojak/netarchitect-cn-cic307

**Academic project:** Computer Networks (CIC-307)
