#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转换逻辑封装模块
提供CSV/MAT文件到A3H格式的转换功能
"""

import os
import sys
import csv
import tempfile
import shutil
from datetime import datetime
from typing import Tuple, Optional, List
from dataclasses import dataclass

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.csv2a3h import convert_csv_to_a3h as csv_converter
from src.extract_smooth_points import extract_smooth_points as mat_extractor
from src.track_parameter_converter import TrackParameterConverter
from src.merge_messages import add_header, parse_adsb_file, parse_radar_file


@dataclass
class FileInfo:
    """文件信息"""
    file_path: str
    file_type: str  # 'csv' or 'mat'
    earliest_time: Optional[datetime] = None
    latest_time: Optional[datetime] = None
    temp_a3h_path: Optional[str] = None
    earliest_ms: int = 0  # 毫秒时间戳（当天毫秒数）
    latest_ms: int = 86400000  # 毫秒时间戳（当天毫秒数）


class Converter:
    """转换器类"""

    def __init__(self):
        self.temp_dir = None
        self.files: List[FileInfo] = []
        self.reference_date: Optional[datetime] = None  # 参考日期（从ADS-B文件获取）

    def create_temp_dir(self) -> str:
        """创建临时目录"""
        if self.temp_dir is None:
            self.temp_dir = tempfile.mkdtemp(prefix='fst_ui_')
        return self.temp_dir

    def cleanup_temp_dir(self):
        """清理临时目录"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            self.temp_dir = None

    def process_csv(self, input_file: str, temp_dir: str) -> Tuple[bool, str, Optional[FileInfo]]:
        """
        处理CSV文件

        Args:
            input_file: 输入CSV文件路径
            temp_dir: 临时目录路径

        Returns:
            (success, error_message, file_info)
        """
        try:
            # 生成输出文件名
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            output_a3h = os.path.join(temp_dir, f"{base_name}.a3h")

            # 调用CSV转换函数
            csv_converter(input_file, output_a3h)

            # 解析时间范围
            earliest_time, latest_time = self._get_csv_time_range(input_file)

            # 计算毫秒时间戳
            earliest_ms = self._time_to_ms(earliest_time) if earliest_time else 0
            latest_ms = self._time_to_ms(latest_time) if latest_time else 86400000

            file_info = FileInfo(
                file_path=input_file,
                file_type='csv',
                earliest_time=earliest_time,
                latest_time=latest_time,
                temp_a3h_path=output_a3h,
                earliest_ms=earliest_ms,
                latest_ms=latest_ms
            )

            return True, "", file_info

        except Exception as e:
            return False, str(e), None

    def _time_to_ms(self, dt: datetime) -> int:
        """将 datetime 转换为当天毫秒数"""
        return dt.hour * 3600000 + dt.minute * 60000 + dt.second * 1000

    def process_mat(self, input_file: str, temp_dir: str) -> Tuple[bool, str, Optional[FileInfo]]:
        """
        处理MAT文件

        Args:
            input_file: 输入MAT文件路径
            temp_dir: 临时目录路径

        Returns:
            (success, error_message, file_info)
        """
        try:
            # 生成临时TXT文件名
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            temp_txt = os.path.join(temp_dir, f"{base_name}_smoothPoints.txt")
            output_a3h = os.path.join(temp_dir, f"{base_name}.a3h")

            # 提取平滑点
            success = mat_extractor(input_file, temp_txt)
            if not success:
                return False, "MAT文件提取平滑点失败", None

            # 使用TrackParameterConverter转换
            converter = TrackParameterConverter()
            converter.convert_file(temp_txt, output_a3h)

            # 解析时间范围
            earliest_time, latest_time = self._get_mat_time_range(temp_txt)

            # 计算毫秒时间戳
            earliest_ms = self._time_to_ms(earliest_time) if earliest_time else 0
            latest_ms = self._time_to_ms(latest_time) if latest_time else 86400000

            file_info = FileInfo(
                file_path=input_file,
                file_type='mat',
                earliest_time=earliest_time,
                latest_time=latest_time,
                temp_a3h_path=output_a3h,
                earliest_ms=earliest_ms,
                latest_ms=latest_ms
            )

            return True, "", file_info

        except Exception as e:
            return False, str(e), None

    def get_time_range(self, file_path: str,
                      ref_date: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取文件的时间范围

        Args:
            file_path: 文件路径
            ref_date: 参考日期（用于MAT文件，使其日期与ADS-B保持一致）

        Returns:
            (earliest_time, latest_time)
        """
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.csv':
            result = self._get_csv_time_range(file_path)
            # 如果获取到时间，更新参考日期
            if result[0] and (ref_date is None or self.reference_date is None):
                self.reference_date = result[0]
            return result
        elif ext == '.mat':
            # 对MAT文件，先提取平滑点再获取时间范围
            try:
                # 创建临时目录用于提取
                temp_dir = tempfile.mkdtemp()
                try:
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    temp_txt = os.path.join(temp_dir, f"{base_name}_smoothPoints.txt")

                    # 提取平滑点
                    success = mat_extractor(file_path, temp_txt)
                    if success and os.path.exists(temp_txt):
                        # 优先使用传入的ref_date，否则使用self.reference_date
                        effective_ref_date = ref_date if ref_date else self.reference_date
                        return self._get_mat_time_range(temp_txt, effective_ref_date)
                finally:
                    # 清理临时目录
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
            return None, None
        else:
            return None, None

    def _get_csv_time_range(self, csv_file: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """获取CSV文件的时间范围"""
        try:
            times = []
            with open(csv_file, 'r', encoding='gbk') as f:
                reader = csv.reader(f, delimiter=',')
                for row in reader:
                    if len(row) == 0 or len(row[0].strip()) != 6:
                        continue

                    # 第10列是时间
                    if len(row) > 10:
                        time_str = row[10]
                        if time_str:
                            try:
                                dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
                                times.append(dt)
                            except ValueError:
                                pass

            if times:
                return min(times), max(times)
            return None, None

        except Exception:
            return None, None

    def _get_mat_time_range(self, txt_file: str,
                           ref_date: Optional[datetime] = None) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取MAT文件(转换后TXT)的时间范围

        Args:
            txt_file: TXT文件路径
            ref_date: 参考日期（用于将MAT文件的时间与ADS-B日期对齐）
        """
        try:
            import numpy as np

            times = []
            with open(txt_file, 'r', encoding='utf-8') as f:
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) < 3:
                        continue

                    # 第2列是时间戳 (MATLAB时间戳)
                    try:
                        time_val = float(parts[2].strip())
                        # 转换MATLAB时间戳到Python datetime
                        # MATLAB时间戳: 从公元0001年开始的天数
                        matlab_days = int(time_val)
                        python_days = matlab_days + 719529  # MATLAB偏移量

                        dt = datetime.fromordinal(python_days)
                        fractional = time_val - matlab_days
                        seconds = int(fractional * 86400)
                        hour = seconds // 3600
                        minute = (seconds % 3600) // 60
                        second = seconds % 60

                        # 如果有参考日期，使用参考日期的yyyy/mm/dd，只保留MAT的时分秒
                        if ref_date:
                            dt = ref_date.replace(hour=hour, minute=minute, second=second)
                        else:
                            dt = dt.replace(hour=hour, minute=minute, second=second)
                        times.append(dt)
                    except (ValueError, IndexError):
                        pass

            if times:
                return min(times), max(times)
            return None, None

        except Exception:
            return None, None

    def merge_and_header(self, temp_dir: str, output_path: str,
                        start_ms: int = 0, end_ms: int = 86400000) -> Tuple[bool, str, int]:
        """
        合并临时目录中的所有A3H文件并添加报文头

        Args:
            temp_dir: 临时目录路径
            output_path: 输出文件路径
            start_ms: 合并起始时间（毫秒，当天毫秒数）
            end_ms: 合并结束时间（毫秒，当天毫秒数）

        Returns:
            (success, error_message, filtered_count)
        """
        try:
            # 查找所有.a3h文件
            a3h_files = [os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                        if f.endswith('.a3h')]

            if not a3h_files:
                return False, "没有找到要合并的A3H文件", 0

            # 读取并合并所有报文
            all_messages = []

            for a3h_file in a3h_files:
                # 尝试解析为ADS-B报文
                adsb_msgs = parse_adsb_file(a3h_file)
                if adsb_msgs:
                    all_messages.extend(adsb_msgs)
                else:
                    # 尝试解析为雷达报文
                    radar_msgs = parse_radar_file(a3h_file)
                    all_messages.extend(radar_msgs)

            if not all_messages:
                return False, "没有找到有效的报文数据", 0

            # 按时间戳排序
            all_messages.sort(key=lambda m: m.timestamp_ms)

            # 按时间范围过滤报文
            filtered_messages = [
                msg for msg in all_messages
                if start_ms <= msg.timestamp_ms <= end_ms
            ]
            filtered_count = len(filtered_messages)

            if not filtered_messages:
                return False, "没有在指定时间范围内的报文", 0

            # 写入合并后的文件
            merged_file = os.path.join(temp_dir, "merged.a3h")
            with open(merged_file, 'w', encoding='gbk', newline='') as f:
                for msg in filtered_messages:
                    f.write(msg.raw + '\n')

            # 添加报文头
            add_header(merged_file, output_path, encoding='gbk', verbose=False)

            return True, "", filtered_count

        except Exception as e:
            return False, str(e), 0


def get_file_time_range(file_path: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    快速获取文件时间范围（不进行转换）

    Args:
        file_path: 文件路径

    Returns:
        (earliest_time, latest_time)
    """
    converter = Converter()
    return converter.get_time_range(file_path)
