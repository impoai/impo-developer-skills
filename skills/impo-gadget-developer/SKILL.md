---
name: impo-gadget-developer
description: The whole Impo gadget developer workflow with an Impo developer API key — create products (Impo assigns each a UUID product ID), pull a manifest to a file, edit its system prompt, scenarios, commands and events, preview the agent instructions, push a new dev revision, connect a development device (an ESP32 board built with the product ID and set up in the Impo app, or a program on a computer paired with pairing.json, such as the bundled virtual lamp), publish to production for a firmware version, and register official units. Use whenever someone builds an Impo gadget or asks to change what the Impo agent knows about their device ("update my gadget's manifest", "add a command to my lamp", "publish the manifest for firmware 1.2", "connect my dev board to Impo", "try my product with the virtual lamp").
---

# Impo gadget developer

An Impo **product** is one kind of gadget: a permanent **product ID** (a UUID that Impo assigns
when the product is created; the firmware declares it as `product_id`), a **name** (only a
label; it can change and need not be unique), and **manifests** that tell the user's Impo agent
what the gadget is and what it can do. This skill does the whole developer workflow with the
user's API key: create the product, write and push its manifest, connect a development device,
publish to production and register factory units.

## Setup

- The user needs a developer profile and an API key from https://impo.ai/developers/keys.
- The key must be in `IMPO_API_KEY`. Never print it, write it into files you commit, or put it in
  a manifest, firmware or a device. If it is missing, ask the user to export it in their shell;
  do not ask them to paste it into the conversation.
- Run the CLI with `python3 scripts/impo.py …` (path relative to this skill). It uses only the
  Python standard library.
- Every command takes the product ID, never the name. `impo.py products` lists names and IDs.

## How devices read manifests

- A manifest belongs to a **channel** and a **minimum firmware version**.
  - **dev**: what you edit and test. The developer's own development devices and devices from
    dev batches read it.
  - **production**: what shipped devices read. `publish` copies the dev manifest for one firmware
    version to production.
- Each channel can hold several manifests, one per minimum firmware version. A device reads the
  manifest with the highest minimum firmware **not above** its own version. Example: production has
  manifests for `1.0.0` (`lamp.set`) and `1.2.0` (`lamp.set`, `lamp.temperature`). A lamp on 1.1
  reads the 1.0 one; a lamp on 1.3 reads the 1.2 one. Add a new firmware version's manifest
  instead of changing an older one when a firmware release adds commands.
- Every command in a manifest must be implemented by that firmware, or the device is treated as
  not set up (official units are refused). The agent only sees the manifest's commands.

## 1. Create a product

```sh
python3 scripts/impo.py product create "Studio Lamp"     # prints: Product ID: <uuid>
```

Each call creates a new product. If the response was lost, run `impo.py products` before trying
again, so you do not create a second one. Record the ID in the user's repository (for example in
the manifest file and the firmware configuration); it never changes. `product rename <id> <name>`
changes only the name.

## 2. Write and push the manifest

```sh
python3 scripts/impo.py manifest pull <id> -o studio-lamp.manifest.json   # add --min-firmware X if several
python3 scripts/impo.py manifest preview studio-lamp.manifest.json
python3 scripts/impo.py manifest push studio-lamp.manifest.json
```

For a new product, copy `examples/studio-lamp.manifest.json`, set `"product"` to the product ID,
edit it and push it. Keep the file in the user's repository next to the firmware so it is
reviewed like code. Pushing creates the next dev revision and delivers it at once to the
developer's own account (connected development devices pick it up without reconnecting).

Write a manifest with `reference/manifest.md` open: names, limits and the JSON Schema subset are
enforced on save, and the server's error says which field is wrong. Good manifests:

- `systemPrompt`: what the device is, where it sits, and general rules for when the agent should and should not use
  it (for example "never change the colour temperature during a video call"). Plain sentences.
- One command per action, named `area.verb` (`lamp.set`, `display.show_text`), with a description
  that says what happens and any limits, and tight parameter schemas (`enum`, `minimum`,
  `maxLength`, `required`, `additionalProperties: false`).
- Events for things the device notices (`button_pressed`), each with a short description.
- `scenarios`: goal-specific behavior in separate `{name, when, instructions}` entries. Explain
  how to combine capabilities, check results, stop and deliver the outcome. Keep these out of
  the general system prompt. Pull before editing to preserve other scenarios; use an empty array
  to clear them. Scenarios guide the agent and do not grant permissions or add commands.

## 3. Connect a development device

A development device joins the developer's own account and reads the product's dev manifest.
There are two kinds; pick the one that matches the device.

### An ESP32 board with the Impo Gadget SDK firmware

The board gets its device tokens from the Impo app during Bluetooth setup. It needs no API key
and no `pairing.json`.

1. In the SDK checkout (`https://github.com/impoai/impo-gadget-sdk`, directory `esp32/`), build
   once for the board so its configuration exists: `tools/board.sh <board> build` (or
   `tools/impo/board.sh build <board>` for the boards the SDK README lists that way; `idf.py build`
   for the ESP32-C5 DevKitC-1). ESP-IDF v6 must be active (`. ~/esp/esp-idf-v6/export.sh`).
2. Set the product ID in that build's configuration and build again. With `tools/board.sh` the
   file is `build-<board>/sdkconfig`; with plain `idf.py` it is `sdkconfig`:
   ```sh
   sed -i.bak 's/^CONFIG_GADGET_PRODUCT_ID=.*/CONFIG_GADGET_PRODUCT_ID="<product id>"/' build-<board>/sdkconfig
   tools/board.sh <board> build
   ```
   The build fails if the value is not a lowercase UUID. A "No SDK token" warning does not matter
   for Impo.
3. Flash it: `tools/board.sh <board> flash <port>` (`ls /dev/cu.usb*` on macOS lists ports).
   Flashing needs the board's USB serial port; if you run in a sandbox, ask the user to allow it.
4. Ask the user to set the board up in the Impo app on **their own account** (the SDK README,
   "Set it up with Impo"). This step needs their phone; you cannot do it for them.
5. When it is connected, the board declares the product and the agent gets the dev manifest. In
   the app the gadget shows as "<product name> · Custom". If it shows "Custom · Not set up",
   the product ID is wrong, the product belongs to another account, or the firmware does not
   implement every command in the manifest.

### A program on a computer (no Bluetooth setup)

For a device that cannot be set up in the app, such as the virtual lamp or your own program,
create its tokens with the API key on the user's computer:

```sh
python3 scripts/impo.py pair "Studio lamp" -o pairing.json
```

`pair` uses the key once to create tokens for one device and writes them to `pairing.json`
(file mode 0600; it refuses to overwrite an existing file unless you pass `--replace`). The
program connects with those tokens and declares its `product_id`. Use a new pair call per device;
to retry a lost response for the same device, pass the printed `--request-id`. `pairing.json` is a
device credential: keep it out of version control.

To try a product without hardware, run the virtual lamp. It needs the SDK's Python package:

```sh
git clone https://github.com/impoai/impo-gadget-sdk
python3 -m venv .venv && . .venv/bin/activate && pip install -e impo-gadget-sdk/linux
python3 examples/virtual_lamp.py --pairing pairing.json --product <product id>
```

It prints "Registered" when it is connected. Then the user can open Gadgets in the Impo app, pick
the lamp and ask the agent to turn it on; the lamp prints each command. It implements `lamp.set`
and `lamp.status`, so its manifest may use only those commands.

## 4. Publish to production

`python3 scripts/impo.py manifest publish <id> --min-firmware 1.2.0` copies the dev manifest for
that firmware version to production. Publishing changes what customers' devices read. Confirm with
the user before publishing, and say which firmware version and revision it affects.

## 5. Official units

Mass-produced units prove they are genuine with a per-unit eFuse key derived from a batch key.
Creating a batch (which shows its key once) is only possible in the portal, never with an API key.
With a key you can register units into an existing batch (`unit register <id> <unit-id>
<batch-id>`, unit ID = the chip's factory MAC, 12 lowercase hex digits) and revoke them
(`unit revoke <id> <unit-id>`). Official units need no `product_id` in firmware and no API key:
the unit proves itself, and its owner sets it up in the Impo app.

## What an API key cannot do

Create or revoke keys, change the developer profile, or create batches. Those return
`session_required`; send the user to https://impo.ai/developers. A key never accesses anyone's
conversations or the Impo app API. If a key may have leaked, revoke it in the portal and create a
new one.

## API key and device tokens

Never put the API key in firmware, app code, a browser, a repository or a manifest; if the user
asks to, explain that anyone who reads it could pair devices to their account and change their
manifests, and use the steps in section 3 instead. An ESP32 board gets its tokens from the Impo
app; a program on a computer gets them from `pair`.

| | API key | Device tokens (`pairing.json`) |
| --- | --- | --- |
| What it is | `impo_dev_…`, generated on the portal's API keys page | `access_token` and `refresh_token`, created for one device by `pair` |
| Where it lives | The user's computer, server or CI secrets (`IMPO_API_KEY`) | The one device it was created for |
| Bound to | The developer account | The account and one pairing (one device); not to a product or the hardware |
| Can | Pair devices; manage products, manifests and units | Connect that device to the account through the gadget gateway |
| Cannot | Create keys, change the profile, create batches, sign in | Edit manifests, pair other devices, call the developer API |
| Expires | Never; until revoked | `access_token` 4 hours (renewed automatically); `refresh_token` 365 days |
| To stop it | Revoke it in the portal | Remove the device from the account (Gadgets); pair again for new tokens |

The device declares `product_id` on every connection and reads that product's dev manifest only if
the product belongs to the account. Official units use neither: their eFuse key proves them, and the
Impo app gives them tokens for their owner's account.

## Errors

The CLI prints the API error code and a hint. Common ones: `invalid_api_key` (unknown or revoked
key), `not_found` (no such product on this account), `invalid_request` (a field is invalid, for example
a product ID that is not a UUID; the message names it),
`pairing_removed` (that device was removed from the account; pair again without `--request-id`).
