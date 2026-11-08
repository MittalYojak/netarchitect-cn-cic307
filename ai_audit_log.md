# AI Audit Log: NetArchitect (CIC-307)

## AI Tools Used

- **Claude:** Initial project planning, problem framing, repository structure, architecture, module breakdown and overall development roadmap.
- **ChatGPT:** Implementation assistance, module generation and repair, test-driven debugging, Cisco IOS configuration generation, platform compatibility fixes and documentation.

*Model versions should be recorded where they can be reliably established. Unknown versions are not retrospectively guessed.*

## Development and Verification Method

AI-generated first drafts were preserved unmodified in Git history wherever indicated by commits labelled `AI first draft`. Subsequent changes were driven by unit-test failures, integration testing, Packet Tracer observations and manual verification.

AI-generated code was reviewed and corrected through an iterative process. Test results, debugging outputs, configuration snapshots and network verification evidence are retained under `capture/raw/` and `capture/screens/`.

## Audit Entries

### 1. VLSM — Wildcard Mask Validation

- **Initial issue:** `mask_to_wildcard()` incorrectly checked for `"01"` in the inverse mask bits. This rejected valid subnet masks (except `/0` and `/32`) and accepted an invalid mask.
- **Evidence:** `capture/raw/pytest_before_fix.txt` recorded 31 VLSM test failures.
- **Correction:** Fixed the bit-pattern validation.
- **Regression tests:** `test_mask_to_wildcard_all_33_prefixes_vs_oracle` and `test_sample_allocation_exact_values`.
- **Verification:** All 110 tests passed after the correction.
- **Fix commit:** `a8797bd`.

### 2. Optical Media Selection — Reach and Budget

- **Initial issue:** The first implementation returned a generic LR/ER option without selecting an appropriate transceiver based on link distance. It also lacked numerical optical-budget explanations.
- **Issues identified during the first repair:** The revised calculations used an inconsistent attenuation assumption for ER/ZR, the ZR IEEE reference was not appropriate, and some explanations echoed input wording unnecessarily.
- **Evidence:** `capture/raw/media_v2_budget_probe.txt` and `capture/raw/pytest_media_v2_findings.txt`.
- **Correction:** Revised the media-selection logic and optical-budget calculations in the second repair.
- **References considered:** Cisco 10GBASE SFP+ Modules Data Sheet and vendor optical specifications.
- **Verification note:** Optical reach and budget assumptions should be treated as implementation assumptions tied to vendor specifications, not universal guarantees for every transceiver.

### 3. Cisco IOS Configuration — Catalyst 2960 Compatibility

- **Initial issue:** The generated ACCESS-SW1 configuration included `switchport trunk encapsulation dot1q`.
- **Observed behaviour:** Cisco Packet Tracer rejected this command on the Catalyst 2960-24TT-L because the switch supports 802.1Q trunking without requiring explicit encapsulation selection.
- **Evidence:** `capture/raw/packet_tracer_2960_error.txt` and `capture/raw/pytest_configgen_platform_fail.txt`.
- **Correction:** Added device-specific capability handling so the encapsulation command is retained for CORE-SW1 but omitted for ACCESS-SW1.
- **Regression tests:** Added tests covering the command's presence or absence and the remaining trunk-hardening commands across all presets.
- **Verification:** The corrected ACCESS-SW1 configuration was accepted in Packet Tracer. The full test suite passed: **377 tests**.

### 4. Campus LAN — Packet Tracer Verification

- **Topology tested:** One multilayer core switch, one access switch and two end devices.
- **Verification performed:** VLAN configuration, trunk operation, SVI status, inter-VLAN connectivity and management VLAN access restrictions.
- **Observed results:** PC1 successfully reached its default gateway; inter-VLAN communication was verified; access to the protected management interface was blocked by the configured ACL.
- **Evidence:** `capture/screens/pt_access_show_interfaces_trunk.png`, `capture/screens/pt_core_show_interfaces_trunk.png` and `capture/screens/pt_core_acl_hits.png`.
- **Outcome:** The Campus LAN configuration was successfully validated in Cisco Packet Tracer.