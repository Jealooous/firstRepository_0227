import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import os

try:
    from openai import OpenAI
except ImportError:
    messagebox.showerror("缺少依赖", "请先运行：pip install openai")
    raise SystemExit


BG     = "#1a1a2e"
BG2    = "#16213e"
FG     = "#e2e8f0"
FG2    = "#a0aec0"
ACCENT = "#667eea"

PROMPT_TEMPLATE = """根据以下内容，生成一道单选题。
只返回 JSON，不要任何多余文字，格式如下：
{{
  "question": "题目内容",
  "options": {{"A": "选项A内容", "B": "选项B内容", "C": "选项C内容", "D": "选项D内容"}},
  "answer": "A",
  "explanation": "答案解析"
}}

用户输入内容：
{content}"""


class QuizApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI 选择题生成器")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.answer_var = tk.StringVar()
        self.correct_answer = None

        self._build_ui()

    def _build_ui(self):
        tk.Label(self.root, text="AI 选择题生成器", font=("微软雅黑", 18, "bold"),
                 bg=BG, fg=FG).pack(pady=(20, 4))
        tk.Label(self.root, text="输入任意内容，AI 自动生成一道选择题",
                 font=("微软雅黑", 10), bg=BG, fg=FG2).pack(pady=(0, 16))

        main = tk.Frame(self.root, bg=BG, padx=24)
        main.pack(fill=tk.BOTH)

        # API Key
        key_frame = tk.Frame(main, bg=BG)
        key_frame.pack(fill=tk.X, pady=(0, 10))
        tk.Label(key_frame, text="API Key：", font=("微软雅黑", 10),
                 bg=BG, fg=FG2, width=9, anchor="w").pack(side=tk.LEFT)
        self.key_entry = tk.Entry(key_frame, font=("Consolas", 10), show="*",
                                   relief=tk.FLAT, bg=BG2, fg=FG, insertbackground=FG,
                                   highlightthickness=1, highlightbackground="#4a5568",
                                   highlightcolor=ACCENT)
        self.key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        env_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if env_key:
            self.key_entry.insert(0, env_key)

        # 内容输入
        tk.Label(main, text="输入内容或主题：", font=("微软雅黑", 10),
                 bg=BG, fg=FG2, anchor="w").pack(fill=tk.X)
        self.input_text = tk.Text(main, height=5, font=("微软雅黑", 11),
                                   relief=tk.FLAT, bg=BG2, fg=FG, insertbackground=FG,
                                   highlightthickness=1, highlightbackground="#4a5568",
                                   highlightcolor=ACCENT, wrap=tk.WORD)
        self.input_text.pack(fill=tk.X, pady=(4, 12), ipady=6)
        self.input_text.insert("1.0", "例如：光合作用是植物利用光能将二氧化碳和水转化为有机物的过程。")

        # 生成按钮
        self.gen_btn = tk.Button(main, text="✨ 生成题目", font=("微软雅黑", 12, "bold"),
                                  command=self._start_generate,
                                  bg=ACCENT, fg="white", relief=tk.FLAT,
                                  activebackground="#5a67d8", activeforeground="white",
                                  cursor="hand2", pady=8)
        self.gen_btn.pack(fill=tk.X, pady=(0, 16))

        ttk.Separator(main, orient="horizontal").pack(fill=tk.X, pady=(0, 16))

        # 题目
        self.question_label = tk.Label(main, text="题目将在这里显示",
                                        font=("微软雅黑", 12), bg=BG, fg="#4a5568",
                                        wraplength=460, justify=tk.LEFT, anchor="w")
        self.question_label.pack(fill=tk.X, pady=(0, 12))

        # 选项
        self.option_frame = tk.Frame(main, bg=BG)
        self.option_frame.pack(fill=tk.X)
        self.radio_buttons = []
        for opt in ["A", "B", "C", "D"]:
            rb = tk.Radiobutton(self.option_frame, text=f"{opt}. —",
                                variable=self.answer_var, value=opt,
                                font=("微软雅黑", 11), bg=BG, fg=FG,
                                selectcolor=BG2, activebackground=BG,
                                activeforeground=FG, state=tk.DISABLED,
                                anchor="w", cursor="hand2")
            rb.pack(fill=tk.X, pady=3)
            self.radio_buttons.append(rb)

        # 提交按钮
        self.submit_btn = tk.Button(main, text="提交答案", font=("微软雅黑", 11),
                                     command=self._submit,
                                     bg="#2d6a4f", fg="white", relief=tk.FLAT,
                                     activebackground="#1b4332", activeforeground="white",
                                     cursor="hand2", pady=6, state=tk.DISABLED)
        self.submit_btn.pack(fill=tk.X, pady=(16, 8))

        self.result_label = tk.Label(main, text="", font=("微软雅黑", 12, "bold"),
                                      bg=BG, wraplength=460, justify=tk.LEFT)
        self.result_label.pack(fill=tk.X)

        self.explain_label = tk.Label(main, text="", font=("微软雅黑", 10),
                                       bg=BG, fg=FG2, wraplength=460, justify=tk.LEFT)
        self.explain_label.pack(fill=tk.X, pady=(4, 20))

    def _start_generate(self):
        api_key = self.key_entry.get().strip()
        content = self.input_text.get("1.0", tk.END).strip()

        if not api_key:
            messagebox.showwarning("提示", "请输入 DeepSeek API Key")
            return
        if not content:
            messagebox.showwarning("提示", "请输入内容或主题")
            return

        self._reset_question()
        self.gen_btn.config(state=tk.DISABLED, text="生成中...")
        self.question_label.config(text="AI 思考中，请稍候...", fg=ACCENT)

        threading.Thread(target=self._generate, args=(api_key, content), daemon=True).start()

    def _generate(self, api_key, content):
        try:
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                max_tokens=1024,
                messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(content=content)}]
            )
            raw = response.choices[0].message.content.strip()
            start = raw.find("{")
            end = raw.rfind("}") + 1
            data = json.loads(raw[start:end])
            self.root.after(0, self._show_question, data)
        except json.JSONDecodeError:
            self.root.after(0, self._show_error, "AI 返回格式异常，请重试")
        except Exception as e:
            self.root.after(0, self._show_error, str(e))

    def _show_question(self, data):
        self.correct_answer = data["answer"].strip().upper()
        self.explanation = data.get("explanation", "")

        self.question_label.config(text=f"Q: {data['question']}", fg=FG)
        options = data["options"]
        for rb, key in zip(self.radio_buttons, ["A", "B", "C", "D"]):
            rb.config(text=f"{key}. {options.get(key, '')}", state=tk.NORMAL)

        self.answer_var.set("")
        self.submit_btn.config(state=tk.NORMAL)
        self.gen_btn.config(state=tk.NORMAL, text="✨ 重新生成")

    def _show_error(self, msg):
        self.question_label.config(text="生成失败，请查看弹出的错误详情", fg="#fc8181")
        self.gen_btn.config(state=tk.NORMAL, text="✨ 生成题目")
        # 用可选中文字的弹窗显示错误，方便复制
        win = tk.Toplevel(self.root)
        win.title("出错了")
        win.configure(bg=BG)
        win.resizable(False, False)
        tk.Label(win, text="错误信息（可选中复制）：", font=("微软雅黑", 10),
                 bg=BG, fg=FG2).pack(padx=16, pady=(12, 4), anchor="w")
        txt = tk.Text(win, font=("Consolas", 10), bg=BG2, fg="#fc8181",
                      width=60, height=8, wrap=tk.WORD, relief=tk.FLAT,
                      highlightthickness=1, highlightbackground="#4a5568")
        txt.pack(padx=16, pady=(0, 8))
        txt.insert("1.0", msg)
        txt.config(state=tk.DISABLED)
        tk.Button(win, text="关闭", command=win.destroy,
                  bg=ACCENT, fg="white", relief=tk.FLAT,
                  padx=16, pady=4, cursor="hand2").pack(pady=(0, 12))

    def _submit(self):
        selected = self.answer_var.get()
        if not selected:
            messagebox.showwarning("提示", "请先选择一个答案")
            return

        for rb, key in zip(self.radio_buttons, ["A", "B", "C", "D"]):
            if key == self.correct_answer:
                rb.config(fg="#68d391")
            elif key == selected and selected != self.correct_answer:
                rb.config(fg="#fc8181")
            rb.config(state=tk.DISABLED)

        self.submit_btn.config(state=tk.DISABLED)

        if selected == self.correct_answer:
            self.result_label.config(text="✅ 回答正确！", fg="#68d391")
        else:
            self.result_label.config(
                text=f"❌ 回答错误，正确答案是 {self.correct_answer}", fg="#fc8181")

        self.explain_label.config(text=f"解析：{self.explanation}")

    def _reset_question(self):
        self.correct_answer = None
        self.answer_var.set("")
        self.question_label.config(text="", fg=FG)
        for rb, key in zip(self.radio_buttons, ["A", "B", "C", "D"]):
            rb.config(text=f"{key}. —", state=tk.DISABLED, fg=FG)
        self.submit_btn.config(state=tk.DISABLED)
        self.result_label.config(text="")
        self.explain_label.config(text="")


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("520x780")
    QuizApp(root)
    root.mainloop()
