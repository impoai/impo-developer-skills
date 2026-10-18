"""A virtual lamp: a development device that runs on your computer.

  python3 scripts/impo.py pair "Studio lamp" -o pairing.json
  python3 examples/virtual_lamp.py --pairing pairing.json --product <product id>

It connects with the device tokens in pairing.json (never the API key), joins your account
and declares product_id, so the agent reads that product's dev manifest. Needs the Impo
Gadget SDK's Python package (pip install -e impo-gadget-sdk/linux); no hardware.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import signal
import tempfile
import time
import urllib.parse

from impogadget import impo_api
from impogadget.link_client import DeviceDescription, LinkSession, Outcome

PRODUCT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def validate_url(value: str) -> str:
    """The gateway URL from pairing.json: HTTPS, or HTTP only on this computer."""
    parsed = urllib.parse.urlsplit(value)
    local = parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or not (
        parsed.scheme == "https" or (local and parsed.scheme == "http")
    ):
        raise ValueError("pairing.json has an invalid gateway URL.")
    return value.rstrip("/")


def save_private(path: Path, value: dict) -> None:
    """Atomic, owner-only write that replaces a symlink rather than following it."""
    fd, temporary = tempfile.mkstemp(prefix=".pairing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(value, output, indent=2)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


COMMANDS = {
    "lamp.set": {"description": "Turn this virtual studio lamp on or off.",
                 "required": {"on": {"type": "boolean", "description": "Whether the lamp should be on."}}},
    "lamp.status": {"description": "Read this virtual studio lamp's current state.", "required": {}},
}


@dataclass(frozen=True)
class ProductDevice(DeviceDescription):
    """Declares product_id so the gadget binds to your product (custom gadgets only)."""
    product_id: str = ""

    def register_params(self) -> dict:
        params = super().register_params()
        if self.product_id:
            params["product_id"] = self.product_id
        return params


class Lamp:
    def __init__(self):
        self.on = False

    def run(self, command: str, params: dict, timeout_ms: int | None) -> dict:
        if command == "lamp.set":
            if set(params) != {"on"} or type(params["on"]) is not bool:
                return {"ok": False, "error": "Expected exactly one boolean parameter: on."}
            self.on = params["on"]
        elif command != "lamp.status":
            return {"ok": False, "error": "Unsupported command."}
        print("Lamp is " + ("on" if self.on else "off"), flush=True)
        return {"ok": True, "payload": {"on": self.on}}


async def serve(path: Path, product_id: str) -> None:
    pairing = json.loads(path.read_text())
    root = validate_url(pairing["api_url_v2"])
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    lamp = Lamp()
    delay = 5
    while not stop.is_set():
        vms, status = await asyncio.to_thread(impo_api.fetch_vms_with_status, pairing["access_token"], root)
        if status == 401:
            tokens, status = await asyncio.to_thread(impo_api.refresh_device_token, pairing["refresh_token"], pairing["node_id"], root)
            if status in (401, 403):
                print("This device was removed from its account. Pair it again to reconnect.")
                return
            if tokens:
                pairing.update(tokens)
                pairing["access_token_saved_at"] = time.time()
                save_private(path, pairing)
                continue
        if vms:
            device = ProductDevice(node_id=pairing["node_id"], display_name=pairing["display_name"], version="1.0.0",
                                   commands=COMMANDS, product_id=product_id)
            options = {}
            if root.startswith("http://"):
                # validate_url permits plaintext only on a local test gateway.
                from websockets.asyncio.client import connect
                async def local_connect(url, headers):
                    return await connect(url.replace("wss://", "ws://", 1), additional_headers=headers, max_size=None)
                options["connect"] = local_connect
            link = LinkSession(noise_host=pairing["noise_host"], vm_id=vms[0]["vm_id"], vm_auth_token=vms[0]["vm_auth_token"], device=device, run_command=lamp.run, **options)
            print("Connecting " + pairing["display_name"] + "…", flush=True)
            async def report_registration():
                while link.registered_at is None:
                    await asyncio.sleep(0.2)
                print("Registered. Ask Impo to turn the lamp on. Press Ctrl+C to stop.", flush=True)
            report = asyncio.create_task(report_registration())
            try:
                result = await link.run(stop)
                if result in (Outcome.UNPAIRED, Outcome.FORBIDDEN):
                    print("This device was removed or is unavailable. Check Gadgets in the Impo app.")
                    return
                if result == Outcome.STOPPED:
                    return
                if link.registered_at:
                    delay = 5
            except (OSError, TimeoutError, ConnectionError):
                print("Connection interrupted. Reconnecting…", flush=True)
            finally:
                report.cancel()
                await asyncio.gather(report, return_exceptions=True)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            delay = min(30, delay * 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pairing", type=Path, default=Path("pairing.json"), help="the file impo.py pair wrote")
    parser.add_argument("--product", required=True, help="your product ID, the UUID from impo.py products")
    args = parser.parse_args()
    if not PRODUCT_ID.match(args.product):
        parser.error("--product is your product ID, a UUID; run impo.py products to see it.")
    try:
        asyncio.run(serve(args.pairing, args.product))
    except (FileNotFoundError, KeyError, ValueError):
        parser.exit(1, "Device tokens are missing or invalid. Run impo.py pair first.\n")
