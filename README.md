# Android Skills

AI Agent Skills for Android development. Compatible with Cursor, Amp, Cline, Codex, and more.

## Available Skills

| Skill | Description | Install |
|-------|-------------|---------|
| [android-lib-lookup](android-lib-lookup/) | Query dependency classes & APIs from cached AAR/JAR | `npx skills add rasy007/android-skills --skill android-lib-lookup` |

## Installation

```bash
# Install a specific skill
npx skills add rasy007/android-skills --skill <skill-name>

# Install globally (available to all AI agents)
npx skills add rasy007/android-skills --skill <skill-name> -g
```

## Contributing

Each skill is a self-contained directory with a `SKILL.md` and optional supporting files:

```
skill-name/
├── SKILL.md              # Required — main instructions for the AI agent
├── README.md             # Optional — human-readable documentation
└── scripts/              # Optional — utility scripts
```
