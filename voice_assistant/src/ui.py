#Python UI


import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Log with Images")
        self.root.geometry("400x600")

        # Chat log frame
        self.chat_frame = tk.Frame(self.root, bg="white")
        self.chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable Canvas for Chat
        self.canvas = tk.Canvas(self.chat_frame, bg="white", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.chat_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Input frame
        self.input_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Text entry
        self.text_entry = tk.Entry(self.input_frame, bg="white", font=("Arial", 12))
        self.text_entry.pack(fill=tk.X, side=tk.LEFT, padx=10, pady=10, expand=True)
        self.text_entry.bind("<Return>", lambda event: self.send_message())

        # Send button
        self.send_button = tk.Button(self.input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5)

        # Attach image button
        self.image_button = tk.Button(self.input_frame, text="Image", command=self.send_image)
        self.image_button.pack(side=tk.LEFT, padx=5)

    def add_message(self, text):
        """Add a text message to the chat log."""
        message_label = tk.Label(self.scrollable_frame, text=text, bg="lightblue", font=("Arial", 12),
                                 wraplength=300, justify="left", anchor="w", padx=10, pady=5)
        message_label.pack(fill=tk.X, pady=5, padx=5, anchor="w")

        # Auto-scroll to the bottom
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def add_image(self, image_path):
        """Add an image to the chat log."""
        try:
            img = Image.open(image_path)
            img.thumbnail((200, 200))  # Resize image to thumbnail
            photo = ImageTk.PhotoImage(img)

            image_label = tk.Label(self.scrollable_frame, image=photo, bg="white")
            image_label.image = photo  # Keep a reference to avoid garbage collection
            image_label.pack(pady=5, padx=5, anchor="w")

            # Auto-scroll to the bottom
            self.canvas.update_idletasks()
            self.canvas.yview_moveto(1.0)
        except Exception as e:
            self.add_message(f"Failed to load image: {e}")

    def send_message(self):
        """Handle sending a text message."""
        message = self.text_entry.get()
        if message.strip():
            self.add_message(f"You: {message}")
        self.text_entry.delete(0, tk.END)

    def send_image(self):
        """Handle sending an image."""
        image_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if image_path:
            self.add_image(image_path)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()