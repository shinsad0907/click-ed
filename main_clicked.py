from auto_clicked import ldplayer
from load_image import LoadImage
from chatgpt import GeminiChatGPT
import threading
from time import sleep
from threading import Lock
import queue

class MainClicked:
    # Global locks
    _screen_capture_lock = Lock()
    _adb_lock = Lock()
    _device_list_lock = Lock()
    _ldplayer_launch_lock = Lock()
    
    # Dictionary để lock theo device ID
    _device_locks = {}
    _device_locks_mutex = Lock()
    
    def __init__(self, dataaccount_clicked=None):
        self.click_chapter_list = [
            (110,308), (450,308), (300,485), (165,660),
            (450,660), (300,850), (165,1020),
        ]
        self.click_chapter = (170,430)
        self.chapter_session_list = [
            (175,360), (175,510), (175,710), (175,880),
            (175,1070), (175,1070),
        ]
        self.chapter_homework_list = [
            (100,300), (100,500), (100,700), (100,900),
            (100,1100), (100,1100),
        ]
        self.click_homework = (310,150)
        self.click_homework_list = [
            (40,300), (40,380), (40,450), (40,570),
        ]
        self.success_click = (250,1200)

        self.dataaccount_clicked = dataaccount_clicked
        self.account_info = dataaccount_clicked["dataaccount_clicked"]
        self.name_ldplayer = dataaccount_clicked["name_ldplayer"]
        self.ldplayer_id = dataaccount_clicked.get("ldplayer_id", "")
        self.account_len = dataaccount_clicked["account_len"]
        self.account_index = dataaccount_clicked["account_index"]
        self.action_callback = dataaccount_clicked.get("action_callback", None)
        self.should_stop = False
        
        # ⭐ MỖI THREAD CÓ INSTANCE LDPLAYER RIÊNG
        self.ld = ldplayer()
        self.device_id = None  # Sẽ được gán sau khi connect ADB
        self.device_lock = None  # Lock riêng cho device này

    def _get_device_lock(self, device_id):
        """Lấy lock riêng cho device_id"""
        with MainClicked._device_locks_mutex:
            if device_id not in MainClicked._device_locks:
                MainClicked._device_locks[device_id] = Lock()
            return MainClicked._device_locks[device_id]

    def emit_action(self, action):
        """Gửi action callback về GUI"""
        if self.action_callback:
            email = self.account_info.split('|')[0]
            self.action_callback(email, action)
    
    def stop_automation(self):
        """Dừng automation"""
        self.should_stop = True
        self.emit_action("⏹️ Dừng tự động...")

    def open_or_check_ldplayer(self):
        """Mở LDPlayer và lấy device ID cố định"""
        print(f"\n📱 [{self.name_ldplayer}] Khởi động...")
        self.emit_action("🔄 Khởi động LDPlayer")
        
        # Launch LDPlayer
        with MainClicked._ldplayer_launch_lock:
            print(f"   [LAUNCH] {self.name_ldplayer}")
            self.ld.open_ldplayer(self.name_ldplayer)
        
        sleep(15)
        self.emit_action("⏳ Chờ ADB kết nối")
        
        # Chờ device kết nối và LẤY DEVICE ID CỐ ĐỊNH
        retry_count = 0
        max_retries = 120
        
        while retry_count < max_retries:
            if self.should_stop:
                return False
                
            with MainClicked._device_list_lock:
                devices = self.ld.DEVICE()
            
            if len(devices) > self.account_index:
                self.device_id = devices[self.account_index]
                self.device_lock = self._get_device_lock(self.device_id)
                self.emit_action(f"✅ Device: {self.device_id}")
                print(f"✅ [{self.name_ldplayer}] Device ID: {self.device_id}")
                break
            
            retry_count += 1
            if retry_count % 5 == 0:
                print(f"⏳ [{self.name_ldplayer}] Chờ ADB... ({retry_count}/{max_retries})")
            sleep(5)
        
        if not self.device_id:
            print(f"❌ [{self.name_ldplayer}] Timeout - không lấy được device ID")
            self.emit_action("❌ Timeout lấy device")
            return False
        
        # Chờ vào home screen
        retry_count = 0
        while retry_count < 60:
            if self.should_stop:
                return False
                
            try:
                if self.ld.is_ldplayer_in_home(self.device_id):
                    self.emit_action("✅ Sẵn sàng")
                    print(f"✅ [{self.name_ldplayer}] ({self.device_id}) READY!\n")
                    return True
            except Exception as e:
                print(f"⚠️ [{self.name_ldplayer}] Check home error: {e}")
            
            retry_count += 1
            sleep(5)
        
        print(f"❌ [{self.name_ldplayer}] Timeout chờ home screen")
        self.emit_action("❌ Timeout home screen")
        return False
    
    def setup_clicked_or_log(self):
        """Login - sử dụng device_id cố định"""
        tk, mk, name_homework = self.account_info.split('|')
        self.ld.index = self.account_index  # Set index cho instance này
        
        if self.ld.setup_clicked():
            while True:
                if self.ld.check_login():
                    with self.device_lock:
                        self.ld.click(402, 1200)
                        sleep(2)
                    
                    print(f"📝 [{self.name_ldplayer}] Username: {tk}")
                    with self.device_lock:
                        self.ld.click(170, 330)
                        self.ld.input(tk)
                        sleep(1)
                    
                    print(f"🔐 [{self.name_ldplayer}] Password")
                    with self.device_lock:
                        self.ld.click(170, 470)
                        self.ld.input(mk)
                        sleep(1)
                    
                    print(f"⏳ [{self.name_ldplayer}] Đăng nhập...")
                    with self.device_lock:
                        self.ld.click(245, 680)
                        sleep(4)
                    
                    with MainClicked._screen_capture_lock:
                        debug_image = self.ld.capture_ldplayer_screen(self.name_ldplayer)
                    
                    sleep(10)
                    
                    if self.ld.check_login_failed():
                        print(f'❌ [{self.name_ldplayer}] Login failed')
                        return True
                    else:
                        print(f'✅ [{self.name_ldplayer}] Login success: {tk}')
                        return True
    
    def set_make_clicked(self, name_homework):
        """Thiết lập làm bài - dùng device_id"""
        self.ld.index = self.account_index
        try:
            with self.device_lock:
                self.ld.click(300, 1030); sleep(2)
                self.ld.click(300, 700); sleep(2)
                self.ld.click(300, 1050); sleep(2)
                self.ld.click(430, 1200); sleep(2)
                self.ld.click(40, 60); sleep(2)
            
            x, y = self.ld.search_name_homework(name_homework)
            with self.device_lock:
                self.ld.click(x, y); sleep(2)
                # self.ld.click(300, 1200); sleep(2)
            return True
        except Exception as e:
            print(f"⚠️ [{self.name_ldplayer}] Setup error: {e}")
            return False

    def make_homework(self):
        """Làm bài tập - dùng device_id"""
        import random
        self.ld.index = self.account_index
        completed_count = 0
        previous_question = None
        
        while completed_count < 20:
            if self.should_stop:
                return
                
            try:
                question_answer = self.ld.get_question_and_answers()
                
                if question_answer != previous_question:
                    print(f"🔄 [{self.name_ldplayer}] Câu {completed_count+1}/20")
                    self.emit_action(f"❓ Câu {completed_count+1}/20")
                    
                    # ⭐ LẤY LẠI TỌA ĐỘ MỖI LẦN (vì layout thay đổi sau mỗi câu)
                    find_answers = self.ld.find_answers_by_xml()
                    ask = GeminiChatGPT().get_response(question_answer)
                    print(f"✅ [{self.name_ldplayer}] Đáp án: {ask}")
                    self.emit_action(f"💡 Đáp án: {ask[:20]}")
                    
                    answered = False
                    for letter in sorted(find_answers.keys()):
                        if letter in ask.split():
                            print(f"🔍 [{self.name_ldplayer}] Click {letter}")
                            with self.device_lock:
                                self.ld.click(find_answers[letter][0], 
                                            find_answers[letter][1])
                            answered = True
                            break
                    
                    # Nếu không tìm được đáp án → random một đáp án
                    if not answered:
                        if find_answers:
                            random_letter = random.choice(list(find_answers.keys()))
                            print(f"⚠️ [{self.name_ldplayer}] Không tìm được đáp án, random chọn {random_letter}")
                            self.emit_action(f"🎲 Random chọn {random_letter}")
                            with self.device_lock:
                                self.ld.click(find_answers[random_letter][0], 
                                            find_answers[random_letter][1])
                            answered = True
                        else:
                            print(f"❌ [{self.name_ldplayer}] Không có đáp án nào để chọn")
                    
                    # Click nút "Trả lời" để submit câu trả lời
                    # ⭐ LẤY LẠI TỌA ĐỘ NÚT TRẢ LỜI (vì layout thay đổi)
                    with self.device_lock:
                        self.ld.click(250, 1200)
                        sleep(2)
                    
                    previous_question = question_answer
                    completed_count += 1
                    print(f"✓ [{self.name_ldplayer}] Hoàn thành: {completed_count}/20\n")
                    self.emit_action(f"✓ Câu {completed_count}/20")
                else:
                    sleep(1)
            except Exception as e:
                print(f"⚠️ [{self.name_ldplayer}] Homework error: {e}")
                self.emit_action(f"⚠️ Lỗi: {str(e)[:30]}")
                sleep(1)
        
        # Hoàn tất
        # for _ in range(5):
        #     with self.device_lock:
        #         self.ld.adb_command(
        #             f'{self.ld.ADB}\\adb.exe -s {self.device_id} '
        #             f'shell input swipe 300 600 300 200'
        #         )
        #     sleep(2)
        
        with self.device_lock:
            self.ld.click(459, 750); sleep(2)
            self.ld.click(459, 700); sleep(2)
            self.ld.click(40, 75); sleep(2)
            self.ld.click(40, 75)

    def main_clicked(self):
        """Main workflow - SỬ DỤNG TỌA ĐỘ ĐỘNG"""
        try:
            print(f"\n{'='*60}")
            print(f"🚀 [{self.name_ldplayer}] Bắt đầu")
            print(f"   Account: {self.account_info}")
            print(f"{'='*60}\n")
            
            self.emit_action("🔄 Khởi động LDPlayer")
            if not self.open_or_check_ldplayer():
                print(f"❌ [{self.name_ldplayer}] Không mở được")
                self.emit_action("❌ Lỗi khởi động")
                return
            
            if self.should_stop:
                self.emit_action("⏹️ Đã dừng")
                return
            
            self.emit_action("🔑 Đang đăng nhập")
            if not self.setup_clicked_or_log():
                print(f"❌ [{self.name_ldplayer}] Login thất bại")
                self.emit_action("❌ Lỗi đăng nhập")
                return
            
            if self.should_stop:
                self.emit_action("⏹️ Đã dừng")
                return
            
            self.emit_action("⚙️ Chuẩn bị bài tập")
            homework_name = self.account_info.split('|')[2]
            if not self.set_make_clicked(homework_name):
                print(f"❌ [{self.name_ldplayer}] Setup thất bại")
                self.emit_action("❌ Lỗi chuẩn bị")
                return

            if self.should_stop:
                self.emit_action("⏹️ Đã dừng")
                return

            self.ld.index = self.account_index
            chapter = self.ld.detect_unfinished_chapters_fixed()
            print(f"📚 [{self.name_ldplayer}] Chương cần làm: {chapter}")
            self.emit_action(f"📚 {len(chapter)} chương cần làm")
            
            for ct in chapter:
                if self.should_stop:
                    self.emit_action("⏹️ Đã dừng")
                    return
                    
                print(f"\n🎯 [{self.name_ldplayer}] Chương {ct}")
                self.emit_action(f"📖 Chương {ct}")
                x, y = self.click_chapter_list[ct - 1]
                
                with self.device_lock:
                    self.ld.click(x, y); sleep(2)
                    self.ld.click(*self.click_chapter); sleep(2)
                
                while True:
                    if self.should_stop:
                        self.emit_action("⏹️ Đã dừng")
                        return
                        
                    # ====== XEM VIDEO - DÙNG TỌA ĐỘ CỐ ĐỊNH ======
                    videos_dict = self.ld.detect_unfinished_videos()  # Chỉ để biết CÓ video nào chưa xem không
                    
                    if not videos_dict:
                        print(f"✓ [{self.name_ldplayer}] Video xong, chuyển sang bài tập")
                        self.emit_action("✅ Video xong")
                        with self.device_lock:
                            self.ld.click(*self.click_homework)
                            sleep(2)
                        
                        # ====== LÀM BÀI TẬP - DÙNG TỌA ĐỘ ĐỘNG ======
                        homework_dict = self.ld.detect_unfinished_lessons()  # {'E': (x, y), 'F': (x, y)}
                        print(f"📝 [{self.name_ldplayer}] Bài tập cần làm: {list(homework_dict.keys())}")
                        self.emit_action(f"📝 {len(homework_dict)} bài tập")
                        
                        for hw, (hw_x, hw_y) in homework_dict.items():
                            if self.should_stop:
                                self.emit_action("⏹️ Đã dừng")
                                return
                                
                            print(f"[{self.name_ldplayer}] Làm bài {hw} tại ({hw_x}, {hw_y})...")
                            self.emit_action(f"✏️ Bài {hw}")
                            
                            # 🔽 CHỈ KÉO XUỐNG khi bài F (bài cuối cùng, ngoài màn hình)
                            with self.device_lock:
                                # CHỈ bài F mới kéo xuống
                                if hw == 'F':
                                    self.ld.adb_command(
                                        f'{self.ld.ADB}\\adb.exe -s {self.device_id} '
                                        f'shell input swipe 300 800 300 400 300'
                                    )
                                    sleep(1)
                                
                                self.ld.click(hw_x, hw_y)
                                sleep(2)
                                self.ld.click(360, 720); sleep(1)
                                self.ld.click(250, 210); sleep(1)
                            
                            self.make_homework()
                            sleep(2)
                        
                        # Thoát về danh sách chương
                        with self.device_lock:
                            self.ld.click(37, 70); sleep(1)
                            self.ld.click(37, 70)
                        break
                    
                    else:
                        # XEM TỪNG VIDEO - DÙNG TỌA ĐỘ ĐỘNG TỪ XML
                        print(f"📹 [{self.name_ldplayer}] Có {len(videos_dict)} video chưa xem, lấy tọa độ từ XML...")
                        self.emit_action(f"📹 {len(videos_dict)} video")
                        
                        for session_idx in sorted(videos_dict.keys()):
                            if self.should_stop:
                                self.emit_action("⏹️ Đã dừng")
                                return
                            
                            print(f"[{self.name_ldplayer}] Chuẩn bị xem video {session_idx}...")
                            
                            # 🔽 KÉO XUỐNG TRƯỚC (nếu cần)
                            if session_idx >= 6:
                                print(f"   ⬇️ Kéo xuống vì video {session_idx}...")
                                with self.device_lock:
                                    self.ld.adb_command(
                                        f'{self.ld.ADB}\\adb.exe -s {self.device_id} '
                                        f'shell input swipe 300 800 300 400 300'
                                    )
                                sleep(1)
                            
                            # ⭐ SAU ĐÓ MỚI DUMP XML ĐỂ LẤY TỌA ĐỘ CHÍNH XÁC
                            video_coords = self.ld.get_video_coords_from_xml()
                            
                            # Kiểm tra xem video này có tọa độ trong XML không
                            if session_idx not in video_coords:
                                print(f"   ⚠️ Video {session_idx}: Không tìm được tọa độ trong XML")
                                continue
                            
                            session_x, session_y = video_coords[session_idx]
                            print(f"[{self.name_ldplayer}] Click video {session_idx} tại ({session_x}, {session_y})...")
                            self.emit_action(f"▶️ Video {session_idx}")
                            
                            # Click video theo tọa độ từ XML
                            try:
                                with self.device_lock:
                                    self.ld.click(session_x, session_y)
                                    print(f"   ✅ Đã click video {session_idx} tại ({session_x}, {session_y})")
                                    sleep(3)
                            except Exception as e:
                                print(f"   ❌ Click video {session_idx} thất bại: {e}")
                                continue
                            
                            if self.should_stop:
                                self.emit_action("⏹️ Đã dừng")
                                return
                            
                            # Chờ video load đủ để hiển thị thời gian, rồi chụp ảnh
                            sleep(2)
                            with MainClicked._screen_capture_lock:
                                path_image = self.ld.capture_ldplayer_screen(self.name_ldplayer)
                            
                            remaining_time = LoadImage().get_video_remaining_time(path_image)
                            if remaining_time and remaining_time > 0:
                                print(f"⏱ [{self.name_ldplayer}] Video {session_idx}: Chờ {remaining_time}s...")
                                self.emit_action(f"⏳ Video {session_idx}: {remaining_time}s")
                                sleep(remaining_time)
                            else:
                                print(f"⚠️ [{self.name_ldplayer}] Video {session_idx}: Không detect thời gian, chờ 60s mặc định")
                                self.emit_action(f"⏳ Video {session_idx}: 60s")
                                sleep(60)
                            
                            if self.should_stop:
                                self.emit_action("⏹️ Đã dừng")
                                return
                            
                            with self.device_lock:
                                self.ld.click(37, 70)
                                print(f"   ← Thoát video {session_idx}")
                                sleep(1)
            
            if self.should_stop:
                self.emit_action("⏹️ Đã dừng")
                return
                
            print(f"\n✅ [{self.name_ldplayer}] HOÀN THÀNH\n")
            self.emit_action("✅ Hoàn thành")
            
        except Exception as e:
            print(f"❌ [{self.name_ldplayer}] Lỗi: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        with open(r'C:\Users\pc\Desktop\shin\click_edcmd\log.txt', 'r', encoding='utf-8') as f:
            data_account_clicked = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        print("❌ Không tìm thấy file log.txt")
        exit()
    
    if len(data_account_clicked) > 5:
        print('⚠️ Mỗi lần chạy chỉ được tối đa 5 tài khoản')
        exit()
    
    if not data_account_clicked:
        print("❌ File log.txt rỗng")
        exit()
    
    ldplayer_ids = ldplayer().get_ldplayer_ids()
    
    print(f"\n{'='*60}")
    print(f"📱 LDPlayer hiện có:")
    for ld_id, ld_name in ldplayer_ids:
        print(f"   ID: {ld_id}, Tên: {ld_name}")
    print(f"{'='*60}\n")
    
    if len(ldplayer_ids) < len(data_account_clicked):
        print(f"⚠️ Chỉ có {len(ldplayer_ids)} LDPlayer nhưng có {len(data_account_clicked)} tài khoản")
        exit()
    
    print(f"🚀 Bắt đầu xử lý {len(data_account_clicked)} tài khoản\n")
    
    threads = []
    
    for i, account in enumerate(data_account_clicked):
        ld_id, ld_name = ldplayer_ids[i]
        
        thread = threading.Thread(
            target=MainClicked({
                "dataaccount_clicked": account,
                "name_ldplayer": ld_name,
                "ldplayer_id": ld_id,
                "account_len": len(data_account_clicked),
                "account_index": i
            }).main_clicked,
            name=f"Thread-{ld_name}",
            daemon=False
        )
        threads.append(thread)
        thread.start()
        print(f"🚀 Khởi động: {ld_name} (ID: {ld_id})")
        sleep(3)
    
    print(f"\n⏳ Đang chờ {len(threads)} threads hoàn thành...\n")
    for thread in threads:
        thread.join()
    
    print("\n" + "="*60)
    print("✅ TẤT CẢ ĐÃ HOÀN THÀNH")
    print("="*60)