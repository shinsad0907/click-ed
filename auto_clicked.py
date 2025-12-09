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
        
        filename = "data_image/ldplayer_screenshot.png"

        # Tìm cửa sổ LDPlayer
        hwnd = win32gui.FindWindow(None, window_name)
        if not hwnd:
            print("Không tìm thấy cửa sổ LDPlayer!")
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
    
    def open_ldplayer(self, name, ld_path = r"C:\LDPlayer\LDPlayer9"):
        ldconsole = fr"{ld_path}\ldconsole.exe"
        subprocess.run([ldconsole, "launch", "--name", name])

    def is_ldplayer_in_home(device_id, adb_path=r"C:\LDPlayer\LDPlayer9"):
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
    
    def input(self,text):
        command = fr'{self.ADB}\\adb.exe -s {self.DEVICE()[self.index]} shell input text {text}'
        self.adb_command(command)
        sleep(2)

    def click(self,x,y):
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
        cmd1 = fr"{self.ADB}\adb.exe -s {self.DEVICE()[self.index]} shell uiautomator dump /sdcard/view.xml"
        subprocess.run(cmd1, shell=True)

        # Copy file về PC
        cmd2 = fr"{self.ADB}\adb.exe -s {self.DEVICE()[self.index]} pull /sdcard/view.xml view.xml"
        subprocess.run(cmd2, shell=True)

        return "view.xml"

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

            if desc.startswith("A."):
                answers["A"] = self.parse_bounds(bounds)
            elif desc.startswith("B."):
                answers["B"] = self.parse_bounds(bounds)
            elif desc.startswith("C."):
                answers["C"] = self.parse_bounds(bounds)
            elif desc.startswith("D."):
                answers["D"] = self.parse_bounds(bounds)

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

            # Tìm đáp án
            if desc.startswith("A."):
                answers["A"] = (desc, self.parse_bounds(bounds))
            elif desc.startswith("B."):
                answers["B"] = (desc, self.parse_bounds(bounds))
            elif desc.startswith("C."):
                answers["C"] = (desc, self.parse_bounds(bounds))
            elif desc.startswith("D."):
                answers["D"] = (desc, self.parse_bounds(bounds))
            else:
                # Cái còn lại là đề bài
                # Lọc đề: phải dài + chứa dấu chấm hỏi hoặc câu mô tả
                if len(desc) > 10:  
                    question = desc

        return question + "\n" +answers["A"][0] + "\n" +answers["B"][0] + "\n" +answers["C"][0] + "\n" +answers["D"][0]
    
    def detect_unfinished_videos(self):
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()

        unfinished = []

        for node in root.iter("node"):
            desc = node.attrib.get("content-desc", "")
            if not desc:
                continue

            # Chỉ bắt các node video
            if "Video" not in desc or "phút" not in desc:
                continue

            # Lấy số thứ tự video: dòng đầu tiên của content-desc
            lines = desc.split("\n")
            try:
                index = int(lines[0].strip())
            except:
                continue

            # Lấy % hoàn thành: dòng cuối
            last_line = lines[-1].strip()

            # Ví dụ: "100%" hoặc "75%"
            if last_line.endswith("%"):
                try:
                    percent = int(last_line.replace("%", ""))
                except:
                    percent = 0
            else:
                # Không có %, nghĩa là chưa xem
                percent = 0

            # Nếu chưa đủ 100%
            if percent < 100:
                unfinished.append(index)

        return unfinished

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
        Trả về list duy nhất gồm các bài chưa làm: ['A','B','C',...]
        Không quan tâm chương số.
        Tối ưu: detect động số bài tập (0/5, 0/20, v.v.)
        """
        xml_file = self.dump_xml()
        tree = ET.parse(xml_file)
        root = tree.getroot()

        result = set()

        for node in root.iter("node"):
            desc = node.attrib.get("content-desc", "")
            if not desc:
                continue

            # Tìm dạng 1.A, 2.B, 10.C, ... → chỉ lấy chữ A/B/C
            m = re.search(r"\d+\.([A-Za-z])", desc)
            if not m:
                continue

            letter = m.group(1).upper()

            # Kiểm tra bài chưa làm - tìm pattern X/Y (X=điểm, Y=tổng bài)
            # Nếu X = 0 thì chưa làm (bất kể Y là bao nhiêu)
            if re.search(r"\b0/\d+\b", desc) or "Điểm đạt được: 0" in desc:
                result.add(letter)

        return sorted(list(result))
    
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





# ld = ldplayer()
# path = ld.dump_xml()
# print(path)

