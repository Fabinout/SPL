#!/usr/bin/env python3
"""SPL IDE — Simple graphical interface for writing, assembling, and running SPL programs."""

import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import sys
import os
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(ROOT, "spl_asm.py")
VM = os.path.join(ROOT, "spl_vm.py")

EXAMPLE = """; Hello, World!
(push 72)  (out 0x01)  ; H
(push 101) (out 0x01)  ; e
(push 108) (out 0x01)  ; l
(push 108) (out 0x01)  ; l
(push 111) (out 0x01)  ; o
(push 44)  (out 0x01)  ; ,
(push 32)  (out 0x01)  ;
(push 87)  (out 0x01)  ; W
(push 111) (out 0x01)  ; o
(push 114) (out 0x01)  ; r
(push 108) (out 0x01)  ; l
(push 100) (out 0x01)  ; d
(push 33)  (out 0x01)  ; !
(push 10)  (out 0x01)  ; newline
(halt)
"""


class SplIDE:
    def __init__(self, root):
        self.root = root
        self.root.title("SPL IDE")
        self.root.geometry("900x620")
        self.current_file = None

        self._build_menu()
        self._build_toolbar()
        self._build_panes()
        self._build_status()

        self.editor.insert("1.0", EXAMPLE)
        self.root.bind("<F5>", lambda e: self.assemble_and_run())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())

    # ---- UI construction ----

    def _build_menu(self):
        menubar = tk.Menu(self.root)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Ouvrir...", command=self.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Enregistrer", command=self.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Enregistrer sous...", command=self.save_file_as)
        file_menu.add_separator()
        file_menu.add_command(label="Quitter", command=self.root.quit)
        menubar.add_cascade(label="Fichier", menu=file_menu)

        run_menu = tk.Menu(menubar, tearoff=0)
        run_menu.add_command(label="Assembler", command=self.assemble)
        run_menu.add_command(label="Assembler et lancer", command=self.assemble_and_run, accelerator="F5")
        menubar.add_cascade(label="Lancer", menu=run_menu)

        self.root.config(menu=menubar)

    def _build_toolbar(self):
        toolbar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        btn_asm = tk.Button(toolbar, text="Assembler", command=self.assemble, padx=8)
        btn_asm.pack(side=tk.LEFT, padx=2, pady=2)

        btn_run = tk.Button(toolbar, text="Assembler + Lancer  (F5)", command=self.assemble_and_run, padx=8)
        btn_run.pack(side=tk.LEFT, padx=2, pady=2)

    def _build_panes(self):
        pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashwidth=6)
        pane.pack(fill=tk.BOTH, expand=True)

        # Left: editor
        left = tk.Frame(pane)
        tk.Label(left, text="  Code SPL", anchor="w", font=("Segoe UI", 9, "bold")).pack(fill=tk.X)
        self.editor = scrolledtext.ScrolledText(
            left, wrap=tk.NONE, font=("Consolas", 11), undo=True, bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4", selectbackground="#264f78", selectforeground="#d4d4d4",
        )
        self.editor.pack(fill=tk.BOTH, expand=True)
        pane.add(left, stretch="always")

        # Right: output
        right = tk.Frame(pane)
        tk.Label(right, text="  Sortie", anchor="w", font=("Segoe UI", 9, "bold")).pack(fill=tk.X)
        self.output = scrolledtext.ScrolledText(
            right, wrap=tk.WORD, font=("Consolas", 11), state=tk.DISABLED, bg="#1a1a2e", fg="#a0ffa0",
        )
        self.output.pack(fill=tk.BOTH, expand=True)
        pane.add(right, stretch="always")

    def _build_status(self):
        self.status_var = tk.StringVar(value="Prêt")
        status = tk.Label(
            self.root, textvariable=self.status_var, anchor="w",
            relief=tk.SUNKEN, bd=1, font=("Segoe UI", 9),
        )
        status.pack(side=tk.BOTTOM, fill=tk.X)

    # ---- Output helpers ----

    def _clear_output(self):
        self.output.config(state=tk.NORMAL)
        self.output.delete("1.0", tk.END)
        self.output.config(state=tk.DISABLED)

    def _append_output(self, text, tag=None):
        self.output.config(state=tk.NORMAL)
        self.output.insert(tk.END, text, tag)
        self.output.see(tk.END)
        self.output.config(state=tk.DISABLED)

    # ---- File operations ----

    def open_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("SPL source", "*.spl"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.editor.delete("1.0", tk.END)
        self.editor.insert("1.0", content)
        self.current_file = path
        self.root.title(f"SPL IDE — {os.path.basename(path)}")
        self.status_var.set(f"Ouvert : {path}")

    def save_file(self):
        if self.current_file:
            self._write_file(self.current_file)
        else:
            self.save_file_as()

    def save_file_as(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".spl",
            filetypes=[("SPL source", "*.spl"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        self._write_file(path)

    def _write_file(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.editor.get("1.0", tk.END))
        self.current_file = path
        self.root.title(f"SPL IDE — {os.path.basename(path)}")
        self.status_var.set(f"Enregistré : {path}")

    # ---- Assemble / Run ----

    def assemble(self):
        self._clear_output()
        source = self.editor.get("1.0", tk.END)

        with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
            f.write(source)
            spl_path = f.name
        rom_path = spl_path.replace(".spl", ".rom")

        try:
            result = subprocess.run(
                [sys.executable, ASM, spl_path, rom_path],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                self._append_output(f"ERREUR D'ASSEMBLAGE\n{result.stderr}")
                self.status_var.set("Assemblage échoué")
                return None

            self._append_output(f"{result.stdout}")

            # Show hex dump of bytecode
            with open(rom_path, "rb") as f:
                data = f.read()
            self._append_output(self._hex_dump(data))
            self.status_var.set(f"Assemblé : {len(data)} octets")
            return rom_path

        except Exception as e:
            self._append_output(f"Erreur : {e}\n")
            self.status_var.set("Erreur")
            return None
        finally:
            os.unlink(spl_path)

    def assemble_and_run(self):
        rom_path = self.assemble()
        if rom_path is None:
            return

        self._append_output("\n--- Exécution ---\n\n")

        try:
            result = subprocess.run(
                [sys.executable, VM, rom_path],
                capture_output=True, timeout=5,
            )
            stdout = result.stdout.decode("utf-8", errors="replace")
            stderr = result.stderr.decode("utf-8", errors="replace")

            if stdout:
                self._append_output(stdout)
            if result.returncode != 0:
                self._append_output(f"\n{stderr}")
                self.status_var.set(f"VM terminée avec erreur (code {result.returncode})")
            else:
                self.status_var.set("Exécution terminée")

        except subprocess.TimeoutExpired:
            self._append_output("\nTimeout : exécution interrompue après 5 s\n")
            self.status_var.set("Timeout")
        except Exception as e:
            self._append_output(f"\nErreur : {e}\n")
            self.status_var.set("Erreur")
        finally:
            if os.path.exists(rom_path):
                os.unlink(rom_path)

    # ---- Hex dump ----

    @staticmethod
    def _hex_dump(data):
        lines = ["\nBytecode :\n"]
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            lines.append(f"  {i:04X}  {hex_part:<48s}  {ascii_part}\n")
        return "".join(lines)


def main():
    root = tk.Tk()
    SplIDE(root)
    root.mainloop()


if __name__ == "__main__":
    main()
