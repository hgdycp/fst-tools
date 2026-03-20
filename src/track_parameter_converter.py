#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track参数转换模块 v2.0.0
功能：将track参数转换为报文格式
遵循参数转换手册规定的映射规则、数据类型转换标准及格式要求

更新日志:
v2.0.0 (2026-03-15):
  - 新增航迹编号(track_id)字段支持
  - 更新报文格式，包含航迹编号
  - 添加航迹编号格式验证
"""

import logging
import os
import random
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time as datetime_time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


class ParameterType(Enum):
    TRACK_ID = "track_id"
    TIME = "time"
    RANGE = "range"
    VELOCITY = "vr"
    AZIMUTH = "az"
    LATITUDE = "lat"
    LONGITUDE = "lon"


class ConversionError(Exception):
    """转换错误异常"""
    def __init__(self, param_name: str, value: Any, message: str):
        self.param_name = param_name
        self.value = value
        self.message = message
        super().__init__(f"参数 '{param_name}' 转换失败 (值: {value}): {message}")


class ValidationError(Exception):
    """校验错误异常"""
    def __init__(self, param_name: str, value: Any, message: str):
        self.param_name = param_name
        self.value = value
        self.message = message
        super().__init__(f"参数 '{param_name}' 校验失败 (值: {value}): {message}")


@dataclass
class ParameterDefinition:
    """参数定义"""
    name: str
    source_column: int
    param_type: ParameterType
    required: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    precision: int = 8
    description: str = ""
    converter: Optional[Callable] = None
    validator: Optional[Callable] = None


@dataclass
class TrackPoint:
    """轨迹点数据"""
    track_id: int = 0
    time_raw: float = 0.0
    range_val: float = 0.0
    velocity: float = 0.0
    azimuth: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    time_ms: int = 0
    raw_data: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ConversionResult:
    """转换结果"""
    success: bool
    message: str
    track_point: Optional[TrackPoint] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class MessageFormat:
    """报文格式定义"""
    name: str
    template: str
    field_order: List[str]
    field_types: Dict[str, type]


class BaseConverter(ABC):
    """转换器基类"""
    
    @abstractmethod
    def convert(self, value: Any) -> Any:
        """转换值"""
        pass
    
    @abstractmethod
    def validate(self, value: Any) -> Tuple[bool, str]:
        """校验值"""
        pass


class TimeConverter(BaseConverter):
    """时间转换器
    将时间戳转换为从当天0点开始的毫秒数
    输入格式：类似MATLAB的时间戳（小数天）
    毫秒部分进行随机分布，每个记录都有独立的随机值
    """
    
    MATLAB_DATETIME_OFFSET = 719529
    
    def __init__(self, reference_date: Optional[datetime] = None):
        self.reference_date = reference_date
        self._date_cache: Dict[str, datetime] = {}
    
    def convert(self, value: Union[float, str]) -> int:
        """将MATLAB时间戳转换为当天0点开始的毫秒数，并随机分布毫秒部分"""
        try:
            if isinstance(value, str):
                value = float(value)
            
            matlab_days = float(value)
            
            python_datetime = datetime.fromordinal(int(matlab_days) + self.MATLAB_DATETIME_OFFSET)
            fractional_day = matlab_days - int(matlab_days)
            seconds_in_day = fractional_day * 86400
            microseconds = int((seconds_in_day - int(seconds_in_day)) * 1_000_000)
            python_datetime = python_datetime.replace(
                hour=int(seconds_in_day // 3600),
                minute=int((seconds_in_day % 3600) // 60),
                second=int(seconds_in_day % 60),
                microsecond=microseconds
            )
            
            midnight = python_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            delta = python_datetime - midnight
            base_milliseconds = int(delta.total_seconds() * 1000)
            
            base_seconds = base_milliseconds // 1000
            random_ms = random.randint(0, 999)
            random_milliseconds = base_seconds * 1000 + random_ms
            
            logger.debug(f"时间转换: {value} -> {random_milliseconds}ms (原始: {base_milliseconds}ms, 日期: {python_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')})")
            
            return random_milliseconds
            
        except (ValueError, TypeError, OverflowError) as e:
            raise ConversionError("time", value, f"时间转换失败: {str(e)}")
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """校验时间值"""
        if value is None:
            return False, "时间值不能为空"
        
        try:
            if isinstance(value, str):
                value = float(value)
            
            if not isinstance(value, (int, float)):
                return False, f"时间值类型错误，期望数字类型，实际为 {type(value).__name__}"
            
            if value < 0:
                return False, "时间值不能为负数"
            
            return True, ""
            
        except (ValueError, TypeError) as e:
            return False, f"时间值格式错误: {str(e)}"
    
    def format_time_string(self, milliseconds: int, date: Optional[datetime] = None) -> str:
        """格式化时间为字符串 (yyyy-mm-dd HH:MM:SS.FFF)"""
        if date is None:
            date = datetime.now()
        
        total_seconds = milliseconds / 1000.0
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = total_seconds % 60
        
        time_obj = date.replace(
            hour=hours,
            minute=minutes,
            second=int(seconds),
            microsecond=int((seconds - int(seconds)) * 1_000_000)
        )
        
        return time_obj.strftime("%Y-%m-%d %H:%M:%S.") + f"{int((seconds % 1) * 1000):03d}"


class NumericConverter(BaseConverter):
    """数值转换器"""
    
    def __init__(
        self,
        precision: int = 8,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_negative: bool = True
    ):
        self.precision = precision
        self.min_value = min_value
        self.max_value = max_value
        self.allow_negative = allow_negative
    
    def convert(self, value: Union[float, str, int]) -> float:
        """转换数值"""
        try:
            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ConversionError("numeric", value, "数值不能为空字符串")
                value = float(value)
            
            result = round(float(value), self.precision)
            
            logger.debug(f"数值转换: {value} -> {result} (精度: {self.precision})")
            
            return result
            
        except (ValueError, TypeError) as e:
            raise ConversionError("numeric", value, f"数值转换失败: {str(e)}")
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """校验数值"""
        if value is None:
            return False, "数值不能为空"
        
        try:
            if isinstance(value, str):
                if not value.strip():
                    return False, "数值不能为空字符串"
                value = float(value)
            
            num_value = float(value)
            
            if not self.allow_negative and num_value < 0:
                return False, "数值不能为负数"
            
            if self.min_value is not None and num_value < self.min_value:
                return False, f"数值 {num_value} 小于最小值 {self.min_value}"
            
            if self.max_value is not None and num_value > self.max_value:
                return False, f"数值 {num_value} 大于最大值 {self.max_value}"
            
            return True, ""
            
        except (ValueError, TypeError) as e:
            return False, f"数值格式错误: {str(e)}"


class RangeConverter(NumericConverter):
    """距离转换器"""
    
    def __init__(self):
        super().__init__(precision=8, min_value=0, allow_negative=False)


class VelocityConverter(NumericConverter):
    """速度转换器"""
    
    def __init__(self):
        super().__init__(precision=8, allow_negative=True)


class AzimuthConverter(NumericConverter):
    """方位角转换器"""
    
    def __init__(self):
        super().__init__(precision=8, min_value=0, max_value=360, allow_negative=False)
    
    def convert(self, value: Union[float, str, int]) -> float:
        result = super().convert(value)
        if result >= 360:
            result = result % 360
        return result


class LatitudeConverter(NumericConverter):
    """纬度转换器"""
    
    def __init__(self):
        super().__init__(precision=8, min_value=-90, max_value=90, allow_negative=True)
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        is_valid, message = super().validate(value)
        if is_valid:
            num_value = float(value) if isinstance(value, str) else value
            if num_value < -90 or num_value > 90:
                return False, f"纬度值 {num_value} 超出有效范围 [-90, 90]"
        return is_valid, message


class LongitudeConverter(NumericConverter):
    """经度转换器"""
    
    def __init__(self):
        super().__init__(precision=8, min_value=-180, max_value=180, allow_negative=True)
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        is_valid, message = super().validate(value)
        if is_valid:
            num_value = float(value) if isinstance(value, str) else value
            if num_value < -180 or num_value > 180:
                return False, f"经度值 {num_value} 超出有效范围 [-180, 180]"
        return is_valid, message


class TrackIdConverter(BaseConverter):
    """航迹编号转换器
    
    航迹编号格式: [编号]
    示例: [20106], [20119] -> [7001], [7002]
    将5位航迹号映射为70开头的四位数字
    """
    
    TRACK_ID_PATTERN = re.compile(r'^\[(\d+)\]$')
    MIN_TRACK_ID = 1
    MAX_TRACK_ID = 99999
    
    def __init__(self):
        self._track_id_map: Dict[int, int] = {}
        self._next_track_id = 7001
    
    def convert(self, value: Union[str, int]) -> int:
        """将航迹编号转换为整数
        
        Args:
            value: 航迹编号，可以是 "[20106]" 格式的字符串或整数
            
        Returns:
            int: 转换后的航迹编号（70开头的四位数字）
        """
        try:
            original_track_id = None
            
            if isinstance(value, int):
                original_track_id = value
            
            elif isinstance(value, str):
                value = value.strip()
                match = self.TRACK_ID_PATTERN.match(value)
                if match:
                    original_track_id = int(match.group(1))
                else:
                    try:
                        original_track_id = int(value)
                    except ValueError:
                        raise ConversionError("track_id", value, "航迹编号格式错误，期望格式: [编号] 或纯数字")
            
            else:
                raise ConversionError("track_id", value, f"不支持的类型: {type(value).__name__}")
            
            if original_track_id not in self._track_id_map:
                self._track_id_map[original_track_id] = self._next_track_id
                logger.debug(f"航迹编号映射: {original_track_id} -> {self._next_track_id}")
                self._next_track_id += 1
            
            new_track_id = self._track_id_map[original_track_id]
            logger.debug(f"航迹编号转换: {value} -> {new_track_id}")
            return new_track_id
            
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError("track_id", value, f"航迹编号转换失败: {str(e)}")
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """校验航迹编号
        
        Args:
            value: 待校验的航迹编号
            
        Returns:
            Tuple[bool, str]: (是否有效, 错误信息)
        """
        if value is None:
            return False, "航迹编号不能为空"
        
        try:
            track_id = None
            
            if isinstance(value, int):
                track_id = value
            elif isinstance(value, str):
                value = value.strip()
                if not value:
                    return False, "航迹编号不能为空字符串"
                
                match = self.TRACK_ID_PATTERN.match(value)
                if match:
                    track_id = int(match.group(1))
                else:
                    try:
                        track_id = int(value)
                    except ValueError:
                        return False, f"航迹编号格式错误: '{value}'，期望格式: [编号] 或纯数字"
            else:
                return False, f"航迹编号类型错误，期望整数或字符串，实际为 {type(value).__name__}"
            
            if track_id < self.MIN_TRACK_ID:
                return False, f"航迹编号 {track_id} 小于最小值 {self.MIN_TRACK_ID}"
            
            if track_id > self.MAX_TRACK_ID:
                return False, f"航迹编号 {track_id} 大于最大值 {self.MAX_TRACK_ID}"
            
            return True, ""
            
        except Exception as e:
            return False, f"航迹编号校验异常: {str(e)}"
    
    def format_track_id(self, track_id: int) -> str:
        """格式化航迹编号为标准格式
        
        Args:
            track_id: 航迹编号整数值
            
        Returns:
            str: 格式化的航迹编号，如 "[20106]"
        """
        return f"[{track_id}]"


class ParameterValidator:
    """参数校验器"""
    
    def __init__(self):
        self._validators: Dict[ParameterType, BaseConverter] = {
            ParameterType.TRACK_ID: TrackIdConverter(),
            ParameterType.TIME: TimeConverter(),
            ParameterType.RANGE: RangeConverter(),
            ParameterType.VELOCITY: VelocityConverter(),
            ParameterType.AZIMUTH: AzimuthConverter(),
            ParameterType.LATITUDE: LatitudeConverter(),
            ParameterType.LONGITUDE: LongitudeConverter(),
        }
        self._custom_validators: Dict[str, Callable] = {}
    
    def register_validator(self, param_type: ParameterType, converter: BaseConverter):
        """注册自定义校验器"""
        self._validators[param_type] = converter
        logger.info(f"已注册校验器: {param_type.value}")
    
    def register_custom_validator(self, name: str, validator: Callable):
        """注册自定义校验函数"""
        self._custom_validators[name] = validator
        logger.info(f"已注册自定义校验函数: {name}")
    
    def validate_parameter(
        self,
        param_type: ParameterType,
        value: Any
    ) -> Tuple[bool, str]:
        """校验单个参数"""
        if param_type not in self._validators:
            return False, f"未知的参数类型: {param_type.value}"
        
        converter = self._validators[param_type]
        return converter.validate(value)
    
    def validate_all(
        self,
        params: Dict[ParameterType, Any]
    ) -> Tuple[bool, List[str]]:
        """校验所有参数"""
        errors = []
        
        for param_type, value in params.items():
            is_valid, message = self.validate_parameter(param_type, value)
            if not is_valid:
                errors.append(f"{param_type.value}: {message}")
        
        return len(errors) == 0, errors


class MessageBuilder:
    """报文构建器"""
    
    # DEFAULT_FORMAT = "$RD,{track_id},{time},0,2,1,{vr},0,0,0,{lon},{lat},0,0,{range},{az},0,0,0,0,0"
    DEFAULT_FORMAT = "$RD,{track_id},{time},0,2,0,0,0,0,0,{lon},{lat},0,0,{range},{az},0,0,0,0,0"
    
    def __init__(self, message_format: Optional[str] = None):
        self.message_format = message_format or self.DEFAULT_FORMAT
        self._formats: Dict[str, MessageFormat] = {}
        self._register_default_formats()
    
    def _register_default_formats(self):
        """注册默认报文格式"""
        self._formats["RD"] = MessageFormat(
            name="RD",
            template=self.DEFAULT_FORMAT,
            field_order=["track_id", "time", "vr", "lon", "lat", "range", "az"],
            field_types={
                "track_id": int,
                "time": int,
                "vr": float,
                "lon": float,
                "lat": float,
                "range": float,
                "az": float
            }
        )
    
    def register_format(self, name: str, message_format: MessageFormat):
        """注册新的报文格式"""
        self._formats[name] = message_format
        logger.info(f"已注册报文格式: {name}")
    
    def build(self, track_point: TrackPoint, format_name: str = "RD") -> str:
        """构建报文"""
        if format_name not in self._formats:
            raise ValueError(f"未知的报文格式: {format_name}")
        
        message_format = self._formats[format_name]
        
        try:
            message = message_format.template.format(
                track_id=track_point.track_id,
                time=track_point.time_ms,
                vr=f"{track_point.velocity:.8f}",
                lon=f"{track_point.longitude:.8f}",
                lat=f"{track_point.latitude:.8f}",
                range=f"{track_point.range_val:.8f}",
                az=f"{track_point.azimuth:.8f}"
            )
            
            logger.debug(f"生成报文: {message}")
            
            return message
            
        except KeyError as e:
            raise ValueError(f"报文格式字段缺失: {e}")
    
    def build_batch(self, track_points: List[TrackPoint], format_name: str = "RD") -> List[str]:
        """批量构建报文"""
        messages = []
        for point in track_points:
            try:
                message = self.build(point, format_name)
                messages.append(message)
            except Exception as e:
                logger.error(f"构建报文失败 (行 {point.line_number}): {e}")
        return messages


class TrackParameterConverter:
    """Track参数转换器主类
    
    数据格式 (v2.0):
    第0列: 航迹编号 [20106]
    第1列: 序号
    第2列: 时间戳
    第3列: 距离
    第4列: 速度
    第5列: 方位
    第6列: 标志
    第7列: 距离(重复)
    第8列: 速度(重复)
    第9列: 方位(重复)
    第10列: 保留
    第11列: 保留
    第12列: 纬度
    第13列: 经度
    """
    
    COLUMN_MAPPING = {
        0: ("track_id", ParameterType.TRACK_ID),
        2: ("time_raw", ParameterType.TIME),
        7: ("range_val", ParameterType.RANGE),
        8: ("velocity", ParameterType.VELOCITY),
        9: ("azimuth", ParameterType.AZIMUTH),
        12: ("latitude", ParameterType.LATITUDE),
        13: ("longitude", ParameterType.LONGITUDE),
    }
    
    def __init__(self, log_file: Optional[str] = None):
        self.validator = ParameterValidator()
        self.message_builder = MessageBuilder()
        self.time_converter = TimeConverter()
        
        self._conversion_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "warnings": 0
        }
        
        if log_file:
            self._setup_file_logging(log_file)
    
    def _setup_file_logging(self, log_file: str):
        """设置文件日志"""
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        )
        logger.addHandler(file_handler)
        logger.info(f"日志文件已创建: {log_file}")
    
    def parse_line(self, line: str, line_number: int = 0) -> ConversionResult:
        """解析单行数据"""
        self._conversion_stats["total"] += 1
        
        try:
            line = line.strip()
            if not line:
                return ConversionResult(
                    success=False,
                    message="空行",
                    errors=["空行，已跳过"]
                )
            
            parts = [p.strip() for p in line.split(',')]
            
            if len(parts) < 14:
                return ConversionResult(
                    success=False,
                    message=f"列数不足: 期望至少14列，实际{len(parts)}列",
                    errors=[f"数据列数不足: {len(parts)} < 14"]
                )
            
            track_point = TrackPoint(raw_data=parts, line_number=line_number)
            errors = []
            warnings = []
            
            for col_idx, (attr_name, param_type) in self.COLUMN_MAPPING.items():
                try:
                    value_str = parts[col_idx]
                    converter = self.validator._validators.get(param_type)
                    
                    if converter is None:
                        warnings.append(f"未找到参数类型 {param_type.value} 的转换器")
                        continue
                    
                    is_valid, msg = converter.validate(value_str)
                    if not is_valid:
                        errors.append(f"第{col_idx + 1}列({param_type.value}): {msg}")
                        continue
                    
                    converted_value = converter.convert(value_str)
                    
                    if param_type == ParameterType.TIME:
                        track_point.time_raw = float(value_str)
                        track_point.time_ms = converted_value
                    elif param_type == ParameterType.TRACK_ID:
                        track_point.track_id = converted_value
                    else:
                        setattr(track_point, attr_name, converted_value)
                        
                except ConversionError as e:
                    errors.append(str(e))
                except Exception as e:
                    errors.append(f"第{col_idx + 1}列解析错误: {str(e)}")
            
            if errors:
                self._conversion_stats["failed"] += 1
                return ConversionResult(
                    success=False,
                    message=f"解析失败，共{len(errors)}个错误",
                    track_point=track_point,
                    errors=errors,
                    warnings=warnings
                )
            
            if warnings:
                self._conversion_stats["warnings"] += 1
            
            self._conversion_stats["success"] += 1
            logger.debug(f"行 {line_number} 解析成功: track_id={track_point.track_id}, time_ms={track_point.time_ms}")
            
            return ConversionResult(
                success=True,
                message="解析成功",
                track_point=track_point,
                warnings=warnings
            )
            
        except Exception as e:
            self._conversion_stats["failed"] += 1
            logger.error(f"行 {line_number} 解析异常: {e}")
            return ConversionResult(
                success=False,
                message=f"解析异常: {str(e)}",
                errors=[str(e)]
            )
    
    def convert_file(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        skip_errors: bool = True
    ) -> Tuple[List[str], List[ConversionResult]]:
        """转换文件"""
        logger.info(f"开始转换文件: {input_file}")
        
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"输入文件不存在: {input_file}")
        
        track_points = []
        results = []
        
        with open(input_file, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                result = self.parse_line(line, line_number)
                results.append(result)
                
                if result.success and result.track_point:
                    track_points.append(result.track_point)
        
        track_points.sort(key=lambda point: point.time_ms)
        
        messages = []
        for point in track_points:
            try:
                message = self.message_builder.build(point)
                messages.append(message)
                logger.debug(f"生成报文: {message}")
            except Exception as e:
                logger.error(f"构建报文失败 (track_id={point.track_id}, time_ms={point.time_ms}): {e}")
                if not skip_errors:
                    raise
        
        if output_file:
            self._write_output(output_file, messages)
            logger.info(f"输出文件已生成: {output_file}")
        
        self._log_statistics()
        
        return messages, results
    
    def _write_output(self, output_file: str, messages: List[str]):
        """写入输出文件"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for message in messages:
                f.write(message + '\n')
    
    def _log_statistics(self):
        """记录统计信息"""
        stats = self._conversion_stats
        logger.info("=" * 60)
        logger.info("转换统计:")
        logger.info(f"  总行数: {stats['total']}")
        logger.info(f"  成功: {stats['success']}")
        logger.info(f"  失败: {stats['failed']}")
        logger.info(f"  警告: {stats['warnings']}")
        logger.info(f"  成功率: {stats['success']/max(stats['total'],1)*100:.2f}%")
        logger.info("=" * 60)
    
    def get_statistics(self) -> Dict[str, int]:
        """获取统计信息"""
        return self._conversion_stats.copy()
    
    def reset_statistics(self):
        """重置统计信息"""
        self._conversion_stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "warnings": 0
        }
    
    def register_message_format(self, name: str, template: str, field_order: List[str]):
        """注册新的报文格式（可扩展性支持）"""
        message_format = MessageFormat(
            name=name,
            template=template,
            field_order=field_order,
            field_types={field: float for field in field_order}
        )
        self.message_builder.register_format(name, message_format)
    
    def register_parameter_converter(
        self,
        param_type: ParameterType,
        converter: BaseConverter
    ):
        """注册新的参数转换器（可扩展性支持）"""
        self.validator.register_validator(param_type, converter)


def create_converter(log_file: Optional[str] = None) -> TrackParameterConverter:
    """创建转换器实例的工厂函数"""
    return TrackParameterConverter(log_file=log_file)
