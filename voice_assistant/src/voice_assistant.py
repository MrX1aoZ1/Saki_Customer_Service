# voice_assistant.py
import threading
import queue
from typing import Optional
from whisper_asr import MicrophoneStream, listen_print_loop
from deepseek_api import DeepSeekLLM
from streaming_tts import tts_processor, audio_player_thread

class VoiceAssistant:
    def __init__(self):
        # 初始化组件
        self.llm = DeepSeekLLM()  # 大语言模型
        self.asr_to_llm = queue.Queue()  # ASR → LLM 的指令队列
        self.llm_to_tts = queue.Queue()  # LLM → TTS 的回复队列
        self.audio_queue = queue.Queue()  # TTS → 扬声器的音频队列
        self.exit_event = threading.Event()  # 系统退出信号

    def llm_thread(self):
        """LLM 处理线程：监听用户输入，生成回复"""
        while not self.exit_event.is_set():
            # 从语音识别获取用户输入
            user_input: Optional[str] = self.asr_to_llm.get()
            
            if user_input is None:  # 收到退出信号
                self.exit_event.set()
                break
            
            # 流式生成回复
            try:
                for chunk in self.llm.stream_response(user_input):
                    self.llm_to_tts.put(chunk)  # 发送文本到TTS
                self.llm_to_tts.put(None)  # 标记本轮回复结束
            except Exception as e:
                print(f"LLM处理失败: {str(e)}")

    def run(self):
        """主控制流程"""
        # 启动LLM线程
        llm_worker = threading.Thread(target=self.llm_thread)
        llm_worker.start()

        # 启动TTS处理线程
        tts_worker = threading.Thread(
            target=tts_processor, 
            args=(self.llm_to_tts, self.audio_queue)
        )
        tts_worker.start()

        # 启动音频播放线程
        audio_worker = threading.Thread(
            target=audio_player_thread, 
            args=(self.audio_queue,)
        )
        audio_worker.start()

        # 启动语音识别主循环
        with MicrophoneStream() as stream:
            listen_print_loop(
                responses=...,  # 需从whisper_asr.py获取实际响应
                stream=stream,
                callback=lambda text: self.asr_to_llm.put(text),  # 将识别结果传入队列
                exit_event=self.exit_event
            )

        # 等待所有线程结束
        llm_worker.join()
        tts_worker.join()
        audio_worker.join()

if __name__ == "__main__":
    assistant = VoiceAssistant()
    assistant.run()