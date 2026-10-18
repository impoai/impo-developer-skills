# Impo developer skills

Agent skills for building [Impo](https://impo.ai) gadgets. With your Impo developer API key, an
agent such as Claude Code does the whole developer workflow from the repository where your
firmware lives: create a product, write and preview its manifest, push dev revisions, connect a
development device (an ESP32 board or the bundled virtual lamp), publish to production for a
firmware version and register official units.

| Skill | What it does |
| --- | --- |
| [`impo-gadget-developer`](skills/impo-gadget-developer/SKILL.md) | Products, manifests, development devices, publishing and units through the Impo developer API |

## Before you start

1. Sign in at https://impo.ai/developers with your Impo account and complete your developer profile.
2. Generate an API key under **API keys**. It is shown once; store it like a password.
3. Export it in the shell your agent runs in:

   ```sh
   export IMPO_API_KEY=impo_dev_…
   ```

   Do not paste the key into a conversation or commit it.

## Install

**Claude Code plugin:**

```text
/plugin marketplace add impoai/impo-developer-skills
/plugin install impo-developer@impo
```

**Or copy the skill** into your project (or `~/.claude/skills/` for every project):

```sh
git clone https://github.com/impoai/impo-developer-skills
cp -R impo-developer-skills/skills/impo-gadget-developer .claude/skills/
```

The skill is a `SKILL.md` with a standard-library Python CLI, so agents that read the
`SKILL.md` format can use it the same way.

## Use

Ask your agent, for example:

- "Create an Impo product called Studio Lamp and write its manifest from this firmware."
- "Add a `lamp.temperature` command with warm, neutral and cool to the Studio Lamp manifest for firmware 1.2."
- "Preview what the agent will be told about my lamp."
- "Build this ESP32 firmware with my product ID and flash it."
- "Try my product with the virtual lamp."
- "Publish the Studio Lamp manifest for firmware 1.2 to production."

The CLI also works on its own:

```sh
cd skills/impo-gadget-developer
python3 scripts/impo.py product create "Studio Lamp"        # prints the product ID (a UUID)
python3 scripts/impo.py manifest pull <product id> -o studio-lamp.manifest.json
python3 scripts/impo.py manifest push studio-lamp.manifest.json
python3 scripts/impo.py pair "Studio lamp" -o pairing.json
python3 examples/virtual_lamp.py --pairing pairing.json --product <product id>
python3 scripts/impo.py manifest publish <product id> --min-firmware 1.2.0
```

## How it fits together

- A **product** is one kind of gadget: a permanent ID (a UUID Impo assigns when you create it;
  the firmware declares it as `product_id`), a name (a label you can change) and manifests.
- A **manifest** tells the user's Impo agent what the gadget is and which commands and events it
  has. Each one is for a channel (dev or production) and a minimum firmware version; a device reads
  the highest one not above its own firmware.
- A **development device** joins your own account and reads the dev manifest. An ESP32 board
  built with your product ID is set up in the Impo app; a program on a computer, such as the
  virtual lamp, uses `pairing.json` from `impo.py pair`. An **official unit** carries a per-unit eFuse key from a production batch, is set up by
  its owner in the Impo app and reads the production manifest.

An API key cannot create keys, change your profile or create batches; use the
[developer portal](https://impo.ai/developers) for those. Revoke a key there if it may have leaked.

## API key and device tokens

Your API key stays on your computer, server or CI. Never put it in firmware, an app or a
repository. A device gets its own tokens: an ESP32 board from the Impo app during setup, a
program on a computer from `impo.py pair`, which uses the key once and writes `pairing.json` for
that one device.

| | API key | Device tokens (`pairing.json`) |
| --- | --- | --- |
| Bound to | Your developer account | Your account and one device; not a product or the hardware |
| Can | Pair devices; manage products, manifests and units | Connect that one device to your account |
| Cannot | Create keys, change your profile, create batches, sign in | Edit manifests, pair other devices, call the developer API |
| Expires | Never; until you revoke it | Access token 4 hours (renewed); refresh token 365 days |
| To stop it | Revoke it in the portal | Remove the device from your account (Gadgets); pair again |

Details: https://impo.ai/developers/docs#credentials

Docs: https://impo.ai/developers/docs · API reference: https://impo.ai/developers/docs/api

## License

MIT
