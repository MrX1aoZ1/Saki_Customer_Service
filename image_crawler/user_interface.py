import asyncio
import platform
import pygame
import threading
import streaming_asr
from LLM_api import DeepSeekLLM
from streaming_tts import StreamingTTS
from database import ImageDB
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
import time

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
PROCESSING_GRAY = (128, 128, 128)
SAKI_COLOR = (119,153,204)
FONT_SIZE = 20
LINE_HEIGHT = 25
SCROLLBAR_WIDTH = 20
MIN_WINDOW_W = 700
MIN_WINDOW_H = 400
#IMAGE_PLACEHOLDER = "D:\\WallPaper\\GnK7KI5bYAASXR3.jpg"         

# True: Normal Mode, False: Saki Mode; To switch between different mode
NORMAL_MODE = True #############################################################################################

class ChatUI:
    def __init__(self): 
        self.normal_mode = NORMAL_MODE

        self.executor = ThreadPoolExecutor(max_workers=4)

        self.llm = DeepSeekLLM(self.normal_mode)
        self.imDB = ImageDB()
        self.tts = StreamingTTS(self.normal_mode)
        self.chat_history = []  
        self.audio_files = []  
        
        self.scroll_offset = 0          # Current scrollbar position
        self.max_scroll = 0     
        self.is_recording = False   
        self.stop_event = None          # Event to stop Recording 
        self.recording_thread = None
        self.current_interim = ""
        self.button_can_use = True

        # Initialize the user interface
        pygame.init()
        self.window_size = (850, 600)
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        pygame.display.set_caption("Smart Voice Assistant")
        self.font = pygame.font.SysFont('Microsoft YaHei', FONT_SIZE, bold=True)
        
        # Define area for char_area, control_panel and record_btn
        self.record_btn = pygame.Rect(self.window_size[0] - 200, 20, 180, 40)
        self.control_panel = pygame.Rect(self.window_size[0] - 220, 0, 220, self.window_size[1])
        self.chat_area = pygame.Rect(0, 0, self.window_size[0] - self.control_panel.width, self.window_size[1])

        self.btn_text = self.font.render("Start Recording", True, BLACK)
        self.record_btn_color = GREEN

        self.running = True
        self.llm_history = []
    
    def wrap_text(self, text, max_width):
        """Automatic line wrapping"""
        lines = []
        words = text.split(' ')
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if self.font.size(test_line)[0] > max_width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
            else:
                current_line.append(word)
        if current_line:
            lines.append(' '.join(current_line))
        return lines
    
    def update_display(self):
        """Update the user interface display"""
        self.screen.fill(WHITE)
        self.record_btn = pygame.Rect(self.window_size[0] - 200, 20, 180, 40)
        self.control_panel = pygame.Rect(self.window_size[0] - 220, 0, 220, self.window_size[1])
        self.chat_area = pygame.Rect(0, 0, self.window_size[0] - self.control_panel.width, self.window_size[1])

        # Measure the height of the chat history
        total_height = 0
        y_pos = self.chat_area.top - self.scroll_offset

        for entry in self.chat_history:
            if (entry['type'] == 'user') or entry['type'] == 'assistant':
                if entry['type'] == 'user':
                    text = f"User: {entry['content']}"
                    color = BLACK
                elif entry['type'] == 'assistant':
                    text = f"Assistant: {entry['content']}"
                    color = SAKI_COLOR
                lines = self.wrap_text(text, self.chat_area.width - SCROLLBAR_WIDTH - 40)

                total_height += len(lines) * LINE_HEIGHT
                for line in lines:
                    line_surf = self.font.render(line, True, color)
                    self.screen.blit(line_surf, (20, y_pos))
                    y_pos += LINE_HEIGHT

            if entry['type'] == 'image' and not self.normal_mode:
                img_surf = pygame.image.load(entry["content"]).convert()
                img_surf = pygame.transform.scale(img_surf, (self.chat_area.width // 2, int(self.chat_area.width // 2 * 9 / 16)))
                self.screen.blit(img_surf, (50, y_pos))
                y_pos += img_surf.get_height() + LINE_HEIGHT

                img_height = int((self.chat_area.width // 2) * 9 / 16)
                total_height += img_height + LINE_HEIGHT

        # Render the interim part if it is recording
        if self.is_recording and self.current_interim:
            interim_text = f"Interim: {self.current_interim}"
            lines = self.wrap_text(interim_text, self.chat_area.width - SCROLLBAR_WIDTH - 40)

            total_height += len(lines) * LINE_HEIGHT
            for line in lines:
                line_surf = self.font.render(line, True, (100, 100, 100))
                self.screen.blit(line_surf, (20, y_pos))
                y_pos += LINE_HEIGHT
        
        self.max_scroll = max(total_height - self.chat_area.height + 200, 0)
        
        # Render the Controll Panel (Gray area) 
        btn_text = self.btn_text
        pygame.draw.rect(self.screen, GRAY, self.control_panel)
        pygame.draw.rect(self.screen, self.record_btn_color, self.record_btn)
        self.screen.blit(btn_text, (self.record_btn.x + 10, self.record_btn.y + 10))
        
        pygame.display.flip()
    
    async def run(self):
        """Main loop"""
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.VIDEORESIZE:
                    self.window_size = (event.w, event.h)
                    if (event.w < MIN_WINDOW_W):
                        self.window_size = (MIN_WINDOW_W, event.h)
                    if (event.h < MIN_WINDOW_H):
                        self.window_size = (event.w, MIN_WINDOW_H)
                    self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
                    # Update the Control Panel and Chat Area
                    self.control_panel = pygame.Rect(0, 0, self.window_size[0], 100)
                    self.chat_area = pygame.Rect(0, self.control_panel.height,self.window_size[0],self.window_size[1] - self.control_panel.height)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.record_btn.collidepoint(event.pos) and self.button_can_use:
                        self.handle_recording()
                elif event.type == pygame.MOUSEWHEEL:
                    self.scroll_offset -= event.y * 20
                    self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))
            
            self.update_display()
            await asyncio.sleep(0.01)
            clock.tick(60)
    
    def handle_recording(self):
        """Start and Stop audio recording"""
        self.executor.submit(self._real_recording)

    def _real_recording(self):
        if not self.is_recording:
            # Start Recording
            self.btn_text = self.font.render("Stop Recording", True, WHITE)
            self.record_btn_color = RED
            print("====Start Recording====")
            print("[User: ]")
            shutil.rmtree("test_output", ignore_errors=True)
            os.makedirs("test_output", exist_ok=True)
            self.stop_event = threading.Event()
            self.recording_thread = threading.Thread(
                target=streaming_asr.recognize_speech,
                args=(self.stop_event, self.normal_mode, self.handle_interim)
            )
            self.recording_thread.start()
            self.is_recording = True
        else:
            # Stop Recording
            self.btn_text = self.font.render("  Processing...", True, WHITE)
            self.record_btn_color = PROCESSING_GRAY
            print("====Stop Recording====")
            self.stop_event.set()
            self.button_can_use = False 
            self.recording_thread.join()
            self.is_recording = False
            self.scroll_offset = self.max_scroll

            # Parse the recorded audio into LLM for processing
            user_inputs = [e['content'] for e in self.chat_history if e['type'] == 'user']

            latest_input = user_inputs[-1]
            print("====LLM Processing====")

            response, self.llm_history = self.llm.stream_by_sentence(latest_input, history=self.llm_history)

            self.tts.start_stream()
            print("[Voice Assistant: ]")
            for chunk in response:
                print(chunk)
                if (chunk[0] != "（") and (chunk[-3:] != "表情）"):
                    self.tts.add_text(chunk)
                    self.chat_history.append({'type': 'assistant', 'content': chunk})
                    time.sleep(1)
                    self.scroll_offset = self.max_scroll
                if not NORMAL_MODE:
                    output = self.imDB.find_matches(chunk)
                    self.chat_history.append({'type': 'image', 'content': output[0][0]})
                    self.scroll_offset = self.max_scroll
            self.tts.stop_stream()

            print("====Finished Output====")
            self.button_can_use = True
            self.record_btn_color = GREEN
            self.btn_text = self.font.render("Start Recording", True, WHITE)
        
    
    def handle_interim(self, text, is_final):
        """Interim handling"""
        if is_final:
            self.chat_history.append({'type': 'user', 'content': text})
            self.scroll_offset = self.max_scroll
            self.current_interim = ""
        else:
            self.current_interim = text
            self.scroll_offset = self.max_scroll
    

if platform.system() == "Emscripten":
    ui = ChatUI()
    asyncio.ensure_future(ui.run()) 
else:
    if __name__ == "__main__":
        ui = ChatUI()
        asyncio.run(ui.run())

# Empty the audio file directory
shutil.rmtree("test_output", ignore_errors=True)
os.makedirs("test_output", exist_ok=True)
