#!/usr/bin/env python3
"""Android Gradle 构建诊断工具 — 扫描配置问题、分析依赖冲突、生成优化建议"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from collections import defaultdict

# ─── 常见 Gradle 错误速查 ────────────────────────────────────────────────

COMMON_ERRORS = {
    "duplicate class": {
        "name": "Duplicate class",
        "pattern": r"Duplicate class .+ found in modules",
        "causes": [
            "多个依赖库包含相同的类",
            "同一库的不同版本被同时引入",
            "Jetifier 转换后产生冲突",
        ],
        "fixes": [
            "使用 ./gradlew :app:dependencies 找出冲突来源",
            "在 build.gradle 中使用 exclude group 排除冲突模块",
            "使用 resolutionStrategy.force 强制统一版本",
            "在 gradle.properties 中设置 android.enableJetifier=true",
        ],
    },
    "could not resolve": {
        "name": "Could not resolve dependency",
        "pattern": r"Could not resolve .+",
        "causes": [
            "依赖的 Maven 仓库未配置",
            "网络问题无法访问仓库",
            "依赖的版本号不存在",
            "私有仓库认证失败",
        ],
        "fixes": [
            "检查 settings.gradle 中的 repositories 配置",
            "确认 Maven 仓库 URL 正确且可访问",
            "检查依赖的 groupId:artifactId:version 是否正确",
            "私有仓库检查 ~/.gradle/gradle.properties 中的认证信息",
        ],
    },
    "merge resources": {
        "name": "Merge Resources / Manifest 失败",
        "pattern": r"Execution failed for task .+merge.+(Resources|Manifest)",
        "causes": [
            "不同模块/库的资源名称冲突",
            "AndroidManifest 属性冲突",
            "资源类型不匹配",
        ],
        "fixes": [
            "在 AndroidManifest 中使用 tools:replace 指定覆盖的属性",
            "使用 resourcePrefix 为模块资源添加前缀",
            "检查冲突资源文件并重命名",
        ],
    },
    "unsupported class file": {
        "name": "Unsupported class file major version",
        "pattern": r"Unsupported class file major version",
        "causes": [
            "使用的 JDK 版本与 AGP 不兼容",
            "编译库用的 JDK 版本高于项目配置",
        ],
        "fixes": [
            "检查 JAVA_HOME 指向的 JDK 版本",
            "在 gradle.properties 中设置 org.gradle.java.home",
            "AGP 7.x 需要 JDK 11+，AGP 8.x 需要 JDK 17+",
        ],
    },
    "out of memory": {
        "name": "Gradle OutOfMemoryError",
        "pattern": r"OutOfMemoryError|GC overhead limit exceeded",
        "causes": [
            "Gradle Daemon JVM 堆内存不足",
            "项目过大，编译过程占用大量内存",
        ],
        "fixes": [
            "在 gradle.properties 中增加 org.gradle.jvmargs=-Xmx4g",
            "启用 Gradle 配置缓存减少内存使用",
            "减少并行编译任务数",
        ],
    },
    "kapt": {
        "name": "Kapt 注解处理器错误",
        "pattern": r"(?:kapt|annotation processor).+error",
        "causes": [
            "注解处理器版本与 Kotlin 版本不兼容",
            "缺少必要的注解处理器依赖",
            "Kapt 与 KSP 混用导致冲突",
        ],
        "fixes": [
            "检查 Kotlin 版本与注解处理器版本兼容性",
            "考虑从 kapt 迁移到 KSP（性能更好）",
            "确保 kapt 配置正确: kapt '<processor>'",
        ],
    },
}


# ─── build.gradle 扫描器 ────────────────────────────────────────────────

class GradleScanner:
    """扫描 build.gradle 配置问题"""

    def __init__(self, module_path: str):
        self.module_path = Path(module_path)
        self.issues = []
        self.gradle_file = None
        self.content = ""
        self._find_gradle_file()

    def _find_gradle_file(self):
        for name in ("build.gradle.kts", "build.gradle"):
            p = self.module_path / name
            if p.exists():
                self.gradle_file = p
                self.content = p.read_text(encoding="utf-8", errors="ignore")
                return
        self.issues.append({
            "level": "error",
            "category": "file",
            "message": "未找到 build.gradle 或 build.gradle.kts",
        })

    def scan_all(self) -> list:
        if not self.gradle_file:
            return self.issues
        self._check_deprecated_apis()
        self._check_dynamic_versions()
        self._check_duplicate_deps()
        self._check_missing_config()
        self._check_hardcoded_versions()
        return self.issues

    def _check_deprecated_apis(self):
        deprecated = {
            r"\bcompile\b(?!Sdk|Only|Options)": ("compile", "implementation"),
            r"\btestCompile\b": ("testCompile", "testImplementation"),
            r"\bandroidTestCompile\b": ("androidTestCompile", "androidTestImplementation"),
            r"\bprovided\b": ("provided", "compileOnly"),
            r"\bapk\b\s": ("apk", "runtimeOnly"),
        }
        for pattern, (old, new) in deprecated.items():
            if re.search(pattern, self.content):
                self.issues.append({
                    "level": "warning",
                    "category": "deprecated",
                    "message": f"使用了过时的 '{old}'，应替换为 '{new}'",
                    "fix": f"将 {old} 替换为 {new}",
                })

    def _check_dynamic_versions(self):
        dynamic_patterns = [
            (r'["\'][\w.]+:[\w-]+:\d+\.\+["\']', "x.+"),
            (r'["\'][\w.]+:[\w-]+:latest\.\w+["\']', "latest.x"),
            (r'["\'][\w.]+:[\w-]+:\+["\']', "+"),
        ]
        for pattern, desc in dynamic_patterns:
            matches = re.findall(pattern, self.content)
            for m in matches:
                self.issues.append({
                    "level": "warning",
                    "category": "dynamic_version",
                    "message": f"使用了动态版本 ({desc}): {m}",
                    "fix": "固定到具体版本号以保证构建可重复性",
                })

    def _check_duplicate_deps(self):
        dep_pattern = r'(?:implementation|api|compileOnly|runtimeOnly)\s*[("]\s*["\']?([\w.]+:[\w-]+)[:"]'
        deps = re.findall(dep_pattern, self.content)
        seen = defaultdict(int)
        for d in deps:
            seen[d] += 1
        for dep, count in seen.items():
            if count > 1:
                self.issues.append({
                    "level": "warning",
                    "category": "duplicate",
                    "message": f"依赖 '{dep}' 被声明了 {count} 次",
                    "fix": "移除重复声明，保留一个即可",
                })

    def _check_missing_config(self):
        if "android" in self.content:
            if not re.search(r'compileSdk|compileSdkVersion', self.content):
                self.issues.append({
                    "level": "error",
                    "category": "config",
                    "message": "缺少 compileSdk/compileSdkVersion 配置",
                })
            if not re.search(r'minSdk|minSdkVersion', self.content):
                self.issues.append({
                    "level": "error",
                    "category": "config",
                    "message": "缺少 minSdk/minSdkVersion 配置",
                })

    def _check_hardcoded_versions(self):
        hardcoded = re.findall(
            r'(?:implementation|api)\s*[("]\s*["\'][\w.]+:[\w-]+:\d+\.\d+\.\d+["\']',
            self.content
        )
        if len(hardcoded) > 5:
            self.issues.append({
                "level": "info",
                "category": "versioning",
                "message": f"有 {len(hardcoded)} 个依赖的版本号直接硬编码",
                "fix": "建议使用 Version Catalog (libs.versions.toml) 统一管理版本号",
            })


# ─── 依赖分析器 ──────────────────────────────────────────────────────────

def analyze_dependencies(deps_text: str, filter_lib: str = None) -> dict:
    """分析 ./gradlew dependencies 输出"""
    conflicts = []
    forced = []

    conflict_pattern = re.compile(
        r'([\w.]+:[\w-]+):(\S+)\s*->\s*(\S+)'
    )
    for match in conflict_pattern.finditer(deps_text):
        lib = match.group(1)
        requested = match.group(2)
        resolved = match.group(3)
        if filter_lib and filter_lib.lower() not in lib.lower():
            continue
        conflicts.append({
            "library": lib,
            "requested": requested,
            "resolved": resolved,
        })

    forced_pattern = re.compile(
        r'([\w.]+:[\w-]+):(\S+)\s*\((\*)\)'
    )
    for match in forced_pattern.finditer(deps_text):
        lib = match.group(1)
        version = match.group(2)
        if filter_lib and filter_lib.lower() not in lib.lower():
            continue
        forced.append({
            "library": lib,
            "version": version,
            "note": "被强制解析（可能被其他依赖覆盖）",
        })

    return {
        "conflicts": conflicts,
        "forced": forced,
        "total_conflicts": len(conflicts),
        "total_forced": len(forced),
    }


# ─── 优化建议生成器 ──────────────────────────────────────────────────────

def generate_optimization(project_root: str) -> list:
    """生成构建优化建议"""
    suggestions = []
    root = Path(project_root)

    props_file = root / "gradle.properties"
    props_content = ""
    if props_file.exists():
        props_content = props_file.read_text(encoding="utf-8", errors="ignore")

    if "org.gradle.parallel" not in props_content or "=false" in props_content.split("org.gradle.parallel")[-1][:20] if "org.gradle.parallel" in props_content else True:
        suggestions.append({
            "category": "并行构建",
            "current": "未启用",
            "suggestion": "在 gradle.properties 中添加: org.gradle.parallel=true",
            "impact": "多模块项目可显著提升构建速度",
        })

    if "org.gradle.caching" not in props_content:
        suggestions.append({
            "category": "构建缓存",
            "current": "未启用",
            "suggestion": "在 gradle.properties 中添加: org.gradle.caching=true",
            "impact": "避免重复编译未变更的模块",
        })

    if "org.gradle.jvmargs" not in props_content:
        suggestions.append({
            "category": "JVM 内存",
            "current": "使用默认值",
            "suggestion": "在 gradle.properties 中添加: org.gradle.jvmargs=-Xmx4g -XX:+HeapDumpOnOutOfMemoryError",
            "impact": "增加可用内存，避免 OOM",
        })
    else:
        xmx_match = re.search(r'-Xmx(\d+)([gGmM])', props_content)
        if xmx_match:
            size = int(xmx_match.group(1))
            unit = xmx_match.group(2).lower()
            mb = size * 1024 if unit == "g" else size
            if mb < 2048:
                suggestions.append({
                    "category": "JVM 内存",
                    "current": f"-Xmx{size}{xmx_match.group(2)}",
                    "suggestion": "建议增加到 -Xmx4g（至少 2g）",
                    "impact": "减少 GC 压力，提升编译速度",
                })

    if "org.gradle.configuration-cache" not in props_content:
        suggestions.append({
            "category": "配置缓存",
            "current": "未启用",
            "suggestion": "在 gradle.properties 中添加: org.gradle.configuration-cache=true",
            "impact": "AGP 8.0+ 支持，大幅减少配置阶段时间",
        })

    if "kotlin.incremental" not in props_content:
        suggestions.append({
            "category": "Kotlin 增量编译",
            "current": "默认启用",
            "suggestion": "确认 gradle.properties 中无 kotlin.incremental=false",
            "impact": "增量编译显著减少编译时间",
        })

    settings_file = root / "settings.gradle.kts"
    if not settings_file.exists():
        settings_file = root / "settings.gradle"
    if settings_file.exists():
        settings_content = settings_file.read_text(encoding="utf-8", errors="ignore")
        if "libs.versions.toml" not in settings_content and "versionCatalogs" not in settings_content:
            toml_file = root / "gradle" / "libs.versions.toml"
            if not toml_file.exists():
                suggestions.append({
                    "category": "版本目录",
                    "current": "未使用 Version Catalog",
                    "suggestion": "创建 gradle/libs.versions.toml 统一管理依赖版本",
                    "impact": "多模块项目中避免版本不一致，IDE 支持自动补全",
                })

    return suggestions


# ─── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Android Gradle 构建诊断工具")
    sub = parser.add_subparsers(dest="command", help="子命令")

    diag_p = sub.add_parser("diagnose", help="全面诊断模块")
    diag_p.add_argument("module_path", help="模块路径")
    diag_p.add_argument("--json", action="store_true", help="JSON格式输出")

    scan_p = sub.add_parser("scan", help="扫描 build.gradle 配置")
    scan_p.add_argument("module_path", help="模块路径")
    scan_p.add_argument("--json", action="store_true", help="JSON格式输出")

    deps_p = sub.add_parser("deps", help="分析依赖输出")
    deps_p.add_argument("deps_file", help="./gradlew dependencies 输出文件")
    deps_p.add_argument("--filter", help="按库名过滤")
    deps_p.add_argument("--json", action="store_true", help="JSON格式输出")

    opt_p = sub.add_parser("optimize", help="生成优化建议")
    opt_p.add_argument("project_root", help="项目根目录")
    opt_p.add_argument("--json", action="store_true", help="JSON格式输出")

    sub.add_parser("errors", help="列出常见错误")

    err_p = sub.add_parser("error", help="查看错误修复方案")
    err_p.add_argument("keyword", help="错误关键词")

    args = parser.parse_args()

    if args.command == "diagnose":
        if not os.path.isdir(args.module_path):
            print(f"错误: 目录不存在: {args.module_path}", file=sys.stderr)
            sys.exit(1)

        scanner = GradleScanner(args.module_path)
        issues = scanner.scan_all()

        root = Path(args.module_path)
        while root.parent != root:
            if (root / "settings.gradle").exists() or (root / "settings.gradle.kts").exists():
                break
            root = root.parent
        optimizations = generate_optimization(str(root))

        if args.json:
            print(json.dumps({
                "issues": issues,
                "optimizations": optimizations,
            }, indent=2, ensure_ascii=False))
        else:
            print("═══════════════════════════════════════════════")
            print("  Gradle 构建诊断报告")
            print("═══════════════════════════════════════════════\n")

            if issues:
                errors = [i for i in issues if i["level"] == "error"]
                warnings = [i for i in issues if i["level"] == "warning"]
                infos = [i for i in issues if i["level"] == "info"]

                if errors:
                    print(f"错误 ({len(errors)}):")
                    for i in errors:
                        print(f"  ✗ [{i['category']}] {i['message']}")
                        if i.get("fix"):
                            print(f"    → {i['fix']}")
                    print()

                if warnings:
                    print(f"警告 ({len(warnings)}):")
                    for i in warnings:
                        print(f"  ⚠ [{i['category']}] {i['message']}")
                        if i.get("fix"):
                            print(f"    → {i['fix']}")
                    print()

                if infos:
                    print(f"建议 ({len(infos)}):")
                    for i in infos:
                        print(f"  ℹ [{i['category']}] {i['message']}")
                        if i.get("fix"):
                            print(f"    → {i['fix']}")
                    print()
            else:
                print("✓ 未发现 build.gradle 配置问题\n")

            if optimizations:
                print(f"优化建议 ({len(optimizations)}):")
                for opt in optimizations:
                    print(f"  [{opt['category']}]")
                    print(f"    当前: {opt['current']}")
                    print(f"    建议: {opt['suggestion']}")
                    print(f"    影响: {opt['impact']}")
                    print()

    elif args.command == "scan":
        if not os.path.isdir(args.module_path):
            print(f"错误: 目录不存在: {args.module_path}", file=sys.stderr)
            sys.exit(1)

        scanner = GradleScanner(args.module_path)
        issues = scanner.scan_all()

        if args.json:
            print(json.dumps(issues, indent=2, ensure_ascii=False))
        else:
            if issues:
                for i in issues:
                    level = i["level"].upper()
                    print(f"[{level}] [{i['category']}] {i['message']}")
                    if i.get("fix"):
                        print(f"  → {i['fix']}")
            else:
                print("✓ 未发现配置问题")

    elif args.command == "deps":
        try:
            text = Path(args.deps_file).read_text(encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            print(f"错误: 文件不存在: {args.deps_file}", file=sys.stderr)
            sys.exit(1)

        result = analyze_dependencies(text, args.filter)

        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"依赖分析: {result['total_conflicts']} 个版本冲突, "
                  f"{result['total_forced']} 个被强制解析\n")
            if result["conflicts"]:
                print("版本冲突:")
                for c in result["conflicts"]:
                    print(f"  {c['library']}  {c['requested']} → {c['resolved']}")
                print()
            if result["forced"]:
                print("强制解析:")
                for f in result["forced"]:
                    print(f"  {f['library']}:{f['version']}  ({f['note']})")

    elif args.command == "optimize":
        if not os.path.isdir(args.project_root):
            print(f"错误: 目录不存在: {args.project_root}", file=sys.stderr)
            sys.exit(1)

        suggestions = generate_optimization(args.project_root)

        if args.json:
            print(json.dumps(suggestions, indent=2, ensure_ascii=False))
        else:
            if suggestions:
                print("构建优化建议:\n")
                for s in suggestions:
                    print(f"  [{s['category']}]")
                    print(f"    当前: {s['current']}")
                    print(f"    建议: {s['suggestion']}")
                    print(f"    影响: {s['impact']}")
                    print()
            else:
                print("✓ 构建配置已经很优化了")

    elif args.command == "errors":
        print("常见 Gradle 构建错误:\n")
        for key, info in COMMON_ERRORS.items():
            print(f"  {key:25s} {info['name']}")
        print(f"\n使用 'error <keyword>' 查看详细修复方案")

    elif args.command == "error":
        keyword = args.keyword.lower()
        found = False
        for key, info in COMMON_ERRORS.items():
            if keyword in key or keyword in info["name"].lower():
                found = True
                print(f"═══ {info['name']} ═══\n")
                print("可能原因:")
                for c in info["causes"]:
                    print(f"  • {c}")
                print("\n修复方法:")
                for f in info["fixes"]:
                    print(f"  ✓ {f}")
                print()
        if not found:
            print(f"未找到 '{args.keyword}' 相关的错误")
            print(f"使用 'errors' 查看所有支持的错误类型")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
