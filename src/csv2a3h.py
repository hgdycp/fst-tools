#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV转A3H格式工具
功能：将CSV文件转换为A3H格式文件
支持命令行参数，提供友好的错误提示
"""

import csv
import sys
import os
import argparse
from datetime import datetime


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='CSV转A3H格式转换工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  %(prog)s                          # 使用默认文件名 (2026-02-04.csv -> 2026-02-04.a3h)
  %(prog)s input.csv                # 指定输入文件
  %(prog)s input.csv output.a3h     # 指定输入和输出文件
'''
    )
    parser.add_argument(
        'input_file',
        nargs='?',
        default='2026-02-04.csv',
        help='输入CSV文件路径 (默认: %(default)s)'
    )
    parser.add_argument(
        'output_file',
        nargs='?',
        default=None,
        help='输出A3H文件路径 (默认: 同输入文件名，后缀改为.a3h)'
    )
    return parser.parse_args()


def get_output_filename(input_file):
    """根据输入文件名生成默认输出文件名"""
    base, _ = os.path.splitext(input_file)
    return base + '.a3h'


def validate_file(file_path, mode='r'):
    """验证文件是否存在或可写"""
    if mode == 'r':
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'输入文件不存在: {file_path}')
        if not os.path.isfile(file_path):
            raise ValueError(f'路径不是文件: {file_path}')
    elif mode == 'w':
        dir_path = os.path.dirname(file_path)
        if dir_path and not os.path.exists(dir_path):
            raise FileNotFoundError(f'输出目录不存在: {dir_path}')


def convert_csv_to_a3h(input_file, output_file):
    """
    将CSV文件转换为A3H格式
    Args:
        input_file: 输入CSV文件路径
        output_file: 输出A3H文件路径
    """
    line_count = 0
    processed_lines = 0

    try:
        with open(input_file, 'r', encoding='gbk') as infile, \
             open(output_file, 'w', encoding='gbk', newline='') as outfile:

            reader = csv.reader(infile, delimiter=',')
            writer = csv.writer(outfile, delimiter=',')

            for row in reader:
                line_count += 1

                # 跳过第一列长度不等于6的行
                if len(row) == 0 or len(row[0].strip()) != 6:
                    continue

                processed_lines += 1

                # 计算秒、毫秒、纳秒（从0开始均匀分布）
                second = (processed_lines - 1) % 60
                ms = (processed_lines - 1) % 1000
                ns = ms * 1000000 + (processed_lines - 1) % 1000000

                # 提取原始字段
                try:
                    icao_hex = row[0]
                    lat = row[1]
                    lon = row[2]
                    heading = row[3]
                    altitude_ft = float(row[4])
                    altitude_m = altitude_ft * 0.3048
                    altitude = f"{altitude_m:.3f}"
                    speed = row[5]

                    # 处理第16列（索引15）
                    speed_ft = row[15] if len(row) > 15 else '0'

                    # 处理第11列（索引10）
                    time_str = row[10] if len(row) > 10 else ''
                except (IndexError, ValueError) as e:
                    print(f"警告: 第 {line_count} 行数据格式错误，已跳过: {e}", file=sys.stderr)
                    continue

                # 格式化时间
                formatted_time = "0000-00-00-00-00-00"
                if time_str:
                    try:
                        dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M")
                        formatted_time = dt.strftime(f"%Y-%m-%d-%H-%M-{second:02d}")
                    except ValueError:
                        pass

                # 生成 $AP 报文
                out_row_ap = [
                    "$AP",
                    icao_hex,
                    formatted_time,
                    str(ms),
                    str(ns),
                    lon,
                    lat,
                    altitude,
                    "6",
                    "213453.451",
                    "0.00",
                    "2.021"
                ]
                writer.writerow(out_row_ap)

                # 生成 $AV 报文 (已注释，只保留AP报文)
                # out_row_av = [
                #     "$AV",
                #     icao_hex,
                #     formatted_time,
                #     str(ms),
                #     str(ns),
                #     speed,
                #     heading,
                #     speed_ft,
                #     "0",
                #     "0"
                # ]
                # writer.writerow(out_row_av)

        return line_count, processed_lines

    except FileNotFoundError as e:
        raise
    except UnicodeDecodeError:
        raise RuntimeError(f'文件编码错误，请确保文件使用GBK编码: {input_file}')
    except Exception as e:
        raise RuntimeError(f'处理文件时出错: {str(e)}')


def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_args()

        # 确定输出文件名
        if args.output_file is None:
            args.output_file = get_output_filename(args.input_file)

        print('=' * 60)
        print('CSV转A3H格式转换工具')
        print('=' * 60)
        print(f'输入文件: {args.input_file}')
        print(f'输出文件: {args.output_file}')
        print()

        # 验证文件
        validate_file(args.input_file, 'r')
        validate_file(args.output_file, 'w')

        # 执行转换
        line_count, processed_lines = convert_csv_to_a3h(args.input_file, args.output_file)

        # 输出结果
        print('-' * 60)
        print(f'转换完成！')
        print(f'  总行数: {line_count}')
        print(f'  处理行数: {processed_lines}')
        print(f'  输出文件: {args.output_file}')
        print('=' * 60)

        return 0

    except FileNotFoundError as e:
        print(f'错误: {e}', file=sys.stderr)
        return 1
    except ValueError as e:
        print(f'错误: {e}', file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f'错误: {e}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('\n操作已取消', file=sys.stderr)
        return 130
    except Exception as e:
        print(f'未知错误: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
