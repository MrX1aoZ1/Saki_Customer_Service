import threading
import queue
import pyaudio
from whisper_asr import recognize_speech
from streaming_tts import StreamingTTS
from LLM_api import DeepSeekLLM


class VoiceAssistant:
    def start_voice_assistant(self):
        print("AI Voice Assistant started")
        print("==========================================")
    
        test_prompt = "你好，你可以用一些很可爱的语言回复我吗，语气可爱就可以，请向我输出一段大约200字的回复"
        addi_info = "你是一個語音小助手，生成文本的時候請模仿人類說話的語氣\n"

        llm = DeepSeekLLM()
        tts = StreamingTTS(
            output_dir="test_output",
            language_code="cmn-CN",
            voice_name="cmn-CN-Chirp3-HD-Leda"
        )


        prompt = recognize_speech()

        final_prompt = addi_info + prompt

        print("Processing audio...")
        print("==========================================")
        print("Response:")

        tts.start_stream()

        try:
            for response_chunk in llm.stream_by_sentence(final_prompt, True):
                print(response_chunk, end="", flush=True)
                tts.add_text(response_chunk)
        except Exception as e:
            print(f"Error in main(): {e}")

        tts.stop_stream()
        
        print()
        print("==========================================")
        print("AI Voice Assistant finished")

def main():
    voice_assistant = VoiceAssistant()
    voice_assistant.start_voice_assistant()

if __name__ == "__main__":
    main()