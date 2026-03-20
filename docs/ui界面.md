# UI界面设计

## 工具栈
Python + PySide6

## 目录结构
```
fst-tools/
├── src/
│   ├── csv2a3h.py                   # CSV转A3H工具
│   ├── extract_smooth_points.py     # MAT文件提取平滑点
│   ├── track_parameter_converter.py # 核心转换引擎
│   └── merge_messages.py            # 报文合并工具
├── cli/
│   └── track_converter_cli.py       # Track转换CLI
└── TEMP/                            # 暂存文件夹（程序运行时创建）
```

## 功能需求

### 1. 文件选择
设计一个 `addPath` 按钮，可以识别 `.csv` 和 `.mat` 文件。

**处理流程：**

| 输入类型 | 调用程序 | 输出消息类型 | 暂存文件 |
|---------|---------|-------------|---------|
| CSV文件 | `src/csv2a3h.py` | `$AP` (ADS-B位置) | `*.a3h` |
| MAT文件 | `src/extract_smooth_points.py` + `cli/track_converter_cli.py` | `$RD` (雷达数据) | `*.a3h` |

**CSV格式要求：**
- 编码：GBK
- 第1列：6位ICAO HEX码
- 第2列：纬度
- 第3列：经度
- 第4列：航向
- 第5列：高度(英尺)
- 第6列：速度
- 第10列：时间戳 (格式: `yyyy/mm/dd HH:MM`)
- 第16列：英尺速度

**MAT格式要求：**
- 包含 `trackList` 变量
- 每个track包含 `smoothPointList` 字段
- 包含 BatchNo, time, range, vr, az, lat, lon 等字段

### 2. 时间识别
在选中CSV或MAT文件后，解析文件获取：
- 最早报文时间
- 最晚报文时间

**时间显示格式：**
- CSV: 从第10列解析，格式 `yyyy-mm-dd-HH-MM-SS`
- MAT: 从smoothPointList中提取time字段

### 3. 运行按钮
点击运行按钮后执行以下操作：

1. **合并 TEMP 目录中的所有 .a3h 文件**
   - 读取所有 .a3h 文件
   - 按时间戳排序
   - 合并为一个文件

2. **添加报文头**
   使用 `merge_messages.py` 中的 `add_header()` 函数，添加以下格式的报文头：
   ```
   #VERSION 2
   #HOME [经度] [纬度] [高度]
   #TIME [采样时间]
   ```
   - 从第一条 `$AP` 报文中自动提取经纬度和时间
   - 高度单位为米

3. **输出文件**
   - 输出文件名为 `Output.a3h`
   - 保存在用户指定目录或当前目录

4. **清理**
   - 删除 TEMP 文件夹中的所有临时文件

## 消息格式参考

| 类型 | 格式 | 说明 |
|-----|------|-----|
| `$AP` | `$AP,icao_hex,yyyy-mm-dd-HH-MM-SS,ms,ns,lon,lat,altitude,...` | ADS-B位置 |
| `$RD` | `$RD,track_id,time_ms,...,lon,lat,...,range,az,...` | 雷达数据 |
| `$AV` | `$AV,icao_hex,yyyy-mm-dd-HH-MM-SS,ms,ns,speed,heading,...` | ADS-B速度(已禁用) |

## 依赖
- Python 3.x
- PySide6 (UI框架)
- scipy, numpy (MAT文件处理)
- GBK编码支持

## 运行方式

### 安装依赖
```bash
pip install PySide6 scipy numpy
```

### 启动UI
```bash
# 方式1: 使用python模块方式
python -m ui.main_window

# 方式2: 直接运行main_window.py
python ui/main_window.py
```

### 使用说明
1. 点击"添加文件"按钮，选择CSV或MAT文件
2. 可以在列表中查看添加的文件和时间范围
3. 点击"运行"按钮执行转换
4. 转换完成后，Output.a3h 文件将生成在当前目录

### 目录结构 (更新后)
```
fst-tools/
├── src/
│   ├── csv2a3h.py                   # CSV转A3H工具
│   ├── extract_smooth_points.py     # MAT文件提取平滑点
│   ├── track_parameter_converter.py # 核心转换引擎
│   └── merge_messages.py            # 报文合并工具
├── ui/                              # UI模块
│   ├── __init__.py
│   ├── converter.py                 # 转换逻辑封装
│   └── main_window.py               # PySide6主窗口
├── cli/
│   └── track_converter_cli.py       # Track转换CLI
└── docs/
    └── ui界面.md
```