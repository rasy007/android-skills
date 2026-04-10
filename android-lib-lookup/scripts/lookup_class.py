#!/usr/bin/env python3
"""
Android/Gradle Dependency Class Lookup Tool

Automatically indexes classes from Gradle-cached AAR/JAR dependencies
and provides instant API lookups. Zero external dependencies.

Usage:
  python3 lookup_class.py --project /path/to/module --class MyThreadExecutor
  python3 lookup_class.py --project /path/to/module --package com.example.util
  python3 lookup_class.py --project /path/to/module --library com.example:utils
  python3 lookup_class.py --project /path/to/module --search Toast
  python3 lookup_class.py --project /path/to/module --stats
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

CACHE_DIR_NAME = ".lib-index-cache"
INDEX_FILE = "class_index.json"
META_FILE = "index_meta.json"

DEPENDENCY_CONFIGS = (
    "implementation",
    "api",
    "compileOnly",
    "runtimeOnly",
    "annotationProcessor",
    "kapt",
    "ksp",
    "testImplementation",
    "androidTestImplementation",
    "debugImplementation",
    "releaseImplementation",
)


# ─── Gradle 解析 ────────────────────────────────────────────

def parse_dependencies_from_gradle(build_gradle_path: str) -> list:
    """从 build.gradle 或 build.gradle.kts 中解析 Maven 依赖坐标。"""
    content = Path(build_gradle_path).read_text(encoding="utf-8")
    is_kts = build_gradle_path.endswith(".kts")
    deps = []
    seen = set()

    if is_kts:
        deps.extend(_parse_kts_dependencies(content, seen))
    else:
        deps.extend(_parse_groovy_dependencies(content, seen))

    return deps


def _parse_groovy_dependencies(content: str, seen: set) -> list:
    """解析 Groovy DSL (build.gradle) 的依赖。"""
    deps = []
    configs = "|".join(DEPENDENCY_CONFIGS)

    # implementation "group:artifact:version"
    # implementation("group:artifact:version")
    # implementation "group:artifact:$variable"
    pattern = re.compile(
        rf"""(?:{configs})\s*[\s(]["']([^"']+)["']"""
    )
    for m in pattern.finditer(content):
        dep = _parse_coord(m.group(1))
        if dep and dep["key"] not in seen:
            seen.add(dep["key"])
            deps.append(dep)

    # implementation group: 'xxx', name: 'xxx', version: 'xxx'
    map_pattern = re.compile(
        rf"""(?:{configs})\s+group\s*:\s*["']([^"']+)["']\s*,\s*name\s*:\s*["']([^"']+)["']"""
    )
    for m in map_pattern.finditer(content):
        key = f"{m.group(1)}:{m.group(2)}"
        if key not in seen:
            seen.add(key)
            deps.append({"group": m.group(1), "artifact": m.group(2), "key": key})

    return deps


def _parse_kts_dependencies(content: str, seen: set) -> list:
    """解析 Kotlin DSL (build.gradle.kts) 的依赖。"""
    deps = []
    configs = "|".join(DEPENDENCY_CONFIGS)

    # implementation("group:artifact:version")
    pattern = re.compile(
        rf"""(?:{configs})\s*\(\s*["']([^"']+)["']"""
    )
    for m in pattern.finditer(content):
        dep = _parse_coord(m.group(1))
        if dep and dep["key"] not in seen:
            seen.add(dep["key"])
            deps.append(dep)

    # libs.xxx style (Version Catalog) — extract comment hints or skip
    # implementation(libs.some.lib) is not resolvable without toml parsing

    return deps


def _parse_coord(raw: str) -> dict:
    """解析 Maven 坐标字符串。"""
    parts = raw.split(":")
    if len(parts) >= 2:
        return {"group": parts[0], "artifact": parts[1], "key": f"{parts[0]}:{parts[1]}"}
    return None


# ─── Gradle 缓存查找 ────────────────────────────────────────

def find_artifact_files(group_id: str, artifact_id: str, gradle_cache: str) -> dict:
    """在 Gradle 缓存中查找 artifact 文件，返回最新版本。"""
    base = Path(gradle_cache) / "modules-2" / "files-2.1" / group_id / artifact_id
    if not base.exists():
        return {}

    try:
        versions = sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return {}

    if not versions:
        return {}

    latest = versions[0]
    result = {"version": latest.name}

    for hash_dir in latest.iterdir():
        if not hash_dir.is_dir():
            continue
        for f in hash_dir.iterdir():
            name = f.name
            if name.endswith("-sources.jar"):
                result["sources_jar"] = str(f)
            elif name.endswith(".aar"):
                result["aar"] = str(f)
            elif name.endswith(".jar") and "sources" not in name and "javadoc" not in name:
                result["jar"] = str(f)
    return result


# ─── 类提取 ─────────────────────────────────────────────────

def extract_classes_from_aar(aar_path: str) -> list:
    """从 AAR 的 classes.jar 中提取所有非内部类的全限定名。"""
    classes = []
    try:
        with zipfile.ZipFile(aar_path, "r") as zf:
            if "classes.jar" not in zf.namelist():
                return classes
            with tempfile.TemporaryDirectory() as tmpdir:
                zf.extract("classes.jar", tmpdir)
                jar_path = os.path.join(tmpdir, "classes.jar")
                classes = _extract_classes_from_jar_file(jar_path)
    except (zipfile.BadZipFile, KeyError, OSError) as e:
        print(f"  警告: 无法解析 AAR {aar_path}: {e}", file=sys.stderr)
    return classes


def extract_classes_from_jar(jar_path: str) -> list:
    """从 JAR 中提取所有非内部类的全限定名。"""
    try:
        return _extract_classes_from_jar_file(jar_path)
    except (zipfile.BadZipFile, OSError) as e:
        print(f"  警告: 无法解析 JAR {jar_path}: {e}", file=sys.stderr)
        return []


def _extract_classes_from_jar_file(jar_path: str) -> list:
    """从 JAR 文件提取类名的核心实现。"""
    classes = []
    with zipfile.ZipFile(jar_path, "r") as jf:
        for entry in jf.namelist():
            if (entry.endswith(".class")
                    and "$" not in entry
                    and not entry.startswith("META-INF/")):
                fqcn = entry.replace("/", ".").replace(".class", "")
                classes.append(fqcn)
    return classes


# ─── 索引构建与缓存 ─────────────────────────────────────────

def find_build_gradle(project_dir: str) -> str:
    """查找 build.gradle 或 build.gradle.kts 文件。"""
    for name in ("build.gradle", "build.gradle.kts"):
        path = os.path.join(project_dir, name)
        if os.path.exists(path):
            return path
    return ""


def build_index(project_dir: str, gradle_cache: str) -> dict:
    """构建完整的类索引。"""
    build_gradle = find_build_gradle(project_dir)
    if not build_gradle:
        print(f"错误: 在 {project_dir} 中未找到 build.gradle 或 build.gradle.kts", file=sys.stderr)
        sys.exit(1)

    gradle_cache_path = Path(gradle_cache) / "modules-2" / "files-2.1"
    if not gradle_cache_path.exists():
        print(f"错误: Gradle 缓存目录不存在: {gradle_cache_path}", file=sys.stderr)
        print("请确保项目已通过 Android Studio 或 Gradle 编译过至少一次。", file=sys.stderr)
        sys.exit(1)

    deps = parse_dependencies_from_gradle(build_gradle)
    print(f"从 {os.path.basename(build_gradle)} 解析到 {len(deps)} 个依赖", file=sys.stderr)

    if not deps:
        print("警告: 未解析到任何依赖。请检查 build file 格式是否正确。", file=sys.stderr)

    index = {
        "class_to_lib": {},
        "lib_to_classes": {},
        "lib_files": {},
    }

    found_count = 0
    not_found = []

    for dep in deps:
        coord = dep["key"]
        files = find_artifact_files(dep["group"], dep["artifact"], gradle_cache)
        if not files:
            not_found.append(coord)
            continue

        found_count += 1
        version = files.get("version", "unknown")
        index["lib_files"][coord] = files

        classes = []
        if "aar" in files:
            classes = extract_classes_from_aar(files["aar"])
        elif "jar" in files:
            classes = extract_classes_from_jar(files["jar"])

        if classes:
            index["lib_to_classes"][coord] = classes
            for cls in classes:
                index["class_to_lib"][cls] = {"lib": coord, "version": version}
            print(f"  {coord}:{version} → {len(classes)} 个类", file=sys.stderr)

    total_classes = len(index["class_to_lib"])
    total_libs = len(index["lib_to_classes"])
    print(f"索引构建完成: {total_classes} 个类, {total_libs} 个库 (缓存命中 {found_count}/{len(deps)})", file=sys.stderr)

    if not_found:
        print(f"  未在 Gradle 缓存中找到 {len(not_found)} 个依赖 (可能需要先编译项目):", file=sys.stderr)
        for nf in not_found[:5]:
            print(f"    - {nf}", file=sys.stderr)
        if len(not_found) > 5:
            print(f"    ... 及其他 {len(not_found) - 5} 个", file=sys.stderr)

    return index


def get_gradle_fingerprint(build_gradle_path: str) -> str:
    """根据 build.gradle 内容生成指纹。"""
    content = Path(build_gradle_path).read_bytes()
    return hashlib.md5(content).hexdigest()


def load_or_build_index(project_dir: str, gradle_cache: str, force_rebuild: bool = False) -> dict:
    """加载缓存索引，过期时自动重建。"""
    cache_dir = Path(project_dir) / CACHE_DIR_NAME
    index_path = cache_dir / INDEX_FILE
    meta_path = cache_dir / META_FILE

    build_gradle = find_build_gradle(project_dir)
    if not build_gradle:
        print(f"错误: 在 {project_dir} 中未找到 build.gradle 或 build.gradle.kts", file=sys.stderr)
        sys.exit(1)

    current_fp = get_gradle_fingerprint(build_gradle)

    if not force_rebuild and index_path.exists() and meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            if meta.get("fingerprint") == current_fp:
                print("使用缓存索引", file=sys.stderr)
                return json.loads(index_path.read_text())
            else:
                print("build file 已变更，重建索引...", file=sys.stderr)
        except (json.JSONDecodeError, OSError):
            print("缓存损坏，重建索引...", file=sys.stderr)

    index = build_index(project_dir, gradle_cache)

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2))
        meta_path.write_text(json.dumps({"fingerprint": current_fp}))

        gitignore = cache_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n")
    except OSError as e:
        print(f"警告: 无法写入缓存: {e}（索引仍可正常使用，但下次需重建）", file=sys.stderr)

    return index


# ─── API 提取 ───────────────────────────────────────────────

def extract_class_api_from_sources(sources_jar: str, target_fqcn: str) -> str:
    """从 sources.jar 中提取指定类的源码。"""
    java_path = target_fqcn.replace(".", "/") + ".java"
    kt_path = target_fqcn.replace(".", "/") + ".kt"

    try:
        with zipfile.ZipFile(sources_jar, "r") as zf:
            for path in (java_path, kt_path):
                if path in zf.namelist():
                    return zf.read(path).decode("utf-8", errors="replace")
    except (zipfile.BadZipFile, OSError):
        pass
    return ""


def extract_class_api_via_javap(aar_or_jar_path: str, target_fqcn: str) -> str:
    """用 javap 从 AAR/JAR 中提取类的 public API。"""
    try:
        if aar_or_jar_path.endswith(".aar"):
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(aar_or_jar_path, "r") as zf:
                    zf.extract("classes.jar", tmpdir)
                cp = os.path.join(tmpdir, "classes.jar")
                return _run_javap(cp, target_fqcn)
        else:
            return _run_javap(aar_or_jar_path, target_fqcn)
    except (zipfile.BadZipFile, OSError):
        return ""


def _run_javap(classpath: str, fqcn: str) -> str:
    """执行 javap 命令。"""
    try:
        result = subprocess.run(
            ["javap", "-public", "-cp", classpath, fqcn],
            capture_output=True, text=True, timeout=10,
        )
        return result.stdout if result.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def get_class_api(index: dict, fqcn: str) -> str:
    """获取指定类的 API 信息，优先 sources.jar，否则 javap。"""
    lib_info = index["class_to_lib"].get(fqcn)
    if not lib_info:
        return ""

    files = index["lib_files"].get(lib_info["lib"], {})

    if "sources_jar" in files:
        source = extract_class_api_from_sources(files["sources_jar"], fqcn)
        if source:
            return source

    for key in ("aar", "jar"):
        if key in files:
            return extract_class_api_via_javap(files[key], fqcn)

    return ""


def parse_source_to_api_summary(source_code: str, fqcn: str) -> str:
    """将源码解析为精简的 API 摘要（public 方法签名 + Javadoc）。"""
    if not source_code:
        return ""

    lines = source_code.split("\n")
    result = []
    class_name = fqcn.rsplit(".", 1)[-1]

    result.append(f"=== {fqcn} ===\n")

    in_comment = False
    class_javadoc = []
    found_class = False

    for line in lines:
        stripped = line.strip()

        if "/*" in stripped:
            in_comment = True
        if in_comment:
            if not found_class:
                class_javadoc.append(stripped)
            if "*/" in stripped:
                in_comment = False
            continue

        if not found_class and re.match(
            r".*\b(class|interface|enum|object)\s+" + re.escape(class_name), stripped
        ):
            found_class = True
            if class_javadoc:
                for jd in class_javadoc[-5:]:
                    result.append(f"  {jd}")
            result.append(f"  {stripped}")
            result.append("")
            class_javadoc = []
            continue

        if found_class:
            if re.match(r"\s*public\s+", stripped) or re.match(r"\s*(fun|val|var|override)\s+", stripped):
                sig = stripped.rstrip("{").strip()
                result.append(f"  {sig}")

            if re.match(r"\s*public\s+static\s+final\s+", stripped):
                result.append(f"  {stripped.rstrip(';').strip()}")

    if not result or len(result) <= 2:
        return source_code

    return "\n".join(result)


# ─── 查询命令 ───────────────────────────────────────────────

def cmd_lookup_class(index: dict, class_name: str, show_source: bool = False):
    """查询指定类名（支持简单类名或全限定名）。"""
    matches = []
    if "." in class_name:
        if class_name in index["class_to_lib"]:
            matches.append(class_name)
        else:
            suffix = "." + class_name.rsplit(".", 1)[-1]
            for fqcn in index["class_to_lib"]:
                if fqcn == class_name or fqcn.endswith(suffix):
                    matches.append(fqcn)
    else:
        for fqcn in index["class_to_lib"]:
            if fqcn.endswith(f".{class_name}") or fqcn == class_name:
                matches.append(fqcn)

    if not matches:
        print(json.dumps({
            "error": f"Class not found: {class_name}",
            "suggestion": "Try --search for fuzzy matching",
        }))
        return

    results = []
    for fqcn in sorted(matches):
        info = index["class_to_lib"][fqcn]
        entry = {
            "class": fqcn,
            "library": info["lib"],
            "version": info["version"],
        }

        api = get_class_api(index, fqcn)
        if api:
            entry["source" if show_source else "api_summary"] = (
                api if show_source else parse_source_to_api_summary(api, fqcn)
            )

        results.append(entry)

    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_lookup_package(index: dict, package_name: str):
    """查询指定包下的所有类。"""
    matches = {}
    for fqcn, info in index["class_to_lib"].items():
        pkg = fqcn.rsplit(".", 1)[0] if "." in fqcn else ""
        if pkg == package_name or pkg.startswith(package_name + "."):
            matches[fqcn] = info

    if not matches:
        print(json.dumps({"error": f"Package not found: {package_name}"}))
        return

    results = [
        {"class": fqcn, "library": info["lib"], "version": info["version"]}
        for fqcn, info in sorted(matches.items())
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


def cmd_lookup_library(index: dict, lib_coord: str):
    """列出指定库的所有 public 类。"""
    classes = index["lib_to_classes"].get(lib_coord, [])
    if not classes:
        for key in index["lib_to_classes"]:
            if lib_coord in key:
                classes = index["lib_to_classes"][key]
                lib_coord = key
                break

    if not classes:
        print(json.dumps({"error": f"Library not found: {lib_coord}"}))
        return

    files = index["lib_files"].get(lib_coord, {})
    has_sources = "sources_jar" in files
    result = {
        "library": lib_coord,
        "version": files.get("version", "unknown"),
        "has_sources": has_sources,
        "class_count": len(classes),
        "classes": sorted(classes),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_search(index: dict, keyword: str):
    """模糊搜索类名。"""
    keyword_lower = keyword.lower()
    matches = []
    for fqcn, info in index["class_to_lib"].items():
        simple_name = fqcn.rsplit(".", 1)[-1] if "." in fqcn else fqcn
        if keyword_lower in simple_name.lower() or keyword_lower in fqcn.lower():
            matches.append({
                "class": fqcn,
                "library": info["lib"],
                "version": info["version"],
            })

    if not matches:
        print(json.dumps({"error": f"No matches found: {keyword}"}))
        return

    matches.sort(key=lambda x: x["class"])
    print(json.dumps(matches[:50], ensure_ascii=False, indent=2))


def cmd_stats(index: dict):
    """显示索引统计信息。"""
    libs_with_sources = sum(
        1 for files in index["lib_files"].values() if "sources_jar" in files
    )
    stats = {
        "total_classes": len(index["class_to_lib"]),
        "total_libraries": len(index["lib_to_classes"]),
        "libraries_with_sources": libs_with_sources,
        "libraries": {
            lib: len(classes)
            for lib, classes in sorted(index["lib_to_classes"].items())
        },
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Android/Gradle Dependency Class Lookup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -p /path/to/module -c com.example.StringUtils
  %(prog)s -p /path/to/module --search Toast
  %(prog)s -p /path/to/module --library com.example:utils
  %(prog)s -p /path/to/module --stats
        """,
    )
    parser.add_argument(
        "--project", "-p", required=True,
        help="Path to Android module (directory containing build.gradle or build.gradle.kts)",
    )
    parser.add_argument(
        "--gradle-cache",
        default=os.path.expanduser("~/.gradle/caches"),
        help="Gradle cache directory (default: ~/.gradle/caches)",
    )
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild index")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--class", "-c", dest="class_name", help="Lookup by class name (FQCN or simple name)")
    group.add_argument("--package", "-pkg", dest="package_name", help="List classes in package")
    group.add_argument("--library", "-lib", dest="library", help="List classes in library (groupId:artifactId)")
    group.add_argument("--search", "-s", dest="search", help="Fuzzy search class names")
    group.add_argument("--stats", action="store_true", help="Show index statistics")

    parser.add_argument("--source", action="store_true", help="Show full source instead of API summary")

    args = parser.parse_args()

    if not os.path.isdir(args.project):
        print(f"错误: 项目路径不存在: {args.project}", file=sys.stderr)
        sys.exit(1)

    index = load_or_build_index(args.project, args.gradle_cache, args.rebuild)

    if args.class_name:
        cmd_lookup_class(index, args.class_name, args.source)
    elif args.package_name:
        cmd_lookup_package(index, args.package_name)
    elif args.library:
        cmd_lookup_library(index, args.library)
    elif args.search:
        cmd_search(index, args.search)
    elif args.stats:
        cmd_stats(index)


if __name__ == "__main__":
    main()
