# Capture notes (raw observations, not fixed yet)ChatGPT model used: Luna
media.py: 22 km returns generic 'LR/ER', does not pick LR vs ER (LR ~10 km reach, ER ~40 km). Optical budget text has no numbers.
media.py: 40001/80000/150000 m accepted as normal 10GBASE-LR/ER, no reach warning (LR ~10 km, ER ~40 km, ZR ~80 km). No distance-based transceiver selection.
vlsm.py: changed import paths only
vlsm.py: mask_to_wildcard checks '01' in the INVERSE bits. A valid wildcard is 0s then 1s, so '01' always appears at the boundary. Every valid mask except /0 and /32 is rejected. Correct check: '01' in mask bits, or '10' in inverse bits. Hard crash in allocate_vlsm.
