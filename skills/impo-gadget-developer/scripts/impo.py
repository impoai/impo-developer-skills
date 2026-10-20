#!/usr/bin/env python3
"""Manage Impo gadget products and manifests with a developer API key.

The key comes from IMPO_API_KEY (generate one at https://impo.ai/developers/keys).
Standard library only; Python 3.9+.

  impo.py products                                   list your products and their IDs
  impo.py product create <name>                      create a product; Impo assigns its ID (a UUID)
  impo.py product show <id>                          manifests, batches and units
  impo.py product rename <id> <name>                 rename (the ID never changes)
  impo.py manifest pull <id> [--channel dev|production] [--min-firmware X] [-o file]
  impo.py manifest preview <file>                    the instructions the agent would get
  impo.py manifest push <file>                       save as the next dev revision
  impo.py manifest publish <id> --min-firmware X     copy that dev manifest to production
  impo.py unit register <id> <unit-id> <batch-id>    register an official unit
  impo.py unit revoke <id> <unit-id>
  impo.py pair <name> [-o pairing.json]              create device tokens for one program on a computer

<id> is a product ID: the UUID Impo assigned, never the name. A manifest file is the manifest
plus the product it belongs to:
  {"product": "<product id>", "minFirmware": "1.0.0", "systemPrompt": "...", "commands": [...], "events": [...], "scenarios": [...]}
"""

import argparse
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

DEFAULT_API = "https://impo.ai/api/v1/developers"
PRODUCT_ID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MANIFEST_FIELDS = ("minFirmware", "systemPrompt", "commands", "events", "scenarios")


class APIError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"{status} {code}: {message}")
        self.status, self.code = status, code


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_base(value):
    parsed = urllib.parse.urlsplit(value)
    local = parsed.hostname in ("127.0.0.1", "localhost")
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise SystemExit("The API must be https (plain http only for localhost).")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SystemExit("The API URL must not contain credentials, a query or a fragment.")
    return value.rstrip("/")


def call(api, key, method, path, body=None):
    request = urllib.request.Request(api + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                              "User-Agent": "impo-developer-skill/1"})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=60) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read() or b"{}").get("error", {})
        except ValueError:
            detail = {}
        raise APIError(error.code, detail.get("code", "error"), detail.get("message", error.reason)) from None


def checked_product_id(value):
    if not PRODUCT_ID.match(value):
        raise SystemExit(f"'{value}' is not a product ID. Product IDs are UUIDs that Impo assigns; "
                         "`impo.py products` lists yours.")
    return value


def read_manifest(file):
    try:
        data = json.loads(Path(file).read_text())
    except (OSError, ValueError) as error:
        raise SystemExit(f"{file}: not a readable JSON manifest ({error}).")
    if not isinstance(data, dict):
        raise SystemExit(f"{file}: a manifest file is a JSON object.")
    product = data.get("product")
    if not isinstance(product, str) or not PRODUCT_ID.match(product):
        raise SystemExit(f'{file}: set "product" to your product ID, the UUID from `impo.py products`.')
    unknown = set(data) - {"product", *MANIFEST_FIELDS}
    if unknown:
        raise SystemExit(f"{file}: unknown fields {sorted(unknown)}; a manifest has {list(MANIFEST_FIELDS)}.")
    return product, {field: data[field] for field in MANIFEST_FIELDS if field in data}


def save_private(path, value):
    """Writes atomically with mode 0600 and never follows an existing symlink."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pairing-")
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(value, handle, indent=2)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except BaseException:
        os.unlink(temporary)
        raise


def show(value):
    print(json.dumps(value, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default=os.environ.get("IMPO_API_URL", DEFAULT_API))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("products")
    product = sub.add_parser("product").add_subparsers(dest="action", required=True)
    created = product.add_parser("create"); created.add_argument("name")
    shown = product.add_parser("show"); shown.add_argument("id")
    renamed = product.add_parser("rename"); renamed.add_argument("id"); renamed.add_argument("name")
    manifest = sub.add_parser("manifest").add_subparsers(dest="action", required=True)
    pulled = manifest.add_parser("pull"); pulled.add_argument("id")
    pulled.add_argument("--channel", choices=["dev", "production"], default="dev")
    pulled.add_argument("--min-firmware"); pulled.add_argument("-o", "--output")
    previewed = manifest.add_parser("preview"); previewed.add_argument("file")
    pushed = manifest.add_parser("push"); pushed.add_argument("file")
    published = manifest.add_parser("publish"); published.add_argument("id"); published.add_argument("--min-firmware", required=True)
    unit = sub.add_parser("unit").add_subparsers(dest="action", required=True)
    registered = unit.add_parser("register"); registered.add_argument("id"); registered.add_argument("unit_id"); registered.add_argument("batch_id")
    revoked = unit.add_parser("revoke"); revoked.add_argument("id"); revoked.add_argument("unit_id")
    paired = sub.add_parser("pair"); paired.add_argument("name"); paired.add_argument("-o", "--output", default="pairing.json")
    paired.add_argument("--request-id", help="reuse to retry the same device; a new device needs a new one")
    paired.add_argument("--replace", action="store_true", help="overwrite an existing file; its device stays on the account")
    args = parser.parse_args()

    key = os.environ.get("IMPO_API_KEY", "")
    if not key.startswith("impo_dev_"):
        raise SystemExit("Set IMPO_API_KEY to a developer API key (https://impo.ai/developers/keys).")
    api = api_base(args.api)
    run = lambda method, path, body=None: call(api, key, method, path, body)
    product_path = lambda value: "/gadget-products/" + checked_product_id(value)
    try:
        if args.command == "products":
            show(run("GET", "/gadget-products"))
        elif args.command == "product" and args.action == "create":
            created = run("POST", "/gadget-products", {"name": args.name})
            print(f"Created '{created['name']}'. Product ID: {created['id']}")
        elif args.command == "product" and args.action == "show":
            show(run("GET", product_path(args.id)))
        elif args.command == "product" and args.action == "rename":
            show(run("PATCH", product_path(args.id), {"name": args.name}))
        elif args.command == "manifest" and args.action == "pull":
            manifests = run("GET", product_path(args.id))["manifests"][args.channel]
            chosen = [m for m in manifests if args.min_firmware in (None, m["minFirmware"])]
            if not chosen:
                raise SystemExit(f"No {args.channel} manifest" + (f" for firmware {args.min_firmware}" if args.min_firmware else "") + ".")
            if args.min_firmware is None and len(chosen) > 1:
                raise SystemExit("Several firmware versions have manifests: " + ", ".join(m["minFirmware"] for m in chosen) + ". Pass --min-firmware.")
            value = {"product": args.id, **{field: chosen[0][field] for field in MANIFEST_FIELDS if field in chosen[0]}}
            text = json.dumps(value, indent=2) + "\n"
            if args.output:
                Path(args.output).write_text(text); print(f"Wrote {args.output} (revision {chosen[0]['revision']}).")
            else:
                print(text, end="")
        elif args.command == "manifest" and args.action == "preview":
            product_id, body = read_manifest(args.file)
            print(run("POST", product_path(product_id) + "/manifests/preview", body)["instructions"])
        elif args.command == "manifest" and args.action == "push":
            product_id, body = read_manifest(args.file)
            result = run("PUT", product_path(product_id) + "/manifests/dev", body)
            delivery = result["delivery"]
            print(f"Saved {product_id} dev revision {result['manifest']['revision']} for firmware {body['minFirmware']} and later; "
                  f"delivered to {delivery['updated']} of {delivery['routes']} accounts.")
        elif args.command == "manifest" and args.action == "publish":
            result = run("POST", product_path(args.id) + "/manifests/publish", {"minFirmware": args.min_firmware})
            print(f"Published {args.id} production revision {result['manifest']['revision']} for firmware {args.min_firmware} and later.")
        elif args.command == "unit" and args.action == "register":
            show(run("POST", product_path(args.id) + "/units", {"unitId": args.unit_id, "batchId": args.batch_id}))
        elif args.command == "unit" and args.action == "revoke":
            show(run("POST", product_path(args.id) + f"/units/{urllib.parse.quote(args.unit_id, safe='')}/revoke"))
        elif args.command == "pair":
            if Path(args.output).exists() and not args.replace and not args.request_id:
                raise SystemExit(f"{args.output} already holds a device's tokens. Use another -o, or pass --replace.")
            request_id = args.request_id or str(uuid.uuid4())
            pairing = run("POST", "/pairings", {"requestId": request_id, "name": args.name})["pairing"]
            # node_id names this device to the gateway; the SDK sends it when it refreshes its tokens.
            save_private(args.output, {**pairing, "node_id": "impo-" + str(uuid.uuid5(uuid.NAMESPACE_URL, request_id)), "display_name": args.name})
            print(f"Paired '{args.name}' to your account; wrote {args.output} (keep it private). Request ID {request_id}.")
    except APIError as error:
        hints = {"invalid_api_key": "The key is unknown or revoked; generate a new one at https://impo.ai/developers/keys.",
                 "session_required": "An API key cannot do this; use the developer portal.",
                 "developer_registration_required": "Complete your developer profile at https://impo.ai/developers/profile.",
                 "pairing_removed": "That device was removed from your account; pair again without --request-id."}
        print(f"Error: {error}", file=sys.stderr)
        if error.code in hints:
            print(hints[error.code], file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
