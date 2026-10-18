# Impo developer skills

Agent skills for building [Impo](https://impo.ai) gadgets. With your Impo developer API key, an
agent such as Claude Code can create products, edit and preview their manifests, push new dev
revisions, publish them to production for a firmware version, register official units and pair
development devices — from the repository where your firmware lives.

| Skill | What it does |
| --- | --- |
| [`impo-gadget-developer`](skills/impo-gadget-developer/SKILL.md) | Products, manifests, publishing, units and development pairing through the Impo developer API |

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

- "List my Impo products."
- "Add a `lamp.temperature` command with warm, neutral and cool to the studio-lamp manifest for firmware 1.2."
- "Preview what the agent will be told about my lamp."
- "Publish the studio-lamp manifest for firmware 1.2 to production."
- "Pair this board as a development device."

The CLI also works on its own:

```sh
python3 skills/impo-gadget-developer/scripts/impo.py products
python3 skills/impo-gadget-developer/scripts/impo.py manifest pull studio-lamp -o studio-lamp.manifest.json
python3 skills/impo-gadget-developer/scripts/impo.py manifest push studio-lamp.manifest.json
python3 skills/impo-gadget-developer/scripts/impo.py manifest publish studio-lamp --min-firmware 1.2.0
```

## How it fits together

- A **product** is one kind of gadget: a permanent ID the firmware declares as `product_id`, a
  name and manifests.
- A **manifest** tells the user's Impo agent what the gadget is and which commands and events it
  has. Each one is for a channel (dev or production) and a minimum firmware version; a device reads
  the highest one not above its own firmware.
- A **development device** is paired with your API key and joins your account; it reads the dev
  manifest. An **official unit** carries a per-unit eFuse key from a production batch, is set up by
  its owner in the Impo app and reads the production manifest.

An API key cannot create keys, change your profile or create batches; use the
[developer portal](https://impo.ai/developers) for those. Revoke a key there if it may have leaked.

## API key and device tokens

Your API key stays on your computer, server or CI. Never put it in firmware, an app or a
repository. A device gets its own tokens: `impo.py pair` uses the key once and writes
`pairing.json` for that one device; copy that file to a board.

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
