import asyncio
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from prompts.planner_system_prompt import planner_system_prompt
from services.ollama_service import OllamaService, OllamaServiceError


class ChatBotApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Dev GX Chat")
        self.root.geometry("760x560")
        self.root.minsize(620, 420)

        self.ollama_service = OllamaService()
        self.messages = [{"role": "system", "content": planner_system_prompt}]
        self.is_loading = False

        self._build_layout()
        self._append_message(
            "assistant",
            "Ola! Eu transformo ideias de software em planos tecnicos de MVP. "
            "Descreve a tua ideia de projeto e eu organizo a solucao.",
        )

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Label(
            container,
            text="Chat local com Ollama",
            font=("Segoe UI", 16, "bold"),
        )
        header.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.chat_area = scrolledtext.ScrolledText(
            container,
            wrap="word",
            font=("Consolas", 11),
            state="disabled",
        )
        self.chat_area.grid(row=1, column=0, sticky="nsew")

        controls = ttk.Frame(container, padding=(0, 12, 0, 0))
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.input_entry = ttk.Entry(controls, textvariable=self.input_var)
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.input_entry.bind("<Return>", self._on_enter_pressed)

        self.send_button = ttk.Button(
            controls,
            text="Enviar",
            command=self.send_message,
        )
        self.send_button.grid(row=0, column=1, padx=(0, 8))

        self.clear_button = ttk.Button(
            controls,
            text="Nova conversa",
            command=self.reset_chat,
        )
        self.clear_button.grid(row=0, column=2)

        self.status_var = tk.StringVar(value="Pronto.")
        status_label = ttk.Label(container, textvariable=self.status_var)
        status_label.grid(row=3, column=0, sticky="w", pady=(10, 0))

        self.input_entry.focus_set()

    def _append_message(self, role: str, content: str) -> None:
        prefix = "Voce" if role == "user" else "Dev GX"
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", f"{prefix}: {content.strip()}\n\n")
        self.chat_area.configure(state="disabled")
        self.chat_area.see("end")

    def _set_loading(self, loading: bool) -> None:
        self.is_loading = loading
        state = "disabled" if loading else "normal"
        self.input_entry.configure(state=state)
        self.send_button.configure(state=state)
        self.clear_button.configure(state=state)
        self.status_var.set("A gerar resposta..." if loading else "Pronto.")
        if not loading:
            self.input_entry.focus_set()

    def _on_enter_pressed(self, _event: tk.Event) -> str:
        self.send_message()
        return "break"

    def send_message(self) -> None:
        if self.is_loading:
            return

        user_message = self.input_var.get().strip()
        if not user_message:
            return

        self.input_var.set("")
        self.messages.append({"role": "user", "content": user_message})
        self._append_message("user", user_message)
        self._set_loading(True)

        worker = threading.Thread(
            target=self._generate_reply,
            args=(list(self.messages),),
            daemon=True,
        )
        worker.start()

    def _generate_reply(self, messages: list[dict[str, str]]) -> None:
        try:
            reply = asyncio.run(self.ollama_service.chat(messages))
            self.root.after(0, self._handle_reply_success, reply)
        except OllamaServiceError as exc:
            self.root.after(0, self._handle_reply_error, str(exc))
        except Exception as exc:
            self.root.after(
                0,
                self._handle_reply_error,
                f"Ocorreu um erro inesperado: {exc}",
            )

    def _handle_reply_success(self, reply: str) -> None:
        self.messages.append({"role": "assistant", "content": reply})
        self._append_message("assistant", reply)
        self._set_loading(False)

    def _handle_reply_error(self, error_message: str) -> None:
        self._set_loading(False)
        messagebox.showerror("Erro ao comunicar com o Ollama", error_message)

    def reset_chat(self) -> None:
        if self.is_loading:
            return

        self.messages = [{"role": "system", "content": planner_system_prompt}]
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.configure(state="disabled")
        self._append_message(
            "assistant",
            "Conversa reiniciada. Descreve uma nova ideia de projeto.",
        )

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    ChatBotApp().run()
