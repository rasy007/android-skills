# Android Skills

AI Agent Skills for Android development. Compatible with Cursor, Amp, Cline, Codex, and more.

## Available Skills

| Skill | Description | Install |
|-------|-------------|---------|
| [android-lib-lookup](android-lib-lookup/) | Query dependency classes & APIs from cached AAR/JAR | `npx skills add rasy007/android-skills --skill android-lib-lookup` |
| [android-adb-toolkit](android-adb-toolkit/) | ADB debugging toolkit: logcat filter, screenshot, screen record, data export | `npx skills add rasy007/android-skills --skill android-adb-toolkit` |
| [android-proguard-helper](android-proguard-helper/) | ProGuard/R8 rule generator — scan source code, auto-generate keep rules | `npx skills add rasy007/android-skills --skill android-proguard-helper` |
| [android-crash-analyzer](android-crash-analyzer/) | Crash/ANR log analyzer — identify type, extract key frames, fix suggestions | `npx skills add rasy007/android-skills --skill android-crash-analyzer` |
| [android-arch-generator](android-arch-generator/) | Architecture code generator — MVVM / MVI / Clean Architecture scaffolding | `npx skills add rasy007/android-skills --skill android-arch-generator` |
| [android-gradle-doctor](android-gradle-doctor/) | Gradle build diagnostics — dependency conflicts, config issues, optimization | `npx skills add rasy007/android-skills --skill android-gradle-doctor` |

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
