---
name: android-gradle-doctor
description: >-
  Android Gradle build problem diagnosis and optimization tool.
  Analyze dependency conflicts, detect version mismatches, scan build.gradle issues,
  generate optimization suggestions for faster builds.
  Use when build fails, dependency conflict, version mismatch, slow build,
  Gradle sync error, duplicate class, incompatible library versions,
  Could not resolve, Configuration cache, build cache, parallel execution.
  Supports build.gradle (Groovy) and build.gradle.kts (Kotlin DSL).
  Analyzes ./gradlew dependencies output, checks common misconfigurations.
  Zero external dependencies — pure Python standard library.
---

# Android Gradle 构建诊断工具

分析 Gradle 构建问题，检测依赖冲突，生成优化建议。

## 适用场景

- Gradle 构建失败（sync error、编译错误）
- 依赖版本冲突（Duplicate class、版本不兼容）
- 构建速度慢，需要优化
- 检查 build.gradle 常见配置问题
- 升级 AGP（Android Gradle Plugin）后出错

## 使用方式

脚本位置：`scripts/gradle_doctor.py`（相对于本 Skill 目录）

### 诊断构建问题

```bash
# 全面诊断（扫描 build.gradle + 检查依赖）
python3 <SKILL_DIR>/scripts/gradle_doctor.py diagnose <module_path>

# 仅扫描 build.gradle 配置问题
python3 <SKILL_DIR>/scripts/gradle_doctor.py scan <module_path>

# JSON格式输出
python3 <SKILL_DIR>/scripts/gradle_doctor.py diagnose <module_path> --json
```

### 分析依赖

```bash
# 分析 dependencies 输出，检测版本冲突
./gradlew :app:dependencies --configuration releaseRuntimeClasspath > deps.txt
python3 <SKILL_DIR>/scripts/gradle_doctor.py deps deps.txt

# 检查指定库的版本冲突
python3 <SKILL_DIR>/scripts/gradle_doctor.py deps deps.txt --filter okhttp
```

### 生成优化建议

```bash
# 构建加速建议
python3 <SKILL_DIR>/scripts/gradle_doctor.py optimize <project_root>
```

### 查看常见错误修复指南

```bash
# 列出所有常见错误
python3 <SKILL_DIR>/scripts/gradle_doctor.py errors

# 查看特定错误的修复方案
python3 <SKILL_DIR>/scripts/gradle_doctor.py error "duplicate class"
python3 <SKILL_DIR>/scripts/gradle_doctor.py error "could not resolve"
```

## 检测项

### build.gradle 扫描

| 检测项 | 说明 |
|--------|------|
| 过时 API | `compile` → `implementation`、`testCompile` → `testImplementation` |
| 重复依赖 | 同一库在不同 configuration 中重复声明 |
| 动态版本 | `1.+`、`latest.release` 等不确定版本 |
| 缺失配置 | 缺少 `compileSdkVersion`、`minSdkVersion` 等 |
| BuildConfig | `buildConfigField` 格式检查 |
| Kotlin 版本 | 检查 Kotlin 版本与 AGP 兼容性 |

### 依赖分析

| 检测项 | 说明 |
|--------|------|
| 版本冲突 | 同一库的不同版本被依赖（`→` 标记） |
| 强制版本 | 被 Gradle 强制解析到其他版本的依赖 |
| 冗余依赖 | 已被传递依赖包含的直接依赖 |

### 构建优化

| 优化项 | 说明 |
|--------|------|
| gradle.properties | 并行构建、构建缓存、JVM 参数 |
| Configuration Cache | AGP 7.0+ 支持 |
| Build Cache | 本地 + 远程缓存 |
| Kotlin 增量编译 | 检查是否启用 |

## AI 使用指南

当用户遇到以下情况时，自动使用本工具：
- "构建失败" / "sync 报错" → `diagnose` 全面诊断
- "依赖冲突" / "Duplicate class" → `deps` 分析依赖
- "构建太慢" / "编译慢" → `optimize` 优化建议
- "build.gradle 有什么问题" → `scan` 扫描配置
