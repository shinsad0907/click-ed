import subprocess
from PIL import Image
import pytesseract
from time import sleep
import json
import threading
from functools import partial
import json,os
import datetime
import base64
import win32gui
import win32ui
import win32con
import win32api
import cv2
import numpy as np
import xml.etree.ElementTree as ET
import re

class ldplayer:
    def __init__(self,index=0) -> None:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.ADB = 'C:\\LDPlayer\\LDPlayer9'
        self.index = index

    def adb_command(self,command):
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8'), result.stderr.decode('utf-8')

    def capture_ldplayer_screen(self, name_window="LDPlayer-1"):
        # Tên cửa sổ LDPlayer (bạn có thể đổi lại nếu khác)
        window_name = name_window
        
        # Lưu ảnh riêng cho mỗi device - tránh ghi đè lẫn nhau
        filename = f"data_image/ldplayer_screenshot_{name_window}.png"

        # Tìm cửa sổ LDPlayer
        hwnd = win32gui.FindWindow(None, window_name)
        if not hwnd:
            print(f"Không tìm thấy cửa sổ LDPlayer: {window_name}")
            return None

        # Lấy kích thước cửa sổ
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # Chụp cửa sổ bằng Windows GDI
        hwindc = win32gui.GetWindowDC(hwnd)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()

        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, width, height)
        memdc.SelectObject(bmp)

        # Copy pixel
        memdc.BitBlt((0, 0), (width, height), srcdc, (0, 0), win32con.SRCCOPY)

        # Lưu file
        bmp.SaveBitmapFile(memdc, filename)

        # Giải phóng
        memdc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwindc)

        return filename

    def get_ldplayer_names(self):
        """Lấy danh sách tên LDPlayer (hỗ trợ cả tên trùng)"""
        ldconsole = fr"{self.ADB}\ldconsole.exe"

        result = subprocess.run(
            [ldconsole, "list2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        names = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split(",")
                name = parts[1].strip()
                names.append(name)

        return names
    
    def get_ldplayer_ids(self):
        """Lấy danh sách ID LDPlayer - để xử lý tên trùng"""
        ldconsole = fr"{self.ADB}\ldconsole.exe"

        result = subprocess.run(
            [ldconsole, "list2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        ids = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split(",")
                ld_id = parts[0].strip()
                ld_name = parts[1].strip()
                ids.append((ld_id, ld_name))  # Trả về (ID, tên)

        return ids
    
    def open_ldplayer(self, name, ld_path = r"C:\LDPlayer\LDPlayer9"):
        ldconsole = fr"{ld_path}\ldconsole.exe"
        subprocess.run([ldconsole, "launch", "--name", name])

    def is_ldplayer_in_home(self, device_id, adb_path=r"C:\LDPlayer\LDPlayer9"):
        cmd = [
            fr"{adb_path}\adb.exe", "-s", device_id,
            "shell", "dumpsys", "activity", "activities"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout

        # Check activity đang top
        if "com.android.launcher3" in output or "com.miui.home" in output:
            return True
        return False
    
    def input(self, text):
        """
        Input text - hỗ trợ tiếng Việt và ký tự đặc biệt bằng shell command
        """
        device = self.DEVICE()[self.index]
        
        # Escape dấu ngoặc kép và ký tự đặc biệt
        escaped_text = text.replace('"', '\\"').replace("'", "\\'")
        
        # Gửi text qua ADB shell input text
        cmd = fr'{self.ADB}\adb.exe -s {device} shell input text "{escaped_text}"'
        
        try:
            self.adb_command(cmd)
        except Exception as e:
            print(f"⚠️ Input text thất bại: {e}")
        
        sleep(2)

    def search_name_homework(self, name_homework):
        """
        Tìm tên bài tập trong XML và trả về tọa độ
        
        Args:
            name_homework: Tên bài tập cần tìm (ví dụ: "lịch sử văn minh")
        
        Returns:
            tuple: (x, y) tọa độ bài tập nếu tìm thấy, None nếu không tìm thấy
        """
        xml_file = self.dump_xml()  # Tạo file XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        name_homework_lower = name_homework.lower().strip()
        
        # Duyệt toàn bộ node trong cây XML
        for node in root.iter():
            content_desc = node.attrib.get("content-desc", "").strip().lower()
            text = node.attrib.get("text", "").strip().lower()
            bounds = node.attrib.get("bounds", "")
            
            # Kiểm tra xem tên bài tập có nằm trong content-desc hoặc text không
            if name_homework_lower in content_desc or name_homework_lower in text:
                print(f"✅ Tìm thấy bài tập: {name_homework}")
                print(f"   Content-desc: {node.attrib.get('content-desc', '')}")
                print(f"   Bounds: {bounds}")
                
                # Parse bounds để lấy tọa độ
                if bounds:
                    try:
                        x, y = self.parse_bounds(bounds)
                        print(f"   Tọa độ: ({x}, {y})")
                        return (x, y)
                    except Exception as e:
                        print(f"⚠️ Lỗi parse bounds: {e}")
                        return None
        
        print(f"❌ Không tìm thấy bài tập: {name_homework}")
        return None

    def click(self,x,y):
        self.index
        command = fr'{self.ADB}\\adb.exe -s {self.DEVICE()[self.index]} shell input tap {x} {y}'
        self.adb_command(command)
        sleep(2)
        
    def DEVICE(self):
        proc = subprocess.Popen(fr"{self.ADB}\adb.exe devices", shell= True, stdout=subprocess.PIPE)
        print(proc)
        serviceList = proc.communicate()[0].decode('ascii').split('\n')

        self.list_device = []
        for i in range(1, len(serviceList)-2):
            try:
                device = serviceList[i].split('\t')[0]
                print(device)
                self.list_device.append(device)
            except:
                pass
        # print(self.list_device)
        return self.list_device

    def check_login(self):
        xml_file = self.dump_xml()  # Tạo file XML
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Duyệt toàn bộ node trong cây XML
        for node in root.iter():
            content_desc = node.attrib.get("content-desc", "")
            if content_desc.strip() == "Đăng nhập":
                return True

        return False


    def setup_clicked(self):
        """
        Xóa dữ liệu ứng dụng CLICK-Ed + mở lại ứng dụng.
        """
        device = self.DEVICE()[self.index]

        # XÓA DỮ LIỆU ỨNG DỤNG
        clear_cmd = fr'{self.ADB}\adb.exe -s {device} shell pm clear realjobscomltd.clickqa'
        self.adb_command(clear_cmd)
        sleep(1.5)

        # MỞ ỨNG DỤNG CLICK-Ed
        open_cmd = fr'{self.ADB}\adb.exe -s {device} shell monkey -p realjobscomltd.clickqa 1'
        self.adb_command(open_cmd)
        sleep(2.5)

        return True

    # def check_devices(self):
    #     devices = self.DEVICE()
    #     if devices:
    #         return True
    #     return False

    def dump_xml(self):
        # Dump UI
        device_id = self.DEVICE()[self.index]
        cmd1 = fr"{self.ADB}\adb.exe -s {device_id} shell uiautomator dump /sdcard/view.xml"
        subprocess.run(cmd1, shell=True)

        # Copy file về PC với tên riêng cho mỗi device
        xml_filename = f"view_{device_id}.xml"
        cmd2 = fr"{self.ADB}\adb.exe -s {device_id} pull /sdcard/view.xml {xml_filename}"
        subprocess.run(cmd2, shell=True)

        return xml_filename

    def parse_bounds(self, bound_str):
        nums = list(map(int, re.findall(r"\d+", bound_str)))
        x1, y1, x2, y2 = nums
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        return cx, cy

    def find_answers_by_xml(self):
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()

        answers = {}

        for node in root.iter("node"):
            desc = node.attrib.get("content-desc", "")
            bounds = node.attrib.get("bounds", "")

            if not desc or not bounds:
                continue

            # Detect tất cả câu từ A-Z, không chỉ A-D
            if len(desc) > 0 and desc[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" and desc[1:2] == ".":
                letter = desc[0]
                answers[letter] = self.parse_bounds(bounds)

        return answers
    
    def get_question_and_answers(self):
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()

        question = ""
        answers = {}

        for node in root.iter("node"):
            desc = node.attrib.get("content-desc", "")
            bounds = node.attrib.get("bounds", "")

            if not desc:
                continue

            # Detect tất cả câu từ A-Z, không chỉ A-D
            if len(desc) > 0 and desc[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" and desc[1:2] == ".":
                letter = desc[0]
                answers[letter] = (desc, self.parse_bounds(bounds))
            else:
                # Cái còn lại là đề bài
                # Lọc đề: phải dài + chứa dấu chấm hỏi hoặc câu mô tả
                if len(desc) > 10:  
                    question = desc

        # Build output với tất cả câu tìm được
        output = question
        for letter in sorted(answers.keys()):
            output += "\n" + answers[letter][0]
        
        return output
    
    def detect_unfinished_videos(self):
        """
        Kéo xuống dần để tìm HẾT video chưa xem.
        Trả về dict: {index: (x, y)} - tọa độ thực tế của từng video
        Sau đó kéo lên lại vị trí ban đầu.
        """
        device_id = self.DEVICE()[self.index]
        unfinished = {}  # {index: (x, y)}
        seen_videos = set()
        max_scrolls = 10
        no_new_video_count = 0
        
        print(f"📹 Bắt đầu tìm video chưa xem...")
        
        for scroll_count in range(max_scrolls):
            xml_file = self.dump_xml()
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            found_new = False
            
            for node in root.iter("node"):
                desc = node.attrib.get("content-desc", "")
                bounds = node.attrib.get("bounds", "")
                
                if not desc or not bounds:
                    continue
                
                if "Video" not in desc or "phút" not in desc:
                    continue
                
                lines = desc.split("\n")
                try:
                    index = int(lines[0].strip())
                except:
                    continue
                
                if index in seen_videos:
                    continue
                
                seen_videos.add(index)
                found_new = True
                
                # Lấy % hoàn thành
                last_line = lines[-1].strip()
                if last_line.endswith("%"):
                    try:
                        percent = int(last_line.replace("%", ""))
                    except:
                        percent = 0
                else:
                    percent = 0
                
                # Nếu chưa đủ 100% → LƯU TỌA ĐỘ
                if percent < 100:
                    x, y = self.parse_bounds(bounds)
                    unfinished[index] = (x, y)
                    print(f"   ➜ Video {index}: {percent}% - Tọa độ ({x}, {y})")
            
            if not found_new:
                no_new_video_count += 1
                if no_new_video_count >= 2:
                    print(f"   ✓ Đã quét hết ({scroll_count + 1} lần kéo)")
                    break
            else:
                no_new_video_count = 0
            
            if scroll_count < max_scrolls - 1:
                cmd = f'{self.ADB}\\adb.exe -s {device_id} shell input swipe 300 800 300 400 300'
                self.adb_command(cmd)
                sleep(1)
        
        # KÉO LÊN LẠI
        print(f"   ⬆ Kéo lên lại vị trí ban đầu...")
        for _ in range(scroll_count + 1):
            cmd = f'{self.ADB}\\adb.exe -s {device_id} shell input swipe 300 400 300 800 300'
            self.adb_command(cmd)
            sleep(0.5)
        
        print(f"📊 Tổng video chưa xem: {sorted(unfinished.keys())}")
        return unfinished

    
    def enter(self):
        device = self.DEVICE()[self.index]
        cmd = fr"{self.ADB}\adb.exe -s {device} shell input keyevent 66"
        self.adb_command(cmd)


    def get_id_machine(self):
        result = subprocess.run([f'{self.ADB}\\ldconsole.exe', 'list'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = result.stdout.strip()
        # Mỗi dòng trong output đại diện cho một máy ảo
        vm_list = output.splitlines()
        if vm_list:
            # Lấy ID của máy ảo đầu tiên (giả sử ID là phần đầu tiên của mỗi dòng)
            return vm_list
        
    def check_login_failed(self):
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for node in root.iter():
            content_desc = node.attrib.get("content-desc", "").strip()

            # Nếu vẫn thấy nút Đăng nhập → login fail
            if content_desc == "Đăng nhập":
                return True

        return False

    def detect_unfinished_lessons(self):
        """
        Kéo xuống tìm HẾT bài tập chưa làm.
        Trả về dict: {letter: (x, y)} - tọa độ thực tế
        """
        device_id = self.DEVICE()[self.index]
        unfinished = {}  # {letter: (x, y)}
        seen_lessons = set()
        max_scrolls = 10
        no_new_lesson_count = 0
        
        print(f"📝 Bắt đầu tìm bài tập chưa làm...")
        
        for scroll_count in range(max_scrolls):
            xml_file = self.dump_xml()
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            found_new = False
            
            for node in root.iter("node"):
                desc = node.attrib.get("content-desc", "")
                bounds = node.attrib.get("bounds", "")
                
                if not desc or not bounds:
                    continue
                
                m = re.search(r"\d+\.([A-Za-z])", desc)
                if not m:
                    continue
                
                letter = m.group(1).upper()
                
                if letter in seen_lessons:
                    continue
                
                seen_lessons.add(letter)
                found_new = True
                
                # Kiểm tra chưa làm
                if re.search(r"\b0/\d+\b", desc) or "Điểm đạt được: 0" in desc:
                    x, y = self.parse_bounds(bounds)
                    unfinished[letter] = (x, y)
                    print(f"   ➜ Bài {letter}: Chưa làm - Tọa độ ({x}, {y})")
            
            if not found_new:
                no_new_lesson_count += 1
                if no_new_lesson_count >= 2:
                    print(f"   ✓ Đã quét hết ({scroll_count + 1} lần kéo)")
                    break
            else:
                no_new_lesson_count = 0
            
            if scroll_count < max_scrolls - 1:
                cmd = f'{self.ADB}\\adb.exe -s {device_id} shell input swipe 300 800 300 400 300'
                self.adb_command(cmd)
                sleep(1)
        
        # KÉO LÊN LẠI
        print(f"   ⬆ Kéo lên lại vị trí ban đầu...")
        for _ in range(scroll_count + 1):
            cmd = f'{self.ADB}\\adb.exe -s {device_id} shell input swipe 300 400 300 800 300'
            self.adb_command(cmd)
            sleep(0.5)
        
        print(f"📊 Tổng bài tập chưa làm: {sorted(unfinished.keys())}")
        return unfinished
    
    def get_video_coords_from_xml(self):
        """
        Lấy tọa độ của các video từ XML (lấy động từ danh sách trên màn hình)
        Trả về dict: {video_index: (x, y)} - tọa độ tiêu đề video
        """
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        video_coords = {}  # {index: (x, y)}
        
        for node in root.iter("node"):
            desc = node.attrib.get("content-desc", "")
            bounds = node.attrib.get("bounds", "")
            
            if not desc or not bounds:
                continue
            
            # Tìm pattern "Video X" hoặc "X Video"
            m = re.search(r'(?:Video\s+)?(\d+)(?:\s+Video)?', desc)
            if not m:
                continue
            
            try:
                video_idx = int(m.group(1))
            except:
                continue
            
            # Kiểm tra xem có chứa từ "Video" không
            if "Video" not in desc:
                continue
            
            # Lấy tọa độ
            x, y = self.parse_bounds(bounds)
            video_coords[video_idx] = (x, y)
            print(f"   ✓ Video {video_idx}: Tọa độ ({x}, {y})")
        
        print(f"📊 Tổng video tìm được: {sorted(video_coords.keys())}")
        return video_coords
        
    def detect_unfinished_chapters_fixed(self):
        """
        Dùng tọa độ chương cố định bạn đưa.
        Nếu chương bất kỳ <100% thì các chương sau cũng chưa làm.
        Trả về list chương chưa hoàn thành.
        """

        chapter_coords = [
            (110,308),  # 1 
            (450,308),  # 2
            (300,485),  # 3
            (165,660),  # 4
            (450,660),  # 5
            (300,850),  # 6
            (165,1020), # 7
        ]

        unfinished = []
        total_chapters = len(chapter_coords)

        for idx, (x, y) in enumerate(chapter_coords, start=1):

            # CLICK vào chương
            self.click(x, y)
            sleep(1.5)

            # Dump XML trong chương
            xml_file = self.dump_xml()
            tree = ET.parse(xml_file)
            root = tree.getroot()

            chapter_done = False

            # Tìm phần trăm hoàn thành
            for node in root.iter("node"):
                desc = node.attrib.get("content-desc", "").lower()
                text = node.attrib.get("text", "").lower()
                combine = desc + " " + text

                # check %. Ví dụ: "100%"
                percent = re.findall(r"(\d+)%", combine)
                if percent:
                    if int(percent[-1]) == 100:
                        chapter_done = True

                # hoặc chữ "Hoàn thành"
                if "hoàn thành" in combine:
                    chapter_done = True

            # Nếu chương này chưa hoàn thành → chương sau cũng chưa
            if not chapter_done:
                # thêm từ chương hiện tại đến chương cuối
                for ch in range(idx, total_chapters + 1):
                    unfinished.append(ch)
                break

            # nếu đã hoàn thành thì quay lại màn danh sách chương
            self.adb_command(fr'{self.ADB}\\adb.exe -s {self.DEVICE()[self.index]} shell input keyevent 4')
            sleep(1.2)

        return unfinished





ld = ldplayer()
path = ld.DEVICE()
print(path)

