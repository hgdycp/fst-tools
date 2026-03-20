#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Track参数转换命令行工具 v2.0
功能：将track参数文件转换为报文格式文件
支持航迹编号字段
"""

import argparse
import logging
import os
import sys
from datetime import datetime

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from track_parameter_converter import (
    TrackParameterConverter,
    create_converter,
    logger
)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='Track参数转换工具 v2.0 - 将track参数转换为报文格式',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s input.txt                          # 转换文件，输出到 input_converted.txt
  %(prog)s input.txt output.txt               # 指定输出文件名
  %(prog)s input.txt -l conversion.log        # 指定日志文件
  %(prog)s input.txt -v                       # 详细输出模式

参数映射说明 (v2.0):
  第0列  -> track_id (航迹编号，格式: [编号])
  第2列  -> time     (时间，转换为当天0点开始的毫秒数)
  第7列  -> range    (距离)
  第8列  -> vr       (速度)
  第9列  -> az       (方位角)
  第12列 -> lat      (纬度)
  第13列 -> lon      (经度)

报文格式 (v2.0):
  $RD, [track_id], [time], 0, 2, 1, [vr], 0, 0, 0, [lon], [lat], 0, 0, [range], [az], 0, 0, 0, 0, 0
'''
    )
    
    parser.add_argument(
        'input_file',
        help='输入文件路径 (track参数文件)'
    )
    
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='输出文件路径 (默认: 输入文件名_converted.txt)'
    )
    
    parser.add_argument(
        '-l', '--log',
        dest='log_file',
        default=None,
        help='日志文件路径 (默认: 不生成日志文件)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='详细输出模式'
    )
    
    parser.add_argument(
        '-s', '--stop-on-error',
        action='store_true',
        help='遇到错误时停止处理'
    )
    
    parser.add_argument(
        '--format',
        dest='message_format',
        default='RD',
        choices=['RD'],
        help='报文格式类型 (默认: RD)'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Track参数转换工具 v2.0.0'
    )
    
    return parser.parse_args()


def get_output_filename(input_file: str) -> str:
    """生成默认输出文件名"""
    base, ext = os.path.splitext(input_file)
    return f"{base}_converted.a3h"


def validate_input_file(file_path: str) -> bool:
    """验证输入文件"""
    if not os.path.exists(file_path):
        print(f"错误: 输入文件不存在: {file_path}", file=sys.stderr)
        return False
    
    if not os.path.isfile(file_path):
        print(f"错误: 路径不是文件: {file_path}", file=sys.stderr)
        return False
    
    if not os.access(file_path, os.R_OK):
        print(f"错误: 无法读取文件: {file_path}", file=sys.stderr)
        return False
    
    return True


def main():
    """主函数"""
    args = parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    
    print("=" * 60)
    print("Track参数转换工具 v2.0.0")
    print("=" * 60)
    print(f"输入文件: {args.input_file}")
    
    if not validate_input_file(args.input_file):
        return 1
    
    output_file = args.output_file or get_output_filename(args.input_file)
    print(f"输出文件: {output_file}")
    
    if args.log_file:
        print(f"日志文件: {args.log_file}")
    
    print()
    
    try:
        converter = create_converter(log_file=args.log_file)
        
        print("正在转换...")
        messages, results = converter.convert_file(
            args.input_file,
            output_file,
            skip_errors=not args.stop_on_error
        )
        
        stats = converter.get_statistics()
        
        print("-" * 60)
        print("转换完成!")
        print(f"  总行数: {stats['total']}")
        print(f"  成功: {stats['success']}")
        print(f"  失败: {stats['failed']}")
        print(f"  警告: {stats['warnings']}")
        print(f"  成功率: {stats['success']/max(stats['total'],1)*100:.2f}%")
        print(f"  输出文件: {output_file}")
        print("=" * 60)
        
        if stats['failed'] > 0:
            print("\n部分行转换失败，请查看日志获取详细信息。")
            return 2
        
        return 0
        
    except FileNotFoundError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"错误: 权限不足 - {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    import logging
    sys.exit(main())
