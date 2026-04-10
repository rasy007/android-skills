# Android Crash Analyzer

智能解析 Android 崩溃和 ANR 日志，自动识别崩溃类型并给出修复建议。

## 功能特性

- **崩溃类型识别** — 自动归类 NPE、OOM、ANR、Native Crash 等 9 种类型
- **关键帧提取** — 从堆栈中提取最相关的应用代码行
- **根因分析** — 基于异常模式给出可能的原因
- **修复建议** — 针对每种崩溃类型提供具体修复方向
- **ANR 分析** — 解析 `traces.txt`，识别主线程阻塞点和死锁
- **Native Crash** — 解析 tombstone / SIGSEGV 信号

## 前置条件

- Python 3.6+

## 安装

```bash
npx skills add --from https://github.com/rasy007/android-skills --subdir android-crash-analyzer
```

## 快速使用

```bash
# 分析崩溃日志文件
python3 scripts/crash_analyzer.py analyze crash.log

# 从stdin分析
cat logcat.txt | python3 scripts/crash_analyzer.py analyze -

# 快速识别异常类型
python3 scripts/crash_analyzer.py identify "java.lang.NullPointerException"

# 查看OOM修复指南
python3 scripts/crash_analyzer.py guide oom
```

## 输出示例

```
═══════════════════════════════════════════════
  Android 崩溃分析报告
═══════════════════════════════════════════════

类型:     NullPointerException (NPE)
严重级别:  HIGH
异常:     Attempt to invoke virtual method 'void android.widget.TextView.setText'
          on a null object reference

关键帧:
  → com.example.app.ui.HomeFragment.onViewCreated(HomeFragment.kt:42)
  → com.example.app.ui.HomeFragment.updateUI(HomeFragment.kt:67)

根因分析:
  1. View 引用在 onDestroyView 后仍被使用
  2. findViewById 返回 null（布局中未定义该 ID）
  3. Fragment 生命周期中 View 尚未创建

修复建议:
  1. 使用 ViewBinding 替代 findViewById
  2. 在 onDestroyView 中置空 binding 引用
  3. 使用 viewLifecycleOwner 感知 View 生命周期
```

## 许可

MIT
