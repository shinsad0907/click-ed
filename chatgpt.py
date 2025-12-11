from groq import Groq
class GeminiChatGPT:
    def __init__(self):
        self.client = Groq(api_key="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")
    
    def get_response(self, messages):
        resp = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",   # Model mạnh nhất, free
            messages=[
                {
                    "role": "user",
                    "content": messages + 
                               "\nChỉ trả lời đúng 1 ký tự trong A, B, C hoặc D. Không giải thích."
                }
            ]
        )

        return resp.choices[0].message.content.strip()

# re = GeminiChatGPT().get_response("Câu hỏi là gì? A. Đáp án A B. Đáp án B C. Đáp án C D. Đáp án D")
# print(re) 
# # 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