from auto_clicked import ldplayer
from load_image import LoadImage
from chatgpt import GeminiChatGPT
import threading
from time import sleep

class MainClicked:
    def __init__(self, dataaccount_clicked=None):
        self.click_chapter_list = [
            (110,308),
            (450,308),
            (300,485),
            (165,660),
            (450,660),
            (300,850),
            (165,1020),
        ]

        self.click_chapter = (170,430)

        self.chapter_session_list = [
            (175,360),
            (175,560),
            (175,760),
            (175,960),
        ]

        self.chapter_homework_list = [
            (100,300),
            (100,500),
            (100,700),
            (100,900),
        ]

        self.click_homework = (310,150)

        self.click_homework_list = [
            (40,300),
            (40,380),
            (40,450),
            (40,570),
        ]
        self.success_click = (250,1200)

        # ====== Sửa lỗi tại đây ======
        self.dataaccount_clicked = dataaccount_clicked
        self.account_info = dataaccount_clicked["dataaccount_clicked"]
        self.name_ldplayer = dataaccount_clicked["name_ldplayer"]
        self.ldplayer_len = dataaccount_clicked["ldplayer_len"]
        self.account_index = dataaccount_clicked["account_index"]



    def open_or_check_ldplayer(self,ld):
        list_devices = ld.DEVICE()
        print(f"Đang mở LDPlayer: {self.name_ldplayer}")
        ld.open_ldplayer(self.name_ldplayer)
        while True:
            print(len(list_devices), self.ldplayer_len)
            if len(list_devices) >= self.ldplayer_len:
                print(f"LDPlayer {self.name_ldplayer} đã sẵn sàng.")
                break
            else:
                sleep(5)

        while True:
            if ld.is_ldplayer_in_home(ld.DEVICE()[self.account_index]):
                print(f"LDPlayer {self.name_ldplayer} đã kết nối ADB.")
                break
            else:
                sleep(5)

        return True
    
    def setup_clicked_or_log(self, ld):
        tk, mk = self.account_info.split('|')
        if ld.setup_clicked():
            while True:
                if ld.check_login():
                    ld.click(402, 1244)
                    sleep(2)
                    ld.click(170, 330)
                    ld.input(tk)
                    ld.click(170, 470)
                    ld.input(mk)
                    ld.click(245, 680)
                    if ld.check_login_falled():
                        print(f'{tk, mk} không chính xác')
                        return False
                    else:
                        return True

    def make_homework(self,ld):
        completed_count = 0
        previous_question = None
        
        while completed_count < 20:
            try:
                # Lấy đề bài hiện tại
                question_answer = ld.get_question_and_answers()
                
                # Kiểm tra xem đề bài có thay đổi hay không
                if question_answer != previous_question:
                    # Đề bài thay đổi = câu mới
                    print(f"🔄 Câu mới phát hiện (hoàn thành: {completed_count}/20)")
                    print(f"Đề bài: {question_answer[:100]}...")
                    
                    # Lấy đáp án và tìm câu trả lời
                    find_answers = ld.find_answers_by_xml()
                    ask = GeminiChatGPT().get_response(question_answer)
                    print("✅ Đáp án ChatGPT trả về:", ask)
                    
                    # Click vào đáp án đúng
                    if 'D' in ask.split():
                        ld.click(find_answers["D"][0], find_answers["D"][1])
                    elif 'C' in ask.split():
                        ld.click(find_answers["C"][0], find_answers["C"][1])
                    elif 'B' in ask.split():
                        ld.click(find_answers["B"][0], find_answers["B"][1])
                    elif 'A' in ask.split():
                        ld.click(find_answers["A"][0], find_answers["A"][1])
                    
                    # Click nút "Tiếp theo"
                    ld.click(250,1200)
                    sleep(2)
                    # Cập nhật biến để kiểm tra lần tiếp theo
                    previous_question = question_answer
                    completed_count += 1
                    print(f"✓ Hoàn thành: {completed_count}/20\n")
                else:
                    # Đề bài chưa thay đổi = vẫn cùng câu, chờ và retry
                    print("⏳ Đề bài chưa thay đổi, chờ...")
                    sleep(1)
            except Exception as e:
                print("⚠️ Lỗi khi làm bài tập:", e)
                sleep(1)
        ld.click(459,750)
        ld.click(459,700)
        ld.click(40,75)
        ld.click(40,75)

    

    def main_clicked(self):
        # print(self.click_chapter_list[0])
        ld = ldplayer(self.account_index)
        device = ld.DEVICE()

        if self.open_or_check_ldplayer(ld):
            print(f"🚀 Bắt đầu tự động hóa cho LDPlayer: {self.name_ldplayer}")
        
        if self.setup_clicked_or_log(ld):
            print('login thành công')
        else:
            print('login không thành công')
            return

        chapter = ld.detect_unfinished_chapters_fixed()
        for ct in chapter:
            if ct:
                print(f"Đang ở chương {ct}")
                x, y = self.click_chapter_list[ct - 1]
                print(f"Click vào chương tại tọa độ: ({x}, {y})")
                ld.click(x, y)
                sleep(2)
                x, y = self.click_chapter
                ld.click(x, y)
                sleep(2)
                while True:
                    session = ld.detect_unfinished_videos()
                    if session == []:
                        print("Đã hoàn thành tất cả các buổi học.")
                        x, y = self.click_homework
                        ld.click(x, y)
                        sleep(2)
                        homework_session = ld.detect_unfinished_lessons()
                        print("Bài tập cần làm shinsad:", homework_session)
                        if homework_session:
                            for hw in homework_session:
                                if hw == 'A':
                                    x, y = self.chapter_homework_list[0]
                                    ld.click(x, y)
                                    sleep(2)
                                    ld.click(360, 720)
                                    ld.click(250,210)
                                    self.make_homework(ld)
                                if hw == 'B':
                                    x, y = self.chapter_homework_list[1]
                                    ld.click(x, y)
                                    sleep(2)
                                    ld.click(360, 720)
                                    ld.click(250,210)
                                    self.make_homework(ld)
                                if hw == 'C':
                                    x, y = self.chapter_homework_list[2]
                                    ld.click(x, y)
                                    sleep(2)
                                    ld.click(360, 720)
                                    ld.click(250,210)
                                    self.make_homework(ld)
                                if hw == 'D':
                                    x, y = self.chapter_homework_list[3]
                                    ld.click(x, y)
                                    sleep(2)
                                    ld.click(360, 720)
                                    ld.click(250,210)
                                    self.make_homework(ld)
                                sleep(2)
                        ld.click(37,70)
                        ld.click(37,70)
                        break  # Thoát khỏi while loop để sang chương tiếp theo
                    else:
                        if 1 in session :
                            ld.click(self.chapter_session_list[0][0], self.chapter_session_list[0][1])
                            path_image = ld.capture_ldplayer_screen(self.name_ldplayer)
                            remaining_time = LoadImage().get_video_remaining_time(path_image)
                            if remaining_time and remaining_time > 0:
                                sleep(remaining_time)
                            ld.click(37,70)
                        if 2 in session :
                            ld.click(self.chapter_session_list[1][0], self.chapter_session_list[1][1])
                            path_image = ld.capture_ldplayer_screen(self.name_ldplayer)
                            remaining_time = LoadImage().get_video_remaining_time(path_image)
                            if remaining_time and remaining_time > 0:
                                sleep(remaining_time)
                            ld.click(37,70)
                        if 3 in session :
                            ld.click(self.chapter_session_list[2][0], self.chapter_session_list[2][1])
                            path_image = ld.capture_ldplayer_screen(self.name_ldplayer)
                            remaining_time = LoadImage().get_video_remaining_time(path_image)
                            if remaining_time and remaining_time > 0:
                                sleep(remaining_time)
                            ld.click(37,70)
                        if 4 in session :
                            ld.click(self.chapter_session_list[3][0], self.chapter_session_list[3][1])
                            path_image = ld.capture_ldplayer_screen(self.name_ldplayer)
                            remaining_time = LoadImage().get_video_remaining_time(path_image)
                            if remaining_time and remaining_time > 0:
                                sleep(remaining_time)
                            ld.click(37,70)


if __name__ == "__main__":
    try:
        with open(r'D:\shin\click-ed\log.txt', 'r', encoding='utf-8') as f:
            data_account_clicked = f.readlines()
        
    except:
        print("Chạy lần đầu tiên, tạo file log.txt và khởi động lại chương trình.")
    if len(data_account_clicked) > 5:
        print('mỗi lần chạy chỉ được 5 tài khoản') 
        exit()
    list_ldplayer = ldplayer().get_ldplayer_names()

    for i, account in enumerate(data_account_clicked, start=0):
        account = account.strip()
        main_thread = threading.Thread(
            target=MainClicked(
                {
                    "dataaccount_clicked": account,
                    "name_ldplayer": list_ldplayer[i],
                    "ldplayer_len": len(list_ldplayer),
                    "account_index": i
                }
            ).main_clicked
        )

        main_thread.start()
        main_thread.join()
# MainClicked().main_clicked()

