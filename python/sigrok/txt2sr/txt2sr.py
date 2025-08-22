import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import subprocess
import numpy as np
import os
import threading

from np2srzip.np2srzip import np2srzip


class SRZipExporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("TXT to SRZip Converter")

        # ==== Top frame for file selection ====
        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(top_frame, text="Data File:").pack(side="left")
        self.file_entry = tk.Entry(top_frame, width=100)
        self.file_entry.pack(side="left", padx=5)
        tk.Button(top_frame, text="Browse", command=self.browse_file).pack(
            side="left", padx=5
        )

        # ==== Output file frame ====
        out_frame = tk.Frame(root)
        out_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(out_frame, text="Output SRZip:").pack(side="left")
        self.output_entry = tk.Entry(out_frame, width=100)
        self.output_entry.pack(side="left", padx=5)
        self.output_entry.insert(0, "output.sr")
        tk.Button(out_frame, text="Browse", command=self.browse_output).pack(
            side="left", padx=5
        )

        # ==== Frame for sample rate ====
        rate_frame = tk.Frame(root)
        rate_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(rate_frame, text="Sample Rate:").pack(side="left")
        self.samplerate_entry = tk.Entry(rate_frame, width=20)
        self.samplerate_entry.insert(0, "100 KHz")
        self.samplerate_entry.pack(side="left", padx=5)

        # ==== Frame for data type selection ====
        type_frame = tk.Frame(root)
        type_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(type_frame, text="Data Type:").pack(side="left")
        self.data_type = tk.StringVar(value="logic")
        self.type_combo = ttk.Combobox(
            type_frame,
            textvariable=self.data_type,
            values=[
                "logic",
                "analog",
            ],  # logic: digital signals, analog: continuous waveforms
            state="readonly",
            width=10,
        )
        self.type_combo.pack(side="left", padx=5)

        # ==== Frame for buttons ====
        button_frame = tk.Frame(root)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.export_btn = tk.Button(
            button_frame, text="Export SRZip", command=self.export_sr
        )
        self.export_btn.pack(side="left", padx=5)

        tk.Button(
            button_frame, text="Open PulseView", command=self.open_pulseview
        ).pack(side="left", padx=5)

        # auto-open checkbox
        self.auto_open_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            button_frame, text="Auto-open in PulseView", variable=self.auto_open_var
        ).pack(side="left", padx=10)

        # ==== Progress bar ====
        self.progress = ttk.Progressbar(button_frame, mode="indeterminate", length=200)
        self.progress.pack(side="left", padx=10)

        # ==== Log area ====
        log_frame = tk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)

        tk.Label(log_frame, text="Log:").pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(
            log_frame, width=120, height=10, state="disabled"
        )
        self.log_area.pack(fill="both", expand=True)

        self.data_file = None
        self.output_file = "output.sr"

    def browse_file(self):
        """Browse and select input TXT file"""
        file = filedialog.askopenfilename(
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if file:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, file)
            self.data_file = file
            self.log(f"Selected file: {file}")

            # set default output file
            base, _ = os.path.splitext(file)
            default_output = base + ".sr"
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, default_output)
            self.output_file = default_output
            self.log(f"Default output file: {default_output}")

    def browse_output(self):
        """Browse and select output SRZip file"""
        file = filedialog.asksaveasfilename(
            defaultextension=".sr",
            filetypes=[("SRZip Files", "*.sr"), ("All Files", "*.*")],
        )
        if file:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, file)
            self.output_file = file
            self.log(f"Output file set to: {file}")

    def export_sr(self):
        """Start exporting SRZip in a separate thread"""
        if not self.data_file:
            messagebox.showerror("Error", "Please select a data file.")
            return

        self.output_file = self.output_entry.get().strip()
        if not self.output_file:
            messagebox.showerror("Error", "Please select output file.")
            return

        # disable button while exporting
        self.export_btn.config(state="disabled")
        self.progress.start(10)
        self.log("Starting SRZip export...")

        # run in separate thread
        t = threading.Thread(target=self._do_export_sr)
        t.start()

    def _do_export_sr(self):
        """Perform the actual export logic or analog depending on selection"""
        try:
            raw_values = np.genfromtxt(self.data_file, dtype=float, comments="=")
            samplerate = self.samplerate_entry.get().strip()

            if self.data_type.get() == "logic":
                # Logic: convert values >0 into 1, others 0
                logic = (raw_values > 0).astype(np.uint8).reshape(-1, 1)
                np2srzip(logic, None, self.output_file, samplerate)
            else:
                # Analog: keep raw float values
                analog = raw_values.astype(np.float32).reshape(-1, 1)
                np2srzip(None, analog, self.output_file, samplerate)

            self._finish_export(f"Exported SRZip: {self.output_file}", success=True)
        except Exception as e:
            self._finish_export(f"Error exporting SRZip: {e}", success=False)

    def _finish_export(self, message, success=False):
        """Schedule UI update after background export finishes"""
        self.root.after(0, lambda: self._update_ui_after_export(message, success))

    def _update_ui_after_export(self, message, success):
        """Update UI components after export"""
        self.progress.stop()
        self.log(message)
        self.export_btn.config(state="normal")

        if success and self.auto_open_var.get():
            self.open_pulseview()

    def open_pulseview(self):
        """Open exported SRZip file with PulseView"""
        if not os.path.exists(self.output_file):
            messagebox.showerror("Error", "No SRZip file found. Please export first.")
            return

        try:
            subprocess.Popen(["pulseview", self.output_file])
            self.log(f"Opened PulseView with {self.output_file}")
        except Exception as e:
            self.log(f"Error opening PulseView: {e}")

    def log(self, message):
        """Append a message to the log area"""
        self.log_area.config(state="normal")
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = SRZipExporterApp(root)
    root.mainloop()
