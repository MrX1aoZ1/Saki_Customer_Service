import asyncio
import platform
import pygame
import threading
import queue
import streaming_asr
from LLM_api_v2 import DeepSeekLLM
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
#IMAGE_PLACEHOLDER = "D:\\WallPaper\\GnK7KI5bYAASXR3.jpg"         

# True: Normal Mode, False: Saki Mode
NORMAL_MODE = False #############################################################################################


class ChatUI:
    def __init__(self): 
        self.normal_mode = NORMAL_MODE

        self.executor = ThreadPoolExecutor(max_workers=4)

        self.llm = DeepSeekLLM(self.normal_mode)
        self.imDB = ImageDB()
        self.tts = StreamingTTS(self.normal_mode)
        self.chat_history = []  
        self.audio_files = []  
        
        # UI状态变量
        self.scroll_offset = 0  
        self.max_scroll = 0     
        self.is_recording = False  # 录音状态
        self.stop_event = None    # 停止录音事件
        self.recording_thread = None  # 录音线程
        self.current_interim = ""  # 当前临时转录文本
        self.button_can_use = True

        # 初始化Pygame窗口
        pygame.init()
        self.window_size = (850, 600)
        self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
        pygame.display.set_caption("智能语音助手")
        self.font = pygame.font.SysFont('Microsoft YaHei', FONT_SIZE, bold=True)
        
        # 定义界面组件区域
        self.record_btn = pygame.Rect(self.window_size[0] - 200, 20, 180, 40)
        self.control_panel = pygame.Rect(self.window_size[0] - 220, 0, 220, self.window_size[1])
        self.chat_area = pygame.Rect(0, 0, self.window_size[0] - self.control_panel.width, self.window_size[1])

        self.btn_text = self.font.render("Start Recording", True, BLACK)
        self.record_btn_color = GREEN

        self.running = True
        self.llm_history = []


    def draw_scrollbar(self):
        """绘制可拖动的滚动条"""
        if self.max_scroll > 0:
            visible_ratio = self.chat_area.height / (self.chat_area.height + self.max_scroll)
            bar_height = max(20, int(self.chat_area.height * visible_ratio))
            bar_y = self.chat_area.top + int((self.scroll_offset / self.max_scroll) * (self.chat_area.height - bar_height))
            pygame.draw.rect(self.screen, GRAY, (
                self.window_size[0] - SCROLLBAR_WIDTH,
                bar_y,
                SCROLLBAR_WIDTH,
                bar_height
            ))
    
    def wrap_text(self, text, max_width):
        """将文本按最大宽度换行"""
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
        """更新界面显示，包括对话历史和临时转录"""
        self.screen.fill(WHITE)
        self.record_btn = pygame.Rect(self.window_size[0] - 200, 20, 180, 40)
        self.control_panel = pygame.Rect(self.window_size[0] - 220, 0, 220, self.window_size[1])
        self.chat_area = pygame.Rect(0, 0, self.window_size[0] - self.control_panel.width, self.window_size[1])
        # 计算总高度以确定滚动范围
        total_height = 0
        for entry in self.chat_history:
            if (entry['type'] == 'user') or entry['type'] == 'assistant':
                if entry['type'] == 'user':
                    text = f"{entry['content']}"
                    color = BLACK
                elif entry['type'] == 'assistant':
                    text = f"{entry['content']}"
                    color = SAKI_COLOR
                lines = self.wrap_text(text, self.chat_area.width - SCROLLBAR_WIDTH - 40)
                total_height += len(lines) * LINE_HEIGHT
            if entry['type'] == 'image' and not self.normal_mode:
                img_height = int((self.chat_area.width // 2) * 9 / 16)
                total_height += img_height + LINE_HEIGHT

        # 如果正在录音，添加临时转录的高度
        if self.is_recording and self.current_interim:
            interim_text = f"Interim: {self.current_interim}"
            lines = self.wrap_text(interim_text, self.chat_area.width - SCROLLBAR_WIDTH - 40)
            total_height += len(lines) * LINE_HEIGHT
        
        self.max_scroll = max(total_height - self.chat_area.height + 200, 0)
        
        # 绘制控制面板
        btn_text = self.btn_text
        pygame.draw.rect(self.screen, GRAY, self.control_panel)
        pygame.draw.rect(self.screen, self.record_btn_color, self.record_btn)
        self.screen.blit(btn_text, (self.record_btn.x + 10, self.record_btn.y + 10))
        
        # 绘制聊天区域
        y_pos = self.chat_area.top - self.scroll_offset
        for entry in self.chat_history:
            if (entry['type'] == 'user') or entry['type'] == 'assistant':
                if entry['type'] == 'user':
                    text = f"User: {entry['content']}"
                    color = BLACK

                elif entry['type'] == 'assistant':
                    text = f"Assistant: {entry['content']}"
                    color = (0, 100, 0)
                lines = self.wrap_text(text, self.chat_area.width - SCROLLBAR_WIDTH - 40)
                for line in lines:
                    line_surf = self.font.render(line, True, color)
                    self.screen.blit(line_surf, (20, y_pos))
                    y_pos += LINE_HEIGHT

            if entry['type'] == 'image':
                img_surf = pygame.image.load(entry["content"]).convert()
                img_surf = pygame.transform.scale(img_surf, (self.chat_area.width // 2, int(self.chat_area.width // 2 * 9 / 16)))
                self.screen.blit(img_surf, (50, y_pos))
                y_pos += img_surf.get_height() + LINE_HEIGHT
        
        # 如果正在录音，显示临时转录
        if self.is_recording and self.current_interim:
            interim_text = f"Interim: {self.current_interim}"
            lines = self.wrap_text(interim_text, self.chat_area.width - SCROLLBAR_WIDTH - 40)
            for line in lines:
                line_surf = self.font.render(line, True, (100, 100, 100))
                self.screen.blit(line_surf, (20, y_pos))
                y_pos += LINE_HEIGHT
        
        self.draw_scrollbar()
        pygame.display.flip()
    
    async def run(self):
        """主运行循环，处理事件和更新显示"""
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                elif event.type == pygame.VIDEORESIZE:
                    self.window_size = (event.w, event.h)
                    if (event.w < 700):
                        self.window_size = (700, event.h)
                    self.screen = pygame.display.set_mode(self.window_size, pygame.RESIZABLE)
                    # 更新组件区域
                    self.control_panel = pygame.Rect(0, 0, self.window_size[0], 100)
                    self.chat_area = pygame.Rect(
                        0, self.control_panel.height,
                        self.window_size[0],
                        self.window_size[1] - self.control_panel.height
                    )
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
        """处理录音的开始和停止"""
        self.executor.submit(self._real_recording)

    def _real_recording(self):
        if not self.is_recording:
            # 开始录音
            self.btn_text = self.font.render("Stop Recording", True, WHITE)
            self.record_btn_color = RED
            print("====Start Recording====")
            print("[User: ]")
            shutil.rmtree("test_output", ignore_errors=True)
            os.makedirs("test_output", exist_ok=True)
            self.stop_event = threading.Event()
            self.recording_thread = threading.Thread(
                target=streaming_asr.recognize_speech,
                args=(self.stop_event, self.normal_mode, self.ui_callback)
            )
            self.recording_thread.start()
            self.is_recording = True
        else:
            # 停止录音并处理
            self.btn_text = self.font.render("  Processing...", True, WHITE)
            self.record_btn_color = PROCESSING_GRAY
            print("====Stop Recording====")
            self.stop_event.set()
            self.button_can_use = False 
            self.recording_thread.join()
            self.is_recording = False
            self.scroll_offset = self.max_scroll
            # 使用最新的用户输入进行语言模型处理
            
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
                    #print(output)
                    self.chat_history.append({'type': 'image', 'content': output[0][0]})
                    self.scroll_offset = self.max_scroll

            self.tts.stop_stream()
            print("====Finished Output====")
            self.button_can_use = True
            self.record_btn_color = GREEN
            self.btn_text = self.font.render("Start Recording", True, WHITE)

        
    
    def ui_callback(self, text, is_final):
        """处理语音识别结果的回调"""
        if is_final:
            self.chat_history.append({'type': 'user', 'content': text})
            self.scroll_offset = self.max_scroll
            #print(text)
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
