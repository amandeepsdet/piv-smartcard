"""Tkinter UI (port of ``index.ts`` + ``index.html``).

Provides Connect / Disconnect buttons, a reader picker, a slot picker
and a certificate display, mirroring the web demo. Tkinter ships with
Python on both Windows and macOS, so there is no extra UI dependency.
"""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext, ttk

from . import piv
from .reader import CardSession, ReaderError, list_readers
from .util import identify_card


class SmartCardDemoApp(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=12)
        self.master.title("PIV Smart Card Demo")
        self.master.minsize(640, 480)
        self.grid(sticky="nsew")
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)

        self.session: CardSession | None = None
        self._build_widgets()
        self.refresh_readers()

    # -- layout ------------------------------------------------------------
    def _build_widgets(self) -> None:
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Reader:").grid(row=0, column=0, sticky="w", pady=4)
        self.reader_var = tk.StringVar()
        self.reader_combo = ttk.Combobox(self, textvariable=self.reader_var, state="readonly")
        self.reader_combo.grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(self, text="Refresh", command=self.refresh_readers).grid(row=0, column=2)

        ttk.Label(self, text="Slot:").grid(row=1, column=0, sticky="w", pady=4)
        self.slot_var = tk.StringVar(value="card_authentication")
        self.slot_combo = ttk.Combobox(
            self, textvariable=self.slot_var, state="readonly", values=list(piv.SLOTS.keys())
        )
        self.slot_combo.grid(row=1, column=1, sticky="ew", padx=6)

        button_bar = ttk.Frame(self)
        button_bar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)
        self.connect_btn = ttk.Button(button_bar, text="Connect", command=self.on_connect)
        self.connect_btn.pack(side="left")
        self.disconnect_btn = ttk.Button(
            button_bar, text="Disconnect", command=self.on_disconnect, state="disabled"
        )
        self.disconnect_btn.pack(side="left", padx=6)
        self.read_btn = ttk.Button(
            button_bar, text="Read Certificate", command=self.on_read, state="disabled"
        )
        self.read_btn.pack(side="left")

        self.output = scrolledtext.ScrolledText(self, height=18, wrap="word")
        self.output.grid(row=3, column=0, columnspan=3, sticky="nsew")
        self.rowconfigure(3, weight=1)

        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w").grid(
            row=4, column=0, columnspan=3, sticky="ew", pady=(8, 0)
        )

    # -- helpers -----------------------------------------------------------
    def _log(self, text: str) -> None:
        self.output.insert("end", text + "\n")
        self.output.see("end")

    def _status(self, text: str) -> None:
        self.status_var.set(text)

    def _run_async(self, work) -> None:
        """Run blocking PC/SC work off the UI thread."""
        threading.Thread(target=work, daemon=True).start()

    # -- actions -----------------------------------------------------------
    def refresh_readers(self) -> None:
        try:
            names = list_readers()
        except ReaderError as exc:
            self._status(str(exc))
            names = []
        self.reader_combo["values"] = names
        if names and not self.reader_var.get():
            self.reader_var.set(names[0])
        self._status(f"Found {len(names)} reader(s).")

    def on_connect(self) -> None:
        name = self.reader_var.get()
        if not name:
            self._status("Select a reader first.")
            return
        self._status(f"Connecting to {name} ...")

        def work():
            try:
                session = CardSession(name).connect()
                atr = session.get_atr()
                self.session = session
                self.after(0, lambda: self._on_connected(identify_card(atr)))
            except ReaderError as exc:
                self.after(0, lambda: self._status(str(exc)))

        self._run_async(work)

    def _on_connected(self, card_name: str) -> None:
        self._log(f"Connected. Card: {card_name}")
        self._status(f"Connected. Card: {card_name}")
        self.connect_btn["state"] = "disabled"
        self.disconnect_btn["state"] = "normal"
        self.read_btn["state"] = "normal"

    def on_disconnect(self) -> None:
        if self.session is not None:
            self.session.disconnect()
            self.session = None
        self._log("Disconnected.")
        self._status("Disconnected.")
        self.connect_btn["state"] = "normal"
        self.disconnect_btn["state"] = "disabled"
        self.read_btn["state"] = "disabled"

    def on_read(self) -> None:
        if self.session is None:
            self._status("Not connected.")
            return
        slot = self.slot_var.get()
        self._status(f"Reading {slot} certificate ...")

        def work():
            try:
                piv.select(self.session)
                info = piv.read_certificate(self.session, slot)
                self.after(0, lambda: self._on_read(slot, info))
            except Exception as exc:  # surface any PIV/APDU error to the UI
                message = str(exc)
                self.after(0, lambda: self._status(f"Read failed: {message}"))

        self._run_async(work)

    def _on_read(self, slot: str, info) -> None:
        self._log(f"\n=== {slot} certificate ===")
        self._log(info.as_lines())
        self._log(info.pem)
        self._status("Certificate read successfully.")


def main() -> None:
    root = tk.Tk()
    SmartCardDemoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
