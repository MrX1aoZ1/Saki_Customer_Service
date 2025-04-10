import requests
import json
from openai import OpenAI
from voice_assistant import VoiceAssistant

if __name__ == "__main__":
    VoiceAssistant().run()

class LLM:
    def __init__(self, api_key):
        self.client = OpenAI(
            base_url='https://tbnx.plus7.plus/v1',
            api_key='sk-rm1AGno4UW48eG2WBZtirTNC7fOhbSe2DzEdhQrTZGzC9vfD'
        )
        self.system_prompt = "You are a helpful assistant"

    def completion(self, prompt, history=[], model="deepseek-chat"):  
        if len(history)< 1:
            history = [{"role": "system", "content": self.system_prompt}]

        history.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model = model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello"},
            ],
            stream=False
        )

        output = response.choices[0].message.content

        history.append({"role": "assistant", "content": output})

        print(response.choices[0].message.content)

        return output, history

# Example Usage
#example_prompt = "You are a helpful AI assistant. How can I help a student understand Newton's laws of motion?"
#response, history = deepseek_api_request(example_prompt)
#print(response)