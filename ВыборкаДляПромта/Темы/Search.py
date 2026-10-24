import json
import glob
import os
import tkinter as tk
from tkinter import ttk


class FastFuzzyJsonSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Оптимизированный поиск по уставам и кодексам")
        self.root.geometry("1000x750")

        # Цветовая палитра
        self.bg_color = "#ffffff"
        self.text_color = "#1c1d22"
        self.header_color = "#b32400"
        self.section_color = "#1f77b4"

        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # Безопасная инициализация структуры данных
        self.all_files_data = list()
        self.debounce_id = None

        self.load_all_json_files()
        self.create_widgets()

    def load_all_json_files(self):
        """Безопасное чтение всех JSON-файлов в папке."""
        json_pattern = os.path.join(self.current_dir, "*.json")
        json_files = glob.glob(json_pattern)

        for file_path in json_files:
            file_name = os.path.basename(file_path)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                sections = json_data.get("sections", list())
                posts = json_data.get("posts", list())
                blocks = list()

                if sections:
                    for sec in sections:
                        blocks.append({
                            "title": sec.get("title", "Раздел").strip(),
                            "text": sec.get("text", "")
                        })
                elif posts:
                    for post in posts:
                        blocks.append({
                            "title": "",
                            "text": post.get("text", "")
                        })

                if blocks:
                    self.all_files_data.append({
                        "file_name": file_name,
                        "title": json_data.get("title", file_name).strip(),
                        "blocks": blocks
                    })
            except Exception as e:
                print(f"Ошибка парсинга файла {file_name}: {e}")

    def create_widgets(self):
        """Создание элементов GUI."""
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        lbl_info = ttk.Label(
            top_frame,
            text="Поиск статьи или фразы:",
            font=("Calibri", 11)
        )
        lbl_info.pack(side=tk.LEFT, padx=(0, 10))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search_change)

        self.entry_search = ttk.Entry(top_frame, textvariable=self.search_var, font=("Calibri", 12))
        self.entry_search.pack(fill=tk.X, expand=True, side=tk.LEFT)
        self.entry_search.focus()

        btn_clear = ttk.Button(top_frame, text="Очистить", command=self.clear_search)
        btn_clear.pack(side=tk.RIGHT, padx=(10, 0))

        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        # spacing1 - интервал между абзацами, spacing2 - внутри завернутых строк
        self.text_output = tk.Text(
            bottom_frame,
            wrap=tk.WORD,
            font=("Calibri", 12),
            bg=self.bg_color,
            fg=self.text_color,
            spacing1=4,
            spacing2=2,
            padx=15,
            pady=10
        )
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.text_output.yview)
        self.text_output.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_output.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text_output.tag_configure("file_header", font=("Calibri", 14, "bold"), foreground=self.header_color)
        self.text_output.tag_configure("block_title", font=("Calibri", 12, "bold"), foreground=self.section_color)
        self.text_output.tag_configure("match_highlight", background="#ffeb3b", foreground="#000000")

        self.text_output.configure(state=tk.DISABLED)

        self.root.bind("<Escape>", lambda event: self.clear_search())
        self.show_all_data()

    def clear_search(self):
        self.search_var.set("")

    def clean_text(self, text):
        """Глубокая очистка текста от "съезжаний", пустых абзацев и форумного мусора."""
        cleaned_lines = list()
        for line in text.splitlines():
            # Схлопываем множественные пробелы в один и убираем невидимые символы
            cleaned_line = " ".join(line.split()).strip()
            # Пропускаем полностью пустые строки и одиночные символы-разделители
            if cleaned_line and cleaned_line != "​":
                cleaned_lines.append(cleaned_line)
        return "\n".join(cleaned_lines)

    def on_search_change(self, *args):
        """Дебаунсинг ввода (150 мс) для устранения подвисаний интерфейса."""
        if self.debounce_id:
            self.root.after_cancel(self.debounce_id)
        self.debounce_id = self.root.after(150, self.execute_search)

    def execute_search(self):
        """Поиск с ранжированием и фильтрацией пустых зон."""
        search_query = self.search_var.get().strip()

        if not search_query:
            self.show_all_data()
            return

        self.text_output.configure(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)

        query_lower = search_query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 1]

        search_results = list()

        for file_info in self.all_files_data:
            for block in file_info["blocks"]:
                block_text = self.clean_text(block["text"])
                if not block_text:
                    continue

                block_text_lower = block_text.lower()
                score = 0
                words_to_highlight = list()

                if query_lower in block_text_lower:
                    score = 100
                    words_to_highlight.append(search_query)
                elif query_words:
                    matched_words = 0
                    for word in query_words:
                        stem = word[:-2] if len(word) > 4 else word
                        if stem in block_text_lower:
                            matched_words += 1
                            words_to_highlight.append(word)

                    if matched_words > 0:
                        score = int((matched_words / len(query_words)) * 50)

                if score > 0:
                    search_results.append((
                        score,
                        file_info["title"],
                        block["title"],
                        block_text,
                        words_to_highlight
                    ))

        search_results.sort(key=lambda x: x[0], reverse=True)

        if search_results:
            current_file_title = ""
            for score, file_title, block_title, text, words in search_results:
                if file_title != current_file_title:
                    current_file_title = file_title
                    self.text_output.insert(tk.END, f"\n{current_file_title}\n", "file_header")

                # Показываем заголовок главы, только если он несет уникальный текст
                if block_title and block_title.lower() != file_title.lower():
                    self.text_output.insert(tk.END, f"\n{block_title}\n", "block_title")

                start_pos = self.text_output.index(tk.CURRENT)
                self.text_output.insert(tk.END, text + "\n")
                end_pos = self.text_output.index(tk.CURRENT)

                for word in words:
                    idx = start_pos
                    while True:
                        idx = self.text_output.search(word, idx, nocase=True, stopindex=end_pos)
                        if not idx:
                            break
                        lastidx = f"{idx}+{len(word)}c"
                        self.text_output.tag_add("match_highlight", idx, lastidx)
                        idx = lastidx
        else:
            self.text_output.insert(tk.END, f"Ничего не найдено по запросу '{search_query}'.")

        self.text_output.configure(state=tk.DISABLED)

    def show_all_data(self):
        """Отображение чистой структуры всех документов."""
        self.text_output.configure(state=tk.NORMAL)
        self.text_output.delete("1.0", tk.END)

        for file_info in self.all_files_data:
            self.text_output.insert(tk.END, f"{file_info['title']}\n", "file_header")
            for block in file_info["blocks"]:
                block_text = self.clean_text(block["text"])
                if block_text:
                    if block["title"] and block["title"].lower() != file_info["title"].lower():
                        self.text_output.insert(tk.END, f"\n{block['title']}\n", "block_title")
                    self.text_output.insert(tk.END, f"{block_text}\n\n")
            self.text_output.insert(tk.END, "\n")

        self.text_output.configure(state=tk.DISABLED)


if __name__ == "__main__":
    root = tk.Tk()
    app = FastFuzzyJsonSearchApp(root)
    root.mainloop()
