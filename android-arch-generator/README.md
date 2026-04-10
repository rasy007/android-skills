# Android Architecture Generator

输入 Feature 名称，自动生成 MVVM / MVI / Clean Architecture 代码骨架。

## 功能特性

- **MVVM** — ViewModel + LiveData/StateFlow + Repository
- **MVI** — Intent + State + SideEffect + Reducer (单向数据流)
- **Clean Architecture** — UseCase + Repository + Entity (分层架构)
- **DI 支持** — 自动生成 Hilt / Koin 配置
- **Kotlin 代码** — 生成现代 Kotlin 代码，支持协程和 Flow

## 前置条件

- Python 3.6+

## 安装

```bash
npx skills add --from https://github.com/rasy007/android-skills --subdir android-arch-generator
```

## 快速使用

```bash
# 生成 MVVM 架构的 Home 页面
python3 scripts/arch_generator.py generate Home \
    --pattern mvvm \
    --package com.example.app.home \
    --output ./generated

# 生成 MVI 架构
python3 scripts/arch_generator.py generate Home \
    --pattern mvi \
    --package com.example.app.home

# 查看架构模式对比
python3 scripts/arch_generator.py patterns
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `feature_name` | Feature 名称（PascalCase） | 必填 |
| `--pattern` | 架构模式 (mvvm/mvi/clean) | mvvm |
| `--package` | 包名 | com.example.app |
| `--output` | 输出目录 | ./generated |
| `--flow` | 数据流方式 (livedata/stateflow) | livedata |
| `--di` | DI框架 (hilt/koin/none) | hilt |

## 许可

MIT
