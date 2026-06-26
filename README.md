# File Sort Tool

<div align="center">

一个面向 Windows 桌面的文件整理工具。

把杂乱目录按文件类型或按月份快速分类，同时保留预览、搜索、撤销和整理报告这些真正实用的细节。

![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square)
![CustomTkinter](https://img.shields.io/badge/UI-CustomTkinter-1f6feb?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0a66c2?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

</div>

## Overview

`File Sort Tool` 从一个简单的分类脚本起步，逐步做成了一个可直接使用的桌面整理器。它不仅能移动文件，还会在整理前给出分类预览，在整理后保留历史和报告，并支持把上一次整理撤销回来。

如果你经常面对下载目录、桌面、临时资料夹这种“东西都在，但越来越难找”的场景，这个项目就是为这种日常混乱准备的。

## Highlights

| Feature | Description |
| --- | --- |
| 分类整理 | 支持按文件类型或按月份整理文件 |
| 整理预览 | 在执行前显示当前目录下各分类数量 |
| 排除规则 | 可排除扩展名、文件名、完整路径或整个文件夹 |
| 文件搜索 | 内置快速搜索，便于定位文件和目录 |
| 撤销整理 | 可恢复上一次整理前的文件位置 |
| 拆除文件夹 | 可将子文件夹内容提到根目录并清理空文件夹 |
| 整理报告 | 展示整理时间、总数、分类明细与耗时 |
| 桌面体验 | 支持主题切换、进度显示和历史记录 |

## Interface Focus

这个项目的重点不是“把文件挪走”这么简单，而是把整理动作做得更可控：

- 先看预览，再决定是否开始整理。
- 整理后可以查看报告，不用靠记忆回想做了什么。
- 如果这次整理不满意，可以直接撤销。
- 即使目录已经整理过，也会尽量避免重复统计和重复分类。

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the desktop app

```bash
python file_sort.py
```

如果当前环境已经具备依赖，也可以直接使用：

```bash
run_file_sort.bat
```

## Main Workflow

1. 选择需要整理的目标目录。
2. 选择分类方式：按文件类型或按月份。
3. 查看分类预览，确认本次整理范围。
4. 根据需要设置排除规则。
5. 开始整理，并观察进度与状态提示。
6. 整理完成后查看报告，或在必要时执行撤销。

## Project Structure

```text
file_sort.py                 主程序，包含 UI 与核心整理逻辑
tests/test_file_sort_core.py 核心行为测试
run_file_sort.bat            快速启动脚本
file_sort.spec               PyInstaller 打包配置
CHANGELOG.md                 更新日志
main.py                      早期原型脚本
```

## Recent Improvements

最近一轮更新主要集中在稳定性和可用性上：

- 修复了预览统计会重复计入已分类文件的问题。
- 修复了搜索缓存刷新不及时的问题。
- 统一了分类目录识别逻辑，降低重复整理时的误判风险。
- 补充了核心回归测试，覆盖分类、预览和搜索关键行为。

详细记录见 [CHANGELOG.md](./CHANGELOG.md)。

## Packaging

项目提供了 `file_sort.spec`，可以直接用于 PyInstaller 打包：

```bash
pyinstaller file_sort.spec
```

## Notes

- 当前主要面向 Windows 使用场景。
- `main.py` 保留为项目早期脚本版本，日常使用请以 `file_sort.py` 为主。
- 如果你想把它继续扩展成完整的个人文件管理工具，这个版本已经具备比较好的基础骨架。
