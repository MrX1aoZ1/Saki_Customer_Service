import os
from openai import OpenAI, APIConnectionError, RateLimitError
import time

class DeepSeekLLM:
    def __init__(self):
        self.client = OpenAI(
            base_url='https://tbnx.plus7.plus/v1',
            api_key='sk-rm1AGno4UW48eG2WBZtirTNC7fOhbSe2DzEdhQrTZGzC9vfD'
        )
        self.system_prompt = "You are a helpful assistant"
    
    def stream_response(self, prompt, max_retries=3):
        """流式生成回复"""
        for _ in range(max_retries):
            try:
                stream = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    max_tokens=100  # 控制每次返回长度
                )
                for chunk in stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
                break
            except (APIConnectionError, RateLimitError) as e:
                print(f"Error: {e}, retrying... ({_+1}/{max_retries})")
                time.sleep(2)

