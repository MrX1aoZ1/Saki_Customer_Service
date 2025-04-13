import threading
import queue
import time

# 1. LLM Generation Thread (Producer)
def llm_generate_stream(prompt, output_queue):
    for sentence in ["Hello!", "How are you?", "This is a streaming example."]:
        time.sleep(0.5)  # Simulate LLM generation delay
        output_queue.put(sentence)  # Send sentence to TTS queue
    output_queue.put(None)  # Signal end of generation

# 2. TTS Processing Thread (Consumer/Producer)
def tts_processor(input_queue, audio_queue):
    while True:
        sentence = input_queue.get()
        if sentence is None:  # End signal
            audio_queue.put(None)
            break
        audio_chunk = tts_service.convert_text_to_audio(sentence)  # Simulate TTS
        audio_queue.put(audio_chunk)

# 3. Audio Playback Thread (Consumer)
def audio_player(audio_queue):
    while True:
        audio_chunk = audio_queue.get()
        if audio_chunk is None:  # End signal
            break
        audio_player.play(audio_chunk)  # Play audio immediately

# 4. Full Workflow with Concurrency
prompt = "Start the conversation."

# Create queues for inter-thread communication
llm_to_tts_queue = queue.Queue()
tts_to_audio_queue = queue.Queue()

# Start threads
llm_thread = threading.Thread(target=llm_generate_stream, args=(prompt, llm_to_tts_queue))
tts_thread = threading.Thread(target=tts_processor, args=(llm_to_tts_queue, tts_to_audio_queue))
audio_thread = threading.Thread(target=audio_player, args=(tts_to_audio_queue,))

llm_thread.start()
tts_thread.start()
audio_thread.start()

# Wait for all threads to finish
llm_thread.join()
tts_thread.join()
audio_thread.join()