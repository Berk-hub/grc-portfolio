#!/usr/bin/env python3

import base64
import json
import os
import sys
import uuid
import urllib.request
import urllib.error

URL = os.getenv("OPENEMS_JSONRPC_URL", "http://localhost:8084/jsonrpc")
USER = os.getenv("OPENEMS_REST_USER", "x")
PASSWORD = os.getenv("OPENEMS_REST_PASSWORD", "admin")


def rpc(method, params):
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
        "params": params,
    }

    token = base64.b64encode(
        f"{USER}:{PASSWORD}".encode()
    ).decode()

    request = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read())
    except Exception as exc:
        raise RuntimeError(f"JSON-RPC request failed: {exc}") from exc

    if "error" in result:
        raise RuntimeError(
            f"{method} failed: "
            + json.dumps(result["error"], indent=2)
        )

    return result.get("result")


def prop(name, value):
    return {"name": name, "value": value}


edge_config = rpc("getEdgeConfig", {})
components = edge_config["components"]

# The one-shot Simulator App was useful for the smoke test.
# Disable it before constructing the persistent real-time test system.
if "_simulator" in components:
    rpc(
        "updateComponentConfig",
        {
            "componentId": "_simulator",
            "properties": [
                prop("enabled", False)
            ],
        },
    )
    print("DISABLED  _simulator")


configs = [
    (
        "Scheduler.AllAlphabetically",
        "scheduler0",
        [
            prop("id", "scheduler0"),
            prop("enabled", True),
        ],
    ),
    (
        "Simulator.Datasource.Single.Channel",
        "simulateConsumption",
        [
            prop("id", "simulateConsumption"),
            prop("enabled", True),
        ],
    ),
    (
        "Simulator.Datasource.Single.Channel",
        "simulateProduction",
        [
            prop("id", "simulateProduction"),
            prop("enabled", True),
        ],
    ),
    (
        "Simulator.NRCMeter.Acting",
        "meter1",
        [
            prop("id", "meter1"),
            prop("alias", "Consumption"),
            prop("enabled", True),
            prop("datasource.id", "simulateConsumption"),
        ],
    ),
    (
        "Simulator.ProductionMeter.Acting",
        "meter2",
        [
            prop("id", "meter2"),
            prop("alias", "Solar PV"),
            prop("enabled", True),
            prop("datasource.id", "simulateProduction"),
        ],
    ),
    (
        "Simulator.GridMeter.Reacting",
        "meter0",
        [
            prop("id", "meter0"),
            prop("enabled", True),
        ],
    ),
    (
        "Simulator.EssSymmetric.Reacting",
        "ess0",
        [
            prop("id", "ess0"),
            prop("enabled", True),
            prop("maxApparentPower", 10000),
            prop("capacity", 10200),
            prop("initialSoc", 50),
        ],
    ),
    (
        "Controller.Symmetric.Balancing",
        "ctrlBalancing0",
        [
            prop("id", "ctrlBalancing0"),
            prop("enabled", True),
            prop("ess.id", "ess0"),
            prop("meter.id", "meter0"),
        ],
    ),
]


# Refresh after disabling Simulator App.
components = rpc("getEdgeConfig", {})["components"]

for factory_pid, component_id, properties in configs:
    if component_id in components:
        rpc(
            "updateComponentConfig",
            {
                "componentId": component_id,
                "properties": [
                    p for p in properties
                    if p["name"] != "id"
                ],
            },
        )
        print(f"UPDATED   {component_id}")
    else:
        rpc(
            "createComponentConfig",
            {
                "factoryPid": factory_pid,
                "properties": properties,
            },
        )
        print(f"CREATED   {component_id}")

final = rpc("getEdgeConfig", {})["components"]

required = [
    "ctrlBackend0",
    "scheduler0",
    "simulateConsumption",
    "simulateProduction",
    "meter0",
    "meter1",
    "meter2",
    "ess0",
    "ctrlBalancing0",
]

missing = [x for x in required if x not in final]

if missing:
    print("MISSING:", ", ".join(missing))
    sys.exit(1)

print()
print("REAL-TIME COMPONENT MODEL READY")
print("Backend controller preserved: ctrlBackend0")
