#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报文合并工具
功能：将ADS-B报文文件和雷达数据报文文件按时间戳顺序合并
"""

import argparse
import os
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Message:
    """报文数据类"""
    raw: str
    msg_type: str  # AP, AV, RD
    timestamp_ms: int  # 统一转换为毫秒时间戳
    icao_hex: str = ""
    track_id: str = ""


def parse_adsb_timestamp(time_str: str, ms: str, ns: str, ref_date: str = None) -> int:
    """
    解析ADS-B时间格式: yyyy-mm-dd-HH-MM-SS, ms, ns
    返回毫秒时间戳
    """
    # 解析主时间字符串 yyyy-mm-dd-HH-MM-SS
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d-%H-%M-%S")
    except ValueError:
        # 如果没有完整日期，尝试只用时分秒
        try:
            if ref_date:
                dt = datetime.strptime(f"{ref_date}-{time_str}", "%Y-%m-%d-%H-%M-%S")
            else:
                dt = datetime.strptime(time_str, "%H-%M-%S")
                # 使用今天的日期
                dt = dt.replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        except ValueError:
            return 0

    # 计算毫秒: HH*3600000 + MM*60000 + SS*1000 + ms
    ms_val = int(ms) if ms else 0
    total_ms = dt.hour * 3600000 + dt.minute * 60000 + dt.second * 1000 + ms_val

    return total_ms


def parse_radar_timestamp(ms_str: str) -> int:
    """
    解析雷达时间格式: 当天毫秒数
    """
    try:
        return int(ms_str)
    except ValueError:
        return 0


def get_first_ap_info(file_path: str, encoding: str = 'gbk') -> dict:
    """
    获取文件中第一条AP报文的经纬度和时间

    返回:
    - lon: 经度
    - lat: 纬度
    - altitude: 高度
    - time_str: 时间字符串 (yyyy-mm-dd-HH-MM-SS)
    - ms: 毫秒
    """
    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith('$AP'):
                continue

            parts = line.split(',')
            if len(parts) < 8:
                continue

            # $AP,icao_hex,yyyy-mm-dd-HH-MM-SS,ms,ns,lon,lat,altitude,...
            return {
                'lon': parts[5],
                'lat': parts[6],
                'altitude': parts[7],
                'time_str': parts[2],
                'ms': parts[3]
            }

    return None


def add_header(input_file: str, output_file: str = None,
               lon: str = None, lat: str = None, altitude: str = None,
               time_str: str = None, ms: str = None,
               encoding: str = 'gbk', verbose: bool = False) -> dict:
    """
    为报文文件添加报文头

    输入参数 (可自定义，否则从第一条AP报文自动获取):
    - lon: 经度
    - lat: 纬度
    - altitude: 高度
    - time_str: 时间字符串 (yyyy-mm-dd-HH-MM-SS)
    - ms: 毫秒

    输出格式:
    #VERSION 2
    #HOME [经度] [纬度] [高度]
    #TIME [采样时间]
    """
    if output_file is None:
        output_file = input_file

    # 如果未指定参数，从第一条AP报文获取
    if lon is None or lat is None or altitude is None or time_str is None or ms is None:
        if verbose:
            print(f"正在从第一条AP报文获取参数...")
        ap_info = get_first_ap_info(input_file, encoding)
        if ap_info is None:
            raise ValueError("文件中未找到AP报文")

        lon = lon or ap_info['lon']
        lat = lat or ap_info['lat']
        altitude = altitude or ap_info['altitude']
        time_str = time_str or ap_info['time_str']
        ms = ms or ap_info['ms']

    if verbose:
        print(f"报文头参数:")
        print(f"  经度: {lon}")
        print(f"  纬度: {lat}")
        print(f"  高度: {altitude}")
        print(f"  时间: {time_str}")

    # 构建报文头
    header_lines = [
        "#VERSION 2",
        f"#HOME {lon} {lat} {altitude}",
        f"#TIME {time_str}"
    ]

    # 读取原文件内容
    with open(input_file, 'r', encoding=encoding, errors='ignore') as f:
        content = f.read()

    # 写入带报文头的文件
    with open(output_file, 'w', encoding=encoding, newline='') as f:
        for header_line in header_lines:
            f.write(header_line + '\n')
        f.write(content)

    if verbose:
        print(f"报文头已添加: {output_file}")

    return {
        'lon': lon,
        'lat': lat,
        'altitude': altitude,
        'time': time_str
    }


def parse_adsb_file(file_path: str, encoding: str = 'gbk') -> List[Message]:
    """解析ADS-B报文文件"""
    messages = []

    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 3:
                continue

            msg_type = parts[0]

            if msg_type == '$AP':
                # $AP,icao_hex,yyyy-mm-dd-HH-MM-SS,ms,ns,...
                if len(parts) < 6:
                    continue
                icao_hex = parts[1]
                time_str = parts[2]
                ms = parts[3] if len(parts) > 3 else '0'
                ns = parts[4] if len(parts) > 4 else '0'

                timestamp_ms = parse_adsb_timestamp(time_str, ms, ns)
                messages.append(Message(
                    raw=line,
                    msg_type=msg_type,
                    timestamp_ms=timestamp_ms,
                    icao_hex=icao_hex
                ))

            elif msg_type == '$AV':
                # $AV,icao_hex,yyyy-mm-dd-HH-MM-SS,ms,ns,...
                if len(parts) < 6:
                    continue
                icao_hex = parts[1]
                time_str = parts[2]
                ms = parts[3] if len(parts) > 3 else '0'
                ns = parts[4] if len(parts) > 4 else '0'

                timestamp_ms = parse_adsb_timestamp(time_str, ms, ns)
                messages.append(Message(
                    raw=line,
                    msg_type=msg_type,
                    timestamp_ms=timestamp_ms,
                    icao_hex=icao_hex
                ))

    return messages


def parse_radar_file(file_path: str, encoding: str = 'gbk') -> List[Message]:
    """解析雷达报文文件"""
    messages = []

    with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split(',')
            if len(parts) < 3:
                continue

            msg_type = parts[0]

            if msg_type == '$RD':
                # $RD,track_id,ms_from_midnight,...
                if len(parts) < 3:
                    continue
                track_id = parts[1]
                ms_str = parts[2]

                timestamp_ms = parse_radar_timestamp(ms_str)
                messages.append(Message(
                    raw=line,
                    msg_type=msg_type,
                    timestamp_ms=timestamp_ms,
                    track_id=track_id
                ))

    return messages


def merge_messages(adsb_file: str, radar_file: str, output_file: str,
                  ref_date: str = None, encoding: str = 'gbk', verbose: bool = False) -> dict:
    """
    合并ADS-B和雷达报文文件

    返回统计信息:
    - adsb_count: ADS-B报文数量
    - radar_count: 雷达报文数量
    - total_count: 总报文数量
    """

    # 解析两个文件
    if verbose:
        print(f"正在解析ADS-B文件: {adsb_file}")

    adsb_messages = parse_adsb_file(adsb_file, encoding)
    adsb_count = len(adsb_messages)

    if verbose:
        print(f"  - 解析到 {adsb_count} 条ADS-B报文")
        print(f"正在解析雷达文件: {radar_file}")

    radar_messages = parse_radar_file(radar_file, encoding)
    radar_count = len(radar_messages)

    if verbose:
        print(f"  - 解析到 {radar_count} 条雷达报文")

    # 合并所有报文
    all_messages = adsb_messages + radar_messages

    if verbose:
        print(f"正在按时间戳排序...")

    # 按时间戳排序
    all_messages.sort(key=lambda m: m.timestamp_ms)

    if verbose:
        print(f"正在写入输出文件: {output_file}")

    # 写入输出文件
    with open(output_file, 'w', encoding=encoding, newline='') as f:
        for msg in all_messages:
            f.write(msg.raw + '\n')

    total_count = len(all_messages)

    if verbose:
        print(f"合并完成!")
        print(f"  - ADS-B报文: {adsb_count}")
        print(f"  - 雷达报文: {radar_count}")
        print(f"  - 总报文数: {total_count}")

    return {
        'adsb_count': adsb_count,
        'radar_count': radar_count,
        'total_count': total_count
    }


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='报文合并工具 - 合并ADS-B和雷达报文文件，或添加报文头',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # merge 子命令
    merge_parser = subparsers.add_parser('merge', help='合并ADS-B和雷达报文文件')
    merge_parser.add_argument('adsb_file', help='ADS-B报文文件路径')
    merge_parser.add_argument('radar_file', help='雷达报文文件路径')
    merge_parser.add_argument('output_file', help='合并输出文件路径')
    merge_parser.add_argument('--date', dest='ref_date',
                              help='参考日期 (格式: yyyy-mm-dd)，用于转换ADS-B时间戳')
    merge_parser.add_argument('--encoding', default='gbk',
                              help='输入文件编码 (默认: gbk)')
    merge_parser.add_argument('-v', '--verbose', action='store_true',
                              help='显示详细输出')

    # add-header 子命令
    header_parser = subparsers.add_parser('add-header', help='为报文文件添加报文头')
    header_parser.add_argument('input_file', help='输入报文文件路径')
    header_parser.add_argument('output_file', nargs='?', default=None,
                               help='输出文件路径 (默认: 覆盖原文件)')
    header_parser.add_argument('--lon', help='经度 (默认: 第一条AP报文的经度)')
    header_parser.add_argument('--lat', help='纬度 (默认: 第一条AP报文的纬度)')
    header_parser.add_argument('--alt', '--altitude', dest='altitude',
                               help='高度 (默认: 第一条AP报文的高度)')
    header_parser.add_argument('--time', help='时间 (格式: yyyy-mm-dd-HH-MM-SS, 默认: 第一条AP报文的时间)')
    header_parser.add_argument('--ms', help='毫秒 (默认: 第一条AP报文的毫秒)')
    header_parser.add_argument('--encoding', default='gbk',
                               help='输入文件编码 (默认: gbk)')
    header_parser.add_argument('-v', '--verbose', action='store_true',
                               help='显示详细输出')

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 如果没有子命令，显示帮助
    if args.command is None:
        parse_args(['--help'])
        return 0

    try:
        if args.command == 'merge':
            return merge_subcommand(args)
        elif args.command == 'add-header':
            return add_header_subcommand(args)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def merge_subcommand(args):
    """处理 merge 子命令"""
    if not os.path.exists(args.adsb_file):
        print(f"错误: ADS-B文件不存在: {args.adsb_file}", file=sys.stderr)
        return 1

    if not os.path.exists(args.radar_file):
        print(f"错误: 雷达文件不存在: {args.radar_file}", file=sys.stderr)
        return 1

    stats = merge_messages(
        adsb_file=args.adsb_file,
        radar_file=args.radar_file,
        output_file=args.output_file,
        ref_date=args.ref_date,
        encoding=args.encoding,
        verbose=args.verbose
    )

    print("=" * 60)
    print("报文合并完成")
    print("=" * 60)
    print(f"ADS-B报文: {stats['adsb_count']}")
    print(f"雷达报文: {stats['radar_count']}")
    print(f"总报文数: {stats['total_count']}")
    print(f"输出文件: {args.output_file}")
    print("=" * 60)

    return 0


def add_header_subcommand(args):
    """处理 add-header 子命令"""
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}", file=sys.stderr)
        return 1

    result = add_header(
        input_file=args.input_file,
        output_file=args.output_file,
        lon=args.lon,
        lat=args.lat,
        altitude=args.altitude,
        time_str=args.time,
        ms=args.ms,
        encoding=args.encoding,
        verbose=args.verbose
    )

    output_file = args.output_file or args.input_file

    print("=" * 60)
    print("报文头添加完成")
    print("=" * 60)
    print(f"经度: {result['lon']}")
    print(f"纬度: {result['lat']}")
    print(f"高度: {result['altitude']}")
    print(f"时间: {result['time']}")
    print(f"输出文件: {output_file}")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
