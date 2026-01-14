import json
from typing import Any, NewType

CapabilityStatement = NewType("CapabilityStatement", dict[str, Any])


def load_capability_statement() -> CapabilityStatement:
    with open("static/capability_statement.json", "r", encoding="utf-8") as f:
        return CapabilityStatement(json.load(f))
