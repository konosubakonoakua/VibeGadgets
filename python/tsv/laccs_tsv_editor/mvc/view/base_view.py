import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os


class BaseView:
    """Base class for all views, providing common UI functionality"""

    def __init__(self, root=None):
        self.root = root or tk.Tk()
        self.popups = []

    def create_label(self, parent, text, font=None, **kwargs):
        """Create a standard label widget"""
        return tk.Label(parent, text=text, font=font, **kwargs)

    def create_button(self, parent, text, command, width=None, **kwargs):
        """Create a standard button widget"""
        button = tk.Button(parent, text=text, command=command, width=width, **kwargs)
        return button

    def create_entry(self, parent, variable=None, width=None, **kwargs):
        """Create a standard entry widget"""
        return tk.Entry(parent, textvariable=variable, width=width, **kwargs)

    def create_frame(self, parent, **kwargs):
        """Create a standard frame widget"""
        return tk.Frame(parent, **kwargs)

    def create_treeview(self, parent, columns, show="headings"):
        """Create a standard treeview widget"""
        tree = ttk.Treeview(parent, columns=columns, show=show)

        # Configure treeview style
        style = ttk.Style()
        style.configure("Treeview", rowheight=25)
        style.configure("Treeview.Heading", font=("Arial", 10, "bold"))

        return tree

    def create_scrollbar(self, parent, orient, command):
        """Create a standard scrollbar widget"""
        return ttk.Scrollbar(parent, orient=orient, command=command)

    def create_notebook(self, parent):
        """Create a standard notebook widget for tabs"""
        return ttk.Notebook(parent)

    def create_checkbutton(self, parent, text, variable, **kwargs):
        """Create a standard checkbutton widget"""
        return tk.Checkbutton(parent, text=text, variable=variable, **kwargs)

    def create_option_menu(self, parent, variable, *options):
        """Create a standard option menu widget"""
        return tk.OptionMenu(parent, variable, *options)

    def show_message(self, title, message, type="info"):
        """Show a message box"""
        if type == "info":
            messagebox.showinfo(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)
        elif type == "error":
            messagebox.showerror(title, message)
        elif type == "question":
            return messagebox.askyesno(title, message)
        elif type == "yesnocancel":
            return messagebox.askyesnocancel(title, message)

    def create_popup_window(self, title, width=400, height=300):
        """Create a popup window"""
        popup = tk.Toplevel(self.root)
        popup.title(title)
        popup.geometry(f"{width}x{height}")
        popup.resizable(True, True)

        # Center the popup window
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry("+{}+{}".format(x, y))

        # Make popup modal
        popup.transient(self.root)
        popup.grab_set()

        # Add to popups list for tracking
        self.popups.append(popup)

        # Bind close event to remove from popups list
        popup.protocol("WM_DELETE_WINDOW", lambda: self._on_popup_close(popup))

        return popup

    def _on_popup_close(self, popup):
        """Handle popup window close event"""
        if popup in self.popups:
            self.popups.remove(popup)
        popup.destroy()

    def close_all_popups(self):
        """Close all popup windows"""
        # Create a copy to iterate over to avoid modification during iteration
        popups_to_close = list(self.popups)
        for popup in popups_to_close:
            try:
                if popup.winfo_exists():
                    popup.destroy()
            except Exception as e:
                print(f"Error closing popup: {e}")
        # Clear the popups list
        self.popups.clear()

    def get_file_path_dialog(self, title, filetypes=[("All files", "*")]):
        """Open file dialog to select a file"""
        return filedialog.askopenfilename(title=title, filetypes=filetypes)

    def get_save_file_path_dialog(
        self, title, defaultextension="", filetypes=[("All files", "*")]
    ):
        """Open save file dialog to select a file path"""
        return filedialog.asksaveasfilename(
            title=title, defaultextension=defaultextension, filetypes=filetypes
        )

    def get_directory_path_dialog(self, title):
        """Open directory dialog to select a folder"""
        return filedialog.askdirectory(title=title)

    def set_window_title(self, title):
        """Set the main window title"""
        self.root.title(title)

    def run(self):
        """Run the main application loop"""
        if self.root:
            self.root.mainloop()
