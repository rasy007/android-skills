# Android Gradle Doctor

Gradle 构建问题诊断和优化工具，检测依赖冲突、配置问题，生成优化建议。

## 功能特性

- **配置扫描** — 检测 build.gradle 中的过时 API、重复依赖、动态版本等
- **依赖分析** — 解析 `./gradlew dependencies` 输出，找出版本冲突
- **优化建议** — 构建加速配置（并行、缓存、JVM 参数）
- **错误指南** — 常见 Gradle 错误的修复方案
- **双 DSL 支持** — Groovy (`build.gradle`) 和 Kotlin (`build.gradle.kts`)

## 前置条件

- Python 3.6+

## 安装

```bash
npx skills add --from https://github.com/rasy007/android-skills --subdir android-gradle-doctor
```

## 快速使用

```bash
# 全面诊断
python3 scripts/gradle_doctor.py diagnose /path/to/module

# 分析依赖冲突
./gradlew :app:dependencies --configuration releaseRuntimeClasspath > deps.txt
python3 scripts/gradle_doctor.py deps deps.txt

# 构建优化建议
python3 scripts/gradle_doctor.py optimize /path/to/project

# 查看常见错误修复
python3 scripts/gradle_doctor.py errors
```

## 常见 Gradle 错误速查

| 错误 | 原因 | 快速修复 |
|------|------|---------|
| `Duplicate class` | 多个库包含同名类 | `exclude group` 排除冲突 |
| `Could not resolve` | 仓库未配置/网络问题 | 检查 repositories 配置 |
| `Execution failed for task :app:merge*` | 资源/Manifest 冲突 | 检查 tools:replace 配置 |
| `Unsupported class file major version` | JDK 版本不匹配 | 检查 JAVA_HOME |
| `R8/D8 error` | 混淆规则缺失 | 运行 android-proguard-helper |

## 许可

MIT
