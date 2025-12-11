import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTableWidget, QTableWidgetItem,
                             QPushButton, QLabel, QLineEdit, QTextEdit, QMessageBox,
                             QHeaderView, QFrame, QProgressBar, QMenu, QAction,
                             QDialog, QFormLayout, QCheckBox, QSpinBox, QTabWidget,
                             QGroupBox, QSplitter, QTreeWidget, QTreeWidgetItem, QFileDialog,
                             QGridLayout, QScrollArea, QSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon
import json
import os
from datetime import datetime
import subprocess
from time import sleep
import win32gui
import win32con
from ldplayer_slot import PlayerSlot


class WorkerThread(QThread):
    """Thread để chạy automation"""
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    status_signal = pyqtSignal(str, str, str)  # account, status, detail
    action_signal = pyqtSignal(str, str)  # account, action detail
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, accounts, ldplayer_instances):
        super().__init__()
        self.accounts = accounts
        self.ldplayer_instances = ldplayer_instances
        self.is_running = True
        self.worker_threads = []  # Track all worker threads
    
    def run(self):
        try:
            from main_clicked import MainClicked
            from auto_clicked import ldplayer
            
            ldplayer_ids = ldplayer().get_ldplayer_ids()
            
            if len(ldplayer_ids) < len(self.accounts):
                self.finished_signal.emit(False, f"Chỉ có {len(ldplayer_ids)} LDPlayer nhưng có {len(self.accounts)} tài khoản")
                return
            
            import threading
            
            for i, account in enumerate(self.accounts):
                if not self.is_running:
                    break
                
                ld_id, ld_name = ldplayer_ids[i]
                email = account.split('|')[0]
                
                self.log_signal.emit(f"Khởi động: {ld_name} - {email}", "info")
                self.status_signal.emit(email, "Đang khởi động", ld_name)
                
                main_clicked = MainClicked({
                    "dataaccount_clicked": account,
                    "name_ldplayer": ld_name,
                    "ldplayer_id": ld_id,
                    "account_len": len(self.accounts),
                    "account_index": i,
                    "action_callback": self.on_action
                })
                
                thread = threading.Thread(
                    target=main_clicked.main_clicked,
                    daemon=False
                )
                self.worker_threads.append((thread, main_clicked))
                thread.start()
                self.progress_signal.emit(i + 1, len(self.accounts))
            
            for thread, _ in self.worker_threads:
                thread.join()
            
            if self.is_running:
                self.finished_signal.emit(True, "Hoàn thành tất cả!")
            else:
                self.finished_signal.emit(False, "Đã dừng bởi người dùng")
            
        except Exception as e:
            self.finished_signal.emit(False, f"Lỗi: {str(e)}")
    
    def on_action(self, email, action):
        """Callback từ MainClicked để emit action signal"""
        self.action_signal.emit(email, action)
    
    def stop(self):
        """Dừng automation"""
        self.is_running = False
        for thread, main_clicked in self.worker_threads:
            if main_clicked and hasattr(main_clicked, 'stop_automation'):
                main_clicked.stop_automation()


class AccountDialog(QDialog):
    """Dialog thêm/sửa tài khoản"""
    def __init__(self, parent=None, account_data=None):
        super().__init__(parent)
        self.account_data = account_data
        self.init_ui()
        
        if account_data:
            self.load_data(account_data)
    
    def init_ui(self):
        self.setWindowTitle("Thông tin tài khoản")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QLineEdit {
                background: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 2px solid #64b5f6;
            }
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1565c0;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📝 Thông tin tài khoản")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #64b5f6; padding: 10px;")
        layout.addWidget(header)
        
        # Form
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignRight)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@email.com")
        self.email_input.setMinimumHeight(35)
        form.addRow("📧 Email:", self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Nhập mật khẩu")
        self.password_input.setMinimumHeight(35)
        
        # Toggle password visibility
        password_layout = QHBoxLayout()
        password_layout.addWidget(self.password_input)
        
        show_pass_btn = QPushButton("👁")
        show_pass_btn.setFixedSize(35, 35)
        show_pass_btn.setCheckable(True)
        show_pass_btn.toggled.connect(lambda checked: self.password_input.setEchoMode(
            QLineEdit.Normal if checked else QLineEdit.Password
        ))
        password_layout.addWidget(show_pass_btn)
        
        form.addRow("🔒 Password:", password_layout)
        
        self.homework_input = QLineEdit()
        self.homework_input.setPlaceholderText("Tên bài tập hoặc khóa học")
        self.homework_input.setMinimumHeight(35)
        form.addRow("📚 Bài tập:", self.homework_input)
        
        layout.addLayout(form)
        
        layout.addStretch()
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background: #ddd;")
        layout.addWidget(line)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Lưu")
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        save_btn.setMinimumHeight(35)
        
        cancel_btn = QPushButton("❌ Hủy")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_data(self, data):
        parts = data.split('|')
        if len(parts) >= 3:
            self.email_input.setText(parts[0])
            self.password_input.setText(parts[1])
            self.homework_input.setText(parts[2])
    
    def get_data(self):
        return f"{self.email_input.text()}|{self.password_input.text()}|{self.homework_input.text()}"


class BulkAddDialog(QDialog):
    """Dialog thêm nhiều tài khoản"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Thêm nhiều tài khoản")
        self.setModal(True)
        self.setMinimumSize(650, 550)
        self.setStyleSheet("""
            QDialog {
                background: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QTextEdit {
                background: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
            }
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1565c0;
            }
            QGroupBox {
                border: 2px solid #3e3e3e;
                border-radius: 6px;
                background: #252525;
                color: #e0e0e0;
            }
            QGroupBox::title {
                color: #64b5f6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("📋 Thêm nhiều tài khoản")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #64b5f6; padding: 10px;")
        layout.addWidget(header)
        
        # Instructions
        info = QLabel(
            "📝 <b>Hướng dẫn:</b> Nhập mỗi dòng một tài khoản theo định dạng:<br>"
            "<code style='background: #f0f0f0; padding: 5px;'>email|password|bài_tập</code>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #555; padding: 12px; background: #e3f2fd; border-radius: 6px; border-left: 4px solid #1976d2;")
        layout.addWidget(info)
        
        # Text area
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText(
            "Ví dụ:\n"
            "user1@email.com|password123|Bài tập Python\n"
            "user2@email.com|pass456|Khóa học AI\n"
            "user3@email.com|mypass789|Project Web"
        )
        self.text_area.setStyleSheet("font-family: 'Consolas', monospace; font-size: 10pt;")
        layout.addWidget(self.text_area)
        
        # Preview
        preview_group = QGroupBox("📊 Thống kê")
        preview_layout = QVBoxLayout()
        
        self.preview_list = QLabel("Chưa có dữ liệu")
        self.preview_list.setStyleSheet("padding: 10px; background: #f5f5f5; border-radius: 4px;")
        preview_layout.addWidget(self.preview_list)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Connect text changed to preview
        self.text_area.textChanged.connect(self.update_preview)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        import_btn = QPushButton("📁 Import từ file")
        import_btn.setObjectName("secondaryBtn")
        import_btn.clicked.connect(self.import_from_file)
        import_btn.setMinimumHeight(35)
        btn_layout.addWidget(import_btn)
        
        btn_layout.addStretch()
        
        add_btn = QPushButton("✅ Thêm tất cả")
        add_btn.clicked.connect(self.accept)
        add_btn.setDefault(True)
        add_btn.setMinimumHeight(35)
        btn_layout.addWidget(add_btn)
        
        cancel_btn = QPushButton("❌ Hủy")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def update_preview(self):
        """Cập nhật preview"""
        text = self.text_area.toPlainText().strip()
        if not text:
            self.preview_list.setText("Chưa có dữ liệu")
            return
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        valid_count = sum(1 for line in lines if line.count('|') >= 2)
        invalid_count = len(lines) - valid_count
        
        preview_text = f"<b>Tổng số dòng:</b> {len(lines)}<br>"
        preview_text += f"<b style='color: #4caf50;'>✓ Hợp lệ:</b> {valid_count}<br>"
        
        if invalid_count > 0:
            preview_text += f"<b style='color: #f44336;'>✗ Không hợp lệ:</b> {invalid_count}"
        
        self.preview_list.setText(preview_text)
    
    def import_from_file(self):
        """Import từ file TXT"""
        filename, _ = QFileDialog.getOpenFileName(self, "Chọn file", "", "Text Files (*.txt);;All Files (*)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.text_area.setPlainText(content)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể đọc file: {str(e)}")
    
    def get_accounts(self):
        """Lấy danh sách tài khoản"""
        text = self.text_area.toPlainText().strip()
        if not text:
            return []
        
        accounts = []
        for line in text.split('\n'):
            line = line.strip()
            if line and line.count('|') >= 2:
                accounts.append(line)
        
        return accounts


class SettingsDialog(QDialog):
    """Dialog cài đặt"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = self.load_settings()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("Cài đặt")
        self.setModal(True)
        self.setMinimumSize(550, 450)
        self.setStyleSheet("""
            QDialog {
                background: #1e1e1e;
                color: #e0e0e0;
            }
            QLabel {
                color: #e0e0e0;
            }
            QSpinBox {
                background: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #3e3e3e;
                border-radius: 4px;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1565c0;
            }
            QGroupBox {
                border: 2px solid #3e3e3e;
                border-radius: 6px;
                background: #252525;
                color: #e0e0e0;
            }
            QGroupBox::title {
                color: #64b5f6;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = QLabel("⚙️ Cài đặt hệ thống")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #64b5f6; padding: 10px;")
        layout.addWidget(header)
        
        # LDPlayer Settings
        ldplayer_group = QGroupBox("🖥️ LDPlayer")
        ldplayer_layout = QFormLayout()
        ldplayer_layout.setSpacing(12)
        
        self.max_instances = QSpinBox()
        self.max_instances.setRange(1, 10)
        self.max_instances.setValue(self.settings.get('max_instances', 5))
        self.max_instances.setMinimumHeight(35)
        ldplayer_layout.addRow("Số instance tối đa:", self.max_instances)
        
        self.auto_close = QCheckBox("Tự động đóng sau khi hoàn thành")
        self.auto_close.setChecked(self.settings.get('auto_close', False))
        ldplayer_layout.addRow(self.auto_close)
        
        ldplayer_group.setLayout(ldplayer_layout)
        layout.addWidget(ldplayer_group)
        
        # Automation Settings
        auto_group = QGroupBox("🤖 Automation")
        auto_layout = QFormLayout()
        auto_layout.setSpacing(12)
        
        self.delay_between = QSpinBox()
        self.delay_between.setRange(0, 60)
        self.delay_between.setValue(self.settings.get('delay_between', 3))
        self.delay_between.setSuffix(" giây")
        self.delay_between.setMinimumHeight(35)
        auto_layout.addRow("Delay giữa các tài khoản:", self.delay_between)
        
        self.retry_on_fail = QCheckBox("Thử lại khi thất bại")
        self.retry_on_fail.setChecked(self.settings.get('retry_on_fail', True))
        auto_layout.addRow(self.retry_on_fail)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(1, 5)
        self.max_retries.setValue(self.settings.get('max_retries', 2))
        self.max_retries.setMinimumHeight(35)
        auto_layout.addRow("Số lần thử lại:", self.max_retries)
        
        auto_group.setLayout(auto_layout)
        layout.addWidget(auto_group)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 Lưu")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setMinimumHeight(35)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Hủy")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setMinimumHeight(35)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def load_settings(self):
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r') as f:
                    return json.load(f)
        except:
            pass
        return {}
    
    def save_settings(self):
        settings = {
            'max_instances': self.max_instances.value(),
            'auto_close': self.auto_close.isChecked(),
            'delay_between': self.delay_between.value(),
            'retry_on_fail': self.retry_on_fail.isChecked(),
            'max_retries': self.max_retries.value()
        }
        
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=2)
        
        QMessageBox.information(self, "Thành công", "✅ Đã lưu cài đặt!")
        self.accept()


class ClickedManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.accounts = []
        self.config_file = "accounts_config.json"
        self.worker = None
        self.ldplayer_instances = []
        self.account_status_items = {}  # Track tree items by email
        self.init_ui()
        self.load_accounts()
        self.load_ldplayer_list()
    
    def init_ui(self):
        self.setWindowTitle("Clicked Manager Pro")
        self.setGeometry(100, 50, 1400, 800)
        
        # Dark theme style
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #1e1e1e;
                color: #e0e0e0;
            }
            QTableWidget {
                border: 1px solid #3e3e3e;
                gridline-color: #2d2d2d;
                background: #2d2d2d;
                border-radius: 6px;
            }
            QTableWidget::item {
                padding: 10px;
                background: #2d2d2d;
                color: #e0e0e0;
            }
            QTableWidget::item:selected {
                background: #0d47a1;
                color: #64b5f6;
            }
            QHeaderView::section {
                background: #252525;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #64b5f6;
                font-weight: 600;
                color: #64b5f6;
            }
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                min-width: 100px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #1565c0;
            }
            QPushButton:pressed {
                background: #0d47a1;
            }
            QPushButton:disabled {
                background: #424242;
                color: #666;
            }
            QPushButton#dangerBtn {
                background: #d32f2f;
            }
            QPushButton#dangerBtn:hover {
                background: #b71c1c;
            }
            QPushButton#secondaryBtn {
                background: #424242;
            }
            QPushButton#secondaryBtn:hover {
                background: #555555;
            }
            QPushButton#successBtn {
                background: #388e3c;
            }
            QPushButton#successBtn:hover {
                background: #2e7d32;
            }
            QLineEdit, QTextEdit, QSpinBox {
                padding: 10px;
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                background: #2d2d2d;
                color: #e0e0e0;
                selection-background-color: #0d47a1;
            }
            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border: 2px solid #64b5f6;
                background: #252525;
            }
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                text-align: center;
                background: #2d2d2d;
                height: 28px;
                font-weight: 600;
                color: #e0e0e0;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1976d2, stop:1 #64b5f6);
                border-radius: 5px;
            }
            QGroupBox {
                font-weight: 600;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background: #252525;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #64b5f6;
            }
            QTabWidget::pane {
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                background: #252525;
            }
            QTabBar::tab {
                background: #333333;
                padding: 12px 24px;
                border: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 3px;
                font-weight: 500;
                color: #a0a0a0;
            }
            QTabBar::tab:selected {
                background: #252525;
                color: #64b5f6;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background: #3e3e3e;
                color: #e0e0e0;
            }
            QTreeWidget {
                border: 1px solid #3e3e3e;
                border-radius: 6px;
                background: #2d2d2d;
                alternate-background-color: #252525;
                color: #e0e0e0;
            }
            QTreeWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QTreeWidget::item:selected {
                background: #0d47a1;
                color: #64b5f6;
            }
            QTreeWidget::item:hover {
                background: #333333;
            }
            QScrollArea {
                background: #1e1e1e;
                border: 1px solid #3e3e3e;
            }
            QLabel {
                color: #e0e0e0;
            }
            QCheckBox {
                color: #e0e0e0;
            }
            QCheckBox::indicator {
                background: #2d2d2d;
                border: 1px solid #3e3e3e;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background: #1976d2;
                border: 1px solid #1976d2;
            }
        """)
        
        # Central widget với tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header
        header_widget = QWidget()
        header_widget.setStyleSheet("background: #252525; border-radius: 8px; padding: 15px;")
        header_layout = QHBoxLayout(header_widget)
        
        title = QLabel("🚀 Clicked Manager Pro")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #64b5f6;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        version_label = QLabel("v2.0")
        version_label.setStyleSheet("color: #888888; font-size: 12px;")
        header_layout.addWidget(version_label)
        
        main_layout.addWidget(header_widget)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self.create_account_page(), "📋 Quản lý tài khoản")
        tabs.addTab(self.create_automation_page(), "⚡ Chạy tự động")
        tabs.addTab(self.create_ldplayer_page(), "🎮 Quản lý LDPlayer")
        
        main_layout.addWidget(tabs)
        
        # Status bar với style
        self.statusBar().setStyleSheet("background: #252525; padding: 8px; border-top: 1px solid #3e3e3e; color: #e0e0e0;")
        self.statusBar().showMessage("✅ Sẵn sàng")
    
    def create_account_page(self):
        """Trang quản lý tài khoản"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        
        add_btn = QPushButton("➕ Thêm tài khoản")
        add_btn.clicked.connect(self.show_add_account_dialog)
        toolbar.addWidget(add_btn)
        
        bulk_add_btn = QPushButton("📋 Thêm nhiều")
        bulk_add_btn.setObjectName("secondaryBtn")
        bulk_add_btn.clicked.connect(self.show_bulk_add_dialog)
        toolbar.addWidget(bulk_add_btn)
        
        toolbar.addStretch()
        
        export_btn = QPushButton("📤 Export")
        export_btn.setObjectName("secondaryBtn")
        export_btn.clicked.connect(self.export_accounts)
        toolbar.addWidget(export_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.setObjectName("secondaryBtn")
        import_btn.clicked.connect(self.import_accounts)
        toolbar.addWidget(import_btn)
        
        clear_btn = QPushButton("🗑️ Xóa tất cả")
        clear_btn.setObjectName("dangerBtn")
        clear_btn.clicked.connect(self.clear_accounts)
        toolbar.addWidget(clear_btn)
        
        layout.addLayout(toolbar)
        
        # Table
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6)
        self.account_table.setHorizontalHeaderLabels([
            "✓", "STT", "📧 Email", "🔒 Password", "📚 Bài tập", "⚙️ Thao tác"
        ])
        
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.account_table.setColumnWidth(0, 60)
        self.account_table.setColumnWidth(1, 70)
        self.account_table.setColumnWidth(5, 200)
        
        self.account_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.account_table.setAlternatingRowColors(True)
        self.account_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_table.customContextMenuRequested.connect(self.show_context_menu)
        
        layout.addWidget(self.account_table)
        
        # Bottom info
        bottom = QHBoxLayout()
        
        self.select_all_cb = QCheckBox("Chọn tất cả")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        self.select_all_cb.setStyleSheet("font-weight: 500;")
        bottom.addWidget(self.select_all_cb)
        
        bottom.addStretch()
        
        self.account_count_label = QLabel("📊 Tổng: 0 tài khoản")
        self.account_count_label.setStyleSheet("font-weight: 600; color: #495057;")
        bottom.addWidget(self.account_count_label)
        
        layout.addLayout(bottom)
        
        return page
    
    def create_automation_page(self):
        """Trang chạy automation"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        
        # Config
        config_group = QGroupBox("⚙️ Cấu hình")
        config_layout = QHBoxLayout()
        config_layout.setSpacing(12)
        
        config_layout.addWidget(QLabel("Số tài khoản chạy cùng lúc:"))
        self.instance_spinbox = QSpinBox()
        self.instance_spinbox.setRange(1, 10)
        self.instance_spinbox.setValue(3)
        self.instance_spinbox.setMinimumHeight(35)
        config_layout.addWidget(self.instance_spinbox)
        
        config_layout.addStretch()
        
        refresh_ld_btn = QPushButton("🔄 Làm mới LDPlayer")
        refresh_ld_btn.setObjectName("secondaryBtn")
        refresh_ld_btn.clicked.connect(self.load_ldplayer_list)
        config_layout.addWidget(refresh_ld_btn)
        
        settings_btn = QPushButton("⚙️ Cài đặt")
        settings_btn.setObjectName("secondaryBtn")
        settings_btn.clicked.connect(self.show_settings)
        config_layout.addWidget(settings_btn)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: LDPlayer list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)
        
        ld_label = QLabel("🖥️ Danh sách LDPlayer")
        ld_label.setStyleSheet("font-weight: 600; font-size: 14px; color: #495057;")
        left_layout.addWidget(ld_label)
        
        self.ldplayer_tree = QTreeWidget()
        self.ldplayer_tree.setHeaderLabels(["Tên instance", "Trạng thái"])
        self.ldplayer_tree.setColumnWidth(0, 200)
        left_layout.addWidget(self.ldplayer_tree)
        
        splitter.addWidget(left_panel)
        
        # Right: Status tree and controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        
        # Status
        status_group = QGroupBox("📊 Trạng thái")
        status_layout = QVBoxLayout()
        status_layout.setSpacing(8)
        
        self.status_label = QLabel("⏸️ Chưa bắt đầu")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #6c757d;")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%v/%m tài khoản hoàn thành")
        status_layout.addWidget(self.progress_bar)
        
        status_group.setLayout(status_layout)
        right_layout.addWidget(status_group)
        
        # Account status tree
        account_status_group = QGroupBox("👥 Trạng thái tài khoản")
        account_status_layout = QVBoxLayout()
        
        self.account_status_tree = QTreeWidget()
        self.account_status_tree.setHeaderLabels(["📧 Tài khoản", "⚡ Trạng thái", "🖥️ LDPlayer", "📝 Hành động"])
        self.account_status_tree.setColumnWidth(0, 200)
        self.account_status_tree.setColumnWidth(1, 120)
        self.account_status_tree.setColumnWidth(2, 120)
        self.account_status_tree.setAlternatingRowColors(True)
        account_status_layout.addWidget(self.account_status_tree)
        
        account_status_group.setLayout(account_status_layout)
        right_layout.addWidget(account_status_group)
        
        # Logs
        log_group = QGroupBox("📜 Nhật ký chi tiết")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: 'Consolas', monospace; font-size: 9pt;")
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        right_layout.addWidget(log_group)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        
        self.start_btn = QPushButton("▶️ Bắt đầu")
        self.start_btn.setObjectName("successBtn")
        self.start_btn.clicked.connect(self.start_automation)
        self.start_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Dừng lại")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_automation)
        self.stop_btn.setMinimumHeight(40)
        btn_layout.addWidget(self.stop_btn)
        
        clear_log_btn = QPushButton("🗑️ Xóa log")
        clear_log_btn.setObjectName("secondaryBtn")
        clear_log_btn.clicked.connect(self.clear_logs)
        clear_log_btn.setMinimumHeight(40)
        btn_layout.addWidget(clear_log_btn)
        
        btn_layout.addStretch()
        
        right_layout.addLayout(btn_layout)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 950])
        
        layout.addWidget(splitter)
        
        return page
    
    def clear_logs(self):
        """Xóa logs"""
        self.log_text.clear()
        self.add_log("📋 Đã xóa nhật ký", "info")
    
    def create_ldplayer_page(self):
        """Trang quản lý LDPlayer"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)
        
        # Control panel
        control_panel = QGroupBox("⚙️ Điều khiển")
        control_panel.setMaximumHeight(100)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(12)
        
        # Columns spinbox
        control_layout.addWidget(QLabel("📊 Số cột:"))
        self.ldplayer_col_spin = QSpinBox()
        self.ldplayer_col_spin.setMinimum(2)
        self.ldplayer_col_spin.setMaximum(6)
        self.ldplayer_col_spin.setValue(4)
        self.ldplayer_col_spin.setMinimumHeight(35)
        self.ldplayer_col_spin.setMaximumWidth(80)
        self.ldplayer_col_spin.valueChanged.connect(self.rearrange_ldplayer_slots)
        control_layout.addWidget(self.ldplayer_col_spin)
        
        # Slots spinbox
        control_layout.addWidget(QLabel("🎮 Số slots:"))
        self.ldplayer_slot_spin = QSpinBox()
        self.ldplayer_slot_spin.setMinimum(4)
        self.ldplayer_slot_spin.setMaximum(24)
        self.ldplayer_slot_spin.setValue(12)
        self.ldplayer_slot_spin.setMinimumHeight(35)
        self.ldplayer_slot_spin.setMaximumWidth(80)
        self.ldplayer_slot_spin.valueChanged.connect(self.update_ldplayer_slots_count)
        control_layout.addWidget(self.ldplayer_slot_spin)
        
        control_layout.addStretch()
        
        # Launch button
        self.ldplayer_launch_btn = QPushButton("▶️ Mở LDPlayer")
        self.ldplayer_launch_btn.setObjectName("secondaryBtn")
        self.ldplayer_launch_btn.clicked.connect(self.launch_ldplayers)
        self.ldplayer_launch_btn.setMinimumHeight(35)
        control_layout.addWidget(self.ldplayer_launch_btn)
        
        # Embed button
        self.ldplayer_embed_btn = QPushButton("🔗 Nhúng tất cả")
        self.ldplayer_embed_btn.setObjectName("successBtn")
        self.ldplayer_embed_btn.clicked.connect(self.embed_all_ldplayers)
        self.ldplayer_embed_btn.setMinimumHeight(35)
        control_layout.addWidget(self.ldplayer_embed_btn)
        
        # Refresh button
        self.ldplayer_refresh_btn = QPushButton("🔄 Làm mới")
        self.ldplayer_refresh_btn.setObjectName("secondaryBtn")
        self.ldplayer_refresh_btn.clicked.connect(self.refresh_ldplayer_slots)
        self.ldplayer_refresh_btn.setMinimumHeight(35)
        control_layout.addWidget(self.ldplayer_refresh_btn)
        
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)
        
        # Status bar
        self.ldplayer_status_label = QLabel("✅ Sẵn sàng")
        self.ldplayer_status_label.setStyleSheet("""
            QLabel {
                background: #e8f5e9;
                color: #2e7d32;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.ldplayer_status_label)
        
        # Scroll area for slots
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 5px;
            }
        """)
        
        # Grid widget for LDPlayer slots
        self.ldplayer_grid_widget = QWidget()
        self.ldplayer_grid_layout = QGridLayout(self.ldplayer_grid_widget)
        self.ldplayer_grid_layout.setSpacing(5)
        self.ldplayer_grid_layout.setContentsMargins(5, 5, 5, 5)
        
        scroll.setWidget(self.ldplayer_grid_widget)
        layout.addWidget(scroll)
        
        # Initialize LDPlayer slots (12 by default)
        self.ldplayer_slots = []
        self.create_ldplayer_slots(12)
        
        # Keep-alive timer for LDPlayer windows
        self.ldplayer_keep_alive_timer = QTimer(self)
        self.ldplayer_keep_alive_timer.timeout.connect(self.refresh_ldplayer_visibility)
        self.ldplayer_keep_alive_timer.start(5000)  # Refresh every 5 seconds
        
        return page
    
    def create_ldplayer_slots(self, count):
        """Create LDPlayer slot containers"""
        # Clear old slots
        for slot in self.ldplayer_slots:
            slot.deleteLater()
        self.ldplayer_slots.clear()
        
        # Create new slots
        cols = self.ldplayer_col_spin.value()
        for i in range(count):
            slot = PlayerSlot(i)
            self.ldplayer_slots.append(slot)
            
            row = i // cols
            col = i % cols
            self.ldplayer_grid_layout.addWidget(slot, row, col)
        
        self.ldplayer_status_label.setText(f"✅ Đã tạo {count} slots - Sắp xếp {cols} cột")
        self.ldplayer_status_label.setStyleSheet("""
            QLabel {
                background: #e8f5e9;
                color: #2e7d32;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
    
    def update_ldplayer_slots_count(self, count):
        """Update number of LDPlayer slots"""
        self.create_ldplayer_slots(count)
    
    def rearrange_ldplayer_slots(self):
        """Rearrange LDPlayer slots based on column count"""
        cols = self.ldplayer_col_spin.value()
        for i, slot in enumerate(self.ldplayer_slots):
            row = i // cols
            col = i % cols
            self.ldplayer_grid_layout.addWidget(slot, row, col)
        
        self.ldplayer_status_label.setText(f"🔄 Đã sắp xếp lại: {cols} cột")
        self.ldplayer_status_label.setStyleSheet("""
            QLabel {
                background: #fff3e0;
                color: #e65100;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
    
    def refresh_ldplayer_slots(self):
        """Refresh all LDPlayer slots"""
        count = len(self.ldplayer_slots)
        self.create_ldplayer_slots(count)
    
    def refresh_ldplayer_visibility(self):
        """Auto-refresh to keep LDPlayer visible"""
        for slot in self.ldplayer_slots:
            if slot.is_embedded:
                slot.keep_visible()
    
    def get_ldplayer_list(self):
        """Get list of LDPlayer instances using auto_clicked"""
        try:
            from auto_clicked import ldplayer
            ld = ldplayer()
            return ld.get_ldplayer_ids()
        except Exception as e:
            print(f"❌ Lỗi lấy danh sách LDPlayer: {e}")
            return []
    
    def launch_ldplayers(self):
        """Launch LDPlayer instances using auto_clicked"""
        ldplayers = self.get_ldplayer_list()
        if not ldplayers:
            QMessageBox.warning(self, "Lỗi", "❌ Không tìm thấy LDPlayer trong hệ thống!")
            return
        
        count = min(len(ldplayers), len(self.ldplayer_slots))
        
        reply = QMessageBox.question(
            self, "Xác nhận", 
            f"Mở {count} LDPlayer?\n\n⏱️ Mỗi máy cách nhau 3 giây",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        try:
            from auto_clicked import ldplayer
            ld = ldplayer()
            
            for i in range(count):
                ld_id, ld_name = ldplayers[i]
                self.ldplayer_status_label.setText(f"▶️ Đang mở {ld_name}... ({i+1}/{count})")
                self.ldplayer_status_label.setStyleSheet("""
                    QLabel {
                        background: #1e3a8a;
                        color: #60a5fa;
                        padding: 10px;
                        border-radius: 5px;
                        font-weight: bold;
                    }
                """)
                QApplication.processEvents()
                
                ld.open_ldplayer(ld_name)
                sleep(3)
            
            self.ldplayer_status_label.setText(f"✅ Đã mở {count} LDPlayer - Đợi 30s rồi nhúng")
            self.ldplayer_status_label.setStyleSheet("""
                QLabel {
                    background: #064e3b;
                    color: #6ee7b7;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
            
            QMessageBox.information(
                self, "Thành công", 
                f"✅ Đã mở {count} LDPlayer!\n\n"
                f"⏳ Đợi 30-40 giây để LDPlayer khởi động\n"
                f"🔗 Sau đó nhấn 'Nhúng tất cả'"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"❌ Lỗi mở LDPlayer:\n{e}")
    
    def find_ldplayer_windows(self):
        """Find all LDPlayer windows"""
        ldplayers = []
        
        def callback(hwnd, results):
            if not win32gui.IsWindowVisible(hwnd):
                return
            
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return
            
            # Filter LDPlayer (exclude Dashboard)
            if ("LDPlayer" in title or "雷電" in title) and "Dashboard" not in title:
                results.append((hwnd, title))
        
        win32gui.EnumWindows(callback, ldplayers)
        ldplayers.sort(key=lambda x: x[1])
        
        return ldplayers
    
    def embed_all_ldplayers(self):
        """Embed all LDPlayer windows into slots"""
        ldplayers = self.find_ldplayer_windows()
        
        if not ldplayers:
            QMessageBox.warning(
                self, "Lỗi", 
                "❌ Không tìm thấy LDPlayer đang chạy!\n\n"
                "Vui lòng:\n"
                "1. Nhấn 'Mở LDPlayer'\n"
                "2. Đợi LDPlayer khởi động\n"
                "3. Nhấn 'Nhúng tất cả'"
            )
            return
        
        print(f"\n{'='*80}")
        print(f"🚀 BẮT ĐẦU NHÚNG {len(ldplayers)} LDPLAYER VÀO {len(self.ldplayer_slots)} SLOTS")
        print(f"{'='*80}\n")
        
        success = 0
        failed = 0
        
        for i, (hwnd, title) in enumerate(ldplayers):
            if i >= len(self.ldplayer_slots):
                break
            
            self.ldplayer_status_label.setText(f"🔗 Đang nhúng {title[:30]}... ({i+1}/{len(ldplayers)})")
            self.ldplayer_status_label.setStyleSheet("""
                QLabel {
                    background: #e3f2fd;
                    color: #1565c0;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
            QApplication.processEvents()
            
            if self.ldplayer_slots[i].embed_window(hwnd, title):
                success += 1
            else:
                failed += 1
            
            # Wait between embeds for stability
            sleep(1.0)
        
        print(f"\n{'='*80}")
        print(f"✅ HOÀN TẤT: {success} thành công, {failed} thất bại")
        print(f"{'='*80}\n")
        
        self.ldplayer_status_label.setText(f"✅ Nhúng xong: {success} thành công, {failed} thất bại")
        self.ldplayer_status_label.setStyleSheet("""
            QLabel {
                background: #e8f5e9;
                color: #2e7d32;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        
        if success > 0:
            QMessageBox.information(
                self, "✅ Thành công", 
                f"Đã nhúng {success}/{len(ldplayers)} LDPlayer!\n\n"
                f"✨ Các LDPlayer đã nằm trong slots\n"
                f"📐 Sắp xếp khít {self.ldplayer_col_spin.value()} cột\n"
                f"🖱️ Có thể tương tác trực tiếp\n"
                f"🔄 Dùng 'Làm mới' nếu có lỗi"
            )
        else:
            QMessageBox.warning(
                self, "Thất bại", 
                f"❌ Không nhúng được LDPlayer!\n\n"
                f"Nguyên nhân có thể:\n"
                f"• LDPlayer chưa khởi động xong\n"
                f"• Xung đột với security/antivirus\n"
                f"• Qt5 không hỗ trợ embed trên hệ thống này\n\n"
                f"Thử:\n"
                f"• Đợi lâu hơn rồi nhấn 'Nhúng tất cả' lại\n"
                f"• Tắt antivirus tạm thời\n"
                f"• Chạy với quyền Administrator"
            )
    
    def show_add_account_dialog(self):
        """Hiển thị dialog thêm tài khoản"""
        dialog = AccountDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data and data.count('|') >= 2:
                self.accounts.append(data)
                self.update_account_table()
                self.save_accounts()
                self.add_log(f"➕ Đã thêm tài khoản: {data.split('|')[0]}", "success")
    
    def show_bulk_add_dialog(self):
        """Hiển thị dialog thêm nhiều tài khoản"""
        dialog = BulkAddDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_accounts = dialog.get_accounts()
            if new_accounts:
                self.accounts.extend(new_accounts)
                self.update_account_table()
                self.save_accounts()
                QMessageBox.information(self, "Thành công", f"✅ Đã thêm {len(new_accounts)} tài khoản!")
                self.add_log(f"➕ Đã thêm {len(new_accounts)} tài khoản", "success")
    
    def show_edit_account_dialog(self, row):
        """Hiển thị dialog sửa tài khoản"""
        if 0 <= row < len(self.accounts):
            dialog = AccountDialog(self, self.accounts[row])
            if dialog.exec_() == QDialog.Accepted:
                data = dialog.get_data()
                if data and data.count('|') >= 2:
                    old_email = self.accounts[row].split('|')[0]
                    self.accounts[row] = data
                    self.update_account_table()
                    self.save_accounts()
                    self.add_log(f"✏️ Đã sửa tài khoản: {old_email}", "info")
    
    def show_context_menu(self, position):
        """Hiển thị context menu"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #e3f2fd;
                color: #1976d2;
            }
        """)
        
        row = self.account_table.rowAt(position.y())
        
        if row >= 0:
            edit_action = QAction("✏️ Sửa", self)
            edit_action.triggered.connect(lambda: self.show_edit_account_dialog(row))
            menu.addAction(edit_action)
            
            delete_action = QAction("🗑️ Xóa", self)
            delete_action.triggered.connect(lambda: self.delete_account(row))
            menu.addAction(delete_action)
            
            menu.addSeparator()
        
        add_action = QAction("➕ Thêm tài khoản", self)
        add_action.triggered.connect(self.show_add_account_dialog)
        menu.addAction(add_action)
        
        bulk_action = QAction("📋 Thêm nhiều tài khoản", self)
        bulk_action.triggered.connect(self.show_bulk_add_dialog)
        menu.addAction(bulk_action)
        
        menu.exec_(self.account_table.viewport().mapToGlobal(position))
    
    def toggle_select_all(self, state):
        """Toggle chọn tất cả"""
        for row in range(self.account_table.rowCount()):
            checkbox_widget = self.account_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(state == Qt.Checked)
    
    def update_account_table(self):
        """Cập nhật bảng tài khoản"""
        self.account_table.setRowCount(len(self.accounts))
        
        for i, account in enumerate(self.accounts):
            parts = account.split('|')
            
            # Checkbox
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.setContentsMargins(5, 0, 5, 0)
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            self.account_table.setCellWidget(i, 0, checkbox_widget)
            
            # STT
            stt_item = QTableWidgetItem(str(i + 1))
            stt_item.setTextAlignment(Qt.AlignCenter)
            self.account_table.setItem(i, 1, stt_item)
            
            # Email
            email_item = QTableWidgetItem(parts[0])
            self.account_table.setItem(i, 2, email_item)
            
            # Password
            password_item = QTableWidgetItem("•" * 10)
            password_item.setForeground(QColor("#6c757d"))
            self.account_table.setItem(i, 3, password_item)
            
            # Bài tập
            homework_item = QTableWidgetItem(parts[2] if len(parts) > 2 else "")
            self.account_table.setItem(i, 4, homework_item)
            
            # Thao tác
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 0, 5, 0)
            action_layout.setSpacing(5)
            
            edit_btn = QPushButton("✏️ Sửa")
            edit_btn.setFixedHeight(32)
            edit_btn.clicked.connect(lambda checked, r=i: self.show_edit_account_dialog(r))
            action_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("🗑️ Xóa")
            delete_btn.setObjectName("dangerBtn")
            delete_btn.setFixedHeight(32)
            delete_btn.clicked.connect(lambda checked, r=i: self.delete_account(r))
            action_layout.addWidget(delete_btn)
            
            self.account_table.setCellWidget(i, 5, action_widget)
        
        # Update count
        self.account_count_label.setText(f"📊 Tổng: {len(self.accounts)} tài khoản")
        self.statusBar().showMessage(f"✅ Đã cập nhật: {len(self.accounts)} tài khoản")
    
    def delete_account(self, row):
        """Xóa tài khoản"""
        email = self.accounts[row].split('|')[0]
        reply = QMessageBox.question(self, "Xác nhận", 
                                     f"Bạn có chắc muốn xóa tài khoản:\n{email}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accounts.pop(row)
            self.update_account_table()
            self.save_accounts()
            self.add_log(f"🗑️ Đã xóa tài khoản: {email}", "warning")
    
    def clear_accounts(self):
        """Xóa tất cả tài khoản"""
        if not self.accounts:
            QMessageBox.information(self, "Thông báo", "⚠️ Không có tài khoản nào để xóa!")
            return
        
        reply = QMessageBox.question(self, "Xác nhận", 
                                     f"⚠️ Bạn có chắc muốn xóa TẤT CẢ {len(self.accounts)} tài khoản?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.accounts.clear()
            self.update_account_table()
            self.save_accounts()
            self.add_log("🗑️ Đã xóa tất cả tài khoản", "warning")
    
    def save_accounts(self):
        """Lưu tài khoản"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"❌ Không thể lưu: {str(e)}")
    
    def load_accounts(self):
        """Load tài khoản"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.accounts = json.load(f)
                self.update_account_table()
                self.add_log(f"✅ Đã load {len(self.accounts)} tài khoản", "success")
        except Exception as e:
            print(f"Không load được config: {e}")
    
    def export_accounts(self):
        """Export tài khoản ra file"""
        if not self.accounts:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Không có tài khoản để export!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Lưu file", 
            f"accounts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;Text Files (*.txt)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    if filename.endswith('.txt'):
                        f.write('\n'.join(self.accounts))
                    else:
                        json.dump(self.accounts, f, ensure_ascii=False, indent=2)
                QMessageBox.information(self, "Thành công", f"✅ Đã export {len(self.accounts)} tài khoản!")
                self.add_log(f"📤 Đã export {len(self.accounts)} tài khoản", "success")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"❌ Không thể export: {str(e)}")
    
    def import_accounts(self):
        """Import tài khoản từ file"""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Chọn file", "", 
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    if filename.endswith('.txt'):
                        imported = [line.strip() for line in f.readlines() if line.strip() and line.count('|') >= 2]
                    else:
                        imported = json.load(f)
                
                self.accounts.extend(imported)
                self.update_account_table()
                self.save_accounts()
                QMessageBox.information(self, "Thành công", f"✅ Đã import {len(imported)} tài khoản!")
                self.add_log(f"📥 Đã import {len(imported)} tài khoản", "success")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"❌ Không thể import: {str(e)}")
    
    def load_ldplayer_list(self):
        """Load danh sách LDPlayer"""
        self.ldplayer_tree.clear()
        
        try:
            from auto_clicked import ldplayer
            self.ldplayer_instances = ldplayer().get_ldplayer_ids()
            
            for ld_id, ld_name in self.ldplayer_instances:
                item = QTreeWidgetItem([ld_name, "⚪ Sẵn sàng"])
                item.setForeground(1, QColor("#28a745"))
                self.ldplayer_tree.addTopLevelItem(item)
            
            self.add_log(f"🖥️ Đã tải {len(self.ldplayer_instances)} LDPlayer", "success")
            self.statusBar().showMessage(f"✅ Tìm thấy {len(self.ldplayer_instances)} LDPlayer")
        except Exception as e:
            self.add_log(f"❌ Lỗi load LDPlayer: {str(e)}", "error")
            QMessageBox.warning(self, "Cảnh báo", f"⚠️ Không thể load LDPlayer: {str(e)}")
    
    def start_automation(self):
        """Bắt đầu automation"""
        # Get selected accounts
        selected_accounts = []
        for row in range(self.account_table.rowCount()):
            checkbox_widget = self.account_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected_accounts.append(self.accounts[row])
        
        if not selected_accounts:
            QMessageBox.warning(self, "Cảnh báo", "⚠️ Vui lòng chọn ít nhất 1 tài khoản!")
            return
        
        max_instances = self.instance_spinbox.value()
        if len(selected_accounts) > max_instances:
            reply = QMessageBox.question(
                self, "Xác nhận",
                f"📊 Bạn chọn {len(selected_accounts)} tài khoản nhưng chỉ chạy {max_instances} cùng lúc.\n"
                f"Các tài khoản sẽ chạy lần lượt. Tiếp tục?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        if len(self.ldplayer_instances) < len(selected_accounts):
            QMessageBox.warning(
                self, "Cảnh báo", 
                f"⚠️ Chỉ có {len(self.ldplayer_instances)} LDPlayer nhưng chọn {len(selected_accounts)} tài khoản!\n"
                f"Vui lòng tăng số LDPlayer hoặc giảm số tài khoản."
            )
            return
        
        # Setup status tree
        self.account_status_tree.clear()
        self.account_status_items.clear()
        
        for i, account in enumerate(selected_accounts):
            email = account.split('|')[0]
            ld_name = self.ldplayer_instances[i][1] if i < len(self.ldplayer_instances) else "N/A"
            
            item = QTreeWidgetItem([email, "⏳ Chờ...", ld_name, "Đang khởi động"])
            item.setForeground(1, QColor("#ffc107"))
            self.account_status_tree.addTopLevelItem(item)
            self.account_status_items[email] = item
        
        # Start
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("▶️ Đang chạy...")
        self.status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #1976d2;")
        self.progress_bar.setMaximum(len(selected_accounts))
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self.add_log(f"▶️ Bắt đầu xử lý {len(selected_accounts)} tài khoản", "info")
        
        # Start worker
        self.worker = WorkerThread(selected_accounts, self.ldplayer_instances[:len(selected_accounts)])
        self.worker.log_signal.connect(self.add_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.status_signal.connect(self.update_account_status)
        self.worker.action_signal.connect(self.append_action_to_tree)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()
    
    def stop_automation(self):
        """Dừng automation"""
        if self.worker:
            reply = QMessageBox.question(
                self, "Xác nhận",
                "⚠️ Bạn có chắc muốn dừng?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.add_log("⏹️ Đang dừng...", "warning")
    
    def add_log(self, message, level="info"):
        """Thêm log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌"
        }
        
        colors = {
            "info": "#1976d2",
            "success": "#28a745",
            "warning": "#ffc107",
            "error": "#dc3545"
        }
        
        icon = icons.get(level, "ℹ️")
        color = colors.get(level, "#333")
        
        self.log_text.append(
            f'<span style="color: #999;">[{timestamp}]</span> '
            f'<span style="color: {color}; font-weight: 500;">{icon} {message}</span>'
        )
    
    def update_progress(self, current, total):
        """Cập nhật progress"""
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"⚡ Đang xử lý: {current}/{total}")
    
    def update_account_status(self, account, status, detail):
        """Cập nhật trạng thái tài khoản trong tree"""
        if account in self.account_status_items:
            item = self.account_status_items[account]
            
            # Update status with color
            status_colors = {
                "Đang khởi động": ("#ffc107", "⏳"),
                "Đang chạy": ("#1976d2", "▶️"),
                "Hoàn thành": ("#28a745", "✅"),
                "Lỗi": ("#dc3545", "❌"),
                "Chờ": ("#6c757d", "⏸️")
            }
            
            color, icon = status_colors.get(status, ("#6c757d", "⚪"))
            item.setText(1, f"{icon} {status}")
            item.setForeground(1, QColor(color))
            item.setText(3, detail)
            
            self.add_log(f"👤 {account}: {detail}", "info")
    
    def append_action_to_tree(self, account, action):
        """Update hành động hiện tại trên TreeView (không append, chỉ update)"""
        if account in self.account_status_items:
            parent_item = self.account_status_items[account]
            
            # Xóa child cũ nếu có (giữ chỉ 1 status line)
            while parent_item.childCount() > 0:
                parent_item.removeChild(parent_item.child(0))
            
            # Tạo 1 child item duy nhất để hiển thị hành động hiện tại
            action_item = QTreeWidgetItem([f"  {action}", "", "", ""])
            action_item.setForeground(0, QColor("#64b5f6"))  # Màu xanh cho action
            parent_item.addChild(action_item)
            
            # Luôn expand parent để hiện action
            self.account_status_tree.expandItem(parent_item)
    
    def on_finished(self, success, message):
        """Khi hoàn thành"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.status_label.setText("✅ Hoàn thành!")
            self.status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #28a745;")
            self.add_log(message, "success")
            QMessageBox.information(self, "Thành công", f"✅ {message}")
        else:
            self.status_label.setText("❌ Có lỗi xảy ra")
            self.status_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #dc3545;")
            self.add_log(message, "error")
            QMessageBox.critical(self, "Lỗi", f"❌ {message}")
        
        self.statusBar().showMessage("✅ Sẵn sàng")
    
    def show_settings(self):
        """Hiển thị settings"""
        dialog = SettingsDialog(self)
        dialog.exec_()


def main():
    app = QApplication(sys.argv)
    
    # Set font
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = ClickedManager()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()