#!/usr/bin/env python3
"""Android 崩溃/ANR 日志分析器 — 解析堆栈、识别类型、给出修复建议"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

# ─── 崩溃类型定义 ────────────────────────────────────────────────────────

CRASH_TYPES = {
    "npe": {
        "name": "NullPointerException (NPE)",
        "patterns": [r"NullPointerException", r"null object reference"],
        "severity": "HIGH",
        "causes": [
            "View 引用在 onDestroyView 后仍被使用",
            "findViewById 返回 null（布局中未定义该 ID）",
            "Fragment 生命周期中 View 尚未创建",
            "异步回调中使用了已被回收的对象",
            "未初始化的成员变量",
        ],
        "fixes": [
            "使用 ViewBinding 替代 findViewById",
            "在 onDestroyView 中置空 binding 引用",
            "使用 viewLifecycleOwner 感知 View 生命周期",
            "使用 Kotlin 的 ?. 安全调用操作符",
            "对可空参数增加 null 检查",
        ],
    },
    "oom": {
        "name": "OutOfMemoryError (OOM)",
        "patterns": [r"OutOfMemoryError", r"Failed to allocate", r"OOM"],
        "severity": "CRITICAL",
        "causes": [
            "加载超大图片未做压缩/采样",
            "Bitmap 未及时回收",
            "Activity/Fragment 内存泄漏（静态引用、Handler、匿名内部类）",
            "集合（List/Map）无限增长",
            "WebView 内存泄漏",
        ],
        "fixes": [
            "使用 Glide/Coil 加载图片（自动管理内存）",
            "检查 Activity 是否被静态变量持有",
            "使用 WeakReference 持有 Context",
            "Handler 使用静态内部类 + WeakReference",
            "用 LeakCanary 检测内存泄漏",
            "在 AndroidManifest 中增加 android:largeHeap（临时方案）",
        ],
    },
    "anr": {
        "name": "Application Not Responding (ANR)",
        "patterns": [r"ANR in", r"Input dispatching timed out", r"Broadcast of Intent",
                     r"executing service", r"ContentProvider not responding"],
        "severity": "CRITICAL",
        "causes": [
            "主线程执行耗时操作（网络请求、数据库查询）",
            "主线程死锁",
            "BroadcastReceiver 超过 10 秒",
            "Service 前台超过 20 秒",
            "ContentProvider 超时",
            "SharedPreferences.commit() 在主线程",
        ],
        "fixes": [
            "耗时操作移到子线程（协程、RxJava、ExecutorService）",
            "使用 SharedPreferences.apply() 替代 commit()",
            "数据库操作使用 Room + Coroutine/RxJava",
            "网络请求使用 OkHttp/Retrofit（异步）",
            "使用 StrictMode 检测主线程违规",
            "BroadcastReceiver 中使用 goAsync() 延长时间",
        ],
    },
    "class_not_found": {
        "name": "ClassNotFoundException",
        "patterns": [r"ClassNotFoundException", r"NoClassDefFoundError"],
        "severity": "HIGH",
        "causes": [
            "ProGuard/R8 混淆了需要反射的类",
            "MultiDex 未正确配置（Android 4.x）",
            "动态加载的类未包含在 APK 中",
            "依赖版本冲突导致类缺失",
        ],
        "fixes": [
            "检查 proguard-rules.pro，添加 -keep 规则",
            "确认 multiDexEnabled true 已配置",
            "检查依赖树 (./gradlew dependencies) 是否有冲突",
            "运行 android-proguard-helper 扫描",
        ],
    },
    "security": {
        "name": "SecurityException",
        "patterns": [r"SecurityException", r"Permission Denial"],
        "severity": "HIGH",
        "causes": [
            "缺少运行时权限（Android 6.0+）",
            "AndroidManifest 中未声明权限",
            "跨进程 ContentProvider 访问被拒绝",
            "FileProvider 配置错误",
        ],
        "fixes": [
            "使用 ActivityCompat.requestPermissions() 动态申请",
            "在 AndroidManifest 中声明 <uses-permission>",
            "ContentProvider 添加 android:exported 和权限声明",
            "使用 FileProvider 替代 file:// URI",
        ],
    },
    "illegal_state": {
        "name": "IllegalStateException",
        "patterns": [r"IllegalStateException", r"Can not perform this action after onSaveInstanceState",
                     r"Fragment already added", r"Activity has been destroyed"],
        "severity": "MEDIUM",
        "causes": [
            "Activity onSaveInstanceState 后执行 Fragment 事务",
            "重复添加 Fragment",
            "Activity 已销毁后仍尝试操作 UI",
            "LifecycleOwner 状态不匹配",
        ],
        "fixes": [
            "使用 commitAllowingStateLoss() 替代 commit()",
            "Fragment 事务前检查 isAdded() / isStateSaved()",
            "使用 Lifecycle 感知组件，避免在 DESTROYED 后操作",
            "使用 Navigation Component 管理 Fragment",
        ],
    },
    "native_crash": {
        "name": "Native Crash (SIGSEGV/SIGABRT)",
        "patterns": [r"Fatal signal", r"SIGSEGV", r"SIGABRT", r"SIGBUS",
                     r"tombstone", r"native crash"],
        "severity": "CRITICAL",
        "causes": [
            "JNI 代码中的空指针或野指针",
            "JNI 引用未正确管理（局部引用溢出）",
            "NDK 库 ABI 不兼容",
            "栈溢出（递归过深）",
            "线程安全问题（竞态条件）",
        ],
        "fixes": [
            "使用 addr2line 将地址转换为源码行号",
            "检查 JNI 代码中的指针操作",
            "使用 ASan (Address Sanitizer) 检测内存问题",
            "确认 so 库对应正确的 ABI (arm64-v8a/armeabi-v7a)",
            "使用 ndk-stack 符号化 tombstone",
        ],
    },
    "stack_overflow": {
        "name": "StackOverflowError",
        "patterns": [r"StackOverflowError"],
        "severity": "HIGH",
        "causes": [
            "无终止条件的递归调用",
            "布局嵌套层级过深 (>10 层)",
            "View measure/layout 循环触发",
            "序列化/反序列化循环引用",
        ],
        "fixes": [
            "检查递归方法的终止条件",
            "使用 ConstraintLayout 减少布局层级",
            "使用 Hierarchy Viewer 检查布局深度",
            "序列化时使用 @Transient 打断循环引用",
        ],
    },
    "resource_not_found": {
        "name": "Resources$NotFoundException",
        "patterns": [r"NotFoundException", r"Resource ID #0x"],
        "severity": "MEDIUM",
        "causes": [
            "硬编码的资源 ID 在不同构建变体中不存在",
            "动态主题切换后资源未更新",
            "资源文件命名错误或路径错误",
            "库项目和应用项目资源 ID 冲突",
        ],
        "fixes": [
            "使用 R.xx.name 而非硬编码 ID",
            "检查多 flavor/buildType 下的资源覆盖",
            "确保资源文件命名符合规则（小写+下划线）",
        ],
    },
}


# ─── 数据模型 ────────────────────────────────────────────────────────────

@dataclass
class CrashReport:
    crash_type: str = "unknown"
    type_name: str = "Unknown"
    severity: str = "MEDIUM"
    exception_message: str = ""
    key_frames: List[str] = field(default_factory=list)
    all_frames: List[str] = field(default_factory=list)
    causes: List[str] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    thread_name: str = "main"
    raw_exception: str = ""


# ─── 解析器 ──────────────────────────────────────────────────────────────

def identify_crash_type(text: str) -> Optional[str]:
    """识别崩溃类型"""
    for type_id, info in CRASH_TYPES.items():
        for pattern in info["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                return type_id
    return None


def extract_exception_line(text: str) -> str:
    """提取异常描述行"""
    patterns = [
        r"(?:Caused by|FATAL EXCEPTION):\s*(.+?)(?:\n|$)",
        r"((?:java|kotlin|android)\.\w+(?:\.\w+)*(?:Exception|Error)(?::\s*.+)?)",
        r"((?:java|kotlin|android)\.\w+(?:\.\w+)*(?:Exception|Error))",
    ]
    for pat in patterns:
        match = re.search(pat, text)
        if match:
            return match.group(1).strip()
    lines = text.strip().split("\n")
    return lines[0] if lines else ""


def extract_stack_frames(text: str) -> List[str]:
    """提取堆栈帧"""
    frames = []
    for match in re.finditer(r"\s+at\s+([\w.$]+\([\w.:]+\))", text):
        frames.append(match.group(1))
    return frames


def extract_key_frames(frames: List[str], app_packages: List[str] = None) -> List[str]:
    """提取关键帧（优先应用代码）"""
    skip_prefixes = (
        "android.", "java.", "javax.", "kotlin.", "kotlinx.",
        "com.android.", "dalvik.", "sun.", "libcore.",
        "androidx.fragment.app.Fragment.performResume",
        "androidx.fragment.app.Fragment.performCreate",
    )

    key = []
    for frame in frames:
        is_framework = any(frame.startswith(p) for p in skip_prefixes)
        if not is_framework:
            key.append(frame)

    if not key and frames:
        key = frames[:3]

    return key[:5]


def parse_anr_trace(text: str) -> CrashReport:
    """解析 ANR trace"""
    report = CrashReport(
        crash_type="anr",
        type_name=CRASH_TYPES["anr"]["name"],
        severity=CRASH_TYPES["anr"]["severity"],
        causes=CRASH_TYPES["anr"]["causes"],
        fixes=CRASH_TYPES["anr"]["fixes"],
    )

    main_thread_match = re.search(
        r'"main".*?\n((?:\s+at .+\n)+)', text, re.MULTILINE
    )
    if main_thread_match:
        frames = extract_stack_frames(main_thread_match.group(1))
        report.all_frames = frames
        report.key_frames = extract_key_frames(frames)

    blocked_match = re.search(r"(waiting to lock|held by thread|BLOCKED)", text)
    if blocked_match:
        report.exception_message = "主线程被阻塞 (可能存在死锁)"
    else:
        report.exception_message = "主线程执行耗时操作"

    return report


def analyze_crash(text: str, crash_type_hint: str = None) -> CrashReport:
    """分析崩溃日志"""
    if crash_type_hint == "anr":
        return parse_anr_trace(text)

    type_id = crash_type_hint or identify_crash_type(text) or "unknown"
    type_info = CRASH_TYPES.get(type_id, {})

    exception_msg = extract_exception_line(text)
    all_frames = extract_stack_frames(text)
    key_frames = extract_key_frames(all_frames)

    thread_match = re.search(r'FATAL EXCEPTION:\s*(\S+)', text)
    thread_name = thread_match.group(1) if thread_match else "main"

    report = CrashReport(
        crash_type=type_id,
        type_name=type_info.get("name", "Unknown"),
        severity=type_info.get("severity", "MEDIUM"),
        exception_message=exception_msg,
        key_frames=key_frames,
        all_frames=all_frames,
        causes=type_info.get("causes", []),
        fixes=type_info.get("fixes", []),
        thread_name=thread_name,
        raw_exception=exception_msg,
    )

    return report


def format_report(report: CrashReport) -> str:
    """格式化分析报告"""
    lines = [
        "═══════════════════════════════════════════════",
        "  Android 崩溃分析报告",
        "═══════════════════════════════════════════════",
        "",
        f"类型:     {report.type_name}",
        f"严重级别:  {report.severity}",
        f"线程:     {report.thread_name}",
        f"异常:     {report.exception_message}",
        "",
    ]

    if report.key_frames:
        lines.append("关键帧:")
        for frame in report.key_frames:
            lines.append(f"  → {frame}")
        lines.append("")

    if report.causes:
        lines.append("根因分析:")
        for i, cause in enumerate(report.causes, 1):
            lines.append(f"  {i}. {cause}")
        lines.append("")

    if report.fixes:
        lines.append("修复建议:")
        for i, fix in enumerate(report.fixes, 1):
            lines.append(f"  {i}. {fix}")
        lines.append("")

    if report.all_frames and len(report.all_frames) > len(report.key_frames):
        lines.append(f"完整堆栈: {len(report.all_frames)} 帧 (前5帧为关键帧)")

    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Android 崩溃/ANR 日志分析器")
    sub = parser.add_subparsers(dest="command", help="子命令")

    analyze_p = sub.add_parser("analyze", help="分析崩溃日志")
    analyze_p.add_argument("input", help="日志文件路径（'-' 从stdin读取）")
    analyze_p.add_argument("--type", help="崩溃类型提示 (anr/npe/oom 等)")
    analyze_p.add_argument("--json", action="store_true", help="JSON格式输出")

    identify_p = sub.add_parser("identify", help="快速识别崩溃类型")
    identify_p.add_argument("exception", help="异常信息")

    guide_p = sub.add_parser("guide", help="查看崩溃修复指南")
    guide_p.add_argument("type", nargs="?", help="崩溃类型 (npe/oom/anr 等)")

    args = parser.parse_args()

    if args.command == "analyze":
        if args.input == "-":
            text = sys.stdin.read()
        else:
            try:
                text = Path(args.input).read_text(encoding="utf-8", errors="ignore")
            except FileNotFoundError:
                print(f"错误: 文件不存在: {args.input}", file=sys.stderr)
                sys.exit(1)

        report = analyze_crash(text, args.type)

        if args.json:
            print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
        else:
            print(format_report(report))

    elif args.command == "identify":
        type_id = identify_crash_type(args.exception)
        if type_id:
            info = CRASH_TYPES[type_id]
            print(f"类型: {info['name']}")
            print(f"严重级别: {info['severity']}")
            print(f"\n可能原因:")
            for c in info["causes"][:3]:
                print(f"  - {c}")
        else:
            print("未能识别崩溃类型，请提供更完整的异常信息")

    elif args.command == "guide":
        if args.type:
            t = args.type.lower().replace("-", "_")
            if t in CRASH_TYPES:
                info = CRASH_TYPES[t]
                print(f"═══ {info['name']} ═══")
                print(f"严重级别: {info['severity']}\n")
                print("常见原因:")
                for c in info["causes"]:
                    print(f"  • {c}")
                print("\n修复方法:")
                for f in info["fixes"]:
                    print(f"  ✓ {f}")
            else:
                print(f"未知类型: {args.type}")
                print(f"可用类型: {', '.join(CRASH_TYPES.keys())}")
        else:
            print("Android 崩溃类型指南\n")
            for type_id, info in CRASH_TYPES.items():
                print(f"  {type_id:20s} {info['name']:40s} [{info['severity']}]")
            print(f"\n使用 'guide <type>' 查看详细修复指南")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
