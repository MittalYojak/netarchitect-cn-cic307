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

- **AI-generated implementation:** The initial implementation of `mask_to_wildcard()` attempted to validate the inverse subnet mask by checking for the bit sequence `"01"`.

- **Representative flawed logic:**
  ```python
  if "01" in inverse_bits:
      raise ValueError("Invalid subnet mask")
  ```

- **Prompt context:** AI assistance was requested to implement subnet-mask and wildcard-mask conversion and validation for the VLSM engine.

- **Technical diagnosis:** A valid inverse subnet mask consists of contiguous zero bits followed by contiguous one bits. Checking for `"01"` incorrectly rejects valid masks and does not reliably detect every invalid pattern.

- **Observed impact:** 31 VLSM tests failed, as recorded in `capture/raw/pytest_before_fix.txt`.

- **Correction:** Replaced the flawed substring check with validation of the required contiguous bit pattern.

- **Regression tests:** `test_mask_to_wildcard_all_33_prefixes_vs_oracle` and `test_sample_allocation_exact_values`.

- **Verification:** All 110 tests passed after correction.

- **Fix commit:** `a8797bd`.

### 2. Optical Media Selection — Reach and Budget

- **Initial issue:** The first implementation returned a generic LR/ER option without selecting an appropriate transceiver based on link distance. It also lacked numerical optical-budget explanations.

- **Issues identified during the first repair:** The revised calculations used an inconsistent attenuation assumption for ER/ZR, the ZR IEEE reference was not appropriate, and some explanations echoed input wording unnecessarily.

- **Evidence:** `capture/raw/media_v2_budget_probe.txt` and `capture/raw/pytest_media_v2_findings.txt`.

- **Correction:** Revised the media-selection logic and optical-budget calculations in the second repair.

- **References considered:** Cisco 10GBASE SFP+ Modules Data Sheet and vendor optical specifications.

- **Verification note:** Optical reach and budget assumptions should be treated as implementation assumptions tied to vendor specifications, not universal guarantees for every transceiver.

### 3. Cisco IOS Configuration — Catalyst 2960 Compatibility

- **AI-generated implementation:** The initial configuration generator added an explicit trunk encapsulation command to the access-switch configuration.

- **Representative flawed configuration:**
  ```text
  interface GigabitEthernet0/1
   switchport trunk encapsulation dot1q
   switchport mode trunk
  ```

- **Prompt context:** AI assistance was requested to generate Cisco IOS trunk configurations for the core and access switches.

- **Technical diagnosis:** The Catalyst 2960-24TT-L supports 802.1Q trunking only. It does not support selecting the encapsulation explicitly, so the generated command is rejected.

- **Observed impact:** Packet Tracer rejected the command. The failure was also captured by `capture/raw/pytest_configgen_platform_fail.txt`.

- **Correction:** Introduced device-specific capability handling. The command remains on CORE-SW1 but is omitted from ACCESS-SW1.

- **Regression tests:** Added tests verifying encapsulation-command compatibility and preservation of the remaining trunk-hardening commands.

- **Verification:** The corrected access-switch configuration was accepted in Packet Tracer. The complete test suite passed: **377 tests**.

### 4. Campus LAN — Packet Tracer Verification

- **Topology tested:** One multilayer core switch, one access switch and two end devices.

- **Verification performed:** VLAN configuration, trunk operation, SVI status, inter-VLAN connectivity and management VLAN access restrictions.

- **Observed results:** PC1 successfully reached its default gateway; inter-VLAN communication was verified; access to the protected management interface was blocked by the configured ACL.

- **Evidence:** `capture/screens/pt_access_show_interfaces_trunk.png`, `capture/screens/pt_core_show_interfaces_trunk.png` and `capture/screens/pt_core_acl_hits.png`.

- **Outcome:** The Campus LAN configuration was successfully validated in Cisco Packet Tracer.