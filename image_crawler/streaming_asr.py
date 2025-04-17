import os
import queue
import re
import sys
import time
import threading
from google.cloud import speech
import pyaudio

# 设置Google Cloud Speech API的凭证文件路径
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./SpeechToText.json"

# 音频采样率和分块大小
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

class MicrophoneStream:
    def __init__(self, normal_mode):
        self._rate = RATE
        self._chunk = CHUNK
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break
            yield b''.join(data)

def listen_print_loop(responses, stream, stop_event, ui_callback=None):
    final_scripts = []
    num_chars_printed = 0

    responses_queue = queue.Queue()
    def queue_responses():
        try:
            for response in responses:
                responses_queue.put(response)
        except Exception as e:
            print(f"Error in queue_responses: {e}")
        finally:
            responses_queue.put(None)

    thread = threading.Thread(target=queue_responses)
    thread.start()

    while True:
        if stop_event.is_set() and not stream.closed:
            stream.closed = True
            return ' '.join(final_scripts)

        try:
            response = responses_queue.get(timeout=0.1)
            if response is None:
                break
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue

            transcript = result.alternatives[0].transcript
            overwrite_chars = " " * (num_chars_printed - len(transcript))

            if not result.is_final:
                sys.stdout.write(transcript + overwrite_chars + "\r")
                sys.stdout.flush()
                num_chars_printed = len(transcript)
                if ui_callback:
                    ui_callback(transcript, False)
            else:
                final_scripts.append(transcript)
                # print(transcript + overwrite_chars)
                num_chars_printed = 0
                if ui_callback:
                    ui_callback(transcript, True)
        except queue.Empty:
            continue

    return ' '.join(final_scripts)

def recognize_speech(stop_event, normal_mode, ui_callback=None):
    client = speech.SpeechClient()

    if normal_mode:         # Normal Mode    
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code="en-US",
        )
    else:                   # Saki Mode
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code="cmn-CN",
        )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    with MicrophoneStream(normal_mode) as stream:
        audio_generator = stream.generator()
        requests = (speech.StreamingRecognizeRequest(audio_content=content) for content in audio_generator)
        responses = client.streaming_recognize(streaming_config, requests)
        transcript = listen_print_loop(responses, stream, stop_event, ui_callback)

    print("User: "+ transcript)

    return transcript

def main():
    print("Starting AI voice assistant")
    stop_event = threading.Event()
    transcription = recognize_speech(stop_event)

if __name__ == "__main__":
    main()