# 完成工具 - ADS-B 轨迹数据转换工具集

## 概述

这是一个 ADS-B 轨迹数据转换工具集，用于将不同格式的轨迹数据转换为 A3H 格式报文。

## 目录结构

```
完成工具/
├── 核心代码/
│   ├── track_parameter_converter.py    # 核心转换器
│   ├── track_converter_cli.py          # 命令行入口
│   ├── csv2a3h_improved.py              # CSV→A3H CLI (改进版)
│   └── csv2a3h.py                       # CSV→A3H CLI (简化版)
├── 辅助工具/
│   ├── extract_smooth_points.py        # MAT→TXT 提取器
│   └── compare_files.py                 # A3H 文件对比工具
├── 数据文件/
│   ├── 2026-02-04.csv                  # 示例 CSV 数据
│   ├── track_20251210172235.mat        # 示例 MAT 数据
│   └── track_20251210172235_smoothPoints.txt
└── 文档/
    ├── 使用手册.md
    └── 文档分析.md
```

## 核心功能

### 1. track_parameter_converter.py

核心转换模块，包含：
- 参数类型构建 (`BaseConverter` 子类)
- 时间戳随机毫秒处理
- track_id 匹配 (7001+ 序列)
- 经纬度/速度合法性校验
- `MessageBuilder` 报文构建
- `TrackParameterConverter` 主流程

### 2. track_converter_cli.py

命令行入口，支持：
- 输入/输出路径参数
- 日志配置
- 严格模式校验
- 批量转换
- 成功率统计

### 3. csv2a3h_improved.py

CSV 转 A3H 工具 (改进版)，支持：
- 自定义输入/输出路径
- GBK 编码流式读写
- ICAO Hex 有效性校验
- 多时间戳格式 (second/ms/ns)
- `$AP` / `$AV` 报文同步输出

### 4. csv2a3h.py

CSV 转 A3H 工具 (简化版)，功能与改进版相同但更简洁，便于调试和对照。

### 5. extract_smooth_points.py

MAT 文件提取工具：
- 依赖 `scipy.io` / `numpy`
- 读取 `trackList` 中的 `smoothPointList`
- 输出可读的 `*_smoothPoints.txt` 文本

### 6. compare_files.py

文件对比工具：
- 使用 `difflib.unified_diff` 对比两份 A3H 输出
- 显示行数差异
- 用于校验不同算法或随机种子下报文一致性

## 数据流程

### 流程一：CSV → A3H

```
2026-02-04.csv → csv2a3h_improved.py → *.a3h
```

### 流程二：MAT → A3H

```
track_*.mat → extract_smooth_points.py → *_smoothPoints.txt
           → track_converter_cli.py → *.a3h
```

## 报文类型

| 报文 | 说明 |
|------|------|
| `$RD` | 雷达数据报文 |
| `$AP` | 位置信息报文 |
| `$AV` | 速度信息报文 |

## 使用示例

```bash
# CSV 转 A3H
python csv2a3h_improved.py input.csv output.a3h

# MAT 转 TXT 再转 A3H
python extract_smooth_points.py track.mat
python track_converter_cli.py track_smoothPoints.txt output.a3h

# 对比输出
python compare_files.py output1.a3h output2.a3h
```

## 后续建议

1. 运行 `csv2a3h_improved.py` 与 `track_converter_cli.py`，确认输出 `.a3h` 报文结构符合下游需求
2. 如需更多报文格式，可在 `track_parameter_converter.py` 中注册新的 `MessageFormat`
