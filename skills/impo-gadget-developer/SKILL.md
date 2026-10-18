---
name: impo-gadget-developer
description: Create and edit Impo gadget products and their manifests with an Impo developer API key — list products, pull a manifest to a file, edit its system prompt, commands and events, preview the agent instructions, push a new dev revision, publish to production for a firmware version, register official units, and pair a development device. Use whenever someone builds an Impo gadget or asks to change what the Impo agent knows about their device ("update my gadget's manifest", "add a command to my lamp", "publish the manifest for firmware 1.2", "pair my dev board to Impo").
---

# Impo gadget developer

An Impo **product** is one kind of gadget: a permanent ID (the firmware declares it as
`product_id`), a name, and **manifests** that tell the user's Impo agent what the gadget is and
what it can do. This skill manages them through the developer API with the user's API key.

## Setup

- The user needs a developer profile and an API key from https://impo.ai/developers/keys.
- The key must be in `IMPO_API_KEY`. Never print it, write it into files you commit, or put it in
  a manifest. If it is missing, ask the user to export it in their shell; do not ask them to paste
  it into the conversation.
- Run the CLI with `python3 scripts/impo.py …` (path relative to this skill). It uses only the
  Python standard library.

## How devices read manifests

- A manifest belongs to a **channel** and a **minimum firmware version**.
  - **dev**: what you edit and test. Development devices (paired with your key, see `pair`) and
    devices from dev batches read it.
  - **production**: what shipped devices read. `publish` copies the dev manifest for one firmware
    version to production.
- Each channel can hold several manifests, one per minimum firmware version. A device reads the
  manifest with the highest minimum firmware **not above** its own version. Example: production has
  manifests for `1.0.0` (`lamp.set`) and `1.2.0` (`lamp.set`, `lamp.temperature`). A lamp on 1.1
  reads the 1.0 one; a lamp on 1.3 reads the 1.2 one. Add a new firmware version's manifest
  instead of changing an older one when a firmware release adds commands.
- Every command in a manifest must be implemented by that firmware, or the device is treated as
  not set up (official units are refused). The agent only sees the manifest's commands.

## Workflow

1. `python3 scripts/impo.py products` — see what exists and the current revisions.
2. To change a manifest, pull it to a file, edit the file, preview, push:
   ```sh
   python3 scripts/impo.py manifest pull studio-lamp -o studio-lamp.manifest.json   # add --min-firmware X if several
   python3 scripts/impo.py manifest preview studio-lamp.manifest.json
   python3 scripts/impo.py manifest push studio-lamp.manifest.json
   ```
   A new product: `product create <id> <name>`, then write the file from
   `examples/studio-lamp.manifest.json` and push it. Keep the manifest file in the user's repository
   next to the firmware so it is reviewed like code.
3. Pushing creates the next dev revision and delivers it at once to the developer's own account
   (development devices pick it up without reconnecting).
4. When the user has tested it, publish for that firmware version:
   `python3 scripts/impo.py manifest publish studio-lamp --min-firmware 1.2.0`.
   Publishing changes what customers' devices read. Confirm with the user before publishing, and say
   which firmware version and revision it affects.

Write a manifest with `reference/manifest.md` open: names, limits and the JSON Schema subset are
enforced on save, and the server's error says which field is wrong. Good manifests:

- `systemPrompt`: what the device is, where it sits, and when the agent should and should not use
  it (for example "never change the colour temperature during a video call"). Plain sentences.
- One command per action, named `area.verb` (`lamp.set`, `display.show_text`), with a description
  that says what happens and any limits, and tight parameter schemas (`enum`, `minimum`,
  `maxLength`, `required`, `additionalProperties: false`).
- Events for things the device notices (`button_pressed`), each with a short description.

## Development devices

`python3 scripts/impo.py pair "Desk lamp" -o pairing.json` pairs one development device to the key
owner's account and writes its `pairing.json` (gateway tokens, file mode 0600). The device then
connects with the Impo gadget SDK and declares its `product_id`; it reads the dev manifest. Use a
new pair call per device; to retry a lost response for the same device, pass the printed
`--request-id`. `pairing.json` is a device credential: keep it out of version control.

## Official units

Mass-produced units prove they are genuine with a per-unit eFuse key derived from a batch key.
Creating a batch (which shows its key once) is only possible in the portal, never with an API key.
With a key you can register units into an existing batch (`unit register <product> <unit-id>
<batch-id>`, unit ID = the chip's factory MAC, 12 lowercase hex digits) and revoke them.

## What an API key cannot do

Create or revoke keys, change the developer profile, or create batches. Those return
`session_required`; send the user to https://impo.ai/developers. A key never accesses anyone's
conversations or the Impo app API. If a key leaks (it may be built into development firmware),
revoke it in the portal and create a new one.

## Errors

The CLI prints the API error code and a hint. Common ones: `invalid_api_key` (unknown or revoked
key), `not_found` (no such product on this account), `conflict` (product ID taken by another
account), `invalid_request` (a manifest field is invalid; the message names it),
`pairing_removed` (that device was removed from the account; pair again without `--request-id`).
