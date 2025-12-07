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
    def __init__(self) -> None:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.ADB = 'C:\\LDPlayer\\LDPlayer9'
    def adb_command(self,command):
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.stdout.decode('utf-8'), result.stderr.decode('utf-8')

    def capture_ldplayer_screen(self):
        # Tên cửa sổ LDPlayer (bạn có thể đổi lại nếu khác)
        window_name = "LDPlayer-1"
        
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

    def input(self,text):
        command = fr'{self.ADB}\\adb.exe -s {self.DEVICE()[0]} shell input text {text}'
        self.adb_command(command)
        sleep(2)

    def click(self,x,y):
        command = fr'{self.ADB}\\adb.exe -s {self.DEVICE()[0]} shell input tap {x} {y}'
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
        print(self.list_device)
        return self.list_device

    def dump_xml(self):
        # Dump UI
        cmd1 = fr"{self.ADB}\adb.exe -s {self.DEVICE()[0]} shell uiautomator dump /sdcard/view.xml"
        subprocess.run(cmd1, shell=True)

        # Copy file về PC
        cmd2 = fr"{self.ADB}\adb.exe -s {self.DEVICE()[0]} pull /sdcard/view.xml view.xml"
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
# ld = ldplayer()
# path = ld.capture_ldplayer_screen()

