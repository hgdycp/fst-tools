#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyInstaller 打包脚本
将UI程序打包成Windows可执行程序
"""

import PyInstaller.__main__
import os
import sys

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 入口文件
ENTRY_FILE = os.path.join(ROOT_DIR, 'ui', 'main_window.py')

# 输出目录
DIST_DIR = os.path.join(ROOT_DIR, 'dist')

# PyInstaller 参数
args = [
    ENTRY_FILE,
    '--name=FST轨迹转换工具',
    '--windowed',  # 不显示控制台窗口
    '--onefile',   # 打包成单个exe文件
    f'--distpath={DIST_DIR}',
    '--add-data=src;src',  # 包含src目录
    '--hidden-import=PySide6',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=scipy',
    '--hidden-import=scipy.io',
    '--hidden-import=numpy',
    '--collect-all=PySide6',
    '--noconfirm',  # 覆盖已存在的输出
]

print("开始打包...")
print(f"入口文件: {ENTRY_FILE}")
print(f"输出目录: {DIST_DIR}")
print()

PyInstaller.__main__.run(args)

print()
print("打包完成！")
print(f"可执行文件位置: {os.path.join(DIST_DIR, 'FST轨迹转换工具.exe')}")
