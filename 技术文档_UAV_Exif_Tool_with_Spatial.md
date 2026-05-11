# UAV Exif信息提取工具 - 技术文档与操作摘要

## 目录

1. [程序概述](#1-程序概述)
2. [程序结构](#2-程序结构)
3. [核心功能模块](#3-核心功能模块)
4. [关键算法实现](#4-关键算法实现)
5. [数据格式与存储](#5-数据格式与存储)
6. [空间索引功能](#6-空间索引功能)
7. [技术规格](#7-技术规格)
8. [对话操作摘要](#8-对话操作摘要)
9. [已知问题与限制](#9-已知问题与限制)

---

## 1. 程序概述

### 1.1 程序功能

UAV Exif信息提取工具是一款用于从无人机（UAV）拍摄的照片和视频中提取GPS、姿态等元数据的图形化应用程序。

### 1.2 支持的数据源

| 数据源 | 功能描述 |
|--------|----------|
| **photo** | 从JPG照片中提取Exif/XMP数据 |
| **video_snapshot** | 从MP4视频中提取快照帧并附加GPS数据 |
| **video_exif** | 从SRT字幕文件中解析GPS轨迹数据 |

### 1.3 输出格式

- CSV（UTF-8 BOM编码）
- XML
- Excel (XLSX)
- Shapefile（ArcGIS兼容）

---

## 2. 程序结构

### 2.1 类结构

```
UAVExifTool (主类)
├── __init__() - 初始化
├── _create_widgets() - 创建GUI组件
├── _create_process_tab() - 数据处理页面
├── _create_spatial_tab() - 空间索引查询页面
├── _browse_input() - 浏览输入路径
├── _browse_output() - 浏览输出路径
├── _start_process() - 启动处理
├── _stop_process() - 停止处理
├── _clear_log() - 清空日志
├── _log() - 写入日志
├── _update_progress() - 更新进度
├── _process_files() - 文件处理主流程
├── _process_photos() - 照片处理
├── _read_exif_binary_fast() - 二进制EXIF快速读取
├── _parse_exif_data() - 解析EXIF数据
├── _find_gps_info() - 查找GPS信息
├── _parse_gps_info() - 解析GPS信息
├── _parse_gps_coordinate() - 解析GPS坐标
├── _parse_gps_altitude() - 解析GPS高度
├── _parse_xmp_fast() - 快速解析XMP数据
├── _list_to_dict() - 列表转字典
├── _process_video_snapshot() - 视频快照处理
├── _write_jpg_exif() - 写入JPG的EXIF信息
├── _parse_srt_file() - 解析SRT文件
├── _process_video_exif() - 视频EXIF处理
├── _save_results() - 保存结果
├── _write_shapefile_pyshp() - 使用pyshp生成Shapefile
├── _write_shapefile_line() - 使用线要素生成Shapefile
├── _write_shapefile_fallback() - 备用Shapefile生成
├── _build_spatial_index() - 构建KD树空间索引
└── _execute_spatial_query() - 执行空间查询
```

### 2.2 文件布局

```
项目根目录/
├── src/
│   └── UAV_Exif_Tool_with_Spatial.py  (主程序)
├── 第一次无人机数据/                    (默认输入)
├── 老师给的视频及信息/                  (视频数据)
├── 输出结果/                           (默认输出)
└── .venv/                             (虚拟环境)
```

---

## 3. 核心功能模块

### 3.1 照片处理 (_process_photos)

**流程：**
1. 扫描输入目录下的所有JPG文件
2. 使用ThreadPoolExecutor并行读取
3. 调用`_read_exif_binary_fast()`提取Exif/XMP数据
4. 返回结果列表

**性能指标：**
- 处理速度：< 0.001秒/文件（已优化至约0.42ms/文件）

### 3.2 视频快照处理 (_process_video_snapshot)

**流程：**
1. 查找同名的SRT和MP4文件
2. 解析SRT文件获取GPS数据
3. 使用OpenCV读取视频帧
4. 按时间戳匹配GPS数据并写入JPG的Exif信息
5. 保存快照到输出目录

### 3.3 视频EXIF处理 (_process_video_exif)

**流程：**
1. 解析SRT文件
2. 提取每帧的GPS和时间戳信息
3. 为每个GPS记录生成虚拟文件名
4. 数据用于空间索引构建

---

## 4. 关键算法实现

### 4.1 二进制EXIF解析 (_read_exif_binary_fast)

```python
def _read_exif_binary_fast(self, file_path):
    """直接二进制读取Exif信息（优化版本）"""
    result = [0.0] * 9  # 9个字段： yaw, pitch, roll, gimbal_*, lat, lon, alt

    with open(file_path, 'rb') as f:
        data = f.read(65536)  # 读取前64KB（足够包含Exif/XMP）

    # 解析逻辑：
    # 1. 检查JPEG头 (0xFFD8)
    # 2. 查找APP1段 (0xFFE1)
    # 3. 解析Exif TIF头和IFD
    # 4. 查找GPS IFD (Tag 0x8825)
    # 5. 解析XMP数据（用于姿态角）
```

### 4.2 GPS坐标解析 (_parse_gps_coordinate)

SRT文件GPS格式示例：
```
[latitude: 28.237419] [longitude: 112.946843] [rel_alt: 250.365 abs_alt: 284.435]
```

注意：程序解析使用的是 `rel_alt`（相对高度），而非 `abs_alt`（绝对高度）。

### 4.3 空间索引构建 (_build_spatial_index)

```python
def _build_spatial_index(self):
    """构建KD树空间索引"""
    coords = []
    valid_data = []
    for d in self.spatial_data:
        lat = d.get('GPS纬度', 0)
        lon = d.get('GPS经度', 0)
        alt = d.get('GPS高度', 0)
        if lat != 0 and lon != 0:
            coords.append([lon, lat, alt])  # 注意：顺序是[lon, lat, alt]
            valid_data.append(d)

    self.spatial_coords = np.array(coords)
    self.spatial_data = valid_data
    self.spatial_index = cKDTree(self.spatial_coords)  # scipy.spatial.cKDTree
```

---

## 5. 数据格式与存储

### 5.1 数据字段

| 字段名 | 类型 | 描述 |
|--------|------|------|
| 文件名 | string | 来源文件名 |
| 无人机偏航角 | float | FlightYawDegree |
| 无人机俯仰角 | float | FlightPitchDegree |
| 无人机翻滚角 | float | FlightRollDegree |
| 云台偏航角 | float | GimbalYawDegree |
| 云台俯仰角 | float | GimbalPitchDegree |
| 云台翻滚角 | float | GimbalRollDegree |
| GPS纬度 | float | 十进制度数 |
| GPS经度 | float | 十进制度数 |
| GPS高度 | float | 相对高度(m) |

### 5.2 Shapefile字段映射

| DBF字段 | 全称 |
|---------|------|
| YAW | 无人机偏航角 |
| PITCH | 无人机俯仰角 |
| ROLL | 无人机翻滚角 |
| GYAW | 云台偏航角 |
| GPITCH | 云台俯仰角 |
| GROLL | 云台翻滚角 |
| LAT | GPS纬度 |
| LON | GPS经度 |
| ALT | GPS高度 |

**注意：** Shapefile的DBF字段名限制为10字符，因此使用缩写名称。

### 5.3 坐标系

Shapefile使用WGS 84坐标系（EPSG:4326）：
```
GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],
PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]
```

---

## 6. 空间索引功能

### 6.1 KD-Tree实现

使用 `scipy.spatial.cKDTree` 实现3D空间索引：

```python
from scipy.spatial import cKDTree
tree = cKDTree(coordinates)  # coordinates: [(lon, lat, alt), ...]
```

### 6.2 查询模式

**K最近邻查询 (KNN)**
```python
distances, indices = tree.query(query_point, k=k)
```

**范围查询 (Range Query)**
```python
indices = tree.query_ball_point(query_point, r=radius)
```

### 6.3 3D距离计算

KD-Tree使用欧几里得距离：
```
distance = sqrt((lon1-lon2)^2 + (lat1-lat2)^2 + (alt1-alt2)^2)
```

### 6.4 GUI查询参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 查询经度 | 112.946843 | SRT数据边界值 |
| 查询纬度 | 28.237419 | SRT数据边界值 |
| 查询高度 | 284.4 | abs_alt值 |
| K值 | 5 | 最近邻数量 |
| 半径 | 0.001度 | 范围查询半径 |

---

## 7. 技术规格

### 7.1 依赖库

| 库名 | 版本 | 用途 |
|------|------|------|
| Python | 3.13+ | 运行时 |
| numpy | - | 数值计算 |
| scipy | - | KD-Tree空间索引 |
| PIL (Pillow) | - | 图像处理 |
| openpyxl | - | Excel文件生成 |
| pyshp | - | Shapefile生成 |
| piexif | - | EXIF读写 |
| opencv-python | - | 视频处理 |

### 7.2 路径处理

**修复前的硬编码路径：**
```python
sys.path.append(r'd:\无人机数据\.venv\Lib\site-packages')
self.input_path.insert(0, r'd:\无人机数据\第一次无人机数据')
```

**修复后的相对路径：**
```python
# sys.path - 使用脚本位置的父目录下的.venv
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(script_dir, '..', '.venv', 'Lib', 'site-packages'))

# 默认路径 - 使用相对于脚本的路径
project_root = os.path.dirname(script_dir)
self.input_path.insert(0, os.path.join(project_root, '第一次无人机数据'))
```

### 7.3 性能指标

| 指标 | 目标 | 实际 |
|------|------|------|
| 单文件处理速度 | < 0.001秒 | ~0.00042秒 |
| 空间索引构建 | - | ~5ms (1832点) |
| KNN查询 | - | < 1ms |
| 范围查询 | - | < 1ms |

---

## 8. 对话操作摘要

### 8.1 已完成的任务

| 序号 | 任务 | 状态 | 说明 |
|------|------|------|------|
| 1 | 扫描项目空间索引功能 | ✅ | 确认项目未实现空间索引 |
| 2 | 实现KD-Tree空间索引 | ✅ | 使用scipy.spatial.cKDTree |
| 3 | 修复video_exif索引错误 | ✅ | 修正返回数据与spatial_data冲突 |
| 4 | 修复video_snapshot GPS缺失 | ✅ | 添加SRT GPS匹配逻辑 |
| 5 | 修复Excel数据丢失 | ✅ | 添加数据类型转换 |
| 6 | 修复Shapefile ArcGIS兼容性 | ✅ | 缩短字段名至10字符内 |
| 7 | 优化照片处理性能 | ✅ | 降至0.42ms/文件 |
| 8 | 文件结构重组 | ✅ | 分为src/和tests/目录 |
| 9 | 修复硬编码路径依赖 | ✅ | 改为相对路径 |

### 8.2 解决的Bug

| Bug描述 | 根因 | 解决方案 |
|---------|------|----------|
| video_exif "list index out of range" | 返回数据覆盖spatial_data | 修改处理逻辑保留原数据 |
| video_snapshot GPS数据为空 | OpenCV提取帧不含元数据 | 添加`_get_gps_from_srt`方法 |
| Excel前6列数据丢失 | 数据类型转换问题 | 添加float强制转换 |
| Shapefile无法在ArcGIS加载 | DBF字段名超10字符 | 使用缩写字段名 |
| 范围查询总返回0结果 | 高度维度不匹配 | 详见8.3已知问题 |

### 8.3 已知问题与限制

**问题：范围查询返回0结果**

| 项目 | 值 |
|------|-----|
| **现象** | 无论半径设为多少，范围查询总返回0结果 |
| **根因** | SRT解析使用`rel_alt`(~250m)，但GUI默认查询高度为284.4m |
| **高度差** | 约34米 |
| **3D距离** | √(0² + 0² + 34²) = 34度 >> 0.004度半径 |
| **影响** | query_ball_point使用3D欧几里得距离，34度远超半径范围 |
| **状态** | **未修复** - 需用户确认方案 |

**建议的修复方案：**

| 方案 | 描述 | 优缺点 |
|------|------|--------|
| 方案1 | 修改SRT解析使用`abs_alt` | ✅ 一劳永逸 ❌ 可能影响其他功能 |
| 方案2 | 修改GUI默认高度为~250 | ✅ 简单 ❌ 不直观 |
| 方案3 | 改为2D查询（忽略高度） | ✅ 符合直觉 ❌ 丢失高度信息 |
| 方案4 | 添加高度源选项 | ✅ 灵活 ❌ 需UI修改 |

---

## 9. 已知问题与限制

### 9.1 待修复问题

1. **范围查询高度维度问题**
   - SRT解析使用`rel_alt`，但查询使用`abs_alt`级别的高度
   - 需选择并实施一种修复方案

2. **建议操作**
   - 用户确认修复方案后实施

### 9.2 使用限制

1. 仅支持JPG图像
2. 仅支持MP4视频 + SRT字幕格式
3. Shapefile字段名限制为10字符
4. 空间查询为3D欧几里得距离

---

## 附录：文件变更记录

### A. 主要版本

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | - | 初始版本 |
| v1.1 (当前) | 2026-04-20 | 添加KD-Tree空间索引、修复多项Bug、优化性能、修复路径依赖 |

### B. 代码行数

- 主程序：约1155行
- 类方法：32个
- 无测试代码（测试代码位于tests/目录）

---

*文档生成时间: 2026-04-20*
*程序版本: UAV Exif Tool with Spatial Index v1.1*