from dataclasses import dataclass, field


@dataclass
class Decision:
    """One engineering decision plus the reasoning behind it."""
    domain: str                      # e.g. "L1 media", "L3 routing", "VLSM"
    choice: str                      # e.g. "OS2 Single-Mode Fiber (10GBASE-ER)"
    justification: str               # natural-language reason using the actual input numbers
    references: list = field(default_factory=list)   # e.g. ["IEEE 802.3an", "RFC 2328"]

    def __str__(self) -> str:
        refs = f" [{', '.join(self.references)}]" if self.references else ""
        return f"[{self.domain}] {self.choice}: {self.justification}{refs}"