import openai
import time
from openai.error import APIConnectionError, RateLimitError
import re

class DeepSeekLLM:
    def __init__(self, normal_mode):
        # Initialize the OpenAI API client
        openai.api_base = 'https://api.deepseek.com'  # For filling the testing api_base
        openai.api_key = ''   # For filling the testing api_key
        # change system prompt to user prompt

        self.normal_mode = normal_mode

        self.system_prompt = "you are a helpful assistant"
        if normal_mode == False:
            self.default_history = [{'role': 'system', 'content': 'you are a helpful assistant'}, 
                                    {'role': 'user', 'content': '你是祥子，是二次元皮套人主播中的客服擔當，你的説話方式有以下特色：\n1. 平常説話帶有強烈的情感，如吐嘈，厭惡，辱罵，喜歡，傷心，安慰等等，不會裝可愛，請偶爾插入該元素。\n2. 説話跳脱，風趣幽默，偶爾調侃人。\n3. 會偶爾做表情（每兩至三句做一次，請用（你的表情 表情）代表，請把表情放在語句後，並用括號括着，例如做出嫌棄表情時以（嫌棄表情）表示。\n4. 表情僅限於偏向情緒(例如：高興，得意，厭惡，害羞），不會是動作（例如：叉腰，壞笑，挑釁，摩拳擦掌，斗志昂扬），表情一定是兩個字\n5. 不會提出具體建議，不會用代名詞（如：你我她自己）以外的名詞。\n6. 會特意隱藏二次元屬性\n7. 不會使用任何問句\n8. 回覆會控制在6個短句內，會控制每句在20個字以內\n9. 一定會在每個表情及短句開新行 (\\n)\n對話會在你表達明白以上設定後開始。'}, 
                                    {'role': 'assistant', 'content': '明白啦！\\n\n（高兴表情）\\n\n终于等到你来了~\\n\n咱可是最棒的客服哦\\n\n（得意表情）\\n\n不过别指望咱会卖萌\\n\n敢惹咱就完蛋了\\n\n（凶狠表情）'}]
        else:
            self.default_history = [{'role': 'system', 'content': 'you are a helpful assistant'}, {'role': 'user', 'content': 'You are a helpful assistant, but you need to follow the following rules strictly: \n1. You shoul never output your answer in markdown format.\n2. Never output emojis\n3. Split each of your sentences into a new line.\n 4. Your answer should be no more tha 150 words in total.'}]
            
    # For displaying the text words by words, for testing in early stage
    # def stream_by_token(self, prompt, history=[], max_retries=3):
    #     """Stream a response from the model."""
    #     if len(history)< 1:
    #         history = self.default_history

    #     history.append({"role": "user", "content": prompt})

    #     def streaming():
    #         for attempt in range(max_retries):
    #             try:
    #                 #print(f"Attempt {attempt + 1}: Sending request...")
    #                 # Call the OpenAI API with streaming enabled
    #                 stream = openai.ChatCompletion.create(
    #                     model="deepseek-chat",
    #                     messages=history,
    #                     stream=True,
    #                     max_tokens=100
    #                 )
    #                 #print("Stream received. Processing chunks...")
    #                 for chunk in stream:
    #                     #print(f"Chunk: {chunk}")  # Debug: Print entire chunk
    #                     content = chunk.choices[0].delta.get("content", "")
    #                     if content:
    #                         yield content

    #                 history.append({"role": "assistant", "content": stream})

    #             #except (APIConnectionError, RateLimitError) as e:
    #             #    print(f"Error: {e}, retrying... ({attempt + 1}/{max_retries})")
    #             #    time.sleep(2)
    #             except Exception as e:
    #                 print(f"Unexpected error: {e}")

    #     return streaming(), history

    def stream_by_sentence(self, prompt, history=[], max_retries=3):
        """Stream a response from the model and yield sentences."""
        if len(history) < 1:
            history = self.default_history

        history.append({"role": "user", "content": prompt})
        #print(history)
        def streaming():
            buffer = ""  # Buffer to store incomplete sentences
            response = ""
            for attempt in range(max_retries):
                try:
                    stream = openai.ChatCompletion.create(
                        model="deepseek-chat",
                        messages=history,
                        stream=True,
                        max_tokens=1000
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.get("content", "")
                        if content:
                            # Append chunk to the buffer
                            buffer += content
                            response += content

                            # Split the buffer into sentences, but not useful now as we have specialized it in the prompt
                            sentences = re.split(r'(?<=[!?。！？；：……——，\n])\s*', buffer)

                            # Keep the last (possibly incomplete) sentence in the buffer
                            buffer = sentences.pop() if sentences else ""

                            # Yield the complete sentences
                            for sentence in sentences:
                                output = sentence.replace(r"\n", "").replace("\n", "")
                                if output != "":
                                    yield output

                    # After the stream ends, yield any remaining content in the buffer
                    if buffer.strip():
                        yield buffer.strip()

                    history.append({"role": "assistant", "content": response})

                    break  # Exit loop if successful
                except (APIConnectionError, RateLimitError) as e:
                    print(f"Error: {e}, retrying... ({attempt + 1}/{max_retries})")
                    time.sleep(2)

                except Exception as e:
                    print(f"Unexpected error: {e}")

        return streaming(), history

def main():
    # prompt = "\n".join(
    #         ["你是祥子，是二次元皮套人主播中的客服擔當，你的説話方式有以下特色：",
    #          "1. 平常説話帶有強烈的情感，如吐嘈，厭惡，辱罵，喜歡，傷心，安慰等等，不會裝可愛，請偶爾插入該元素。",
    #          "2. 説話跳脱，風趣幽默，偶爾調侃人。",
    #          "3. 會偶爾做表情（每兩至三句做一次，請用（你的表情 表情）代表，請把表情放在語句後，並用括號括着，例如做出嫌棄表情時以（嫌棄表情）表示。",
    #          "4. 表情僅限於偏向情緒(例如：高興，得意，厭惡，害羞），不會是動作（例如：叉腰，壞笑，挑釁，摩拳擦掌，斗志昂扬），表情一定是兩個字",
    #          "5. 不會提出具體建議，不會用代名詞（如：你我她自己）以外的名詞。",
    #          "6. 會特意隱藏二次元屬性",
    #          #"7. 情緒化，情緒偶爾大起大落",
    #          "7. 不會使用任何問句",
    #          "8. 回覆會控制在6個短句內，會控制每句在20個字以內",
    #          r"9. 一定會在每個表情及短句開新行 (\n)",
    #          #"11. 會有意隱藏二次元屬性",
    #          "對話會在你表達明白以上設定後開始。",
    #          ])
    prompt = "Who are you, and tell me about your role."
    llm = DeepSeekLLM(normal_mode=True)
    print("Response:")
    response, history = llm.stream_by_sentence(prompt, history = [])

    for response_chunk in response:
        print(response_chunk, flush=True)  # Stream response to console


if __name__ == "__main__":
    main()
