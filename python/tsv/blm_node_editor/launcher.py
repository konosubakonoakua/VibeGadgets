#!/usr/bin/env python3

import tkinter as tk
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from launcher.node_controller import NodeEditor

if __name__ == "__main__":
    root = tk.Tk()
    root.title("BLM Node Manager")
    root.geometry("1300x1000")
    root.minsize(1300, 800)

    app = NodeEditor(root)

    root.mainloop()
