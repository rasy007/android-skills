#!/usr/bin/env python3
"""Android ProGuard/R8 混淆规则分析器 — 扫描源码并生成 keep 规则"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# ─── 常见库 ProGuard 规则模板 ─────────────────────────────────────────────

LIBRARY_TEMPLATES = {
    "gson": """\
# Gson
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn sun.misc.**
-keep class com.google.gson.** { *; }
-keep class * extends com.google.gson.TypeAdapter
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
# 保留所有使用 @SerializedName 注解的类的成员
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName *;
}""",

    "retrofit": """\
# Retrofit
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions
-keepclasseswithmembers class * {
    @retrofit2.http.* <methods>;
}
-keepclassmembers,allowshrinking,allowobfuscation interface * {
    @retrofit2.http.* <methods>;
}""",

    "okhttp": """\
# OkHttp
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn javax.annotation.**
-keepnames class okhttp3.internal.publicsuffix.PublicSuffixDatabase
-dontwarn org.codehaus.mojo.animal_sniffer.*
-dontwarn okhttp3.internal.platform.ConscryptPlatform""",

    "room": """\
# Room
-keep class * extends androidx.room.RoomDatabase
-keep @androidx.room.Entity class *
-dontwarn androidx.room.paging.**
-keepclassmembers class * extends androidx.room.RoomDatabase {
    abstract *;
}
-keepclassmembers @androidx.room.Entity class * {
    *;
}
-keepclassmembers class * {
    @androidx.room.Dao *;
}""",

    "glide": """\
# Glide
-keep public class * implements com.bumptech.glide.module.GlideModule
-keep class * extends com.bumptech.glide.module.AppGlideModule {
    <init>(...);
}
-keep public enum com.bumptech.glide.load.ImageHeaderParser$** {
    **[] $VALUES;
    public *;
}
-keep class com.bumptech.glide.load.data.ParcelFileDescriptorRewinder$InternalRewinder {
    *** rewind();
}""",

    "eventbus": """\
# EventBus
-keepattributes *Annotation*
-keepclassmembers class * {
    @org.greenrobot.eventbus.Subscribe <methods>;
}
-keep enum org.greenrobot.eventbus.ThreadMode { *; }""",

    "dagger": """\
# Dagger
-dontwarn com.google.errorprone.annotations.**
-keep class dagger.** { *; }
-keep class javax.inject.** { *; }
-keep class * extends dagger.internal.Binding
-keep class * extends dagger.internal.ModuleAdapter
-keep class * extends dagger.internal.StaticInjection""",

    "hilt": """\
# Hilt
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keep class * extends dagger.hilt.android.internal.managers.ViewComponentManager$FragmentContextWrapper { *; }
-keepnames @dagger.hilt.android.lifecycle.HiltViewModel class * extends androidx.lifecycle.ViewModel""",

    "rxjava": """\
# RxJava
-dontwarn io.reactivex.**
-keep class io.reactivex.** { *; }
-keepclassmembers class io.reactivex.** { *; }""",

    "coroutines": """\
# Kotlin Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembers class kotlinx.coroutines.** {
    volatile <fields>;
}""",

    "moshi": """\
# Moshi
-keep class com.squareup.moshi.** { *; }
-keepclassmembers class * {
    @com.squareup.moshi.* <methods>;
    @com.squareup.moshi.* <fields>;
}
-keep @com.squareup.moshi.JsonQualifier @interface *
-keepnames @com.squareup.moshi.JsonClass class *""",

    "jackson": """\
# Jackson
-keep class com.fasterxml.jackson.** { *; }
-keepclassmembers class * {
    @com.fasterxml.jackson.annotation.* <fields>;
    @com.fasterxml.jackson.annotation.* <methods>;
}
-keepattributes *Annotation*""",

    "kotlin-serialization": """\
# Kotlin Serialization
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers @kotlinx.serialization.Serializable class ** {
    *** Companion;
}
-keepclasseswithmembers class **.$serializer {
    kotlinx.serialization.KSerializer serializer(...);
}""",

    "firebase": """\
# Firebase
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**""",

    "crashlytics": """\
# Crashlytics
-keepattributes *Annotation*
-keepattributes SourceFile,LineNumberTable
-keep public class * extends java.lang.Exception
-keep class com.crashlytics.** { *; }
-dontwarn com.crashlytics.**""",

    "navigation": """\
# Navigation Component
-keepnames class * extends android.os.Parcelable
-keepnames class * extends java.io.Serializable
-keepnames class androidx.navigation.fragment.NavHostFragment""",

    "workmanager": """\
# WorkManager
-keep class * extends androidx.work.Worker
-keep class * extends androidx.work.ListenableWorker {
    public <init>(android.content.Context, androidx.work.WorkerParameters);
}""",

    "paging": """\
# Paging
-keep class * extends androidx.paging.PagingSource
-keep class * extends androidx.paging.RemoteMediator""",

    "databinding": """\
# DataBinding
-keep class * extends androidx.databinding.ViewDataBinding {
    public static * inflate(android.view.LayoutInflater);
    public static * inflate(android.view.LayoutInflater, android.view.ViewGroup, boolean);
    public static * bind(android.view.View);
}""",
}

# ─── 扫描器 ──────────────────────────────────────────────────────────────

class ProGuardScanner:
    """扫描源码目录，检测需要 keep 规则的模式"""

    def __init__(self, module_path: str):
        self.module_path = Path(module_path)
        self.findings = {
            "reflection": [],
            "serialization": [],
            "jni": [],
            "manifest": [],
            "enum": [],
            "webview": [],
        }

    def scan_all(self):
        self._scan_source_files()
        self._scan_manifest()
        return self.findings

    def scan_type(self, scan_type: str):
        if scan_type == "all":
            return self.scan_all()
        if scan_type in ("reflection", "serialization", "jni", "enum", "webview"):
            self._scan_source_files(only_type=scan_type)
        elif scan_type == "manifest":
            self._scan_manifest()
        return self.findings

    def _find_source_files(self):
        """查找所有 Java/Kotlin 源文件"""
        src_dirs = [
            self.module_path / "src",
        ]
        for src_dir in src_dirs:
            if not src_dir.exists():
                continue
            for ext in ("*.java", "*.kt"):
                yield from src_dir.rglob(ext)

    def _get_package_and_class(self, filepath: Path) -> str:
        """从文件路径和内容推断 FQCN"""
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except (OSError, IOError):
            return ""
        pkg_match = re.search(r"^package\s+([\w.]+)", content, re.MULTILINE)
        if pkg_match:
            pkg = pkg_match.group(1)
            class_name = filepath.stem
            return f"{pkg}.{class_name}"
        return ""

    def _scan_source_files(self, only_type: str = None):
        for filepath in self._find_source_files():
            try:
                content = filepath.read_text(encoding="utf-8", errors="ignore")
            except (OSError, IOError):
                continue

            fqcn = self._get_package_and_class(filepath)
            if not fqcn:
                continue

            if only_type is None or only_type == "reflection":
                self._check_reflection(content, fqcn)

            if only_type is None or only_type == "serialization":
                self._check_serialization(content, fqcn)

            if only_type is None or only_type == "jni":
                self._check_jni(content, fqcn)

            if only_type is None or only_type == "enum":
                self._check_enum(content, fqcn)

            if only_type is None or only_type == "webview":
                self._check_webview(content, fqcn)

    def _check_reflection(self, content: str, fqcn: str):
        patterns = [
            r'Class\.forName\s*\(\s*"([^"]+)"',
            r'\.getMethod\s*\(\s*"([^"]+)"',
            r'\.getDeclaredMethod\s*\(\s*"([^"]+)"',
            r'\.getField\s*\(\s*"([^"]+)"',
            r'\.getDeclaredField\s*\(\s*"([^"]+)"',
        ]
        for pat in patterns:
            matches = re.findall(pat, content)
            for m in matches:
                self.findings["reflection"].append({
                    "class": fqcn,
                    "target": m,
                    "type": "reflection",
                })

    def _check_serialization(self, content: str, fqcn: str):
        if re.search(r"@SerializedName", content):
            self.findings["serialization"].append({
                "class": fqcn,
                "type": "gson_serialized",
            })
        if re.search(r"implements\s+Serializable", content):
            self.findings["serialization"].append({
                "class": fqcn,
                "type": "java_serializable",
            })
        if re.search(r"implements\s+Parcelable|@Parcelize", content):
            self.findings["serialization"].append({
                "class": fqcn,
                "type": "parcelable",
            })
        if re.search(r"@Serializable", content):
            self.findings["serialization"].append({
                "class": fqcn,
                "type": "kotlin_serializable",
            })

    def _check_jni(self, content: str, fqcn: str):
        if re.search(r"\bnative\s+\w+\s+\w+\s*\(", content):
            self.findings["jni"].append({
                "class": fqcn,
                "type": "jni_native",
            })

    def _check_enum(self, content: str, fqcn: str):
        if re.search(r"\benum\s+(class\s+)?\w+", content):
            self.findings["enum"].append({
                "class": fqcn,
                "type": "enum",
            })

    def _check_webview(self, content: str, fqcn: str):
        if re.search(r"@JavascriptInterface", content):
            self.findings["webview"].append({
                "class": fqcn,
                "type": "javascript_interface",
            })

    def _scan_manifest(self):
        manifest_paths = [
            self.module_path / "src" / "main" / "AndroidManifest.xml",
            self.module_path / "AndroidManifest.xml",
        ]
        manifest_path = None
        for p in manifest_paths:
            if p.exists():
                manifest_path = p
                break
        if not manifest_path:
            return

        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            ns = "{http://schemas.android.com/apk/res/android}"
            pkg = root.get("package", "")
            app = root.find("application")
            if app is None:
                return
            for tag in ("activity", "service", "receiver", "provider"):
                for elem in app.iter(tag):
                    name = elem.get(f"{ns}name", "")
                    if name.startswith("."):
                        name = pkg + name
                    elif "." not in name:
                        name = f"{pkg}.{name}"
                    if name:
                        self.findings["manifest"].append({
                            "class": name,
                            "type": f"manifest_{tag}",
                        })
        except ET.ParseError:
            pass


# ─── 规则生成器 ──────────────────────────────────────────────────────────

def generate_rules(findings: dict) -> str:
    """根据扫描结果生成 ProGuard 规则"""
    rules = []
    seen = set()

    if findings.get("reflection"):
        rules.append("# ─── 反射调用 ───")
        for item in findings["reflection"]:
            cls = item["class"]
            if cls not in seen:
                rules.append(f"-keep class {cls} {{ *; }}")
                seen.add(cls)
            target = item.get("target", "")
            if target and "." in target and target not in seen:
                rules.append(f"-keep class {target} {{ *; }}")
                seen.add(target)
        rules.append("")

    if findings.get("serialization"):
        rules.append("# ─── 序列化 ───")
        for item in findings["serialization"]:
            cls = item["class"]
            t = item["type"]
            if cls in seen:
                continue
            seen.add(cls)
            if t == "gson_serialized":
                rules.append(f"-keepclassmembers class {cls} {{ *; }}")
            elif t == "java_serializable":
                rules.append(f"-keepnames class {cls} {{ *; }}")
            elif t == "parcelable":
                rules.append(f"-keep class {cls} {{ *; }}")
            elif t == "kotlin_serializable":
                rules.append(f"-keepclassmembers @kotlinx.serialization.Serializable class {cls} {{ *; }}")
        rules.append("")

    if findings.get("jni"):
        rules.append("# ─── JNI ───")
        for item in findings["jni"]:
            cls = item["class"]
            if cls not in seen:
                rules.append(f"-keepclasseswithmembers class {cls} {{ native <methods>; }}")
                seen.add(cls)
        rules.append("")

    if findings.get("manifest"):
        rules.append("# ─── 四大组件 (AndroidManifest) ───")
        for item in findings["manifest"]:
            cls = item["class"]
            if cls not in seen:
                rules.append(f"-keep class {cls}")
                seen.add(cls)
        rules.append("")

    if findings.get("enum"):
        rules.append("# ─── 枚举 ───")
        enum_classes = [item["class"] for item in findings["enum"] if item["class"] not in seen]
        if enum_classes:
            rules.append("-keepclassmembers enum * {")
            rules.append("    public static **[] values();")
            rules.append("    public static ** valueOf(java.lang.String);")
            rules.append("}")
            for cls in enum_classes:
                seen.add(cls)
        rules.append("")

    if findings.get("webview"):
        rules.append("# ─── WebView JavascriptInterface ───")
        for item in findings["webview"]:
            cls = item["class"]
            if cls not in seen:
                rules.append(f"-keepclassmembers class {cls} {{")
                rules.append(f"    @android.webkit.JavascriptInterface <methods>;")
                rules.append(f"}}")
                seen.add(cls)
        rules.append("")

    if not rules:
        return "# 未检测到需要额外 keep 规则的模式"

    header = [
        "# ═══════════════════════════════════════════════════════════",
        "# 自动生成的 ProGuard/R8 规则",
        f"# 扫描路径: {os.getcwd()}",
        "# ═══════════════════════════════════════════════════════════",
        "",
    ]
    return "\n".join(header + rules)


# ─── 规则检查器 ──────────────────────────────────────────────────────────

def check_rules_file(filepath: str) -> list:
    """检查 proguard-rules.pro 中的潜在问题"""
    issues = []
    try:
        content = Path(filepath).read_text(encoding="utf-8")
    except FileNotFoundError:
        return [{"level": "error", "message": f"文件不存在: {filepath}"}]

    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if re.match(r"-keep\s+class\s+\*\s*\{", stripped):
            issues.append({
                "level": "warning",
                "line": i,
                "message": "过于宽泛的 keep 规则 (-keep class * {})，会阻止几乎所有优化",
                "suggestion": "改为精确匹配特定包或类",
            })

        if re.match(r"-dontwarn\s+\*\*$", stripped):
            issues.append({
                "level": "warning",
                "line": i,
                "message": "-dontwarn ** 会抑制所有警告，可能掩盖真实问题",
                "suggestion": "改为针对特定包的 -dontwarn",
            })

        if "-keepattributes" in stripped and "Signature" not in content:
            if "Gson" in content or "Retrofit" in content or "Moshi" in content:
                issues.append({
                    "level": "info",
                    "line": i,
                    "message": "使用了 Gson/Retrofit/Moshi 但未保留 Signature 属性",
                    "suggestion": "添加 -keepattributes Signature",
                })

        if "SourceFile" not in content and "LineNumberTable" not in content:
            if i == 1:
                issues.append({
                    "level": "info",
                    "line": 0,
                    "message": "未保留 SourceFile/LineNumberTable，崩溃堆栈将不可读",
                    "suggestion": "添加 -keepattributes SourceFile,LineNumberTable",
                })

    return issues


# ─── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Android ProGuard/R8 混淆规则分析器")
    sub = parser.add_subparsers(dest="command", help="子命令")

    scan_p = sub.add_parser("scan", help="扫描源码并生成 keep 规则")
    scan_p.add_argument("module_path", help="Android模块路径")
    scan_p.add_argument("--type", default="all",
                        choices=["all", "reflection", "serialization", "jni", "manifest", "enum", "webview"],
                        help="扫描类型")
    scan_p.add_argument("-o", "--output", help="输出到文件")
    scan_p.add_argument("--json", action="store_true", help="JSON格式输出")

    tpl_p = sub.add_parser("templates", help="列出所有库规则模板")

    tpl_get = sub.add_parser("template", help="获取指定库的规则模板")
    tpl_get.add_argument("library", help="库名 (如 gson, retrofit, room)")

    check_p = sub.add_parser("check", help="检查 proguard-rules.pro")
    check_p.add_argument("filepath", help="规则文件路径")

    args = parser.parse_args()

    if args.command == "scan":
        if not os.path.isdir(args.module_path):
            print(f"错误: 目录不存在: {args.module_path}", file=sys.stderr)
            sys.exit(1)

        scanner = ProGuardScanner(args.module_path)
        findings = scanner.scan_type(args.type)

        if args.json:
            print(json.dumps(findings, indent=2, ensure_ascii=False))
            return

        total = sum(len(v) for v in findings.values())
        print(f"扫描完成，发现 {total} 个需要 keep 规则的模式:\n")
        for category, items in findings.items():
            if items:
                print(f"  {category}: {len(items)} 个")
        print()

        rules = generate_rules(findings)
        if args.output:
            Path(args.output).write_text(rules, encoding="utf-8")
            print(f"规则已写入: {args.output}")
        else:
            print(rules)

    elif args.command == "templates":
        print("可用的库规则模板:\n")
        for name in sorted(LIBRARY_TEMPLATES.keys()):
            print(f"  - {name}")
        print(f"\n共 {len(LIBRARY_TEMPLATES)} 个模板")
        print("使用方法: proguard_analyzer.py template <library>")

    elif args.command == "template":
        lib = args.library.lower().replace("-", "").replace("_", "")
        if lib == "kotlinserialization":
            lib = "kotlin-serialization"
        if lib in LIBRARY_TEMPLATES:
            print(LIBRARY_TEMPLATES[lib])
        else:
            print(f"未找到 '{args.library}' 的模板", file=sys.stderr)
            print(f"可用模板: {', '.join(sorted(LIBRARY_TEMPLATES.keys()))}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "check":
        issues = check_rules_file(args.filepath)
        if not issues:
            print("✓ 未发现潜在问题")
        else:
            for issue in issues:
                level = issue["level"].upper()
                line = f"L{issue.get('line', '?')}: " if issue.get("line") else ""
                print(f"[{level}] {line}{issue['message']}")
                if issue.get("suggestion"):
                    print(f"  → {issue['suggestion']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
