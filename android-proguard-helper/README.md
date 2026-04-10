# Android ProGuard/R8 Helper

自动扫描源码并生成 ProGuard/R8 混淆规则，内置 20+ 常见库规则模板。

## 功能特性

- **智能扫描** — 检测反射调用、`@SerializedName`、JNI 方法、四大组件
- **规则生成** — 根据扫描结果自动生成精确的 keep 规则
- **库模板** — 内置 Gson、Retrofit、OkHttp、Room、Glide、EventBus 等 20+ 库的规则
- **规则检查** — 分析现有 `proguard-rules.pro` 中的潜在问题和冗余
- **语法参考** — ProGuard/R8 规则语法完整速查

## 前置条件

- Python 3.6+

## 安装

```bash
npx skills add --from https://github.com/rasy007/android-skills --subdir android-proguard-helper
```

## 快速使用

```bash
# 扫描模块源码，生成keep规则
python3 scripts/proguard_analyzer.py scan /path/to/module

# 获取Gson的混淆规则
python3 scripts/proguard_analyzer.py template gson

# 检查现有规则文件
python3 scripts/proguard_analyzer.py check /path/to/proguard-rules.pro
```

## 扫描检测项

| 检测类型 | 检测内容 | 生成规则 |
|---------|---------|---------|
| 反射 | `Class.forName`、`getMethod`、`getDeclaredField` | `-keep class <target>` |
| 序列化 | `@SerializedName`、`Serializable`、`Parcelable` | `-keepclassmembers` |
| JNI | `native` 方法声明 | `-keepclasseswithmembers *native*` |
| 四大组件 | AndroidManifest 中的组件声明 | `-keep class <component>` |
| 枚举 | `enum` 类 | `-keepclassmembers enum *` |
| WebView | `@JavascriptInterface` | `-keepclassmembers *javascript*` |

## 支持的库模板

Gson / Retrofit / OkHttp / Room / Glide / EventBus / Dagger / Hilt /
RxJava / Coroutines / Moshi / Jackson / Kotlin Serialization /
Firebase / Crashlytics / Navigation / WorkManager / Paging / DataBinding

## 许可

MIT
