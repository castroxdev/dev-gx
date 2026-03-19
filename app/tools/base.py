from dataclasses import dataclass


@dataclass(frozen=True)
class PlannerTool:
    name: str
    purpose: str
    guidance: str
