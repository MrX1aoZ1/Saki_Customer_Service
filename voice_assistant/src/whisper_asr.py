#Streaming ASR

import queue
import re
import sys
import time
import threading

from google.cloud import speech
import pyaudio

# Audio recording parameters
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms
OUTPUT_FILE = "audio.wav"
TRANSCRIPT_FILE = "transcript.txt"


class MicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self: object, rate: int = RATE, chunk: int = CHUNK) -> None:
        """The audio -- and generator -- is guaranteed to be on the main thread."""
        self._rate = rate
        self._chunk = chunk
        self.audio_frames = []

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self: object) -> object:
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            channels=1,
            rate=self._rate,
            input=True,
            frames_per_buffer=self._chunk,
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(
        self: object,
        type: object,
        value: object,
        traceback: object,
    ) -> None:
        """Closes the stream, regardless of whether the connection was lost or not."""
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(
        self: object,
        in_data: object,
        frame_count: int,
        time_info: object,
        status_flags: object,
    ) -> object:
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        self.audio_frames.append(in_data)
        return None, pyaudio.paContinue

    def generator(self: object) -> object:
        """Generates audio chunks from the stream of audio data in chunks."""
        while not self.closed:
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Consume other buffered data
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b"".join(data)


def listen_print_loop(responses: object, stream: MicrophoneStream, callback: callable, exit_event: threading.Event) -> str:
    """Iterates through server responses and prints them."""
    with open(TRANSCRIPT_FILE, "a", encoding="utf-8") as f_txt:

        # 写入WAV文件头（需新增wave库）
        import wave
        with wave.open(OUTPUT_FILE, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(RATE)


        num_chars_printed = 0
        for response in responses:
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
            else:
                print(transcript + overwrite_chars)
                callback(transcript)
                # Exit recognition if "exit" or "quit" is spoken
                if re.search(r"\b(exit|quit)\b", transcript, re.I):
                    print("Exiting...")
                    
                    break

                num_chars_printed = 0

        return transcript


def main() -> None:
    """Transcribe speech from microphone input."""
    language_code = "en-US"  # BCP-47 language tag

    client = speech.SpeechClient()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True,
    )

    open(TRANSCRIPT_FILE, "w").close()

    with MicrophoneStream(RATE, CHUNK) as stream:
        audio_generator = stream.generator()
        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )

        responses = client.streaming_recognize(streaming_config, requests)

        # Process the transcription responses
        listen_print_loop(responses, stream)


if __name__ == "__main__":
    main()