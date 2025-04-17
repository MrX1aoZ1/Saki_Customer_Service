import openai
import time
#from openai.error import APIConnectionError, RateLimitError
import re

class DeepSeekLLM:
    def __init__(self):
        # Initialize the OpenAI API client
        openai.api_base = 'https://tbnx.plus7.plus/v1'
        openai.api_key = 'sk-rm1AGno4UW48eG2WBZtirTNC7fOhbSe2DzEdhQrTZGzC9vfD'
        self.system_prompt = "You are a helpful assistant"

    def stream_by_sentence(self, prompt, chinese=True, max_retries=3):
        """Stream a response from the model and yield sentences."""
        buffer = ""  # Buffer to store incomplete sentences
        for attempt in range(max_retries):
            try:
                # Call the OpenAI API with streaming enabled
                stream = openai.ChatCompletion.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    max_tokens=500
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.get("content", "")
                    if content:
                        # Append chunk to the buffer
                        buffer += content
                        # Split the buffer into sentences
                        if chinese:
                            sentences = re.split(r'(?<=[!?。！？；：……——，])\s*', buffer)
                        # Keep the last (possibly incomplete) sentence in the buffer
                        buffer = sentences.pop() if sentences else ""
                        # Yield the complete sentences
                        for sentence in sentences:
                            yield sentence
                # After the stream ends, yield any remaining content in the buffer
                if buffer.strip():
                    yield buffer.strip()
                break  # Exit loop if successful
            #except (APIConnectionError, RateLimitError) as e:
            #    print(f"Error: {e}, retrying... ({attempt + 1}/{max_retries})")
            #    time.sleep(2)
            except Exception as e:
                print(f"Unexpected error: {e}")

def main():
    prompt = "你好，你可以用一些很可爱的语言回复我吗，再加上一些表情符号什么的，请向我输出一段大约400字的回复"
    llm = DeepSeekLLM()
    print("Response:")
    try:
        for response_chunk in llm.stream_by_sentence(prompt, True):
            print(response_chunk, end="", flush=True)
    except Exception as e:
        print(f"Error in main(): {e}")

if __name__ == "__main__":
    main()
