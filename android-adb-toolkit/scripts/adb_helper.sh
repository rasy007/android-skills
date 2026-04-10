#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

usage() {
    cat <<'USAGE'
Android ADB Toolkit — 一站式调试工具集

用法: adb_helper.sh <command> [args...]

命令:
  logcat <package>                按包名过滤日志
  logcat-tag <tag>                按TAG过滤
  logcat-level <E|W|I|D|V>       按级别过滤
  screenshot [output_dir]         截图并拉取
  screenrecord [duration] [dir]   录屏(默认30秒)
  dump-prefs <package> [dir]      导出SharedPreferences
  dump-db <package> [dir]         导出数据库文件
  meminfo <package>               内存快照
  cpuinfo <package>               CPU使用率
  device-info                     设备详情
  install <apk_path>              安装APK
  uninstall <package>             卸载应用
  clear-data <package>            清除应用数据
  force-stop <package>            强制停止
  start-activity <component>      启动Activity
  send-broadcast <action>         发送广播
  list-packages                   列出已安装应用
  app-info <package>              应用信息
  current-activity                当前前台Activity
  wifi-connect <device_ip>        WiFi调试连接
USAGE
    exit 1
}

check_adb() {
    if ! command -v adb &>/dev/null; then
        echo "错误: adb 未找到，请确保 Android SDK Platform-Tools 已安装并加入 PATH" >&2
        exit 1
    fi
    local devices
    devices=$(adb devices | grep -c "device$" || true)
    if [ "$devices" -eq 0 ]; then
        echo "错误: 未检测到已连接设备，请检查 USB 连接或 WiFi 调试" >&2
        exit 1
    fi
}

get_pid() {
    local pkg=$1
    adb shell pidof "$pkg" 2>/dev/null || echo ""
}

cmd_logcat() {
    local pkg=${1:?请指定包名}
    echo "=== Logcat: $pkg ==="
    adb logcat -c
    local pid
    pid=$(get_pid "$pkg")
    if [ -n "$pid" ]; then
        echo "PID: $pid"
        adb logcat --pid="$pid" -v time
    else
        echo "进程未运行，使用 grep 过滤..."
        adb logcat -v time | grep -iE "$pkg|AndroidRuntime"
    fi
}

cmd_logcat_tag() {
    local tag=${1:?请指定TAG}
    echo "=== Logcat TAG: $tag ==="
    adb logcat -c
    adb logcat -s "$tag:V" -v time
}

cmd_logcat_level() {
    local level=${1:?请指定级别 (E/W/I/D/V)}
    echo "=== Logcat Level: $level ==="
    adb logcat -c
    adb logcat "*:$level" -v time
}

cmd_screenshot() {
    local outdir=${1:-.}
    mkdir -p "$outdir"
    local remote="/sdcard/screenshot_${TIMESTAMP}.png"
    local local_file="$outdir/screenshot_${TIMESTAMP}.png"
    echo "截图中..."
    adb shell screencap -p "$remote"
    adb pull "$remote" "$local_file"
    adb shell rm "$remote"
    echo "已保存: $local_file"
}

cmd_screenrecord() {
    local duration=${1:-30}
    local outdir=${2:-.}
    mkdir -p "$outdir"
    local remote="/sdcard/record_${TIMESTAMP}.mp4"
    local local_file="$outdir/record_${TIMESTAMP}.mp4"
    echo "录屏中 (${duration}秒, Ctrl+C停止)..."
    adb shell screenrecord --time-limit "$duration" "$remote" || true
    sleep 1
    adb pull "$remote" "$local_file"
    adb shell rm "$remote"
    echo "已保存: $local_file"
}

cmd_dump_prefs() {
    local pkg=${1:?请指定包名}
    local outdir=${2:-.}
    mkdir -p "$outdir"
    echo "=== 导出 SharedPreferences: $pkg ==="
    local prefs_dir="shared_prefs"
    local files
    files=$(adb shell run-as "$pkg" ls "$prefs_dir" 2>/dev/null || echo "")
    if [ -z "$files" ]; then
        echo "无法访问 (应用需要 debuggable=true)，尝试 root 方式..."
        files=$(adb shell "su -c 'ls /data/data/$pkg/shared_prefs/'" 2>/dev/null || echo "")
    fi
    if [ -z "$files" ]; then
        echo "错误: 无法访问应用 SharedPreferences (需要 debuggable 或 root)" >&2
        return 1
    fi
    local out_sp_dir="$outdir/${pkg}_prefs_${TIMESTAMP}"
    mkdir -p "$out_sp_dir"
    echo "$files" | while IFS= read -r f; do
        [ -z "$f" ] && continue
        adb shell run-as "$pkg" cat "$prefs_dir/$f" > "$out_sp_dir/$f" 2>/dev/null || \
            adb shell "su -c 'cat /data/data/$pkg/shared_prefs/$f'" > "$out_sp_dir/$f" 2>/dev/null
        echo "  已导出: $f"
    done
    echo "保存目录: $out_sp_dir"
}

cmd_dump_db() {
    local pkg=${1:?请指定包名}
    local outdir=${2:-.}
    mkdir -p "$outdir"
    echo "=== 导出数据库: $pkg ==="
    local db_dir="databases"
    local files
    files=$(adb shell run-as "$pkg" ls "$db_dir" 2>/dev/null || echo "")
    if [ -z "$files" ]; then
        echo "无法访问 (应用需要 debuggable=true)，尝试 root 方式..."
        files=$(adb shell "su -c 'ls /data/data/$pkg/databases/'" 2>/dev/null || echo "")
    fi
    if [ -z "$files" ]; then
        echo "错误: 无法访问应用数据库 (需要 debuggable 或 root)" >&2
        return 1
    fi
    local out_db_dir="$outdir/${pkg}_db_${TIMESTAMP}"
    mkdir -p "$out_db_dir"
    local tmpdir="/data/local/tmp/db_export_$$"
    adb shell "mkdir -p $tmpdir" 2>/dev/null
    echo "$files" | while IFS= read -r f; do
        [ -z "$f" ] && continue
        adb shell run-as "$pkg" cat "$db_dir/$f" > "$out_db_dir/$f" 2>/dev/null || \
            adb shell "su -c 'cat /data/data/$pkg/databases/$f'" > "$out_db_dir/$f" 2>/dev/null
        echo "  已导出: $f"
    done
    adb shell "rm -rf $tmpdir" 2>/dev/null
    echo "保存目录: $out_db_dir"
}

cmd_meminfo() {
    local pkg=${1:?请指定包名}
    echo "=== 内存信息: $pkg ==="
    adb shell dumpsys meminfo "$pkg"
}

cmd_cpuinfo() {
    local pkg=${1:?请指定包名}
    echo "=== CPU信息: $pkg ==="
    local pid
    pid=$(get_pid "$pkg")
    if [ -n "$pid" ]; then
        adb shell top -n 3 -p "$pid" -b
    else
        echo "进程未运行" >&2
        return 1
    fi
}

cmd_device_info() {
    echo "=== 设备信息 ==="
    echo "型号:     $(adb shell getprop ro.product.model)"
    echo "品牌:     $(adb shell getprop ro.product.brand)"
    echo "Android:  $(adb shell getprop ro.build.version.release)"
    echo "SDK:      $(adb shell getprop ro.build.version.sdk)"
    echo "ABI:      $(adb shell getprop ro.product.cpu.abi)"
    echo "分辨率:   $(adb shell wm size 2>/dev/null | tail -1)"
    echo "密度:     $(adb shell wm density 2>/dev/null | tail -1)"
    echo "序列号:   $(adb shell getprop ro.serialno)"
    echo "电池:     $(adb shell dumpsys battery | grep -E 'level|status|temperature')"
    echo "可用内存: $(adb shell cat /proc/meminfo | head -3)"
}

cmd_install() {
    local apk=${1:?请指定APK路径}
    if [ ! -f "$apk" ]; then
        echo "错误: 文件不存在: $apk" >&2
        exit 1
    fi
    echo "安装中: $apk"
    adb install -r -d "$apk"
    echo "安装完成"
}

cmd_uninstall() {
    local pkg=${1:?请指定包名}
    echo "卸载: $pkg"
    adb uninstall "$pkg"
}

cmd_clear_data() {
    local pkg=${1:?请指定包名}
    echo "清除数据: $pkg"
    adb shell pm clear "$pkg"
}

cmd_force_stop() {
    local pkg=${1:?请指定包名}
    echo "强制停止: $pkg"
    adb shell am force-stop "$pkg"
}

cmd_start_activity() {
    local component=${1:?请指定组件名 (package/activity)}
    echo "启动: $component"
    adb shell am start -n "$component"
}

cmd_send_broadcast() {
    local action=${1:?请指定广播Action}
    echo "发送广播: $action"
    adb shell am broadcast -a "$action"
}

cmd_list_packages() {
    echo "=== 已安装应用 (第三方) ==="
    adb shell pm list packages -3 | sed 's/package://' | sort
    echo ""
    echo "总计: $(adb shell pm list packages -3 | wc -l | tr -d ' ') 个第三方应用"
}

cmd_app_info() {
    local pkg=${1:?请指定包名}
    echo "=== 应用信息: $pkg ==="
    adb shell dumpsys package "$pkg" | grep -E "versionCode|versionName|targetSdk|minSdk|firstInstallTime|lastUpdateTime|flags|dataDir"
}

cmd_current_activity() {
    echo "=== 当前前台Activity ==="
    adb shell dumpsys activity activities | grep -E "mResumedActivity|mFocusedActivity" | head -2
    echo ""
    echo "=== Activity栈顶 ==="
    adb shell dumpsys activity top | head -5
}

cmd_wifi_connect() {
    local ip=${1:?请指定设备IP}
    echo "切换到WiFi调试模式..."
    adb tcpip 5555
    sleep 2
    echo "连接 $ip:5555..."
    adb connect "$ip:5555"
    echo "可以拔掉USB线了"
}

# --- 主入口 ---
[ $# -eq 0 ] && usage
check_adb

case "$1" in
    logcat)         shift; cmd_logcat "$@" ;;
    logcat-tag)     shift; cmd_logcat_tag "$@" ;;
    logcat-level)   shift; cmd_logcat_level "$@" ;;
    screenshot)     shift; cmd_screenshot "$@" ;;
    screenrecord)   shift; cmd_screenrecord "$@" ;;
    dump-prefs)     shift; cmd_dump_prefs "$@" ;;
    dump-db)        shift; cmd_dump_db "$@" ;;
    meminfo)        shift; cmd_meminfo "$@" ;;
    cpuinfo)        shift; cmd_cpuinfo "$@" ;;
    device-info)    cmd_device_info ;;
    install)        shift; cmd_install "$@" ;;
    uninstall)      shift; cmd_uninstall "$@" ;;
    clear-data)     shift; cmd_clear_data "$@" ;;
    force-stop)     shift; cmd_force_stop "$@" ;;
    start-activity) shift; cmd_start_activity "$@" ;;
    send-broadcast) shift; cmd_send_broadcast "$@" ;;
    list-packages)  cmd_list_packages ;;
    app-info)       shift; cmd_app_info "$@" ;;
    current-activity) cmd_current_activity ;;
    wifi-connect)   shift; cmd_wifi_connect "$@" ;;
    *)              echo "未知命令: $1" >&2; usage ;;
esac
