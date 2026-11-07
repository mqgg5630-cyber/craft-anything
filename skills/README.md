# skills/

Prompt skills the user authored with the agent. They are not part of the engine, the tool registry or the
workspace crates: nothing here is compiled, and `cargo xtask layers` does not read this folder.

Each skill is a self-contained folder with a `SKILL.md` (YAML front matter plus instructions) and, when it
needs them, `references/` and `scripts/`.

| Skill | What it does |
|---|---|
| [`seasonal-wallpaper-set`](seasonal-wallpaper-set/SKILL.md) | Turns one themed phone wallpaper (fixed couple characters + hand lettering) into a full set of another season, 10 variants, characters locked. |

To install one into a coding-agent app, copy the folder into that app's skills directory, e.g.
`~/.claude/skills/<name>/` or the shared `~/.agents/skills/<name>/`.
