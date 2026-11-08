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

NetArchitect includes a switch configuration generator in `engine/configgen.py`.

The generated Campus LAN switch configurations are available in:

```text
exports/campus_lan/
├── CORE-SW1.cfg
├── ACCESS-SW1.cfg
└── campus_lan.pkt
```

The Campus LAN topology was tested in Cisco Packet Tracer using a multilayer core switch, an access switch and end devices.

Verification included:

- VLAN creation and assignment.
- Trunk configuration and native VLAN verification.
- Inter-VLAN connectivity.
- Access to the management VLAN.
- Access-control list (ACL) enforcement.
- End-to-end connectivity between PCs.

A platform compatibility issue involving the `switchport trunk encapsulation dot1q` command on Catalyst 2960 switches was identified during Packet Tracer testing and corrected.

Supporting screenshots and raw verification evidence are available in `capture/`.

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
