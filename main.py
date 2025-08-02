import os
import random
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLabel, QPushButton, QComboBox, QSystemTrayIcon,
                             QMenu, QProgressBar, QFrame, QHBoxLayout, QMessageBox, QSpinBox, QGridLayout, QTextEdit,
                             QSizePolicy, QStyle, QCheckBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QColor, QPalette, QFont, QFontMetrics


class StretchlyStyleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.autostart_enabled = False
        # 初始化变量
        self.work_time = 30*60  # 默认20分钟（转换为秒）
        self.break_time = 20  # 休息20秒
        self.long_break_time = 5 * 60  # 长休息时间(秒)
        self.break_interval = 4  # 几次短休息后长休息
        self.break_counter = 0
        self.is_working = True
        self.remaining = self.work_time
        self.break_win = None  # 休息窗口引用
        self.break_timer = None  # 休息计时器
        self.normal_break_time = 20
        self.current_break_time = self.normal_break_time

        # 设置窗口属性
        self.setWindowTitle("EyeCare 护眼精灵")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.is_dark = False
        self.init_ui()
        self.init_tray()

        # 主计时器
        self.main_timer = QTimer(self)
        self.main_timer.timeout.connect(self.update_timer)
        self.main_timer.start(1000)  # 1秒更新

        # 默认最小化到托盘
        self.hide()
        self.check_autostart()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def init_ui(self):
        """初始化主界面"""
        main_widget = QWidget()
        main_widget.setObjectName("MainWidget")
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # --- 新增：顶部标题栏（含关闭和最小化按钮）---
        title_bar = QWidget()
        title_bar.setFixedHeight(30)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setAlignment(Qt.AlignRight)

        # 隐藏到托盘按钮
        self.tray_btn = QPushButton()
        # self.tray_btn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMinButton))  # 使用系统图标
        self.tray_btn.setFixedSize(25, 25)

        self.tray_btn.setToolTip("隐藏到系统托盘")
        self.tray_btn.setText("最小化")
        self.tray_btn.clicked.connect(self.hide_to_tray)
        title_layout.addWidget(self.tray_btn)
        layout.addWidget(title_bar)


        # 计时器显示
        self.time_label = QLabel(self.format_time(self.remaining))
        self.time_label.setFont(QFont("Arial", 48, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)

        # 状态标签
        self.status_label = QLabel("工作中...")
        self.status_label.setFont(QFont("Arial", 14))
        self.status_label.setAlignment(Qt.AlignCenter)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, self.work_time)
        self.progress.setValue(self.remaining)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)

        # 控制按钮
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("暂停")
        # self.start_btn.setFixedHeight(40)
        self.start_btn.clicked.connect(self.toggle_timer)

        settings_btn = QPushButton("设置")
        # settings_btn.setFixedHeight(40)
        settings_btn.clicked.connect(self.show_settings)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(settings_btn)

        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addLayout(btn_layout)

        main_widget.setLayout(layout)

        # 应用样式
        self.update_style()

    def hide_to_tray(self):
        """隐藏窗口到系统托盘"""
        self.hide()
        self.tray.showMessage(
            "EyeCare",
            "程序已最小化到托盘，点击图标可恢复",
            QSystemTrayIcon.Information,
            2000  # 显示2秒
        )

    def init_tray(self):
        """初始化系统托盘（带错误处理）"""
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                raise Exception("系统托盘不可用")

            self.tray = QSystemTrayIcon(self)

            # 设置图标（优先尝试自定义图标，失败则用默认图标）
            icon_path = "icon.png"
            if os.path.exists(icon_path):
                self.tray.setIcon(QIcon(icon_path))
            else:
                from PyQt5.QtWidgets import QStyle
                default_icon = self.style().standardIcon(QStyle.SP_MessageBoxInformation)
                self.tray.setIcon(default_icon)

            # 创建菜单
            menu = QMenu()
            show_action = menu.addAction("显示窗口")
            show_action.triggered.connect(self.show_in_top_left)
            exit_action = menu.addAction("退出")
            exit_action.triggered.connect(self.close)
            self.tray.setContextMenu(menu)

            # 点击图标显示窗口
            self.tray.activated.connect(lambda r: self.show_in_top_left() if r == QSystemTrayIcon.Trigger else None)

            self.tray.show()
            self.tray.showMessage("EyeCare", "程序已最小化到托盘", QSystemTrayIcon.Information, 2000)

        except Exception as e:
            print(f"托盘初始化失败: {e}")
            # 回退：直接显示窗口
            self.show_in_top_left()

    def on_tray_activated(self, reason):
        """处理托盘图标点击事件"""
        if reason == QSystemTrayIcon.Trigger:  # 左键点击
            self.show_in_top_left()

    def show_in_top_left(self):
        """在左上角显示窗口"""

        # 设置窗口位置为左上角
        screen_geometry = QApplication.desktop().availableGeometry()
        window_width = self.width()
        self.move(screen_geometry.width() - window_width - 20, 20)  # 距离右上角20像素
        self.show()
        self.raise_()
        self.activateWindow()

    def format_time(self, seconds):
        """格式化时间显示为MM:SS"""
        mins, secs = divmod(seconds, 60)
        return f"{mins:02d}:{secs:02d}"

    def update_style(self):
        """更新主题样式"""
        palette = QPalette()

        if self.is_dark:
            # 深色主题
            bg_color = QColor(40, 44, 52)
            text_color = QColor(220, 220, 220)
            accent_color = QColor(100, 149, 237)  # 蓝色
        else:
            # 浅色主题
            bg_color = QColor(240, 240, 240)
            text_color = QColor(70, 70, 70)
            accent_color = QColor(70, 130, 180)  # 蓝色

        # 应用调色板
        palette.setColor(QPalette.Window, bg_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Button, bg_color.lighter(110))
        palette.setColor(QPalette.ButtonText, text_color)
        palette.setColor(QPalette.Highlight, accent_color)

        self.setPalette(palette)

        # 自定义控件样式
        self.setStyleSheet(f"""
            #MainWidget {{
                background-color: {bg_color.name()};
                border-radius: 15px;
                border: 1px solid {bg_color.darker(120).name()};
            }}
            QProgressBar {{
                border: 1px solid {bg_color.darker(130).name()};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color.name()};
                border-radius: 4px;
            }}
            QPushButton {{
                border: 1px solid {bg_color.darker(130).name()};
                border-radius: 5px;
                padding: 5px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {bg_color.lighter(110).name()};
            }}
        """)

    def update_timer(self):
        """更新计时器"""
        if self.remaining > 0:
            self.remaining -= 1
            self.time_label.setText(self.format_time(self.remaining))
            self.progress.setValue(self.remaining)
        else:
            self.switch_mode()  # 时间到自动切换模式

    def toggle_timer(self):
        """暂停/继续计时 - 修复版"""
        try:
            if self.main_timer.isActive():
                # 暂停逻辑
                self.main_timer.stop()
                self.start_btn.setText("继续")
                self.status_label.setText("已暂停")

                # 暂停休息计时器（如果存在且正在运行）
                if hasattr(self, 'break_timer') and self.break_timer and self.break_timer.isActive():
                    self.break_timer.stop()
            else:
                # 继续逻辑
                self.main_timer.start()
                self.start_btn.setText("暂停")

                # 根据当前模式设置状态文本
                status_text = "工作中..." if self.is_working else "休息中..."
                self.status_label.setText(status_text)

                # 继续休息计时器（如果存在且不在运行）
                if hasattr(self, 'break_timer') and self.break_timer and not self.break_timer.isActive():
                    self.break_timer.start()

        except Exception as e:
            print(f"计时器切换错误: {str(e)}")
            # 恢复默认状态
            self.main_timer.stop()
            if hasattr(self, 'break_timer') and self.break_timer:
                self.break_timer.stop()
            self.start_btn.setText("开始")
            self.status_label.setText("已停止")

    def show_break_notification(self):
        """显示全屏休息提醒 - 完整版（支持长短休息）"""
        # 先清理已有资源
        if self.break_timer:
            self.break_timer.stop()
            self.break_timer.deleteLater()
            self.break_timer = None

        if self.break_win:
            self.break_win.close()
            self.break_win.deleteLater()
            self.break_win = None

        # 随机鼓励语库
        encouragements = [
            "做得好！短暂的休息能让眼睛更明亮哦~ ✨",
            "你值得这片刻的放松，眼睛会感谢你的！ 😊",
            "保护视力就是投资未来，你做得太棒了！ 👏",
            "休息是为了走更远的路，你的眼睛真幸运！ 🌟",
            "聪明的你都知道适时休息，继续保持！ 💪",
            "20秒的放松，换来看世界的清晰！ 🌈",
            "你对自己的照顾，让未来更明亮！ ☀️",
            "爱护眼睛的你，真是闪闪发光！ ⭐",
            "短暂的休息，大大的回报！ 🌸",
            "你的眼睛正在享受这美好的休息时刻！ 🎉"
        ]

        # 根据休息类型设置提示内容
        if self.current_break_time == self.long_break_time:
            title = "🌟 长时间休息时间到！"
            tips = [
                "💡 深度放松建议:",
                "• 起身走动5分钟",
                "• 做全身拉伸运动",
                "• 远眺窗外风景",
                "• 喝杯水放松一下"
            ]
        else:
            title = "👀 眼睛休息时间到！"
            tips = [
                "💡 快速放松建议:",
                "• 远眺20秒放松眼睛",
                "• 眨眼10次湿润眼球",
                "• 深呼吸3次放松身心",
                "• 转动脖子缓解僵硬"
            ]

        # 随机生成柔和背景色
        def random_pastel_color():
            h = random.randint(0, 359)
            s = random.randint(50, 150)
            v = random.randint(200, 255)
            return QColor.fromHsv(h, s, v)

        bg_color = random_pastel_color()
        text_color = "#333333"  # 保持深色文字确保可读性

        # 主窗口设置
        self.break_win = QMainWindow()
        self.break_win.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.break_win.setAttribute(Qt.WA_TranslucentBackground)
        self.break_win.setGeometry(QApplication.desktop().screenGeometry())

        # 背景部件
        bg = QWidget(self.break_win)
        bg.setStyleSheet(
            f"background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 0.88);")
        bg.setGeometry(self.break_win.geometry())

        # 主容器
        main_container = QWidget()
        main_container.setFixedSize(self.break_win.size())
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setAlignment(Qt.AlignCenter)

        # 内容面板
        content_panel = QFrame()
        content_panel.setMinimumSize(820, 620)
        content_panel.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.92);
            border-radius: 30px;
            padding: 35px;
        """)

        # 内容布局
        content_layout = QVBoxLayout(content_panel)
        content_layout.setAlignment(Qt.AlignCenter)
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(25, 25, 25, 25)

        # 1. 表情图标
        icon = QLabel(random.choice(["👀", "👁️", "😊", "🌿", "🌞", "🌸"]))
        icon.setFont(QFont("Arial", 110))
        icon.setStyleSheet(f"color: {bg_color.darker(150).name()}; margin-bottom: 15px;")
        icon.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(icon)

        # 2. 主标题
        title_label = QLabel(title)
        title_label.setFont(QFont("微软雅黑", 30, QFont.Bold))
        title_label.setStyleSheet(f"""
            color: {bg_color.darker(200).name()};
            qproperty-wordWrap: true;
            padding: 8px 15px;
            margin: 5px 0;
            min-width: 780px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title_label)

        # 3. 鼓励语
        encouragement = QLabel(random.choice(encouragements))
        encouragement.setFont(QFont("微软雅黑", 21))
        metrics = QFontMetrics(encouragement.font())
        text_width = metrics.width(encouragement.text())

        if text_width > 700:
            encouragement.setStyleSheet(f"""
                color: {text_color};
                qproperty-wordWrap: true;
                padding: 10px 25px;
                min-width: 750px;
                max-width: 750px;
            """)
            encouragement.setFixedHeight(80)
        else:
            encouragement.setStyleSheet(f"color: {text_color}; padding: 10px 25px;")

        encouragement.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(encouragement)

        # 4. 倒计时
        self.break_timer_label = QLabel(f"{self.current_break_time}秒")
        self.break_timer_label.setFont(QFont("Arial", 70, QFont.Bold))
        self.break_timer_label.setStyleSheet(f"""
            color: {bg_color.darker(200).name()};
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 15px;
            padding: 12px 35px;
            min-width: 180px;
            margin: 10px 0;
        """)
        content_layout.addWidget(self.break_timer_label)

        # 5. 休息建议
        tips_frame = QWidget()
        tips_layout = QVBoxLayout(tips_frame)
        tips_layout.setSpacing(4)
        tips_layout.setContentsMargins(10, 5, 10, 5)

        test_font = QFont("微软雅黑", 15)
        fm = QFontMetrics(test_font)
        char_width = fm.width("中")
        max_chars_per_line = 12

        for i, tip in enumerate(tips):
            item_widget = QWidget()
            item_layout = QHBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(3)

            bullet_symbol = "▪"
            bullet = QLabel(bullet_symbol if i > 0 else "→")
            bullet.setFont(QFont("Arial", 14))
            bullet.setStyleSheet(f"color: {text_color}; min-width: 10px;")
            item_layout.addWidget(bullet)

            label = QLabel()
            label.setFont(QFont("微软雅黑", 15))
            label.setStyleSheet(f"color: {text_color}; margin:0; padding:0;")

            wrapped_text = []
            current_line = ""
            for char in tip:
                if len(current_line) >= max_chars_per_line:
                    wrapped_text.append(current_line)
                    current_line = char
                else:
                    current_line += char
            if current_line:
                wrapped_text.append(current_line)

            label.setText("\n".join(wrapped_text))
            label.setWordWrap(True)
            label.setFixedWidth(char_width * max_chars_per_line + 10)

            item_layout.addWidget(label)
            tips_layout.addWidget(item_widget)

        total_lines = sum(len(tip) // max_chars_per_line + 1 for tip in tips)
        tips_frame.setFixedHeight(total_lines * 24 + 10)

        content_layout.addWidget(tips_frame)

        # 6. 跳过按钮
        skip_btn = QPushButton(f"好的，我已休息 ({self.current_break_time}秒后自动继续)")
        skip_btn.setFixedHeight(58)
        skip_btn.setMinimumWidth(340)
        skip_btn.setFont(QFont("微软雅黑", 15, QFont.Bold))
        skip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color.darker(150).name()};
                color: white;
                border-radius: 8px;
                padding: 8px 16px;
                margin-top: 15px;
            }}
            QPushButton:hover {{
                background-color: {bg_color.darker(180).name()};
            }}
        """)
        skip_btn.clicked.connect(self.skip_break)
        content_layout.addWidget(skip_btn)

        main_layout.addWidget(content_panel)
        self.break_win.setCentralWidget(main_container)

        # 初始化倒计时
        self.break_countdown = self.current_break_time
        self.break_timer = QTimer(self.break_win)
        self.break_timer.timeout.connect(self.update_break_timer)
        self.break_timer.start(1000)

        self.break_win.show()

    def update_break_timer(self):
        """更新休息倒计时 - 安全版本"""
        try:
            if not hasattr(self, 'break_countdown') or not self.break_timer:
                return

            if self.break_countdown > 0:
                self.break_countdown -= 1
                if hasattr(self, 'break_timer_label'):
                    self.break_timer_label.setText(f"{self.break_countdown}秒")
            else:
                self.cleanup_break_timer()
                self.switch_mode()
        except Exception as e:
            print(f"倒计时更新错误: {str(e)}")
            self.cleanup_break_timer()

    def cleanup_break_timer(self):
        """安全清理休息计时器"""
        try:
            if hasattr(self, 'break_timer') and self.break_timer:
                self.break_timer.stop()
                self.break_timer.deleteLater()
                self.break_timer = None
        except:
            pass

    def skip_break(self):
        """跳过休息 - 安全版本"""
        self.cleanup_break_timer()
        if hasattr(self, 'break_win') and self.break_win:
            try:
                self.break_win.close()
                self.break_win.deleteLater()
            except:
                pass
            finally:
                self.break_win = None
        self.switch_mode()

    def switch_mode(self):
        """切换工作/休息模式 - 修复版"""
        self.is_working = not self.is_working

        if self.is_working:
            # 切换到工作模式
            self.remaining = self.work_time
            self.status_label.setText("工作中...")
            self.progress.setMaximum(self.work_time)
            self.progress.setValue(self.remaining)

            # 关闭休息窗口（如果存在）
            if self.break_win:
                self.break_win.close()
                self.break_win = None
        else:
            # 更新休息计数器并确定休息时长
            self.break_counter += 1
            if self.break_counter % self.break_interval == 0:  # 长休息
                self.current_break_time = self.long_break_time
                self.status_label.setText("长时间休息中...")
            else:  # 普通休息
                self.current_break_time = self.normal_break_time
                self.status_label.setText("休息中...")

            # 设置剩余时间和进度条
            self.remaining = self.current_break_time
            self.progress.setMaximum(self.current_break_time)
            self.progress.setValue(self.remaining)

            # 显示休息通知
            self.show_break_notification()

        # 更新时间显示
        self.time_label.setText(self.format_time(self.remaining))

        # 确保主计时器运行
        if not self.main_timer.isActive():
            self.main_timer.start()

    def set_autostart(self, enable=True):
        """设置开机自启动"""
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
        exe_path = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])

        try:
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_WRITE) as reg_key:
                if enable:
                    winreg.SetValueEx(reg_key, "EyeCare", 0, winreg.REG_SZ, f'"{exe_path}"')
                else:
                    try:
                        winreg.DeleteValue(reg_key, "EyeCare")
                    except FileNotFoundError:
                        pass
            self.autostart_enabled = enable
            return True
        except Exception as e:
            print(f"设置自启动失败: {e}")
            return False

    def save_and_close(self):
        """保存设置并关闭对话框"""
        try:
            # 保存自启动设置
            if hasattr(self, 'autostart_cb'):
                self.set_autostart(self.autostart_cb.isChecked())

            # 保存其他设置
            new_work_time = self.work_spin.value() * 60
            new_break_time = self.break_spin.value()
            new_theme = self.theme_combo.currentText() == "深色f模式"

            # 应用新设置
            if self.is_working:
                self.remaining = new_work_time - (self.work_time - self.remaining)
            else:
                self.remaining = new_break_time - (self.break_time - self.remaining)

            self.work_time = new_work_time
            self.break_time = new_break_time

            # 更新主题
            if new_theme != self.is_dark:
                self.is_dark = new_theme
                self.update_style()

            # 更新UI
            self.progress.setMaximum(self.work_time if self.is_working else self.break_time)
            self.progress.setValue(self.remaining)
            self.time_label.setText(self.format_time(self.remaining))

            QMessageBox.information(self, "提示", "设置已保存！")
            self.sender().parent().parent().accept()  # 关闭对话框

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错:\n{str(e)}")

    def show_settings(self):
        """显示设置对话框"""
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QCheckBox, QVBoxLayout, QLabel, QSpinBox, QComboBox

        settings_dialog = QDialog(self)
        settings_dialog.setWindowTitle("设置")
        settings_dialog.setFixedSize(300, 300)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 工作时间设置
        work_label = QLabel("工作时间 (分钟):")
        self.work_spin = QSpinBox()
        self.work_spin.setRange(1, 120)
        self.work_spin.setValue(self.work_time // 60)

        # 休息时间设置
        break_label = QLabel("休息时间 (秒):")
        self.break_spin = QSpinBox()
        self.break_spin.setRange(5, 300)
        self.break_spin.setValue(self.break_time)

        # 主题设置
        theme_label = QLabel("主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色模式", "深色模式"])
        self.theme_combo.setCurrentIndex(1 if self.is_dark else 0)

        # 自启动设置
        self.autostart_cb = QCheckBox("开机自动启动")
        self.autostart_cb.setChecked(self.autostart_enabled)

        # 添加到布局
        layout.addWidget(work_label)
        layout.addWidget(self.work_spin)
        layout.addWidget(break_label)
        layout.addWidget(self.break_spin)
        layout.addWidget(theme_label)
        layout.addWidget(self.theme_combo)
        layout.addWidget(self.autostart_cb)
        layout.addStretch()

        # 创建按钮框
        button_box = QDialogButtonBox()
        save_button = button_box.addButton("保存", QDialogButtonBox.AcceptRole)
        cancel_button = button_box.addButton("取消", QDialogButtonBox.RejectRole)
        layout.addWidget(button_box)

        settings_dialog.setLayout(layout)

        def save_all_settings():
            """保存所有设置"""
            try:
                # 保存自启动设置
                self.set_autostart(self.autostart_cb.isChecked())

                # 保存其他设置
                new_work_time = self.work_spin.value() * 60
                new_break_time = self.break_spin.value()
                new_theme = self.theme_combo.currentText() == "深色模式"

                # 应用新设置
                if self.is_working:
                    self.remaining = new_work_time - (self.work_time - self.remaining)
                else:
                    self.remaining = new_break_time - (self.break_time - self.remaining)

                self.work_time = new_work_time
                self.break_time = new_break_time

                # 更新主题
                if new_theme != self.is_dark:
                    self.is_dark = new_theme
                    self.update_style()

                # 更新UI
                self.progress.setMaximum(self.work_time if self.is_working else self.break_time)
                self.progress.setValue(self.remaining)
                self.time_label.setText(self.format_time(self.remaining))

                QMessageBox.information(settings_dialog, "提示", "设置已保存！")
                settings_dialog.accept()

            except Exception as e:
                QMessageBox.critical(settings_dialog, "错误", f"保存设置时出错:\n{str(e)}")

        # 连接信号
        save_button.clicked.connect(save_all_settings)
        cancel_button.clicked.connect(settings_dialog.reject)

        settings_dialog.exec_()

    def check_autostart(self):
        """检查当前是否设置了自启动"""
        import winreg
        key = winreg.HKEY_CURRENT_USER
        subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            with winreg.OpenKey(key, subkey, 0, winreg.KEY_READ) as reg_key:
                try:
                    value, _ = winreg.QueryValueEx(reg_key, "EyeCare")
                    exe_path = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])
                    self.autostart_enabled = f'"{exe_path}"' == value
                except FileNotFoundError:
                    self.autostart_enabled = False
        except Exception as e:
            print(f"检查自启动失败: {e}")
            self.autostart_enabled = False
    def save_settings(self, dialog):
        """保存设置"""
        try:
            # 获取设置值
            new_work_time = self.work_spin.value() * 60
            new_break_time = self.break_spin.value()
            new_theme = self.theme_combo.currentText() == "深色模式"

            # 应用新设置
            if self.is_working:
                self.remaining = new_work_time - (self.work_time - self.remaining)
            else:
                self.remaining = new_break_time - (self.break_time - self.remaining)

            self.work_time = new_work_time
            self.break_time = new_break_time

            # 更新主题
            if new_theme != self.is_dark:
                self.is_dark = new_theme
                self.update_style()

            # 更新UI
            self.progress.setMaximum(self.work_time if self.is_working else self.break_time)
            self.progress.setValue(self.remaining)
            self.time_label.setText(self.format_time(self.remaining))

            dialog.accept()
            QMessageBox.information(self, "提示", "设置已保存！")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置时出错:\n{str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件 - 增强版"""
        self.cleanup_break_timer()
        if hasattr(self, 'main_timer') and self.main_timer:
            self.main_timer.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion样式

    # 设置高DPI支持
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    window = StretchlyStyleApp()
    sys.exit(app.exec_())