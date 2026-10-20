# Manifest reference

The API validates every field on save and names the field in its error.

```text
Manifest = {
  minFirmware:  string     dot-separated integers: "0", "1.2", "1.2.0"
  systemPrompt: string     ≤ 4,000 characters; identity and general operating rules
  commands:     Command[]  ≤ 64
  events:       Event[]    ≤ 32
  scenarios:    Scenario[] ≤ 16
}
Command = { name, description, parameters: Schema }
Event   = { name, description, data: Schema | null }
Scenario = { name, when, instructions }
```

The server also returns `revision` (incremented on every save in that channel) and `instructions`
(derived: the system prompt, `- name: description` for each command, then a distinct
Scenarios section; read-only).

## Scenarios

Keep goal-specific behavior separate from `systemPrompt`. Each scenario describes when
and how to combine available capabilities, check the result, stop, clean up and deliver it.

- `name`: 1–80 characters on one line, unique without regard to case.
- `when`: 1–500 characters describing the relevant user goal or situation.
- `instructions`: 1–4,000 characters describing the behavior.

All three fields are trimmed and required; NUL is rejected. Scenarios do not add commands,
automatic triggers or permissions. The user's explicit requirements and platform rules take
precedence. The API supports scenarios in preview, save, read and publish; the CLI preserves
them through pull, preview and push. Omitting the field preserves scenarios on an existing
dev manifest; send `"scenarios": []` to clear them. Preview uses only the submitted fields.

Camera captures stay in the agent's internal `/workspace/observations/` directory.
They do not automatically become reply attachments. The agent inspects them with `read_file`
and copies only chosen deliverables into `/workspace/outputs/` using the sandbox shell.
A scenario can specify the evidence its goal requires.

## Names and descriptions

- Command names: lowercase segments joined by dots, at most four segments after the first:
  `^[a-z][a-z0-9_]*(\.[a-z0-9_]+){0,3}$` (`lamp.set`, `display.draw_text`).
- Event names: `^[a-z_]{1,32}$` (`button_pressed`).
- Names are unique within their list.
- Descriptions: 1–500 characters for a command, 1–200 for an event.

## Schema subset

`parameters` must be an object schema; use `{"type": "object", "properties": {}}` for a command
without parameters. Allowed keywords:

`type` (`object`, `string`, `number`, `integer`, `boolean`, `array`), `description`, `properties`,
`required`, `additionalProperties` (only `false`), `items`, `enum`, `minimum`, `maximum`,
`minLength`, `maxLength`, `minItems`, `maxItems`, `default`.

Nesting depth is at most 4, and one schema is at most 8 KiB as JSON. Any other keyword is refused.
The agent's parameters are checked against the schema before a command is sent to the device; a
mismatch fails with `invalid_params` and never reaches the firmware.

## Firmware versions

A device reads the manifest with the highest `minFirmware` not above its own firmware version, in
its channel (dev for development devices and dev batches, production for production batches). A
device below every manifest's minimum reads none. Use `"0"` for "every firmware".

## Matching the firmware

The firmware still registers the commands it implements. Every command in the manifest must be
among them; otherwise an official unit is refused (`manifest_mismatch`) and a development device is
treated as not set up. Commands the firmware registers but the manifest omits are not offered to
the agent.

## Example

```json
{
  "product": "6f1c2b9e-4a7d-4e2b-9c1a-3d5e7f9a1b2c",
  "minFirmware": "1.2.0",
  "systemPrompt": "Studio Lamp is a desk lamp with a warm and a cool LED channel. Never change the colour temperature during a video call.",
  "scenarios": [
    {
      "name": "Focused work",
      "when": "The user starts or finishes focused work.",
      "instructions": "Turn the lamp on when work starts and off when work finishes. Report the confirmed result."
    }
  ],
  "commands": [
    {
      "name": "lamp.set",
      "description": "Turn the lamp on or off.",
      "parameters": {"type": "object", "properties": {"on": {"type": "boolean"}}, "required": ["on"], "additionalProperties": false}
    },
    {
      "name": "lamp.temperature",
      "description": "Choose a warm, neutral or cool light.",
      "parameters": {"type": "object", "properties": {"tone": {"type": "string", "enum": ["warm", "neutral", "cool"]}}, "required": ["tone"], "additionalProperties": false}
    }
  ],
  "events": [{"name": "button_pressed", "description": "The lamp's touch button was pressed.", "data": null}]
}
```

The `product` field is the product's ID (the UUID from `impo.py products`) and tells the CLI which
product the file belongs to; it is not sent as part of the manifest.
