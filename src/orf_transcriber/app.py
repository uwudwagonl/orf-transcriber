"""Tkinter GUI for ORF Transcriber.

Designed for non-technical users: large fonts, simple layout, clear status
messages in German. Heavy work runs in a background thread; the UI polls a
queue every 100 ms for progress events.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import APP_NAME, __version__, config
from .paths import default_output_dir
from .worker import Event, Job

POLL_MS = 100
PADDING = 12


def _open_in_explorer(path: Path) -> None:
    path = Path(path)
    if not path.exists():
        return
    try:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except OSError:
        webbrowser.open(path.as_uri())


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent: tk.Tk, settings: config.Settings) -> None:
        super().__init__(parent)
        self.title("Einstellungen")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.settings = settings
        self.result: config.Settings | None = None

        frm = ttk.Frame(self, padding=PADDING)
        frm.grid(sticky="nsew")

        row = 0
        ttk.Label(frm, text="Modellgröße:").grid(row=row, column=0, sticky="w", pady=4)
        self.model_var = tk.StringVar(value=settings.model)
        model_cb = ttk.Combobox(
            frm,
            textvariable=self.model_var,
            state="readonly",
            width=42,
            values=[label for _, label in config.MODEL_CHOICES],
        )
        # initial display value
        for code, label in config.MODEL_CHOICES:
            if code == settings.model:
                model_cb.set(label)
                break
        model_cb.grid(row=row, column=1, sticky="we", pady=4)
        self._model_cb = model_cb
        row += 1

        ttk.Label(frm, text="Sprache:").grid(row=row, column=0, sticky="w", pady=4)
        self.lang_var = tk.StringVar(value=settings.language)
        lang_cb = ttk.Combobox(
            frm,
            textvariable=self.lang_var,
            state="readonly",
            width=42,
            values=[label for _, label in config.LANGUAGE_CHOICES],
        )
        for code, label in config.LANGUAGE_CHOICES:
            if code == settings.language:
                lang_cb.set(label)
                break
        lang_cb.grid(row=row, column=1, sticky="we", pady=4)
        self._lang_cb = lang_cb
        row += 1

        self.keep_video_var = tk.BooleanVar(value=settings.keep_video)
        ttk.Checkbutton(
            frm,
            text="Videodatei behalten (sonst nur Transkript)",
            variable=self.keep_video_var,
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=8)
        row += 1

        info = ttk.Label(
            frm,
            text=(
                "Hinweis: Beim ersten Start wird das Sprachmodell "
                "(ca. 1.5 GB) automatisch heruntergeladen."
            ),
            wraplength=380,
            foreground="#555",
        )
        info.grid(row=row, column=0, columnspan=2, sticky="we", pady=(8, 0))
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(btns, text="Abbrechen", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btns, text="Speichern", command=self._save, style="Accent.TButton").pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._save())
        self.update_idletasks()
        self._center_on(parent)

    def _center_on(self, parent: tk.Tk) -> None:
        parent.update_idletasks()
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px + (pw - w)//2}+{py + (ph - h)//2}")

    def _save(self) -> None:
        model_label = self._model_cb.get()
        lang_label = self._lang_cb.get()
        model_code = next((c for c, l in config.MODEL_CHOICES if l == model_label), self.settings.model)
        lang_code = next((c for c, l in config.LANGUAGE_CHOICES if l == lang_label), self.settings.language)

        self.result = config.Settings(
            output_dir=self.settings.output_dir,
            model=model_code,
            language=lang_code,
            keep_video=self.keep_video_var.get(),
            compute_type=self.settings.compute_type,
            device=self.settings.device,
        )
        self.destroy()


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("780x620")
        self.minsize(640, 520)

        self.settings = config.load()
        self.events: queue.Queue[Event] = queue.Queue()
        self.job: Job | None = None
        self.last_output: dict[str, str | None] | None = None

        self._build_styles()
        self._build_ui()
        self.after(POLL_MS, self._drain_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── styling ──────────────────────────────────────────────────────────
    def _build_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("vista" if os.name == "nt" else "clam")
        except tk.TclError:
            pass
        base_font = ("Segoe UI", 11) if os.name == "nt" else ("Helvetica", 11)
        self.option_add("*Font", base_font)
        style.configure("Header.TLabel", font=(base_font[0], 16, "bold"))
        style.configure("Big.TButton", font=(base_font[0], 13, "bold"), padding=10)
        style.configure("Accent.TButton", font=(base_font[0], 11, "bold"))

    # ── ui ──────────────────────────────────────────────────────────────
    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=PADDING)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        header = ttk.Frame(outer)
        header.grid(row=0, column=0, sticky="we")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="ORF ON Transkript", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Einstellungen …", command=self._open_settings).grid(row=0, column=1, sticky="e")

        intro = ttk.Label(
            outer,
            text=(
                "Link von on.orf.at hier einfügen. Das Video wird heruntergeladen, "
                "das Gesprochene wird als Word-Dokument gespeichert."
            ),
            wraplength=720,
        )
        intro.grid(row=1, column=0, sticky="we", pady=(8, 12))

        # URL row
        url_frame = ttk.LabelFrame(outer, text="ORF-Link", padding=PADDING)
        url_frame.grid(row=2, column=0, sticky="we")
        url_frame.columnconfigure(0, weight=1)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Consolas", 11))
        self.url_entry.grid(row=0, column=0, sticky="we", padx=(0, 8))
        ttk.Button(url_frame, text="Aus Zwischenablage", command=self._paste).grid(row=0, column=1)

        # Output folder
        out_frame = ttk.LabelFrame(outer, text="Speicherort", padding=PADDING)
        out_frame.grid(row=3, column=0, sticky="we", pady=(12, 0))
        out_frame.columnconfigure(0, weight=1)
        self.out_var = tk.StringVar(value=self.settings.output_dir or str(default_output_dir()))
        ttk.Entry(out_frame, textvariable=self.out_var).grid(row=0, column=0, sticky="we", padx=(0, 8))
        ttk.Button(out_frame, text="Ordner wählen …", command=self._choose_dir).grid(row=0, column=1)

        # Big action button
        action_row = ttk.Frame(outer)
        action_row.grid(row=4, column=0, sticky="we", pady=(16, 8))
        action_row.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(
            action_row,
            text="Herunterladen und transkribieren",
            command=self._start,
            style="Big.TButton",
        )
        self.start_btn.grid(row=0, column=0, sticky="we")
        self.cancel_btn = ttk.Button(action_row, text="Abbrechen", command=self._cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))

        # Progress
        prog_frame = ttk.Frame(outer)
        prog_frame.grid(row=5, column=0, sticky="we", pady=(8, 4))
        prog_frame.columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Bereit.")
        ttk.Label(prog_frame, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(prog_frame, mode="determinate", maximum=1.0)
        self.progress.grid(row=1, column=0, sticky="we", pady=(4, 0))

        # Log
        log_frame = ttk.LabelFrame(outer, text="Verlauf", padding=PADDING)
        log_frame.grid(row=6, column=0, sticky="nsew", pady=(12, 0))
        outer.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=12, wrap="word", state="disabled", font=("Consolas", 10))
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)

        # Footer
        footer = ttk.Frame(outer)
        footer.grid(row=7, column=0, sticky="we", pady=(8, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, text=f"v{__version__}", foreground="#888").grid(row=0, column=0, sticky="w")
        self.open_btn = ttk.Button(footer, text="Speicherort öffnen", command=self._open_output, state="disabled")
        self.open_btn.grid(row=0, column=1, sticky="e")

        self.url_entry.focus_set()

    # ── actions ─────────────────────────────────────────────────────────
    def _paste(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self.url_var.set(text.strip())

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.out_var.get() or str(Path.home()))
        if chosen:
            self.out_var.set(chosen)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self, self.settings)
        self.wait_window(dlg)
        if dlg.result is not None:
            self.settings = dlg.result
            self.settings.output_dir = self.out_var.get()
            config.save(self.settings)
            self._log("Einstellungen gespeichert.")

    def _start(self) -> None:
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Bitte einen ORF-Link einfügen.")
            return
        if "on.orf.at" not in url:
            ok = messagebox.askyesno(
                APP_NAME,
                "Der Link sieht nicht wie ein ORF ON-Link aus. Trotzdem versuchen?",
            )
            if not ok:
                return

        out_dir = Path(self.out_var.get().strip() or default_output_dir())
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(APP_NAME, f"Speicherordner kann nicht erstellt werden:\n{exc}")
            return
        self.settings.output_dir = str(out_dir)
        config.save(self.settings)

        self._set_running(True)
        self._clear_log()
        self.progress["value"] = 0
        self.status_var.set("Starte …")
        self.last_output = None
        self.open_btn["state"] = "disabled"

        self.job = Job(url=url, settings=self.settings, events=self.events)
        self.job.start()

    def _cancel(self) -> None:
        if self.job and self.job.is_alive():
            self.job.cancel()
            self.status_var.set("Wird abgebrochen …")

    def _open_output(self) -> None:
        if not self.last_output:
            return
        target = self.last_output.get("docx") or self.last_output.get("video")
        if target:
            _open_in_explorer(Path(target).parent)

    def _on_close(self) -> None:
        if self.job and self.job.is_alive():
            if not messagebox.askyesno(APP_NAME, "Es läuft gerade ein Vorgang. Wirklich beenden?"):
                return
            self.job.cancel()
        self.destroy()

    # ── event pump ──────────────────────────────────────────────────────
    def _drain_events(self) -> None:
        try:
            while True:
                evt = self.events.get_nowait()
                self._handle(evt)
        except queue.Empty:
            pass
        self.after(POLL_MS, self._drain_events)

    def _handle(self, evt: Event) -> None:
        if evt.progress is not None:
            self.progress["value"] = max(0.0, min(evt.progress, 1.0))

        if evt.kind == "status":
            self.status_var.set(evt.message)
            self._log(evt.message)
        elif evt.kind == "log":
            self._log(evt.message)
        elif evt.kind == "segment":
            self._log(f"  · {evt.message}")
        elif evt.kind == "done":
            self.status_var.set(evt.message)
            self._log(evt.message)
            self.last_output = evt.payload  # type: ignore[assignment]
            self.open_btn["state"] = "normal"
            self._set_running(False)
            messagebox.showinfo(APP_NAME, "Transkript fertig!\n\nDu kannst es jetzt im Speicherort öffnen.")
        elif evt.kind == "error":
            self.status_var.set("Fehler.")
            self._log(f"FEHLER: {evt.message}")
            if evt.payload:
                self._log(str(evt.payload))
            self._set_running(False)
            messagebox.showerror(APP_NAME, f"Es ist ein Fehler aufgetreten:\n\n{evt.message}")

    def _set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.start_btn["state"] = state
        self.url_entry["state"] = state
        self.cancel_btn["state"] = "normal" if running else "disabled"

    def _log(self, text: str) -> None:
        self.log["state"] = "normal"
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log["state"] = "disabled"

    def _clear_log(self) -> None:
        self.log["state"] = "normal"
        self.log.delete("1.0", "end")
        self.log["state"] = "disabled"


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
