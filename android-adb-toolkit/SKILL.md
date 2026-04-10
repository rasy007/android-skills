---
name: android-adb-toolkit
description: >-
  Android ADB debugging toolkit with automation scripts.
  Smart logcat filtering by package/tag/level, screenshot, screen recording,
  app data export (SharedPreferences, database), memory/CPU profiling.
  Use when debugging Android apps, capturing logs, taking screenshots,
  recording screen, dumping app data, checking device info, profiling performance.
  Covers device management, app install/uninstall, shell commands, intent firing.
  Works with emulator and physical devices. Pure bash — zero dependencies.
---

# Android ADB Debugging Toolkit

一站式 ADB 调试工具集，覆盖日常 Android 调试全流程。提供可直接执行的 bash 脚本。

## 适用场景

- 需要抓取应用日志（logcat）并按包名/TAG/级别过滤
- 截图或录屏并自动拉取到本地
- 导出应用的 SharedPreferences 或数据库文件
- 采集内存/CPU 快照进行性能分析
- 批量安装/卸载应用
- 查看设备信息、网络状态、进程列表

## 使用方式

脚本位置：`scripts/adb_helper.sh`（相对于本 Skill 目录）

### 前置条件

- `adb` 已安装并在 PATH 中（Android SDK Platform-Tools）
- 设备已通过 USB 或 WiFi 连接，且 `adb devices` 可见

### 命令速查

```bash
# 按包名过滤日志（最常用）
bash <SKILL_DIR>/scripts/adb_helper.sh logcat <package_name>

# 按TAG过滤日志
bash <SKILL_DIR>/scripts/adb_helper.sh logcat-tag <TAG>

# 按级别过滤（E=Error, W=Warning, I=Info, D=Debug, V=Verbose）
bash <SKILL_DIR>/scripts/adb_helper.sh logcat-level E

# 截图并拉取到当前目录
bash <SKILL_DIR>/scripts/adb_helper.sh screenshot [output_dir]

# 录屏（默认30秒，Ctrl+C停止）
bash <SKILL_DIR>/scripts/adb_helper.sh screenrecord [duration_seconds] [output_dir]

# 导出SharedPreferences
bash <SKILL_DIR>/scripts/adb_helper.sh dump-prefs <package_name> [output_dir]

# 导出数据库文件
bash <SKILL_DIR>/scripts/adb_helper.sh dump-db <package_name> [output_dir]

# 内存快照
bash <SKILL_DIR>/scripts/adb_helper.sh meminfo <package_name>

# CPU使用率
bash <SKILL_DIR>/scripts/adb_helper.sh cpuinfo <package_name>

# 设备详情
bash <SKILL_DIR>/scripts/adb_helper.sh device-info

# 安装APK
bash <SKILL_DIR>/scripts/adb_helper.sh install <apk_path>

# 卸载应用
bash <SKILL_DIR>/scripts/adb_helper.sh uninstall <package_name>

# 清除应用数据
bash <SKILL_DIR>/scripts/adb_helper.sh clear-data <package_name>

# 强制停止应用
bash <SKILL_DIR>/scripts/adb_helper.sh force-stop <package_name>

# 启动Activity
bash <SKILL_DIR>/scripts/adb_helper.sh start-activity <package_name/activity_name>

# 发送广播
bash <SKILL_DIR>/scripts/adb_helper.sh send-broadcast <action>

# 列出所有已安装应用
bash <SKILL_DIR>/scripts/adb_helper.sh list-packages

# 查看应用信息（版本号、权限等）
bash <SKILL_DIR>/scripts/adb_helper.sh app-info <package_name>

# 查看当前前台Activity
bash <SKILL_DIR>/scripts/adb_helper.sh current-activity

# 连接WiFi调试
bash <SKILL_DIR>/scripts/adb_helper.sh wifi-connect <device_ip>
```

## 常用 ADB 命令分类速查

### 设备管理
| 命令 | 说明 |
|------|------|
| `adb devices -l` | 列出设备详情 |
| `adb -s <serial> shell` | 指定设备执行 |
| `adb tcpip 5555` | 开启WiFi调试 |
| `adb connect <ip>:5555` | WiFi连接 |

### 应用管理
| 命令 | 说明 |
|------|------|
| `adb install -r <apk>` | 覆盖安装 |
| `adb install-multiple <apk1> <apk2>` | 安装split APK |
| `adb uninstall <pkg>` | 卸载 |
| `adb shell pm clear <pkg>` | 清除数据 |
| `adb shell pm list packages -3` | 列出第三方应用 |
| `adb shell dumpsys package <pkg>` | 应用详情 |

### 调试
| 命令 | 说明 |
|------|------|
| `adb logcat -c` | 清除日志 |
| `adb logcat --pid=$(adb shell pidof <pkg>)` | 按进程过滤 |
| `adb bugreport <output>` | 完整Bug报告 |
| `adb shell am set-debug-app -w <pkg>` | 等待调试器 |

### 性能
| 命令 | 说明 |
|------|------|
| `adb shell dumpsys meminfo <pkg>` | 内存详情 |
| `adb shell top -n 1 -s cpu` | CPU排行 |
| `adb shell dumpsys gfxinfo <pkg>` | 帧率信息 |
| `adb shell dumpsys battery` | 电池信息 |

## AI 使用指南

当用户提到以下关键词时，自动使用本工具：
- "帮我抓日志" / "看下日志" → `logcat`
- "截个图" / "截屏" → `screenshot`
- "录个屏" → `screenrecord`
- "看下内存" / "内存泄漏" → `meminfo`
- "导出数据" / "看下SP" → `dump-prefs`
- "看下数据库" → `dump-db`
- "装一下" / "安装APK" → `install`
- "当前页面是什么" → `current-activity`
