# 完成工具 - ADS-B 轨迹数据转换工具集

## 概述

这是一个 ADS-B 轨迹数据转换工具集，用于将不同格式的轨迹数据转换为 A3H 格式报文。

## 目录结构

```
fst-tools/
├── src/
│   ├── track_parameter_converter.py    # 核心转换器
│   ├── csv2a3h.py                     # CSV→A3H 转换器
│   └── merge_messages.py              # 报文合并工具
├── cli/
│   └── track_converter_cli.py          # 命令行入口
├── utils/
│   ├── extract_smooth_points.py        # MAT→TXT 提取器
│   └── compare_files.py                # A3H 文件对比工具
├── data/sample/                        # 示例数据
└── docs/                              # 文档
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

### 3. csv2a3h.py

CSV 转 A3H 工具，支持：
- 自定义输入/输出路径
- GBK 编码流式读写
- ICAO Hex 有效性校验
- 多时间戳格式 (second/ms/ns)
- `$AP` / `$AV` 报文同步输出

### 4. extract_smooth_points.py

MAT 文件提取工具：
- 依赖 `scipy.io` / `numpy`
- 读取 `trackList` 中的 `smoothPointList`
- 输出可读的 `*_smoothPoints.txt` 文本

### 5. merge_messages.py

报文合并工具，支持两个子命令：

**merge 子命令** - 合并 ADS-B 和雷达报文
- 合并 ADS-B 报文 ($AP/$AV) 和雷达报文 ($RD)
- 按时间戳排序
- 支持自定义参考日期

**add-header 子命令** - 添加报文头
- 为报文文件添加文件头信息
- 自动从第一条 AP 报文获取经纬度和时间
- 支持自定义参数

输出格式：
```
#VERSION 2
#HOME [经度] [纬度] [高度]
#TIME [采样时间]
```

### 6. compare_files.py

文件对比工具：
- 使用 `difflib.unified_diff` 对比两份 A3H 输出
- 显示行数差异
- 用于校验不同算法或随机种子下报文一致性

## 数据流程

### 流程一：CSV → A3H

```
2026-02-04.csv → csv2a3h.py → *.a3h
```

### 流程二：MAT → A3H

```
track_*.mat → extract_smooth_points.py → *_smoothPoints.txt
           → track_converter_cli.py → *.a3h
```

## 报文类型

| 报文 | 说明 |
|------|------|
| `$RD` | 雷达数据报文 (track_id, 时间, 距离, 速度, 方位, 经纬度) |
| `$AP` | ADS-B 位置信息报文 (icao_hex, 时间, 经纬度, 高度) |

## 使用示例

```bash
# CSV 转 A3H
python src/csv2a3h.py input.csv output.a3h

# MAT 转 TXT 再转 A3H
python src/extract_smooth_points.py track.mat
python cli/track_converter_cli.py track_smoothPoints.txt output.a3h

# 合并 ADS-B 和雷达报文
python src/merge_messages.py merge adsb.a3h radar.a3h merged.a3h

# 为报文文件添加报文头 (自动获取参数)
python src/merge_messages.py add-header merged.a3h

# 为报文文件添加报文头 (自定义参数)
python src/merge_messages.py add-header merged.a3h --lon 121.9 --lat 24.62 --alt 6400 --time 2026-02-04-17-13-30 --ms 790

# 对比输出
python utils/compare_files.py output1.a3h output2.a3h
```

## 后续建议

1. 运行 `csv2a3h.py` 与 `track_converter_cli.py`，确认输出 `.a3h` 报文结构符合下游需求
2. 如需更多报文格式，可在 `track_parameter_converter.py` 中注册新的 `MessageFormat`
