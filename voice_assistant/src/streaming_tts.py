import os
import queue
import re
import threading
from google.cloud import texttospeech
from pydub.playback import play
import time
import shutil
import io

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./TextToSpeech.json"

class StreamingTTS:
    def __init__(self, output_dir, language_code, voice_name, file_prefix="text"):
        self.client = texttospeech.TextToSpeechClient()
        self.output_dir = output_dir
        self.file_counter = 1
        self.file_prefix = file_prefix
        self.running = False
        
        # Empty and create output directory
        shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 语音参数配置
        self.voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        # 队列系统
        self.text_queue = queue.Queue()
        self.file_queue = queue.Queue()

    def split_sentences(self, text):
        """智能分句逻辑"""
        return re.split(r'(?<=[ .!?。！？]) +', text)
    
    def filter_punctuation(self, text):
        emoji_pattern = re.compile("[^\\u4e00-\\u9fa5^a-z^A-Z^0-9]")  # 匹配所有非中文字母、数字的字符
        cleaned_text = emoji_pattern.sub(r' ', text)
        return cleaned_text

    def _tts_worker(self):
        """TTS工作线程"""
        while self.running or not self.text_queue.empty():
            try:
                text_chunk = self.text_queue.get(timeout=1)
                if text_chunk is None:
                    break
                
                # 分句处理
                sentences = self.split_sentences(text_chunk)

                for sentence in sentences:
                    clean_sentence = self.filter_punctuation(sentence)

                    if not clean_sentence.strip():
                        continue
                    
                    # create audio
                    synthesis_input = texttospeech.SynthesisInput(text=clean_sentence)
                    response = self.client.synthesize_speech(
                        input=synthesis_input,
                        voice=self.voice,
                        audio_config=self.audio_config
                    )
                    
                    # Create .mp3 file
                    filename = f"{self.file_prefix}_{self.file_counter}.mp3"
                    self.file_counter += 1
                    
                    # 放入文件队列
                    self.file_queue.put((filename, response.audio_content))
                    
            except queue.Empty:
                continue

    def _file_writer(self):
        """文件写入线程"""
        while self.running or not self.file_queue.empty():
            try:
                filename, content = self.file_queue.get(timeout=1)
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(content)
                # print(f"生成文件: {filepath}")
                self.file_queue.task_done()
            except queue.Empty:
                continue

    def start_stream(self):
        """启动流式处理"""
        self.running = True
        # 启动工作线程
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.writer_thread = threading.Thread(target=self._file_writer)
        
        self.tts_thread.start()
        self.writer_thread.start()

    def add_text(self, text):
        """添加待处理文本"""
        self.text_queue.put(text)

    def stop_stream(self):
        """停止流式处理"""
        self.running = False
        self.text_queue.put(None)  # 结束信号
        
        # 等待线程结束
        self.tts_thread.join()
        self.writer_thread.join()
        
        # 清空剩余任务
        while not self.file_queue.empty():
            filename, content = self.file_queue.get()
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(content)
            # print(f"最后生成文件: {filepath}")

def main():
    test_sentences = [
        "在正文部分，","APA格式使用「括號引用」",
        "（parenthetical citation）","的方式來注明徵引資料。",
        "簡言之，","當你以引用、","概要或改寫的方式提及他人的觀點時，",
        "必須在其後括注資料來源。","至於括號內的內容，",
        "APA格式並不會因文獻資料的媒體形式不同而有所改變，","詳情可見後續說明。"
    ]
    
    tts = StreamingTTS(
        output_dir="test_output",
        language_code="cmn-CN",
        voice_name="cmn-CN-Chirp3-HD-Leda"
    )
    
    tts.start_stream()
    
    print("开始流式生成...")
    for sentence in test_sentences:
        print(f"发送文本: {sentence}")
        tts.add_text(sentence)
        time.sleep(1)  # 模拟实时输入间隔
    
    # 结束处理
    print("\n等待剩余任务完成...")
    tts.stop_stream()
    print("测试完成！")

if __name__ == "__main__":
    main()