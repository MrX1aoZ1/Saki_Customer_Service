import os
import queue
import re
import threading
from google.cloud import texttospeech
import time
import shutil
from playaudio import playaudio

# Credensial of Google Cloud API Text-To-Speech
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
        self.text_queue = queue.Queue()          # Queue for text chunk from LLM
        self.mp3_filename_queue = queue.Queue()  # Queue for playing MP3 files

    def split_sentences(self, text):
        """Split the sentence with punctuation"""
        return re.split(r'(?<=[。！？!?\.\,])[ \n]+(?=[^\s])', text)
    
    def filter_punctuation(self, text):
        """Skip the symbols that is not Chinese, English, number"""
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
                text_chunk = self.text_queue.get(timeout=1)        # Get text from the text_queue
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
                    filepath = os.path.join(self.output_dir, filename)
                    with open(filepath, "wb") as f:
                        f.write(response.audio_content)

                    # Push the saved MP3 files into the audio-to-be-play queue
                    self.mp3_filename_queue.put(filepath)  

            except queue.Empty:
                continue

    def _audio_player(self): 
        """Audio playing thread: Continuously checking the queue for audio to play"""    
        while self.running or not self.mp3_filename_queue.empty():

            try:
                filepath = self.mp3_filename_queue.get(timeout=1)

                while True:
                    time.sleep(0.1)
                    if os.path.isfile(filepath):
                        break

                playaudio(filepath)
                self.mp3_filename_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Play error: {str(e)}")

    def start_stream(self):  
        self.running = True             
        self.tts_thread = threading.Thread(target=self._tts_worker)
        self.player_thread = threading.Thread(target=self._audio_player)
        self.tts_thread.start()
        self.player_thread.start()

    def add_text(self, text):
        """Push the text to the text queue"""
        self.text_queue.put(text)

    def stop_stream(self):
        self.running = False
        
        # Wait for every thread to finish
        self.tts_thread.join()
        self.player_thread.join()


def main():
    """A random paragraph copied from the internet for testing"""
    test_sentences = [
        "在正文部分，APA格式使用「括號引用」",
        "（parenthetical citation）的方式來注明徵引資料。",
        "簡言之，當你以引用、概要或改寫的方式提及他人的觀點時，",
        "必須在其後括注資料來源。", "至於括號內的內容，",
        "APA格式並不會因文獻資料的媒體形式不同而有所改變，", "詳情可見後續說明。"
    ]

    # Another paragraph for testing
    # test_sentences = [
    #     "The sun dipped below the horizon, casting hues of amber and violet across the sky as a gentle breeze rustled the leaves of the ancient oak tree. Nearby, a squirrel scampered up its trunk, pausing to nibble on an acorn before darting into the shadows. In the distance, the faint hum of cicadas blended with the rhythmic chirping of crickets, creating a symphony of twilight sounds. A lone kayak drifted lazily down the river, its occupant lost in thought, trailing fingertips in the cool water. Along the bank, wildflowers swayed—daisies, goldenrod, and purple asters—painting the meadow in bursts of color. Suddenly, a heron took flight, its wings slicing through the air with graceful precision, vanishing into the mist that began to rise from the water’s surface. The aroma of pine and damp earth lingered, a reminder of the afternoon’s brief rain shower. Somewhere in the woods, an owl hooted, signaling the shift from day to night. Stars emerged one by one, flickering like distant lanterns, while the moon ascended, casting a silvery glow over the landscape. A fox trotted cautiously through the underbrush, its eyes gleaming in the dim light, searching for prey. The world seemed to hold its breath, suspended in the quiet magic of dusk. Yet, even as darkness settled, life thrived—unseen creatures stirring, nocturnal blooms unfurling, and the wind carrying whispers of stories untold. It was a moment both fleeting and eternal, a snapshot of nature’s quiet resilience. Meanwhile, in a cottage nestled at the forest’s edge, a light flickered in the window, smoke curling from the chimney as someone inside hummed an old folk tune, oblivious to the owl’s watchful gaze or the fox’s stealthy hunt. Time moved differently here, unbound by clocks or calendars, governed only by the rhythms of the earth."
    # ]
    
    tts = StreamingTTS(normal_mode=False)
    
    tts.start_stream()

    print("Start Streaming...")

    for sentence in test_sentences:
        tts.add_text(sentence)
        time.sleep(0.3)         
    
    print("\nWait for audio generation...")

    tts.stop_stream()

    print("\nFinished Test！")

if __name__ == "__main__":
    main()

