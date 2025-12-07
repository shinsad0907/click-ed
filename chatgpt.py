import google.generativeai as genai
from gotrue import model
class GeminiChatGPT:
    def __init__(self):
        genai.configure(api_key="AIzaSyB0zaSe78bLdBvMniM9EnmfNWYi16L2OaM")   # Thay bằng API key của bạn
    
    def get_response(self, messages):
        model = genai.GenerativeModel("gemini-2.5-flash")

        resp = model.generate_content(f'{messages}, chỉ trả lời ABCD thôi nhé, không trả lời thêm bất kì điều gì nữa chỉ duy nhất trả lời ABCD thôi, tuyệt đối không thêm bất kì cái gì nữa')
        return resp.text
