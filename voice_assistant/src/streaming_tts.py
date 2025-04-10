#Streaming TTS

import threading
import queue
import time
from deepseek_api import DeepSeekLLM

# Simulated TTS service and audio player
class TTSService:
    """Simulates a Text-to-Speech (TTS) service that converts text to audio."""
    @staticmethod
    def convert_text_to_audio(text):
        time.sleep(0.3)  # Simulate processing delay
        return f"AudioChunk({text})"  # Simulated audio chunk

class AudioPlayer:
    """Simulates an audio player that plays audio chunks."""
    @staticmethod
    def play(audio_chunk):
        print(f"Playing: {audio_chunk}")
        time.sleep(0.2)  # Simulate playback duration

# Instantiate the TTS service and audio player
tts_service = TTSService()
audio_player = AudioPlayer()

# 1. LLM Generation Thread (Producer)
# def llm_generate_stream(prompt, output_queue):
#     """Simulates streaming text generation from an LLM."""
#     for sentence in ["Hello!", "How are you?", "This is a streaming example."]:
#         time.sleep(0.5)  # Simulate LLM generation delay
#         print(f"LLM generated: {sentence}")
#         output_queue.put(sentence)  # Send sentence to TTS queue
#     output_queue.put(None)  # Signal end of generation
def llm_generate_stream(prompt, output_queue):
    """集成DeepSeek的真实流式生成"""
    llm = DeepSeekLLM()
    buffer = ""
    for chunk in llm.stream_response(prompt):
        buffer += chunk
        if '.' in chunk or '?' in chunk:  # 简单分句逻辑
            output_queue.put(buffer.strip())
            buffer = ""

# 2. TTS Processing Thread (Consumer/Producer)
def tts_processor(input_queue, audio_queue):
    """Processes text into audio chunks using TTS and sends them to the audio queue."""
    while True:
        sentence = input_queue.get()  # Get text from LLM queue
        if sentence is None:  # End signal
            audio_queue.put(None)  # Signal end of audio processing
            break
        print(f"TTS processing: {sentence}")
        audio_chunk = tts_service.convert_text_to_audio(sentence)  # Convert text to audio
        audio_queue.put(audio_chunk)  # Send audio chunk to audio queue

# 3. Audio Playback Thread (Consumer)
def audio_player_thread(audio_queue):
    """Plays audio chunks from the audio queue."""
    while True:
        audio_chunk = audio_queue.get()  # Get audio chunk
        if audio_chunk is None:  # End signal
            print("Audio playback finished.")
            break
        print(f"Audio playback: {audio_chunk}")
        audio_player.play(audio_chunk)  # Play audio immediately

# 4. Full Workflow with Concurrency
def main():
    """Coordinates the full workflow using threads."""
    prompt = "Start the conversation."

    # Create queues for inter-thread communication
    llm_to_tts_queue = queue.Queue()
    tts_to_audio_queue = queue.Queue()

    # Start threads
    llm_thread = threading.Thread(target=llm_generate_stream, args=(prompt, llm_to_tts_queue))
    tts_thread = threading.Thread(target=tts_processor, args=(llm_to_tts_queue, tts_to_audio_queue))
    audio_thread = threading.Thread(target=audio_player_thread, args=(tts_to_audio_queue,))

    llm_thread.start()
    tts_thread.start()
    audio_thread.start()

    # Wait for all threads to finish
    llm_thread.join()
    tts_thread.join()
    audio_thread.join()

    print("All threads have finished execution.")

# Run the main workflow
if __name__ == "__main__":
    main()