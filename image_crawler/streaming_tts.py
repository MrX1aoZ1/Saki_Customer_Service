import os
import queue
import re
import threading
from google.cloud import texttospeech
import time
import shutil
from pydub import AudioSegment
from playaudio import playaudio

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./TextToSpeech.json"

class StreamingTTS:
    def __init__(self, normal_mode):
        """Initialize the streaming TTS class."""
        self.client = texttospeech.TextToSpeechClient()
        self.output_dir = "test_output"
        self.file_counter = 1
        self.file_prefix = "text"
        self.running = False

        """Emptying the output directory"""
        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        if normal_mode:     # True = Normal Mode
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Chirp-HD-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )
        else:               # False = Saki Mode
            self.voice = texttospeech.VoiceSelectionParams(
                language_code="cmn-CN",
                name="cmn-CN-Chirp3-HD-Leda",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
            )


        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        """Initialize the queue"""
        self.text_queue = queue.Queue()          # 存儲待處理文本
        self.file_queue = queue.Queue()          # 存儲文件名和音頻內容
        self.mp3_filename_queue = queue.Queue()  # 存儲生成的MP3文件名

    def split_sentences(self, text):
        """Split the sentence with punctuation"""
        return re.split(r'(?<=[ .,!?。！，？]) +', text)
    
    def filter_punctuation(self, text):
        """Skip the words that is not Chinese, English, number"""
        emoji_pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9+=/\-\']',  flags=re.UNICODE)
        cleaned_text = emoji_pattern.sub(r' ', text)
        return cleaned_text

    def _tts_worker(self):
        """TTS Workflow"""
        shutil.rmtree(self.output_dir, ignore_errors=True)
        os.makedirs(self.output_dir, exist_ok=True)
        self.file_counter = 1

        while self.running or not self.text_queue.empty():
            try:
                text_chunk = self.text_queue.get(timeout=1)
                if text_chunk is None:
                    break
                
                sentences = self.split_sentences(text_chunk)

                for sentence in sentences:
                    clean_sentence = self.filter_punctuation(sentence)

                    if not clean_sentence.strip():
                        continue
                    
                    # Process TTS
                    synthesis_input = texttospeech.SynthesisInput(text=clean_sentence)
                    response = self.client.synthesize_speech(
                        input=synthesis_input,
                        voice=self.voice,
                        audio_config=self.audio_config
                    )
                    
                    # Create the file
                    filename = f"{self.file_prefix}_{self.file_counter}.mp3"
                    self.file_counter += 1
                    
                    # Queuing
                    self.file_queue.put((filename, response.audio_content))
                    
            except queue.Empty:
                continue

    def _file_writer(self):
        """文件寫入線程：將音頻內容寫入MP3文件並記錄文件名"""
        while self.running or not self.file_queue.empty():
            try:
                filename, content = self.file_queue.get(timeout=1)
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(content)
                self.file_queue.task_done()
                self.mp3_filename_queue.put(filepath)  # 將完整路徑加入隊列
            except queue.Empty:
                continue

    def _audio_player(self):
        """音頻播放線程：持續監控並播放隊列中的音頻"""
        while self.running or not self.mp3_filename_queue.empty():

            try:
                filepath = self.mp3_filename_queue.get(timeout=1)
                #print(filepath)
                filepath = filepath.replace("\\", "/")
                #print(filepath)
                while True:
                    time.sleep(0.1)
                    if os.path.isfile(filepath):
                        #print ("yes")
                        break
                #audio = AudioSegment.from_mp3(filepath) # Stucked here
                playaudio(filepath)#audio)
                #print("test2")
                self.mp3_filename_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"播放錯誤: {str(e)}")

    def start_stream(self):
        """啟動流式處理，開啟所有工作線程"""
        self.running = True
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.writer_thread = threading.Thread(target=self._file_writer)
        self.player_thread = threading.Thread(target=self._audio_player)
        self.tts_thread.start()
        self.writer_thread.start()
        self.player_thread.start()

    def add_text(self, text):
        """添加待處理的文本到隊列"""
        self.text_queue.put(text)

    def stop_stream(self):
        """停止流式處理，清理剩餘任務"""
        self.running = False
        
        # 等待所有線程結束
        self.tts_thread.join()
        self.writer_thread.join()
        self.player_thread.join()

        # 處理剩餘文件
        while not self.file_queue.empty():
            filename, content = self.file_queue.get()
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(content)
            self.mp3_filename_queue.put(filepath)

        # 處理剩餘播放任務
        while not self.mp3_filename_queue.empty():
            filepath = self.mp3_filename_queue.get()
            #audio = AudioSegment.from_mp3(filepath)
            playaudio(filepath)#audio)

def main():
    # For testing
    test_sentences = [
        "在正文部分，APA格式使用「括號引用」",
        "（parenthetical citation）的方式來注明徵引資料。",
        "簡言之，當你以引用、概要或改寫的方式提及他人的觀點時，",
        "必須在其後括注資料來源。", "至於括號內的內容，",
        "APA格式並不會因文獻資料的媒體形式不同而有所改變，", "詳情可見後續說明。"
    ]
    
    tts = StreamingTTS(normal_mode=False)
    
    tts.start_stream()

    print("Start Streaming...")

    for sentence in test_sentences:
        tts.add_text(sentence)
        time.sleep(0.3)  # 模擬實時輸入
    
    print("\nWait for audio generation...")

    tts.stop_stream()

    print("\nFinished Test！")

if __name__ == "__main__":
    main()

