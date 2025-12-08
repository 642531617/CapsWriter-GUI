import sys
import os
import subprocess
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QTextEdit, QLabel,
                               QTabWidget, QSplitter, QGroupBox, QPlainTextEdit,
                               QMessageBox, QListWidget, QFileDialog, QAbstractItemView)
from PySide6.QtCore import QThread, Signal, Qt, QTimer
from PySide6.QtGui import QFont, QTextCursor, QIcon


# ===========================
# 辅助函数：去除 ANSI 颜色代码
# ===========================
def clean_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


# ===========================
# 自定义组件：支持拖拽的文件列表
# ===========================
class DragDropListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if os.path.isfile(f):
                items = [self.item(i).text() for i in range(self.count())]
                if f not in items:
                    self.addItem(f)


# ===========================
# 长驻进程工作线程 (用于 Server 和 Mic Client)
# ===========================
class ProcessWorker(QThread):
    log_signal = Signal(str)
    status_signal = Signal(bool)

    def __init__(self, script_name):
        super().__init__()
        self.script_name = script_name
        self.process = None
        self.is_running = True

    def run(self):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            # 确定基准目录
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                exe_name = self.script_name.replace('.py', '.exe')
                cmd = [os.path.join(base_dir, exe_name)]
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cmd = [sys.executable, "-u", self.script_name]

            self.log_signal.emit(f"正在尝试启动: {cmd}")
            self.log_signal.emit(f"工作目录 (CWD): {base_dir}")

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=base_dir,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.status_signal.emit(True)

            while self.is_running:
                if self.process.poll() is not None:
                    break

                raw_line = self.process.stdout.readline()
                if raw_line:
                    try:
                        line = raw_line.decode('utf-8').rstrip()
                    except UnicodeDecodeError:
                        try:
                            line = raw_line.decode('gbk').rstrip()
                        except:
                            line = raw_line.decode('utf-8', errors='ignore').rstrip()

                    self.log_signal.emit(line)

            if self.process:
                ret = self.process.returncode
                self.log_signal.emit(f"进程已退出，代码: {ret}")

        except Exception as e:
            self.log_signal.emit(f"启动发生异常: {str(e)}")
        finally:
            self.status_signal.emit(False)

    def stop(self):
        self.is_running = False
        if self.process:
            self.log_signal.emit(f"正在终止进程 PID: {self.process.pid}...")
            # 【核心修复】使用 taskkill /F /T 强制杀死进程树
            if sys.platform == 'win32':
                try:
                    subprocess.run(f"taskkill /F /T /PID {self.process.pid}",
                                   shell=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except Exception:
                    pass

            # 兜底调用 terminate
            try:
                self.process.terminate()
                self.process.wait(timeout=1)
            except:
                pass


# ===========================
# 任务型工作线程 (用于文件转录)
# ===========================
class TaskWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, script_name, args):
        super().__init__()
        self.script_name = script_name
        self.args = args
        self.process = None  # 【修改】改为类属性以便停止

    def run(self):
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        try:
            if getattr(sys, 'frozen', False):
                base_dir = os.path.dirname(sys.executable)
                exe_name = self.script_name.replace('.py', '.exe')
                cmd = [os.path.join(base_dir, exe_name)] + self.args
            else:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                cmd = [sys.executable, "-u", self.script_name] + self.args

            self.log_signal.emit(f">>> 开始转录 {len(self.args)} 个文件...")

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=base_dir,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            while True:
                # 【修改】增加对 process 是否存在的检查
                if not self.process: break

                raw_line = self.process.stdout.readline()
                if not raw_line and self.process.poll() is not None:
                    break
                if raw_line:
                    try:
                        line = raw_line.decode('utf-8').rstrip()
                    except UnicodeDecodeError:
                        try:
                            line = raw_line.decode('gbk').rstrip()
                        except:
                            line = raw_line.decode('utf-8', errors='ignore').rstrip()
                    self.log_signal.emit(line)

            self.log_signal.emit(">>> 转录任务结束。")

        except Exception as e:
            self.log_signal.emit(f"转录执行错误: {str(e)}")
        finally:
            self.finished_signal.emit()

    # 【修改】增加 stop 方法
    def stop(self):
        if self.process:
            if sys.platform == 'win32':
                try:
                    subprocess.run(f"taskkill /F /T /PID {self.process.pid}",
                                   shell=True,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                except:
                    pass
            try:
                self.process.terminate()
            except:
                pass


# ===========================
# 主窗口 UI
# ===========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CapsWriter Offline - 控制台")
        self.resize(1000, 750)

        icon_path = os.path.join("assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = "icon.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMainWindow { background-color: #f0f2f5; }
            QGroupBox { font-weight: bold; border: 1px solid #dcdcdc; border-radius: 6px; margin-top: 10px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; color: #333; }
            QTextEdit, QPlainTextEdit, QListWidget { border: 1px solid #ccc; border-radius: 4px; background-color: #fafafa; font-family: "Consolas", "Microsoft YaHei"; font-size: 10pt; }
            QPushButton { background-color: #0078d4; color: white; border-radius: 4px; padding: 8px 16px; font-weight: bold; }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:pressed { background-color: #005a9e; }
            QPushButton:disabled { background-color: #ccc; }
            QPushButton#stop_btn, QPushButton#clear_btn { background-color: #d13438; }
            QPushButton#stop_btn:hover, QPushButton#clear_btn:hover { background-color: #a4262c; }
            QTabWidget::pane { border: 1px solid #ccc; background: white; }
            QTabBar::tab { background: #e1e1e1; padding: 8px 20px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #0078d4; }
        """)

        self.server_thread = None
        self.client_thread = None
        self.transcribe_thread = None
        self.server_running = False
        self.server_buffer = []
        self.client_buffer = []
        self.last_server_line = ""
        self.last_client_line = ""

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.flush_logs)
        self.log_timer.start(100)

        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        control_layout = QHBoxLayout()
        self.btn_start = QPushButton("启动服务 (Start)")
        self.btn_start.clicked.connect(self.start_services)
        self.btn_stop = QPushButton("停止服务 (Stop)")
        self.btn_stop.setObjectName("stop_btn")
        self.btn_stop.clicked.connect(self.stop_services)
        self.btn_stop.setEnabled(False)

        self.status_label = QLabel("状态: 未运行")
        self.status_label.setStyleSheet("color: #666; font-weight: bold; margin-left: 15px;")

        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        layout.addLayout(control_layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        self.monitor_tab = QWidget()
        self.setup_monitor_tab()
        self.tabs.addTab(self.monitor_tab, "运行监控")

        self.transcribe_tab = QWidget()
        self.setup_transcribe_tab()
        self.tabs.addTab(self.transcribe_tab, "文件转录")

        self.hotwords_tab = QWidget()
        self.setup_hotwords_tab()
        self.tabs.addTab(self.hotwords_tab, "热词管理")

        self.config_tab = QWidget()
        self.setup_config_tab()
        self.tabs.addTab(self.config_tab, "设置 (Config)")

    def setup_monitor_tab(self):
        layout = QVBoxLayout(self.monitor_tab)
        splitter = QSplitter(Qt.Vertical)

        server_group = QGroupBox("服务端日志 (Server Log)")
        s_layout = QVBoxLayout(server_group)
        self.server_log = QTextEdit()
        self.server_log.setReadOnly(True)
        self.server_log.document().setMaximumBlockCount(2000)
        s_layout.addWidget(self.server_log)
        splitter.addWidget(server_group)

        client_group = QGroupBox("麦克风客户端 / 识别结果 (Client Log)")
        c_layout = QVBoxLayout(client_group)
        self.client_log = QTextEdit()
        self.client_log.setReadOnly(True)
        self.client_log.setFont(QFont("Microsoft YaHei", 11))
        self.client_log.document().setMaximumBlockCount(2000)
        c_layout.addWidget(self.client_log)
        splitter.addWidget(client_group)

        layout.addWidget(splitter)

    def setup_transcribe_tab(self):
        layout = QVBoxLayout(self.transcribe_tab)
        file_group = QGroupBox("待转录文件 (支持拖拽)")
        f_layout = QVBoxLayout(file_group)
        self.file_list = DragDropListWidget()
        f_layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加文件...")
        btn_add.clicked.connect(self.add_files_dialog)
        btn_clear = QPushButton("清空列表")
        btn_clear.setObjectName("clear_btn")
        btn_clear.clicked.connect(self.file_list.clear)
        self.btn_transcribe = QPushButton("开始转录 (Start Transcribe)")
        self.btn_transcribe.setStyleSheet("background-color: #107c10;")
        self.btn_transcribe.clicked.connect(self.start_transcription)

        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_transcribe)
        f_layout.addLayout(btn_layout)

        layout.addWidget(file_group, 2)

        log_group = QGroupBox("转录进度日志")
        l_layout = QVBoxLayout(log_group)
        self.transcribe_log = QTextEdit()
        self.transcribe_log.setReadOnly(True)
        self.transcribe_log.setPlaceholderText("转录日志将显示在这里...")
        l_layout.addWidget(self.transcribe_log)
        layout.addWidget(log_group, 3)

    def setup_hotwords_tab(self):
        layout = QVBoxLayout(self.hotwords_tab)
        hw_tabs = QTabWidget()
        self.editors = {}
        files = {
            "中文热词 (hot-zh.txt)": "hot-zh.txt",
            "英文热词 (hot-en.txt)": "hot-en.txt",
            "替换规则 (hot-rule.txt)": "hot-rule.txt",
            "日记关键词 (keywords.txt)": "keywords.txt"
        }
        for title, filename in files.items():
            tab = QWidget()
            t_layout = QVBoxLayout(tab)
            editor = QPlainTextEdit()
            self.editors[filename] = editor
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    editor.setPlainText(f.read())
            else:
                editor.setPlaceholderText(f"文件 {filename} 不存在，保存时将自动创建。")
            t_layout.addWidget(editor)
            hw_tabs.addTab(tab, title)
        layout.addWidget(hw_tabs)

        btn_save = QPushButton("保存所有热词修改")
        btn_save.clicked.connect(lambda: self.save_files(self.editors))
        layout.addWidget(btn_save)

    def setup_config_tab(self):
        layout = QVBoxLayout(self.config_tab)
        self.config_editor = QPlainTextEdit()
        self.config_editor.setFont(QFont("Consolas", 10))
        if os.path.exists("config.py"):
            with open("config.py", 'r', encoding='utf-8') as f:
                self.config_editor.setPlainText(f.read())
        layout.addWidget(self.config_editor)

        btn_save_conf = QPushButton("保存配置 (config.py)")
        btn_save_conf.clicked.connect(self.save_config)
        layout.addWidget(btn_save_conf)
        layout.addWidget(QLabel("提示: 修改配置需要重启服务才能生效。"))

    def start_services(self):
        if getattr(sys, 'frozen', False):
            server_script = "core_server.exe"
            client_script = "core_client.exe"
            base_dir = os.path.dirname(sys.executable)
        else:
            server_script = "core_server.py"
            client_script = "core_client.py"
            base_dir = os.path.dirname(os.path.abspath(__file__))

        server_path = os.path.join(base_dir, server_script)
        if not os.path.exists(server_path):
            QMessageBox.critical(self, "错误", f"未找到核心文件:\n{server_path}\n请确保打包完整。")
            return

        self.server_log.clear()
        self.client_log.clear()
        self.server_log.append(f">>> 正在启动 Server ({server_script})...")

        self.server_thread = ProcessWorker(server_script)
        self.server_thread.log_signal.connect(self.buffer_server_log)
        self.server_thread.status_signal.connect(self.on_server_status_change)
        self.server_thread.start()

        self.client_log.append(f">>> 正在启动 Mic Client ({client_script})...")
        self.client_thread = ProcessWorker(client_script)
        self.client_thread.log_signal.connect(self.buffer_client_log)
        self.client_thread.start()

        self.update_ui_state(running=True)

    def stop_services(self):
        if self.client_thread: self.client_thread.stop()
        if self.server_thread: self.server_thread.stop()
        self.update_ui_state(running=False)
        self.server_log.append("\n>>> 服务已停止")

    def on_server_status_change(self, is_running):
        self.server_running = is_running

    def update_ui_state(self, running):
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)
        self.status_label.setText("状态: 正在运行" if running else "状态: 已停止")
        self.status_label.setStyleSheet(
            f"color: {'#00cc00' if running else '#666'}; font-weight: bold; margin-left: 15px;")

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音视频文件", "", "Audio/Video (*.mp3 *.wav *.mp4 *.m4a *.flac);;All Files (*.*)")
        if files:
            self.file_list.addItems(files)

    def start_transcription(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加要转录的文件！")
            return
        if not self.server_running:
            QMessageBox.critical(self, "错误", "转录功能依赖服务端。\n请先点击顶部的 [启动服务] 按钮！")
            return

        files = [self.file_list.item(i).text() for i in range(self.file_list.count())]

        self.btn_transcribe.setEnabled(False)
        self.btn_transcribe.setText("转录中...")
        self.transcribe_log.clear()

        if getattr(sys, 'frozen', False):
            script_name = "core_client.exe"
        else:
            script_name = "core_client.py"

        self.transcribe_thread = TaskWorker(script_name, files)
        self.transcribe_thread.log_signal.connect(self.update_transcribe_log)
        self.transcribe_thread.finished_signal.connect(self.on_transcribe_finished)
        self.transcribe_thread.start()

    def update_transcribe_log(self, text):
        clean_text = clean_ansi_codes(text)
        self.transcribe_log.append(clean_text)
        self.transcribe_log.moveCursor(QTextCursor.End)

    def on_transcribe_finished(self):
        self.btn_transcribe.setEnabled(True)
        self.btn_transcribe.setText("开始转录 (Start Transcribe)")
        QMessageBox.information(self, "完成", "所有文件处理任务已结束。")

    def buffer_server_log(self, text):
        clean_text = clean_ansi_codes(text)
        if not clean_text.strip(): return
        if clean_text == self.last_server_line: return
        self.server_buffer.append(clean_text)
        self.last_server_line = clean_text

    def buffer_client_log(self, text):
        clean_text = clean_ansi_codes(text)
        if not clean_text.strip(): return
        if clean_text == self.last_client_line: return
        self.client_buffer.append(clean_text)
        self.last_client_line = clean_text

    def flush_logs(self):
        if self.server_buffer:
            self.server_log.append("\n".join(self.server_buffer))
            self.server_buffer.clear()
            self.server_log.moveCursor(QTextCursor.End)
        if self.client_buffer:
            self.client_log.append("\n".join(self.client_buffer))
            self.client_buffer.clear()
            self.client_log.moveCursor(QTextCursor.End)

    def save_files(self, editor_dict):
        try:
            for filename, editor in editor_dict.items():
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(editor.toPlainText())
            QMessageBox.information(self, "成功", "热词文件已保存！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def save_config(self):
        try:
            with open("config.py", 'w', encoding='utf-8') as f:
                f.write(self.config_editor.toPlainText())
            QMessageBox.information(self, "成功", "配置已保存！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def closeEvent(self, event):
        # 停止所有服务
        self.stop_services()
        # 停止正在进行的转录任务
        if self.transcribe_thread:
            self.transcribe_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())