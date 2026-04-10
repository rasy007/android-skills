---
name: android-crash-analyzer
description: >-
  Android crash log and ANR stacktrace analyzer.
  Parse crash stacktraces, identify crash type (NPE, OOM, ANR, SecurityException),
  extract key frames, find root cause, generate fix suggestions.
  Use when user pastes crash logs, logcat errors, ANR traces, tombstone files,
  OutOfMemoryError, NullPointerException, ClassNotFoundException,
  Fatal signal, SIGSEGV, native crash, StrictMode violation.
  Supports Java/Kotlin exceptions, native crashes, ANR traces.
  Zero external dependencies — pure Python standard library.
---

# Android 崩溃/ANR 日志分析器

智能解析 Android 崩溃和 ANR 日志，识别崩溃类型、提取关键帧、给出修复建议。

## 适用场景

- 用户粘贴了 crash 日志或 logcat 错误
- ANR 问题排查（`traces.txt`）
- Native crash（SIGSEGV、Fatal signal）
- OOM 崩溃分析
- 生产环境异常报告解读

## 使用方式

脚本位置：`scripts/crash_analyzer.py`（相对于本 Skill 目录）

### 分析崩溃日志

```bash
# 从文件分析
python3 <SKILL_DIR>/scripts/crash_analyzer.py analyze <crash_log_file>

# 从stdin分析（用户粘贴）
echo "<crash_log>" | python3 <SKILL_DIR>/scripts/crash_analyzer.py analyze -

# JSON格式输出
python3 <SKILL_DIR>/scripts/crash_analyzer.py analyze <crash_log_file> --json

# 分析ANR日志
python3 <SKILL_DIR>/scripts/crash_analyzer.py analyze <traces_file> --type anr
```

### 快速识别崩溃类型

```bash
# 从一行异常信息快速识别
python3 <SKILL_DIR>/scripts/crash_analyzer.py identify "java.lang.NullPointerException: Attempt to invoke virtual method..."
```

### 查看常见崩溃修复指南

```bash
# 列出所有崩溃类型的修复指南
python3 <SKILL_DIR>/scripts/crash_analyzer.py guide

# 查看特定类型的指南
python3 <SKILL_DIR>/scripts/crash_analyzer.py guide npe
python3 <SKILL_DIR>/scripts/crash_analyzer.py guide oom
python3 <SKILL_DIR>/scripts/crash_analyzer.py guide anr
```

## 支持的崩溃类型

| 类型 | 典型异常 | 常见原因 |
|------|---------|---------|
| NPE | `NullPointerException` | 空引用调用、Fragment view 生命周期 |
| OOM | `OutOfMemoryError` | 大图加载、内存泄漏、集合无限增长 |
| ANR | Application Not Responding | 主线程阻塞、死锁、数据库操作 |
| ClassNotFound | `ClassNotFoundException` | 混淆、MultiDex、动态加载 |
| SecurityException | `SecurityException` | 缺少权限、跨进程访问 |
| IllegalState | `IllegalStateException` | Fragment 事务时序、Activity 销毁后操作 |
| Native | SIGSEGV / SIGABRT | JNI 错误、野指针、栈溢出 |
| StackOverflow | `StackOverflowError` | 递归无终止条件、布局嵌套过深 |
| Resource | `Resources$NotFoundException` | 资源 ID 错误、动态主题切换 |

## 输出格式

分析结果包含：
1. **崩溃类型** — 归类到上述类型之一
2. **异常信息** — 完整的异常描述
3. **关键帧** — 堆栈中最相关的应用代码帧
4. **根因分析** — 可能的原因列表
5. **修复建议** — 具体的代码修复方向
6. **严重级别** — Critical / High / Medium / Low

## AI 使用指南

当用户粘贴以下内容时，自动使用本工具：
- Java/Kotlin 异常堆栈 → `analyze`
- "ANR" / "应用无响应" → `analyze --type anr`
- logcat 中的 `FATAL EXCEPTION` → `analyze`
- 单行异常信息 → `identify`
- "为什么会NPE" / "OOM怎么排查" → `guide`
