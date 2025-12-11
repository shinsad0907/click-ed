"""LDPlayer Slot Component for GUI Integration"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QWindow
from time import sleep
import win32gui
import win32con


class PlayerSlot(QWidget):
    """Fixed-size slot container for embedding LDPlayer windows"""
    def __init__(self, slot_id, width=320, height=580):
        super().__init__()
        self.slot_id = slot_id
        self.hwnd = None
        self.is_embedded = False
        self.slot_width = width
        self.slot_height = height
        self.init_ui()
        
    def init_ui(self):
        """Create fixed-size slot container"""
        self.setFixedSize(self.slot_width, self.slot_height)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with slot number
        self.header = QLabel(f"Slot {self.slot_id + 1}: Trống")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setFixedHeight(30)
        self.header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a2e, stop:1 #16213e);
                color: #64b5f6;
                font-weight: bold;
                font-size: 12px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.header)
        
        # Container for LDPlayer
        self.container = QWidget()
        self.container.setFixedSize(self.slot_width, self.slot_height - 30)
        self.container.setStyleSheet("""
            QWidget {
                background-color: #0f0f0f;
                border: 2px solid #3e3e3e;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
        """)
        # IMPORTANT: Allow container to accept embedded windows
        self.container.setAttribute(Qt.WA_NativeWindow)
        self.container.setAttribute(Qt.WA_DontCreateNativeAncestors)
        self.container.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.container)
        
        # Placeholder label
        self.placeholder = QLabel("Chờ nhúng LDPlayer...", self.container)
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setGeometry(0, 0, self.slot_width, self.slot_height - 30)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 14px;
                border: none;
            }
        """)
        
    def embed_window(self, hwnd, title):
        """Embed LDPlayer window into slot"""
        try:
            self.hwnd = hwnd
            self.header.setText(f"📱 {title[:25]}")
            self.header.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0d3b66, stop:1 #06a77d);
                    color: #64b5f6;
                    font-weight: bold;
                    font-size: 12px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 5px;
                }
            """)
            
            print(f"🔗 Embedding {title} to Slot {self.slot_id + 1}...")
            
            # Hide placeholder
            self.placeholder.hide()
            
            # Get container HWND
            container_hwnd = int(self.container.winId())
            
            # Save original style
            original_style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            
            # Remove decorations but keep important flags
            new_style = original_style
            new_style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | 
                          win32con.WS_SYSMENU | win32con.WS_MINIMIZEBOX | 
                          win32con.WS_MAXIMIZEBOX)
            new_style |= win32con.WS_CHILD | win32con.WS_VISIBLE
            win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
            
            # Set parent
            win32gui.SetParent(hwnd, container_hwnd)
            
            # Move and resize with delays
            win32gui.MoveWindow(hwnd, 0, 0, self.slot_width, self.slot_height - 30, True)
            sleep(0.1)
            
            # Show and update
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.UpdateWindow(hwnd)
            sleep(0.1)
            
            # Force invalidate for re-render
            win32gui.InvalidateRect(hwnd, None, True)
            sleep(0.1)
            
            # Redraw all
            win32gui.RedrawWindow(hwnd, None, None, 
                                 win32con.RDW_FRAME | 
                                 win32con.RDW_INVALIDATE | 
                                 win32con.RDW_UPDATENOW | 
                                 win32con.RDW_ALLCHILDREN | 
                                 win32con.RDW_ERASE)
            
            # Reset position to ensure correct sizing
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 
                                 0, 0, 
                                 self.slot_width, self.slot_height - 30,
                                 win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED)
            
            self.is_embedded = True
            print(f"✅ Slot {self.slot_id + 1}: Embedding successful!\n")
            
            # Wait for LDPlayer to re-render
            sleep(0.5)
            return True
            
        except Exception as e:
            print(f"❌ Error embedding to Slot {self.slot_id + 1}: {e}\n")
            self.header.setText(f"Slot {self.slot_id + 1}: Lỗi")
            self.header.setStyleSheet("""
                QLabel {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #7f1d1d, stop:1 #b91c1c);
                    color: #fca5a5;
                    font-weight: bold;
                    font-size: 12px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 5px;
                }
            """)
            return False
    
    def keep_visible(self):
        """Keep LDPlayer visible and interactive"""
        if self.is_embedded and self.hwnd:
            try:
                # Check if window still exists
                if not win32gui.IsWindow(self.hwnd):
                    return
                    
                # Ensure window is still visible
                if not win32gui.IsWindowVisible(self.hwnd):
                    win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                    win32gui.UpdateWindow(self.hwnd)
                    # Force re-render
                    win32gui.InvalidateRect(self.hwnd, None, True)
                
                # Check parent is correct
                container_hwnd = int(self.container.winId())
                current_parent = win32gui.GetParent(self.hwnd)
                
                if current_parent != container_hwnd:
                    win32gui.SetParent(self.hwnd, container_hwnd)
                    win32gui.MoveWindow(self.hwnd, 0, 0, 
                                       self.slot_width, self.slot_height - 30, True)
                    win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)
                    
            except:
                pass
