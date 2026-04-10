---
name: android-lib-lookup
description: >-
  Query Android/Gradle dependency classes and APIs from cached AAR/JAR files.
  Auto-index all Maven dependencies, lookup class by name, browse packages, search APIs.
  Use when encountering unknown Java/Kotlin classes from remote dependencies, needing
  library API signatures, decompiling AAR classes, or writing code with third-party SDKs.
  Supports build.gradle (Groovy) and build.gradle.kts (Kotlin DSL).
  Works with implementation, api, compileOnly, kapt, ksp, annotationProcessor.
  Zero external dependencies — pure Python standard library.
---

# Android Dependency Class Lookup

Automatically indexes classes from Gradle-cached AAR/JAR dependencies and provides
instant API lookups. Zero external dependencies — pure Python standard library.

## When to Use

- Encountering unknown classes (especially from internal or third-party AAR dependencies)
- Needing to know the exact API of a dependency library
- Wanting to use a library's feature but unsure about method signatures
- Confirming which dependency a class belongs to

## Lookup Flow

### Step 1: Get the Fully Qualified Class Name

**Always check import statements first** — the same simple class name may exist in multiple libraries:

1. Look at `import` statements at the top of the file for the FQCN (e.g., `com.example.StringUtils`)
2. Use FQCN for precise lookup
3. Only use simple class name or fuzzy search when import is unavailable

### Step 2: Identify the Module Path

The tool needs the Android module path (directory containing `build.gradle` or `build.gradle.kts`).

### Step 3: Run the Query

Script location: `scripts/lookup_class.py` (relative to this skill directory)

**Lookup by class name (most common):**

```bash
python3 <SKILL_DIR>/scripts/lookup_class.py -p <MODULE_PATH> -c <class_name>
```

Examples:
```bash
# Precise lookup with FQCN (recommended)
python3 scripts/lookup_class.py -p /path/to/module -c com.example.StringUtils

# Simple name lookup (returns all matches)
python3 scripts/lookup_class.py -p /path/to/module -c StringUtils

# Show full source code instead of API summary
python3 scripts/lookup_class.py -p /path/to/module -c StringUtils --source
```

**Other queries:**

```bash
# List all classes in a package
python3 scripts/lookup_class.py -p <MODULE_PATH> --package com.example.util

# List all classes in a library
python3 scripts/lookup_class.py -p <MODULE_PATH> --library com.example:utils

# Fuzzy search
python3 scripts/lookup_class.py -p <MODULE_PATH> --search Toast

# Index statistics
python3 scripts/lookup_class.py -p <MODULE_PATH> --stats
```

### Step 4: Use the Results

Results are JSON with: `class` (FQCN), `library` (Maven coordinate), `version`, and `api_summary` (public method signatures with Javadoc when sources.jar is available).

## Key Features

- **Auto-indexing**: First query builds the index automatically (~0.5s), subsequent queries use cache (~0.1s)
- **Auto-invalidation**: Rebuilds when build.gradle changes
- **Dual extraction**: Prefers sources.jar for source-level API (with Javadoc), falls back to javap
- **Gradle DSL support**: Both Groovy (`build.gradle`) and Kotlin DSL (`build.gradle.kts`)
- **Dependency configs**: implementation, api, compileOnly, runtimeOnly, kapt, ksp, annotationProcessor, etc.

## Coding Guidelines

When writing code based on lookup results:
- Prefer internal utility classes over reinventing the wheel
- When a class exists in multiple libraries, use the one already imported in the current file
- Match method signatures and parameter types exactly as shown in the API summary
