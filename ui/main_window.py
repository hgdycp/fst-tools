#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FST轨迹数据转换工具 - PySide6 GUI
主窗口模块
"""

import os
import sys
from datetime import datetime
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QFileDialog, QMessageBox,
    QGroupBox, QLineEdit, QProgressDialog
)
from PySide6.QtCore import Qt, QThread, Signal

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.converter import Converter, FileInfo


class ConversionThread(QThread):
    """后台转换线程"""

    progress = Signal(str)
    finished = Signal(bool, str)


class MainWindow(QMainWindow):
    """主窗口类"""

    def __init__(self):
        super().__init__()
        self.converter = Converter()
        self.file_infos: List[FileInfo] = []
        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("FST轨迹数据转换工具")
        self.setMinimumSize(600, 500)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)

        # 标题
        title_label = QLabel("FST轨迹数据转换工具")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 文件操作组
        file_group = QGroupBox("文件操作")
        file_layout = QVBoxLayout()

        # 按钮行
        btn_layout = QHBoxLayout()
        self.add_file_btn = QPushButton("添加文件")
        self.add_file_btn.clicked.connect(self.add_files)
        self.remove_file_btn = QPushButton("移除选中")
        self.remove_file_btn.clicked.connect(self.remove_selected)
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_list)

        btn_layout.addWidget(self.add_file_btn)
        btn_layout.addWidget(self.remove_file_btn)
        btn_layout.addWidget(self.clear_btn)
        file_layout.addLayout(btn_layout)

        # 文件列表
        self.file_list = QListWidget()
        file_layout.addWidget(self.file_list)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # 时间范围组
        time_group = QGroupBox("时间范围")
        time_layout = QHBoxLayout()

        self.earliest_label = QLabel("最早时间: -")
        self.latest_label = QLabel("最晚时间: -")

        time_layout.addWidget(self.earliest_label)
        time_layout.addWidget(self.latest_label)
        time_group.setLayout(time_layout)
        main_layout.addWidget(time_group)

        # 运行按钮
        self.run_btn = QPushButton("运行")
        self.run_btn.setMinimumHeight(50)
        self.run_btn.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.run_btn.clicked.connect(self.run_conversion)
        main_layout.addWidget(self.run_btn)

        # 状态栏
        self.statusBar().showMessage("就绪")

    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择CSV或MAT文件",
            "",
            "所有支持的文件 (*.csv *.mat);;CSV文件 (*.csv);;MAT文件 (*.mat)"
        )

        if not files:
            return

        self.statusBar().showMessage(f"正在添加 {len(files)} 个文件...")

        for file_path in files:
            # 检查是否已存在
            exists = False
            for info in self.file_infos:
                if info.file_path == file_path:
                    exists = True
                    break

            if exists:
                continue

            # 获取文件时间范围
            earliest, latest = self.converter.get_time_range(file_path)

            # 添加文件信息
            file_info = FileInfo(
                file_path=file_path,
                file_type='csv' if file_path.lower().endswith('.csv') else 'mat',
                earliest_time=earliest,
                latest_time=latest
            )
            self.file_infos.append(file_info)

            # 更新列表显示
            ext = os.path.splitext(file_path)[1]
            time_str = ""
            if earliest and latest:
                time_str = f"时间: {earliest.strftime('%H:%M')}-{latest.strftime('%H:%M')}"
            else:
                time_str = "时间: 解析中..."

            display_text = f"{os.path.basename(file_path)} ({ext[1:].upper()}, {time_str})"
            self.file_list.addItem(display_text)

        self.update_time_range()
        self.statusBar().showMessage(f"已添加 {len(files)} 个文件")

    def remove_selected(self):
        """移除选中项"""
        current_row = self.file_list.currentRow()
        if current_row >= 0:
            self.file_list.takeItem(current_row)
            self.file_infos.pop(current_row)
            self.update_time_range()

    def clear_list(self):
        """清空列表"""
        self.file_list.clear()
        self.file_infos.clear()
        self.update_time_range()

    def update_time_range(self):
        """更新时间范围显示"""
        if not self.file_infos:
            self.earliest_label.setText("最早时间: -")
            self.latest_label.setText("最晚时间: -")
            return

        earliest_times = [f.earliest_time for f in self.file_infos if f.earliest_time]
        latest_times = [f.latest_time for f in self.file_infos if f.latest_time]

        if earliest_times:
            earliest = min(earliest_times)
            self.earliest_label.setText(f"最早时间: {earliest.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.earliest_label.setText("最早时间: -")

        if latest_times:
            latest = max(latest_times)
            self.latest_label.setText(f"最晚时间: {latest.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.latest_label.setText("最晚时间: -")

    def run_conversion(self):
        """运行转换"""
        if not self.file_infos:
            QMessageBox.warning(self, "警告", "请先添加文件")
            return

        # 显示进度对话框
        progress = QProgressDialog("正在转换...", "取消", 0, len(self.file_infos), self)
        progress.setWindowTitle("转换进度")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        try:
            # 创建临时目录
            temp_dir = self.converter.create_temp_dir()

            # 处理每个文件
            for i, file_info in enumerate(self.file_infos):
                progress.setValue(i)
                progress.setLabelText(f"正在处理: {os.path.basename(file_info.file_path)}")

                if progress.wasCanceled():
                    QMessageBox.warning(self, "取消", "转换已取消")
                    return

                QApplication.processEvents()

                if file_info.file_type == 'csv':
                    success, error, new_info = self.converter.process_csv(
                        file_info.file_path, temp_dir
                    )
                else:
                    success, error, new_info = self.converter.process_mat(
                        file_info.file_path, temp_dir
                    )

                if not success:
                    QMessageBox.critical(self, "错误", f"处理文件失败: {error}")
                    return

                # 更新文件信息
                if new_info:
                    self.file_infos[i] = new_info

            progress.setValue(len(self.file_infos))
            progress.setLabelText("正在合并文件...")

            # 合并文件并添加报文头
            output_path = os.path.join(os.getcwd(), "Output.a3h")
            success, error = self.converter.merge_and_header(temp_dir, output_path)

            if not success:
                QMessageBox.critical(self, "错误", f"合并失败: {error}")
                return

            # 清理临时目录
            self.converter.cleanup_temp_dir()
            self.file_infos.clear()
            self.file_list.clear()

            QMessageBox.information(
                self,
                "完成",
                f"转换完成！\n输出文件: {output_path}"
            )

            self.update_time_range()
            self.statusBar().showMessage("转换完成")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")
        finally:
            progress.close()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
