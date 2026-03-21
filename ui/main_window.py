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
    QGroupBox, QLineEdit, QProgressDialog, QSlider, QCheckBox
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
        self.setMinimumSize(700, 600)

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
        time_layout = QVBoxLayout()

        # 数据显示行
        data_layout = QHBoxLayout()
        self.earliest_label = QLabel("最早时间: -")
        self.latest_label = QLabel("最晚时间: -")
        data_layout.addWidget(self.earliest_label)
        data_layout.addWidget(self.latest_label)
        time_layout.addLayout(data_layout)

        # 合并时间范围选择
        merge_time_layout = QVBoxLayout()

        # 启用时间范围过滤的复选框
        self.enable_time_filter = QCheckBox("启用合并时间范围过滤")
        self.enable_time_filter.setChecked(False)
        self.enable_time_filter.stateChanged.connect(self.on_time_filter_changed)
        merge_time_layout.addWidget(self.enable_time_filter)

        # 起始时间滑动条
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("起始时间:"))
        self.start_slider = QSlider(Qt.Horizontal)
        self.start_slider.setMinimum(0)
        self.start_slider.setMaximum(86399)  # 简化为0-86399 (秒)
        self.start_slider.setValue(0)
        self.start_slider.setPageStep(3600)  # 1小时 = 3600秒
        self.start_slider.setTickPosition(QSlider.TicksBelow)
        self.start_slider.setTickInterval(3600)  # 每小时一个刻度
        self.start_slider.setEnabled(False)
        self.start_slider.setMinimumWidth(400)
        self.start_slider.valueChanged.connect(self.on_start_time_changed)
        start_layout.addWidget(self.start_slider, 1)  # stretch = 1
        self.start_time_label = QLabel("00:00:00")
        self.start_time_label.setMinimumWidth(70)
        start_layout.addWidget(self.start_time_label)
        merge_time_layout.addLayout(start_layout)

        # 结束时间滑动条
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("结束时间:"))
        self.end_slider = QSlider(Qt.Horizontal)
        self.end_slider.setMinimum(0)
        self.end_slider.setMaximum(86399)  # 简化为0-86399 (秒)
        self.end_slider.setValue(86399)
        self.end_slider.setPageStep(3600)  # 1小时
        self.end_slider.setTickPosition(QSlider.TicksBelow)
        self.end_slider.setTickInterval(3600)  # 每小时一个刻度
        self.end_slider.setEnabled(False)
        self.end_slider.setMinimumWidth(400)
        self.end_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #999;
                height: 8px;
                background: white;
                margin: 2px 0;
            }
            QSlider::handle:horizontal {
                background: #0078d7;
                border: 1px solid #5c5c5c;
                width: 18px;
                margin: -2px 0;
                border-radius: 3px;
            }
        """)
        self.end_slider.valueChanged.connect(self.on_end_time_changed)
        end_layout.addWidget(self.end_slider)
        self.end_time_label = QLabel("23:59:59")
        self.end_time_label.setMinimumWidth(70)
        end_layout.addWidget(self.end_time_label)
        merge_time_layout.addLayout(end_layout)

        time_layout.addLayout(merge_time_layout)
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

        # 先处理所有CSV文件，获取参考日期
        csv_files = [f for f in files if f.lower().endswith('.csv')]
        for file_path in csv_files:
            # 检查是否已存在
            exists = False
            for info in self.file_infos:
                if info.file_path == file_path:
                    exists = True
                    break

            if exists:
                continue

            # 获取文件时间范围（这会更新converter的reference_date）
            earliest, latest = self.converter.get_time_range(file_path)

            # 添加文件信息
            file_info = FileInfo(
                file_path=file_path,
                file_type='csv',
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

        # 再处理所有MAT文件，使用已获取的参考日期
        mat_files = [f for f in files if f.lower().endswith('.mat')]
        for file_path in mat_files:
            # 检查是否已存在
            exists = False
            for info in self.file_infos:
                if info.file_path == file_path:
                    exists = True
                    break

            if exists:
                continue

            # 获取文件时间范围（使用CSV的参考日期）
            earliest, latest = self.converter.get_time_range(
                file_path, ref_date=self.converter.reference_date
            )

            # 添加文件信息
            file_info = FileInfo(
                file_path=file_path,
                file_type='mat',
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
        self.converter.reference_date = None  # 清除参考日期
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
            # 更新滑动条范围（转换为秒）
            if self.enable_time_filter.isChecked():
                self.start_slider.setValue(self._time_to_ms(earliest) // 1000)
        else:
            self.earliest_label.setText("最早时间: -")

        if latest_times:
            latest = max(latest_times)
            self.latest_label.setText(f"最晚时间: {latest.strftime('%Y-%m-%d %H:%M:%S')}")
            # 更新滑动条范围（转换为秒）
            if self.enable_time_filter.isChecked():
                self.end_slider.setValue(self._time_to_ms(latest) // 1000)
        else:
            self.latest_label.setText("最晚时间: -")

    def _ms_to_time_str(self, ms: int) -> str:
        """将毫秒转换为时间字符串 HH:MM:SS"""
        hours = ms // 3600000
        minutes = (ms % 3600000) // 60000
        seconds = (ms % 60000) // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _time_to_ms(self, dt: datetime) -> int:
        """将 datetime 转换为当天毫秒数"""
        return dt.hour * 3600000 + dt.minute * 60000 + dt.second * 1000

    def on_time_filter_changed(self, state):
        """时间范围过滤复选框状态变化"""
        enabled = self.enable_time_filter.isChecked()
        self.start_slider.setEnabled(enabled)
        self.end_slider.setEnabled(enabled)
        if enabled and self.file_infos:
            self.update_time_range()

    def on_start_time_changed(self, value):
        """起始时间滑动条变化"""
        # 确保起始时间不超过结束时间
        if value > self.end_slider.value():
            self.end_slider.setValue(value)
        ms = value * 1000  # 转换为毫秒
        self.start_time_label.setText(self._ms_to_time_str(ms))

    def on_end_time_changed(self, value):
        """结束时间滑动条变化"""
        # 确保结束时间不早于起始时间
        if value < self.start_slider.value():
            self.start_slider.setValue(value)
        ms = value * 1000  # 转换为毫秒
        self.end_time_label.setText(self._ms_to_time_str(ms))

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

            # 获取合并时间范围
            if self.enable_time_filter.isChecked():
                start_ms = self.start_slider.value() * 1000  # 秒转换为毫秒
                end_ms = self.end_slider.value() * 1000  # 秒转换为毫秒
            else:
                start_ms = 0
                end_ms = 86399999  # 23:59:59.999

            # 合并文件并添加报文头
            output_path = os.path.join(os.getcwd(), "Output.a3h")
            success, error, filtered_count = self.converter.merge_and_header(
                temp_dir, output_path, start_ms, end_ms
            )

            if not success:
                QMessageBox.critical(self, "错误", f"合并失败: {error}")
                return

            # 显示过滤后的报文数量
            if self.enable_time_filter.isChecked():
                time_range_info = f"\n时间范围: {self._ms_to_time_str(start_ms)} - {self._ms_to_time_str(end_ms)}"
                filter_info = f"\n过滤后报文数: {filtered_count}"
            else:
                time_range_info = ""
                filter_info = f"\n总报文数: {filtered_count}"

            # 清理临时目录
            self.converter.cleanup_temp_dir()
            self.file_infos.clear()
            self.file_list.clear()

            QMessageBox.information(
                self,
                "完成",
                f"转换完成！\n输出文件: {output_path}{time_range_info}{filter_info}"
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
