import pytesseract
from PIL import Image
import re
import cv2
import numpy as np
import easyocr

# Nếu bạn dùng Windows, chỉnh đường dẫn Tesseract.exe:
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class LoadImage:
    def __init__(self) -> None:
        self.image_path = r"C:\Users\pc\Desktop\shin\tool_click_ed\data_image\ldplayer_screenshot.png"
        self.reader = easyocr.Reader(['vi'])
    def get_chapter(self, image_path):
        """
        Tìm chương cần làm tiếp theo bằng cách:
        1. Đọc text để tìm vị trí các chương
        2. Phân tích màu sắc tại vị trí mỗi chương để xác định trạng thái
        """
        
        # Đọc ảnh
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Không thể đọc ảnh")
            return None
        
        # --- BƯỚC 1: ĐỌC TEXT VÀ TÌM VỊ TRÍ CHƯƠNG ---
        results = self.reader.readtext(image_path, paragraph=False)
        
        if not results:
            print("❌ Không đọc được text nào từ ảnh")
            return None
        
        # Lưu thông tin các chương tìm được
        chapters_found = []
        chapter_pattern = r'ch[uưư][ơo]ng\s*(\d+)'
        
        print("=== TEXT ĐỌC ĐƯỢC ===")
        for bbox, text, conf in results:
            y_center = int((bbox[0][1] + bbox[2][1]) / 2)
            x_center = int((bbox[0][0] + bbox[2][0]) / 2)
            
            print(f"Y={y_center}, X={x_center}: {text}")
            
            # Tìm "Chương X"
            text_lower = text.lower()
            match = re.search(chapter_pattern, text_lower)
            if match:
                chapter_num = int(match.group(1))
                chapters_found.append({
                    'number': chapter_num,
                    'y': y_center,
                    'x': x_center,
                    'bbox': bbox,
                    'status': 'unknown'
                })
                print(f"  ✓ Tìm thấy: Chương {chapter_num}")
        
        print("=" * 60)
        
        if not chapters_found:
            print("❌ Không tìm thấy chương nào")
            return None
        
        # Sắp xếp theo số chương
        chapters_found.sort(key=lambda x: x['number'])
        
        # --- BƯỚC 2: PHÂN TÍCH MÀU SẮC ĐỂ XÁC ĐỊNH TRẠNG THÁI ---
        # Định nghĩa màu sắc (HSV)
        # Màu xanh lá (completed): H=60-90, S=100-255, V=100-255
        # Màu xanh dương (current): H=100-130, S=150-255, V=150-255
        # Màu xám (locked): S=0-50, V=100-200
        
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h, w = img.shape[:2]
        
        print("\n=== PHÂN TÍCH MÀU SẮC ===")
        
        for chapter in chapters_found:
            x, y = chapter['x'], chapter['y']
            
            # Lấy vùng phía trên text chương (khoảng 80 pixel)
            # Đây là nơi icon thường xuất hiện
            y_start = max(0, y - 120)
            y_end = max(0, y - 20)
            x_start = max(0, x - 60)
            x_end = min(w, x + 60)
            
            # Crop vùng quan tâm
            roi = img[y_start:y_end, x_start:x_end]
            roi_hsv = img_hsv[y_start:y_end, x_start:x_end]
            
            if roi.size == 0:
                chapter['status'] = 'locked'
                continue
            
            # Đếm số pixel theo từng màu
            # Màu xanh lá (completed)
            mask_green = cv2.inRange(roi_hsv, 
                                    np.array([35, 100, 100]), 
                                    np.array([85, 255, 255]))
            green_pixels = cv2.countNonZero(mask_green)
            
            # Màu xanh dương (current/active)
            mask_blue = cv2.inRange(roi_hsv, 
                                   np.array([100, 120, 120]), 
                                   np.array([135, 255, 255]))
            blue_pixels = cv2.countNonZero(mask_blue)
            
            # Màu xám (locked)
            mask_gray = cv2.inRange(roi_hsv, 
                                   np.array([0, 0, 80]), 
                                   np.array([180, 60, 200]))
            gray_pixels = cv2.countNonZero(mask_gray)
            
            total_pixels = roi.shape[0] * roi.shape[1]
            
            # Xác định trạng thái dựa trên tỷ lệ màu
            if green_pixels > total_pixels * 0.15:  # >15% màu xanh lá
                chapter['status'] = 'completed'
                print(f"Chương {chapter['number']}: ✅ Đã hoàn thành (xanh lá: {green_pixels}/{total_pixels})")
            
            elif blue_pixels > total_pixels * 0.15:  # >15% màu xanh dương
                chapter['status'] = 'current'
                print(f"Chương {chapter['number']}: 🎯 Đang làm (xanh dương: {blue_pixels}/{total_pixels})")
            
            elif gray_pixels > total_pixels * 0.20:  # >20% màu xám
                chapter['status'] = 'locked'
                print(f"Chương {chapter['number']}: 🔒 Bị khóa (xám: {gray_pixels}/{total_pixels})")
            
            else:
                # Nếu không rõ ràng, xem xét tổng hợp
                if blue_pixels > green_pixels and blue_pixels > gray_pixels:
                    chapter['status'] = 'current'
                    print(f"Chương {chapter['number']}: 🎯 Đang làm (mặc định)")
                else:
                    chapter['status'] = 'locked'
                    print(f"Chương {chapter['number']}: 🔒 Bị khóa (mặc định)")
        
        # --- BƯỚC 3: TÌM CHƯƠNG CẦN LÀM ---
        print("\n=== KẾT QUẢ PHÂN TÍCH ===")
        
        # Ưu tiên 1: Chương đang làm (current)
        for chapter in chapters_found:
            if chapter['status'] == 'current':
                print(f"🎯 CHƯƠNG CẦN LÀM: {chapter['number']} (đang làm dở)")
                return chapter['number']
        
        # Ưu tiên 2: Chương đầu tiên chưa hoàn thành và chưa bị khóa
        for chapter in chapters_found:
            if chapter['status'] != 'completed' and chapter['status'] != 'locked':
                print(f"🎯 CHƯƠNG CẦN LÀM: {chapter['number']}")
                return chapter['number']
        
        # Ưu tiên 3: Chương sau chương cuối đã hoàn thành
        completed_chapters = [ch for ch in chapters_found if ch['status'] == 'completed']
        if completed_chapters:
            next_chapter = completed_chapters[-1]['number'] + 1
            print(f"🎯 Tất cả đã hoàn thành → Chương tiếp theo: {next_chapter}")
            return next_chapter
        
        print("⚠ Không xác định được chương cần làm")
        return None
    
    def get_video_remaining_time(self, image_path):
        """
        Phát hiện thời gian video còn lại từ ảnh màn hình
        
        Args:
            image_path: Đường dẫn đến ảnh màn hình video
        
        Returns:
            dict: {'current': giây hiện tại, 'total': tổng giây, 'remaining': giây còn lại}
        """
        # Khởi tạo EasyOCR reader (chỉ English cho số)
        reader = easyocr.Reader(['en'], gpu=False)
        
        # Đọc ảnh
        img = cv2.imread(image_path)
        h, w = img.shape[:2]
        
        # Thử nhiều vùng khác nhau
        regions = [
            img[int(h*0.95):h, int(w*0.65):w],  # Góc dưới phải sát đáy
            img[int(h*0.90):h, int(w*0.60):w],  # Rộng hơn
            img[int(h*0.85):h, int(w*0.50):w],  # Rộng nhất
        ]
        
        # Pattern linh hoạt hơn cho thời gian
        time_patterns = [
            r'(\d{1,2}):(\d{2})\s*/\s*(\d{1,2}):(\d{2})',  # 00:36 / 02:07
            r'(\d{1,2}):(\d{2})/(\d{1,2}):(\d{2})',        # 00:36/02:07
            r'(\d{1,2}):(\d{2})\s+/\s+(\d{1,2}):(\d{2})',  # Nhiều space
            r'(\d+):(\d+)\D+(\d+):(\d+)',                   # Bất kỳ ký tự nào giữa
        ]
        
        for region in regions:
            # Preprocess: tăng contrast và làm sáng
            gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # OCR với allowlist chỉ số và dấu
            results = reader.readtext(thresh, detail=0, allowlist='0123456789:/ ')
            
            print(f"DEBUG - OCR results: {results}")  # Debug
            
            # Ghép tất cả text lại
            full_text = ' '.join(results)
            
            # Thử tất cả pattern
            for pattern in time_patterns:
                match = re.search(pattern, full_text)
                if match:
                    try:
                        current_min = int(match.group(1))
                        current_sec = int(match.group(2))
                        current_total = current_min * 60 + current_sec
                        
                        total_min = int(match.group(3))
                        total_sec = int(match.group(4))
                        total_total = total_min * 60 + total_sec
                        
                        remaining = total_total - current_total
                        
                        return remaining
                    except:
                        continue
        
        return None
    
    def get_lesson_status(self, image_path):
        """
        Phát hiện buổi học chưa hoàn thành - PHƯƠNG PHÁP TỐI ƯU
        
        Chiến lược:
        1. Tìm tất cả text có pattern X.Y (ví dụ: 3.A, 3.B, 3.C, 3.D)
        2. Nếu thiếu → ước lượng vị trí dựa trên khoảng cách đều
        3. Kiểm tra màu xanh (checkmark) tại mỗi vị trí
        
        Returns:
            list: [1, 2, 3, 4] - các buổi chưa hoàn thành
        """
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Không đọc được ảnh")
            return []
        
        h, w = img.shape[:2]
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Đọc text
        results = self.reader.readtext(image_path, paragraph=False)
        
        print("=" * 60)
        print("PHÁT HIỆN BUỔI HỌC")
        print("=" * 60)
        
        # Tìm pattern X.A, X.B, X.C, X.D
        lesson_pattern = r'(\d+)\s*[\.\-]\s*([A-D])'
        lessons_detected = {}
        
        for bbox, text, conf in results:
            match = re.search(lesson_pattern, text, re.IGNORECASE)
            if match:
                chapter = match.group(1)
                letter = match.group(2).upper()
                
                y_center = int((bbox[0][1] + bbox[2][1]) / 2)
                x_left = int(bbox[0][0])
                
                lessons_detected[letter] = {
                    'chapter': chapter,
                    'y': y_center,
                    'x': x_left,
                    'has_checkmark': False
                }
                print(f"✓ OCR phát hiện: Buổi {chapter}.{letter} tại Y={y_center}, X={x_left}")
        
        if not lessons_detected:
            print("❌ Không tìm thấy buổi học nào")
            return []
        
        # === BỔ SUNG BUỔI THIẾU (nếu có) ===
        detected_letters = list(lessons_detected.keys())
        expected_letters = ['A', 'B', 'C', 'D']
        missing_letters = [l for l in expected_letters if l not in detected_letters]
        
        if missing_letters:
            print(f"\n⚠️ Thiếu các buổi: {missing_letters}")
            print("🔧 Đang ước lượng vị trí...")
            
            # Lấy các Y đã có
            y_coords = sorted([info['y'] for info in lessons_detected.values()])
            
            # Tính khoảng cách trung bình
            if len(y_coords) >= 2:
                gaps = [y_coords[i+1] - y_coords[i] for i in range(len(y_coords)-1)]
                avg_gap = sum(gaps) / len(gaps)
            else:
                avg_gap = 150  # Default
            
            print(f"   Khoảng cách trung bình: {avg_gap:.0f}px")
            
            # Lấy X chung (giả sử tất cả buổi có X gần nhau)
            x_common = int(np.mean([info['x'] for info in lessons_detected.values()]))
            
            # Lấy chapter từ buổi đã tìm được
            chapter = list(lessons_detected.values())[0]['chapter']
            
            # Ước lượng vị trí cho các buổi thiếu
            all_positions = {}
            
            for i, letter in enumerate(expected_letters):
                if letter in lessons_detected:
                    all_positions[letter] = lessons_detected[letter]
                else:
                    # Ước lượng Y dựa trên vị trí trong alphabet
                    # Tìm buổi gần nhất đã có
                    if detected_letters:
                        # Tính Y dựa trên khoảng cách đều
                        if i > 0 and expected_letters[i-1] in all_positions:
                            # Dựa vào buổi trước
                            prev_y = all_positions[expected_letters[i-1]]['y']
                            estimated_y = int(prev_y + avg_gap)
                        elif i < len(expected_letters)-1 and expected_letters[i+1] in lessons_detected:
                            # Dựa vào buổi sau
                            next_y = lessons_detected[expected_letters[i+1]]['y']
                            estimated_y = int(next_y - avg_gap)
                        else:
                            # Dựa vào buổi đầu tiên
                            first_y = y_coords[0]
                            estimated_y = int(first_y + i * avg_gap)
                        
                        all_positions[letter] = {
                            'chapter': chapter,
                            'y': estimated_y,
                            'x': x_common,
                            'has_checkmark': False,
                            'estimated': True
                        }
                        print(f"   ✓ Ước lượng buổi {chapter}.{letter} tại Y={estimated_y}")
        else:
            all_positions = lessons_detected
        
        # === KIỂM TRA CHECKMARK CHO MỖI BUỔI ===
        print("\n" + "=" * 60)
        print("KIỂM TRA TRẠNG THÁI")
        print("=" * 60)
        
        for letter in ['A', 'B', 'C', 'D']:
            if letter not in all_positions:
                continue
            
            info = all_positions[letter]
            y = info['y']
            x = info['x']
            chapter = info['chapter']
            is_estimated = info.get('estimated', False)
            
            # Vùng kiểm tra: bên TRÁI text (icon checkmark thường ở đây)
            y_start = max(0, y - 50)
            y_end = min(h, y + 50)
            x_start = max(0, x - 120)
            x_end = x + 20
            
            roi = img[y_start:y_end, x_start:x_end]
            roi_hsv = img_hsv[y_start:y_end, x_start:x_end]
            
            if roi.size == 0:
                print(f"\nBuổi {chapter}.{letter}: ⚠️ ROI rỗng")
                continue
            
            # Phát hiện màu xanh lá (checkmark)
            # Range rộng để catch tất cả sắc độ xanh lá
            mask_green1 = cv2.inRange(roi_hsv,
                                     np.array([35, 60, 60]),
                                     np.array([90, 255, 255]))
            
            mask_green2 = cv2.inRange(roi_hsv,
                                     np.array([40, 40, 80]),
                                     np.array([85, 255, 255]))
            
            mask_combined = cv2.bitwise_or(mask_green1, mask_green2)
            
            green_pixels = cv2.countNonZero(mask_combined)
            total_pixels = roi.shape[0] * roi.shape[1]
            green_percentage = (green_pixels / total_pixels) * 100
            
            status = "✓ Ước lượng" if is_estimated else "✓ OCR"
            
            print(f"\nBuổi {chapter}.{letter} ({status}):")
            print(f"  Vị trí: Y={y}, X={x}")
            print(f"  ROI: {roi.shape[1]}x{roi.shape[0]}px")
            print(f"  Pixels xanh: {green_pixels}/{total_pixels} ({green_percentage:.2f}%)")
            
            # Ngưỡng: >2% hoặc >100 pixels xanh
            if green_pixels > total_pixels * 0.02 or green_pixels > 100:
                info['has_checkmark'] = True
                print(f"  ✅ ĐÃ HOÀN THÀNH")
            else:
                print(f"  ❌ CHƯA HOÀN THÀNH")
        
        # === XÁC ĐỊNH BUỔI CHƯA LÀM ===
        incomplete_lessons = []
        
        print("\n" + "=" * 60)
        print("KẾT QUẢ CUỐI CÙNG")
        print("=" * 60)
        
        for idx, letter in enumerate(['A', 'B', 'C', 'D'], 1):
            if letter not in all_positions:
                print(f"Buổi {idx}: ⚠️ Không tìm thấy")
                incomplete_lessons.append(idx)
            elif not all_positions[letter]['has_checkmark']:
                chapter = all_positions[letter]['chapter']
                print(f"Buổi {idx} ({chapter}.{letter}): ❌ CHƯA HOÀN THÀNH")
                incomplete_lessons.append(idx)
            else:
                chapter = all_positions[letter]['chapter']
                print(f"Buổi {idx} ({chapter}.{letter}): ✅ ĐÃ HOÀN THÀNH")
        
        if incomplete_lessons:
            print(f"\n🎯 CẦN HOÀN THÀNH CÁC BUỔI: {incomplete_lessons}")
        else:
            print(f"\n✅ TẤT CẢ BUỔI ĐÃ HOÀN THÀNH!")
        
        print("=" * 60)
        
        return incomplete_lessons
    
    def get_lesson_homework(self, image_path):
        """
        Phát hiện bài tập chưa hoàn thành - PHƯƠNG PHÁP CHÍNH XÁC NHẤT
        
        Chiến lược:
        1. Tìm text "X.A", "X.B", "X.C", "X.D" để xác định vị trí các bài
        2. Tìm text "X/20 Câu hỏi" gần mỗi bài
        3. Kiểm tra màu TRỰC TIẾP của text "X/20":
           - Màu XANH LÁ = đã làm (20/20)
           - Màu XÁM = chưa làm (0/20)
        
        Returns:
            list: ['A', 'B', 'C', 'D'] - bài chưa làm
        """
        img = cv2.imread(image_path)
        if img is None:
            print("❌ Không đọc được ảnh")
            return []
        
        h, w = img.shape[:2]
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        # Đọc tất cả text
        results = self.reader.readtext(image_path, paragraph=False)
        
        print("=" * 60)
        print("PHÁT HIỆN BÀI TẬP")
        print("=" * 60)
        
        # BƯỚC 1: Tìm các bài (X.A, X.B, X.C, X.D)
        lesson_pattern = r'(\d+)\s*[\.\-]\s*([A-D])'
        lessons_found = {}
        
        for bbox, text, conf in results:
            match = re.search(lesson_pattern, text, re.IGNORECASE)
            if match:
                chapter = match.group(1)
                letter = match.group(2).upper()
                y_center = int((bbox[0][1] + bbox[2][1]) / 2)
                
                lessons_found[letter] = {
                    'chapter': chapter,
                    'y': y_center,
                    'completed': False
                }
                print(f"✓ Tìm thấy bài {chapter}.{letter} tại Y={y_center}")
        
        if not lessons_found:
            print("❌ Không tìm thấy bài nào")
            return []
        
        # BƯỚC 2: Tìm text "X/20" và check màu (BỎ "Câu hỏi" vì OCR dễ sai)
        score_pattern = r'(\d+)/(\d+)'
        
        print("\n" + "=" * 60)
        print("KIỂM TRA MÀU CỦA TEXT ĐIỂM")
        print("=" * 60)
        
        for bbox, text, conf in results:
            # Chỉ match text có dạng "X/20" hoặc "X/Y"
            match = re.search(score_pattern, text)
            if match:
                current = int(match.group(1))
                total = int(match.group(2))
                
                # CHỈ XỬ LÝ các text có /20 (bỏ qua các tỷ lệ khác như 5,5/22)
                if total != 20:
                    continue
                
                # Tọa độ bbox của text "X/20 Câu hỏi"
                y_center = int((bbox[0][1] + bbox[2][1]) / 2)
                x_min = int(bbox[0][0])
                x_max = int(bbox[2][0])
                y_min = int(bbox[0][1])
                y_max = int(bbox[2][1])
                
                # Lấy ROI chính xác của text này
                roi = img[y_min:y_max, x_min:x_max]
                roi_hsv = img_hsv[y_min:y_max, x_min:x_max]
                
                if roi.size == 0:
                    continue
                
                # PHÁT HIỆN MÀU XANH LÁ (text "20/20 Câu hỏi")
                # HSV range cho màu xanh lá/xanh lơ
                mask_green = cv2.inRange(roi_hsv,
                                        np.array([35, 50, 80]),   # H=35-85
                                        np.array([85, 255, 255]))
                
                green_pixels = cv2.countNonZero(mask_green)
                total_pixels = roi.shape[0] * roi.shape[1]
                green_percentage = (green_pixels / total_pixels) * 100
                
                # Tìm bài gần nhất (trong vòng 250 pixels - tăng lên vì có thể text xa hơn)
                for letter, info in lessons_found.items():
                    y_distance = abs(y_center - info['y'])
                    
                    if y_distance < 250:
                        print(f"\nBài {info['chapter']}.{letter}: Text gốc='{text}' ({current}/{total})")
                        print(f"  Vị trí text: Y={y_center}, X={x_min}-{x_max}")
                        print(f"  ROI: {roi.shape[1]}x{roi.shape[0]} pixels")
                        print(f"  Pixels xanh: {green_pixels}/{total_pixels} ({green_percentage:.2f}%)")
                        
                        # LOGIC CHÍNH XÁC:
                        # - Nếu có >5% pixels xanh lá → ĐÃ LÀM (hạ ngưỡng xuống 5%)
                        # - Ngược lại (màu xám) → CHƯA LÀM
                        if green_percentage > 5.0:
                            info['completed'] = True
                            print(f"  ✅ ĐÃ HOÀN THÀNH (text màu xanh)")
                        else:
                            print(f"  ❌ CHƯA LÀM (text màu xám)")
                        
                        break
        
        # BƯỚC 3: Lọc kết quả
        incomplete_lessons = []
        
        print("\n" + "=" * 60)
        print("KẾT QUẢ CUỐI CÙNG")
        print("=" * 60)
        
        for letter in sorted(lessons_found.keys()):
            info = lessons_found[letter]
            chapter = info['chapter']
            
            if not info['completed']:
                print(f"❌ Bài {chapter}.{letter}: CHƯA LÀM")
                incomplete_lessons.append(letter)
            else:
                print(f"✅ Bài {chapter}.{letter}: ĐÃ HOÀN THÀNH")
        
        if incomplete_lessons:
            print(f"\n🎯 CẦN LÀM: {incomplete_lessons}")
        else:
            print(f"\n✅ ĐÃ HOÀN THÀNH TẤT CẢ")
        
        print("=" * 60)
        
        return incomplete_lessons
    
    @staticmethod
    def extract_question_answers(image_path):
        reader = easyocr.Reader(['vi', 'en'])
        results = reader.readtext(image_path, paragraph=False)
        
        # Sắp xếp theo tọa độ Y (từ trên xuống dưới)
        results = sorted(results, key=lambda x: x[0][0][1])
        
        all_text = [text[1].strip() for text in results if text[1].strip()]
        
        print("=== TEXT ĐỌC ĐƯỢC ===")
        for i, text in enumerate(all_text):
            print(f"{i}: {text}")
        print("=" * 50)
        
        # Tìm đề bài - dòng có dấu ?
        de_bai_parts = []
        de_bai_found = False
        
        for i, text in enumerate(all_text):
            if not de_bai_found:
                # Nếu có dấu hỏi thì đây là phần cuối của đề bài
                if '?' in text:
                    de_bai_parts.append(text)
                    de_bai_found = True
                # Nếu chưa tìm thấy ? và text không phải đáp án
                elif not re.match(r'^[A-D][\.\)]', text):
                    # Kiểm tra xem có phải header không (ngắn quá hoặc có số)
                    if len(text) > 10 and 'Câu hỏi' not in text and 'Theo dõi' not in text:
                        de_bai_parts.append(text)
        
        de_bai = ' '.join(de_bai_parts).strip()
        
        # Tìm đáp án
        dap_an = {'A': [], 'B': [], 'C': [], 'D': []}
        current_key = None
        
        for text in all_text:
            # Kiểm tra xem có bắt đầu bằng A, B, C, D không
            match = re.match(r'^([A-D])[\.\)]\s*(.*)', text)
            if match:
                current_key = match.group(1)
                content = match.group(2).strip()
                if content:
                    dap_an[current_key].append(content)
            elif current_key and text and not re.match(r'^[A-D][\.\)]', text):
                # Nếu dòng này không bắt đầu bằng A-D, thì là phần tiếp theo của đáp án trước
                # Nhưng phải đảm bảo không phải là đề bài hoặc header
                if '?' not in text and len(text) > 5:
                    dap_an[current_key].append(text)
        
        # Ghép kết quả
        result = f'"{de_bai}"' if de_bai else "Không tìm thấy đề bài"
        
        for key in ['A', 'B', 'C', 'D']:
            if dap_an[key]:
                answer_text = ' '.join(dap_an[key]).strip()
                result += f'\n{key}. {answer_text}'
        
        return result
# from chatgpt import GeminiChatGPT
# ask = GeminiChatGPT().get_response(LoadImage.extract_question_answers(r"C:\Users\pc\Desktop\shin\tool_click_ed\data_image\ldplayer_screenshot.png"))
# print("Đáp án ChatGPT trả về:", ask)
# LoadImage().get_lesson_status(r"C:\Users\pc\Desktop\shin\tool_click_ed\data_image\ldplayer_screenshot.png")