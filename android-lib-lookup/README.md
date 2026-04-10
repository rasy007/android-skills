# android-lib-lookup

Automatically query Android/Gradle project dependency classes and APIs from locally cached AAR/JAR files.

## Features

- **Class lookup** — Input a class name, get the library it belongs to, version, and full API signatures
- **Package browsing** — List all classes under a package
- **Library listing** — List all public classes in a Maven dependency
- **Fuzzy search** — Search class names by keyword
- **Auto-indexing** — Builds index on first query, caches for subsequent use
- **Kotlin DSL support** — Works with both `build.gradle` and `build.gradle.kts`
- **Zero dependencies** — Pure Python 3.6+ standard library, no pip install needed

## Prerequisites

- Python 3.6+
- Project must have been compiled at least once via Android Studio or Gradle (so dependencies are cached in `~/.gradle/caches`)

## Quick Start

```bash
# Lookup a class by fully qualified name (recommended)
python3 scripts/lookup_class.py \
  --project /path/to/your/module \
  --class com.example.StringUtils

# Lookup by simple class name (may return multiple matches)
python3 scripts/lookup_class.py \
  --project /path/to/your/module \
  --class StringUtils
```

First run automatically builds the index (~0.5s). Subsequent queries use cache (~0.1s).

## Full Usage

### Class Lookup

```bash
# Precise FQCN lookup (recommended)
python3 scripts/lookup_class.py -p <MODULE_PATH> -c com.example.StringUtils

# Simple name lookup (returns all libraries containing this class)
python3 scripts/lookup_class.py -p <MODULE_PATH> -c StringUtils

# Show full source code instead of API summary
python3 scripts/lookup_class.py -p <MODULE_PATH> -c StringUtils --source
```

### Package Browsing

```bash
python3 scripts/lookup_class.py -p <MODULE_PATH> --package com.example.util
```

### Library Listing

```bash
python3 scripts/lookup_class.py -p <MODULE_PATH> --library com.example:utils
```

### Fuzzy Search

```bash
python3 scripts/lookup_class.py -p <MODULE_PATH> --search Toast
```

### Index Statistics

```bash
python3 scripts/lookup_class.py -p <MODULE_PATH> --stats
```

### Force Rebuild Index

```bash
python3 scripts/lookup_class.py -p <MODULE_PATH> --rebuild -c SomeClass
```

## Parameters

| Parameter | Short | Description |
|-----------|-------|-------------|
| `--project` | `-p` | Android module path (directory with build.gradle) |
| `--class` | `-c` | Lookup by class name (FQCN or simple name) |
| `--package` | `-pkg` | List classes in a package |
| `--library` | `-lib` | List classes in a library (groupId:artifactId) |
| `--search` | `-s` | Fuzzy search class names |
| `--stats` | | Show index statistics |
| `--source` | | Output full source code instead of API summary |
| `--rebuild` | | Force rebuild index |
| `--gradle-cache` | | Custom Gradle cache path (default: `~/.gradle/caches`) |

## Output Format

Query results are JSON:

```json
[
  {
    "class": "com.example.StringUtils",
    "library": "com.example:utils",
    "version": "1.2.3",
    "api_summary": "=== com.example.StringUtils ===\n\n  public class StringUtils {\n\n  public static boolean isEmpty(CharSequence str)\n  ..."
  }
]
```

| Field | Description |
|-------|-------------|
| `class` | Fully qualified class name |
| `library` | Maven coordinate (groupId:artifactId) |
| `version` | Version string |
| `api_summary` | Public method signatures with Javadoc (from sources.jar) or javap output |

## How It Works

1. Parses `build.gradle` / `build.gradle.kts` to extract all dependency coordinates
2. Locates each dependency's AAR/JAR in `~/.gradle/caches/modules-2/files-2.1/`
3. Extracts all `.class` entries from `classes.jar` inside each AAR, builds FQCN → library mapping
4. Caches the index to `<MODULE_PATH>/.lib-index-cache/` (auto-gitignored)
5. On query, looks up the class in the index, then extracts API details from `sources.jar` (preferred) or via `javap`

## Supported Dependency Configurations

`implementation`, `api`, `compileOnly`, `runtimeOnly`, `annotationProcessor`, `kapt`, `ksp`, `testImplementation`, `androidTestImplementation`, `debugImplementation`, `releaseImplementation`

## Index Caching

- Cached in `<MODULE_PATH>/.lib-index-cache/` with auto `.gitignore`
- Automatically invalidated when `build.gradle` content changes
- Use `--rebuild` to force regeneration
- If cache directory is not writable, the tool still works (just rebuilds each time)

## Publishing to skills.sh

See the [skills.sh documentation](https://skills.sh/) for publishing instructions.

```bash
# Initialize (if creating a standalone repo)
npx skills init android-lib-lookup

# Publish
npx skills add <your-github-user>/android-lib-lookup
```
