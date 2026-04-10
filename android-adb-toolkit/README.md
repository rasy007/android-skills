# Android ADB Toolkit

一站式 ADB 调试工具集，覆盖日常 Android 调试全流程。

## 功能特性

- **智能 Logcat 过滤** — 按包名、TAG、日志级别精确过滤
- **截图/录屏** — 一键截图或录屏，自动拉取到本地并以时间戳命名
- **应用数据导出** — 导出 SharedPreferences、SQLite 数据库到本地
- **性能采集** — 内存/CPU 使用快照
- **应用管理** — 安装、卸载、清除数据、强制停止
- **设备信息** — 型号、系统版本、屏幕分辨率、网络状态一览
- **WiFi 调试** — 快速切换到无线调试模式

## 前置条件

- Android SDK Platform-Tools（`adb` 命令可用）
- 设备已连接（USB 或 WiFi）

## 安装

```bash
npx skills add --from https://github.com/rasy007/android-skills --subdir android-adb-toolkit
```

## 快速使用

```bash
# 抓取包名日志
bash scripts/adb_helper.sh logcat com.example.myapp

# 截图
bash scripts/adb_helper.sh screenshot ~/Desktop

# 导出SharedPreferences
bash scripts/adb_helper.sh dump-prefs com.example.myapp ~/Desktop

# 内存快照
bash scripts/adb_helper.sh meminfo com.example.myapp

# 设备信息
bash scripts/adb_helper.sh device-info
```

## 完整命令列表

| 命令 | 参数 | 说明 |
|------|------|------|
| `logcat` | `<package>` | 按包名过滤日志 |
| `logcat-tag` | `<tag>` | 按TAG过滤 |
| `logcat-level` | `<E\|W\|I\|D\|V>` | 按级别过滤 |
| `screenshot` | `[output_dir]` | 截图并拉取 |
| `screenrecord` | `[duration] [output_dir]` | 录屏 |
| `dump-prefs` | `<package> [output_dir]` | 导出SP |
| `dump-db` | `<package> [output_dir]` | 导出数据库 |
| `meminfo` | `<package>` | 内存快照 |
| `cpuinfo` | `<package>` | CPU使用 |
| `device-info` | — | 设备详情 |
| `install` | `<apk_path>` | 安装APK |
| `uninstall` | `<package>` | 卸载应用 |
| `clear-data` | `<package>` | 清除数据 |
| `force-stop` | `<package>` | 强制停止 |
| `start-activity` | `<component>` | 启动Activity |
| `send-broadcast` | `<action>` | 发送广播 |
| `list-packages` | — | 列出已安装应用 |
| `app-info` | `<package>` | 应用详情 |
| `current-activity` | — | 当前前台Activity |
| `wifi-connect` | `<device_ip>` | WiFi调试连接 |

## 工作原理

脚本封装了 `adb` 命令，提供更友好的参数和输出格式。关键特性：

- **包名日志过滤**：通过 `pidof` 获取进程 PID，再用 `--pid` 精确过滤
- **截图/录屏**：通过 `screencap`/`screenrecord` 在设备端执行，再用 `adb pull` 拉取
- **数据导出**：使用 `run-as` 访问应用沙箱，对 debuggable 应用直接读取
- **自动命名**：所有输出文件以时间戳命名，避免覆盖

## 许可

MIT
