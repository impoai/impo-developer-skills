# Manifest reference

The API validates every field on save and names the field in its error.

```text
Manifest = {
  minFirmware:  string     dot-separated integers: "0", "1.2", "1.2.0"
  systemPrompt: string     ≤ 4,000 characters; what the gadget is and how the agent should use it
  commands:     Command[]  ≤ 64
  events:       Event[]    ≤ 32
}
Command = { name, description, parameters: Schema }
Event   = { name, description, data: Schema | null }
```

The server also returns `revision` (incremented on every save in that channel) and `instructions`
(derived: the system prompt followed by `- name: description` for each command; read-only).

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
  "product": "studio-lamp",
  "minFirmware": "1.2.0",
  "systemPrompt": "Studio Lamp is a desk lamp with a warm and a cool LED channel. Turn it on when the user starts focused work and dim it in the evening. Never change the colour temperature during a video call.",
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

The `product` field tells the CLI which product the file belongs to; it is not sent as part of the
manifest.
