import tkinter as tk
import sys
import os

# Add the parent directory to the path so we can import the mvc module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mvc.controller.main_controller import MainController


class TSVEditorApp:
    """Main application class for the TSV Editor"""

    def __init__(self):
        # Initialize the main window
        self.root = tk.Tk()
        self.root.title("LACCS TSV Editor")

        # Set minimum window size
        self.root.minsize(800, 600)

        # Configure window to expand
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Initialize main controller
        self.main_controller = MainController(self.root)

    def run(self):
        """Run the main application loop"""
        # Center the window on the screen
        self._center_window()

        # Start the main loop
        self.root.mainloop()

    def _center_window(self):
        """Center the window on the screen"""
        # Update window to get correct dimensions
        self.root.update_idletasks()

        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        # Get window dimensions
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()

        # Calculate position to center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2

        # Set window position
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")


if __name__ == "__main__":
    # Create and run the application
    app = TSVEditorApp()
    app.run()
