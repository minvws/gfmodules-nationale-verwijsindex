import json
import os
from typing import Any, NewType

CapabilityStatement = NewType("CapabilityStatement", dict[str, Any])


def load_capability_statement() -> CapabilityStatement:
    dir_name = os.path.dirname(__file__)
    with open(f"{dir_name}/../../static/capability_statement.json", "r", encoding="utf-8") as f:
        return CapabilityStatement(json.load(f))
