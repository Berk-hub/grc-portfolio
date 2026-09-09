#!/usr/bin/env python3

import base64
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = (
    "http://localhost:8084/rest/channel/"
    "ctrlBackend0/LastSuccessfulResend"
)

TOKEN = base64.b64encode(b"x:admin").decode()

OUT = Path(
    "evidence/backend-loss/"
    "13-historic-resend-monitor.jsonl"
)

def read_value():
    req = urllib.request.Request(
        URL,
        headers={
            "Authorization": f"Basic {TOKEN}"
        },
    )

    with urllib.request.urlopen(
        req,
        timeout=10,
    ) as response:
        return json.loads(response.read()).get("value")

started = time.time()
timeout = 66 * 60

with OUT.open("a", encoding="utf-8") as f:
    while time.time() - started < timeout:
        value = read_value()

        row = {
            "observed_at_utc": (
                datetime.now(timezone.utc).isoformat()
            ),
            "last_successful_resend": value,
        }

        f.write(json.dumps(row) + "\n")
        f.flush()

        print(json.dumps(row), flush=True)

        if value is not None:
            break

        time.sleep(30)
