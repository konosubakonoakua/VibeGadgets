import tkinter as tk
from tkinter import messagebox, filedialog
import os
import sys
import json
from datetime import datetime

# Import MVC components
from ..model.tsv_file import TSVFile
from ..model.recent_files import RecentFilesManager
from ..view.table_view import TableView
from .file_tab_controller import FileTabController


class MainController:
    """Main controller for the TSV Editor application"""

    def __init__(self, root):
        # Initialize model, view and controller components
        self.root = root

        # Model
        self.recent_files_manager = self._init_recent_files_manager()
        self.backup_enabled = True
        self.lazy_load_threshold = 10  # Default threshold in MB

        # View
        self.view = TableView(root)

        # Controllers
        self.tab_controllers = []
        self.current_tab_controller = None

        # UI variables
        self.backup_var = tk.BooleanVar(value=self.backup_enabled)
        self.lazy_load_var = tk.StringVar(value=f"{self.lazy_load_threshold}M")

        # Active popups
        self.active_popups = []

        # Initialize the application
        self.initialize()

    def _init_recent_files_manager(self):
        """Initialize the recent files manager"""
        # Determine the config path
        if getattr(sys, "frozen", False):
            # Running as executable
            app_dir = os.path.dirname(sys.executable)
        else:
            # Running as script
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        config_dir = os.path.join(app_dir, ".config")
        os.makedirs(config_dir, exist_ok=True)
        recent_files_path = os.path.join(config_dir, "recent_files.json")

        return RecentFilesManager(recent_files_path)

    def initialize(self):
        """Initialize the application"""
        # Setup UI components
        self.setup_ui()

        # Load recent files
        self.recent_files = self.recent_files_manager.get_recent_files()

        # Show history dashboard if there are recent files, otherwise create a new tab
        if self.recent_files:
            self.show_history_dashboard()
        else:
            self.new_tab()

    def setup_ui(self):
        """Setup the UI components"""
        # Add buttons to the button frame
        self.view.add_file_operations_buttons(
            self.new_tab,  # New button callback
            self.open_file_dialog,  # Open button callback
            self.save_data,  # Save button callback
            self.save_as_data,  # Save As button callback
        )

        # Add edit operation buttons
        self.view.add_edit_operations_buttons(
            self.add_row,  # Add Row button callback
            self.delete_row,  # Delete Row button callback
        )

        # Add auto backup checkbox
        self.view.add_backup_checkbox(
            self.backup_var,
            lambda: setattr(self, "backup_enabled", self.backup_var.get()),
        )

        # Add lazy load threshold setting
        threshold_options = ["1M", "5M", "10M", "20M", "50M", "100M"]
        self.view.add_lazy_load_setting(
            self.lazy_load_var, threshold_options, self._update_lazy_load_threshold
        )

        # Bind tab events
        self.view.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.view.notebook.bind("<Double-1>", self.on_tab_double_click)
        self.view.notebook.bind("<Button-2>", self.on_tab_middle_click)

        # Bind application shortcuts
        self.bind_application_shortcuts()

        # Initialize status bar
        self.setup_status_bar()

    def setup_status_bar(self):
        """Setup the status bar"""
        # This is a placeholder - in a real implementation, you'd create a status bar
        pass

    def bind_application_shortcuts(self):
        """Bind global application shortcuts"""
        # Ctrl+N - New file
        self.root.bind("<Control-n>", lambda event: self.new_tab())

        # Ctrl+O - Open file
        self.root.bind("<Control-o>", lambda event: self.open_file_dialog())

        # Ctrl+S - Save file
        self.root.bind("<Control-s>", lambda event: self.save_data())

        # Ctrl+Shift+S - Save As
        self.root.bind("<Control-Shift-S>", lambda event: self.save_as_data())

        # Ctrl+W - Close tab
        self.root.bind("<Control-w>", lambda event: self.close_tab())

        # Ctrl+F - Search
        self.root.bind("<Control-f>", lambda event: self.activate_search())

        # Ctrl+H - Show help
        self.root.bind("<Control-h>", lambda event: self.show_help())

    def _update_lazy_load_threshold(self):
        """Update the lazy load threshold"""
        try:
            # Extract numeric value from the string (e.g., "10M" -> 10)
            value_str = self.lazy_load_var.get()
            if value_str.endswith("M"):
                self.lazy_load_threshold = int(value_str[:-1])
        except ValueError:
            # If parsing fails, default to 10MB
            self.lazy_load_threshold = 10
            self.lazy_load_var.set("10M")

    def new_tab(self):
        """Create a new blank tab"""
        # Create model
        tsv_file = TSVFile()
        tsv_file.lazy_load_threshold = self.lazy_load_threshold

        # Create controller
        tab_controller = FileTabController(tsv_file, self.view, self)

        # Add to tab controllers list
        self.tab_controllers.append(tab_controller)
        self.current_tab_controller = tab_controller

        # Select the new tab
        self.view.select_tab(tab_controller.tab_frame)

        # Update window title
        self.update_title()

    def open_file_dialog(self):
        """Open file dialog to select a file"""
        file_path = self.view.get_file_path_dialog(
            "Open TSV/CSV/TXT File",
            filetypes=[
                ("TSV files", "*.tsv"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if file_path:
            self.open_file(file_path)

    def open_file(self, file_path):
        """Open a file and create a new tab for it"""
        # Check if the file already has a tab open
        for tab_controller in self.tab_controllers:
            if tab_controller.model.filename == file_path:
                # Switch to the existing tab
                self.view.select_tab(tab_controller.tab_frame)
                self.current_tab_controller = tab_controller
                return

        # Create model and load data
        tsv_file = TSVFile()
        tsv_file.lazy_load_threshold = self.lazy_load_threshold
        tsv_file.load_data(file_path)

        # Create controller
        tab_controller = FileTabController(tsv_file, self.view, self)

        # Add to tab controllers list
        self.tab_controllers.append(tab_controller)
        self.current_tab_controller = tab_controller

        # Select the new tab
        self.view.select_tab(tab_controller.tab_frame)

        # Update recent files
        self.recent_files_manager.add_to_recent_files(file_path)

        # Update window title
        self.update_title()

    def save_data(self):
        """Save the current file"""
        if (
            not self.current_tab_controller
            or not self.current_tab_controller.model.filename
        ):
            return self.save_as_data()

        # Create backup if enabled
        if self.backup_enabled:
            self.backup_file(self.current_tab_controller.model.filename)

        # Save the data
        success = self.current_tab_controller.model.save_data()
        if success:
            self.update_title()
            # Update recent files order
            self.recent_files_manager.add_to_recent_files(
                self.current_tab_controller.model.filename
            )

    def save_as_data(self):
        """Save the current file with a new name"""
        if not self.current_tab_controller:
            return False

        # Get current filename or default extension
        current_filename = self.current_tab_controller.model.filename
        default_extension = ".tsv" if not current_filename else ""

        # Open save dialog
        new_file_path = self.view.get_save_file_path_dialog(
            "Save As",
            defaultextension=default_extension,
            filetypes=[
                ("TSV files", "*.tsv"),
                ("CSV files", "*.csv"),
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )

        if new_file_path:
            # Create backup if enabled and this is an existing file
            if self.backup_enabled and self.current_tab_controller.model.filename:
                self.backup_file(self.current_tab_controller.model.filename)

            # Save the data
            success = self.current_tab_controller.model.save_as_data(new_file_path)
            if success:
                # Update tab title
                tab_name = os.path.basename(new_file_path)
                self.view.update_tab_title(
                    self.current_tab_controller.tab_frame, tab_name
                )

                # Update window title
                self.update_title()

                # Update recent files
                self.recent_files_manager.add_to_recent_files(new_file_path)

                return True

        return False

    def backup_file(self, file_path):
        """Create a backup of the specified file"""
        try:
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(file_path), ".backups")
            os.makedirs(backup_dir, exist_ok=True)

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.basename(file_path)
            name, ext = os.path.splitext(base_name)
            backup_filename = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)

            # Copy file contents
            with open(file_path, "rb") as src, open(backup_path, "wb") as dst:
                dst.write(src.read())

        except Exception as e:
            print(f"Error creating backup: {str(e)}")

    def restore_backup(self):
        """Restore a file from backup"""
        if (
            not self.current_tab_controller
            or not self.current_tab_controller.model.filename
        ):
            messagebox.showwarning("Warning", "No file opened in this tab")
            return

        # Get backup directory
        backup_dir = os.path.join(
            os.path.dirname(self.current_tab_controller.model.filename), ".backups"
        )

        if not os.path.exists(backup_dir):
            messagebox.showinfo("Info", "No backups found for this file")
            return

        # Get list of backup files
        base_name = os.path.basename(self.current_tab_controller.model.filename)
        name, ext = os.path.splitext(base_name)
        backup_files = []

        for filename in os.listdir(backup_dir):
            if filename.startswith(name) and filename.endswith(ext):
                # Extract timestamp from filename
                timestamp_str = filename[len(name) + 1 : -len(ext)]
                try:
                    timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    backup_files.append((timestamp, filename))
                except ValueError:
                    # Not a valid backup file with timestamp
                    pass

        if not backup_files:
            messagebox.showinfo("Info", "No valid backups found for this file")
            return

        # Sort backup files by timestamp (newest first)
        backup_files.sort(reverse=True, key=lambda x: x[0])

        # Show selection dialog
        backup_window = self.view.create_popup_window(
            "Restore Backup", width=500, height=300
        )

        # Create listbox with scrollbar
        frame = self.view.create_frame(backup_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Vertical scrollbar
        v_scrollbar = self.view.create_scrollbar(frame, tk.VERTICAL, None)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Create listbox
        backup_listbox = tk.Listbox(
            frame, yscrollcommand=v_scrollbar.set, width=50, height=10
        )
        backup_listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        v_scrollbar.config(command=backup_listbox.yview)

        # Populate listbox
        for timestamp, filename in backup_files:
            display_text = f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {filename}"
            backup_listbox.insert(tk.END, display_text)

        # Select the first item by default
        if backup_listbox.size() > 0:
            backup_listbox.selection_set(0)

        # Create button frame
        button_frame = self.view.create_frame(backup_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        # OK button
        def on_ok():
            selection = backup_listbox.curselection()
            if selection:
                # Get selected backup
                timestamp, filename = backup_files[selection[0]]
                backup_path = os.path.join(backup_dir, filename)

                # Ask for confirmation
                if messagebox.askyesno(
                    "Confirm Restore",
                    f"Are you sure you want to restore from this backup?\n{filename}",
                ):
                    # Restore from backup
                    if self.current_tab_controller.model.restore_from_backup(
                        backup_path
                    ):
                        # Refresh the table
                        self.current_tab_controller.populate_table()
                        messagebox.showinfo("Success", "File restored from backup")
                    else:
                        messagebox.showerror("Error", "Failed to restore from backup")

                # Close the window
                backup_window.destroy()

        ok_button = self.view.create_button(button_frame, "Restore", on_ok, width=10)
        ok_button.pack(side=tk.RIGHT, padx=5)

        # Cancel button
        cancel_button = self.view.create_button(
            button_frame, "Cancel", backup_window.destroy, width=10
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)

    def add_row(self):
        """Add a new row to the current table"""
        if self.current_tab_controller:
            self.current_tab_controller.add_row()

    def delete_row(self):
        """Delete selected rows from the current table"""
        if self.current_tab_controller:
            self.current_tab_controller.delete_row()

    def close_tab(self):
        """Close the current tab"""
        if not self.current_tab_controller:
            return

        # Check if there are unsaved changes
        if self.current_tab_controller.model.modified:
            response = messagebox.askyesnocancel(
                "Save Changes", "Do you want to save changes to this file?"
            )
            if response is None:  # Cancel
                return
            if response:  # Yes
                if self.current_tab_controller.model.filename:
                    self.save_data()
                else:
                    if not self.save_as_data():
                        return

        # Remove the tab controller
        self.tab_controllers.remove(self.current_tab_controller)

        # Close the tab in the view
        self.view.close_tab(self.current_tab_controller.tab_frame)

        # Update current tab
        if self.tab_controllers:
            self.current_tab_controller = self.tab_controllers[0]
            self.view.select_tab(self.current_tab_controller.tab_frame)
        else:
            self.current_tab_controller = None
            self.new_tab()  # Create a new blank tab if all are closed

        # Update window title
        self.update_title()

    def on_tab_changed(self, event):
        """Handle tab change event"""
        if not self.view.notebook.tabs():
            self.current_tab_controller = None
            return

        # Get the selected tab index
        current_index = self.view.notebook.index(self.view.notebook.select())

        # Update current_tab_controller based on index
        if 0 <= current_index < len(self.tab_controllers):
            self.current_tab_controller = self.tab_controllers[current_index]
            self.update_title()

    def on_tab_double_click(self, event):
        """Handle double click on tab to close other tabs"""
        # Check if event is on a tab header
        try:
            # Get the clicked tab's index
            x, y = event.x, event.y
            tab_idx = self.view.notebook.index("@%d,%d" % (x, y))
            if tab_idx is not None:
                self.close_other_tabs(tab_idx)
        except tk.TclError:
            # Event not on a tab header, do nothing
            pass

    def on_tab_middle_click(self, event):
        """Handle middle mouse button click on tab to close current tab"""
        # Check if event is on a tab header
        try:
            # Get the clicked tab's index
            x, y = event.x, event.y
            tab_idx = self.view.notebook.index("@%d,%d" % (x, y))
            if tab_idx is not None and 0 <= tab_idx < len(self.tab_controllers):
                # Save the current tab index
                current_idx = self.view.notebook.index(self.view.notebook.select())

                # If the clicked tab is the current tab, just close it
                if tab_idx == current_idx:
                    self.close_tab()
                else:
                    # If the clicked tab is not the current tab, select it first then close it
                    self.view.select_tab(self.tab_controllers[tab_idx].tab_frame)
                    self.current_tab_controller = self.tab_controllers[tab_idx]
                    self.close_tab()
        except tk.TclError:
            # Event not on a tab header, do nothing
            pass

    def close_other_tabs(self, keep_index):
        """Close all tabs except the one at the given index"""
        if len(self.tab_controllers) <= 1:
            return

        # Check if there are unsaved changes in any tab
        unsaved_tabs = [
            i
            for i, tab_controller in enumerate(self.tab_controllers)
            if i != keep_index and tab_controller.model.modified
        ]

        if unsaved_tabs:
            response = messagebox.askyesnocancel(
                "Save Changes",
                "There are unsaved changes in other tabs. Do you want to save before closing?",
            )
            if response is None:  # Cancel
                return
            if response:  # Yes
                for i in unsaved_tabs:
                    if self.tab_controllers[i].model.filename:
                        # Temporarily set current_tab to save
                        old_current = self.current_tab_controller
                        self.current_tab_controller = self.tab_controllers[i]
                        self.save_data()
                        self.current_tab_controller = old_current
                    else:
                        # File has no name, can't save
                        if not messagebox.askyesno(
                            "Save As",
                            f"File '{os.path.basename(self.tab_controllers[i].model.filename) if self.tab_controllers[i].model.filename else 'Untitled'}' has no name. Would you like to save it?",
                        ):
                            # User chose not to save, proceed with closing
                            pass
                        else:
                            # Temporarily set current_tab to save as
                            old_current = self.current_tab_controller
                            self.current_tab_controller = self.tab_controllers[i]
                            if not self.save_as_data():
                                # Save as cancelled, abort closing other tabs
                                self.current_tab_controller = old_current
                                return
                            self.current_tab_controller = old_current

        # Close all tabs except the one to keep
        tabs_to_close = [i for i in range(len(self.tab_controllers)) if i != keep_index]
        # Close from last to first to avoid index issues
        for i in reversed(tabs_to_close):
            self.view.close_tab(self.tab_controllers[i].tab_frame)
            del self.tab_controllers[i]

        # Update current tab
        self.current_tab_controller = self.tab_controllers[0]
        self.update_title()

    def show_history_dashboard(self):
        """Show history dashboard with recently opened files"""
        # Get recent files
        recent_files = self.recent_files_manager.get_recent_files()

        # Create dashboard
        dashboard, recent_files_listbox, buttons_frame = (
            self.view.create_history_dashboard(recent_files)
        )

        # Add this popup to the active popups list
        self.active_popups.append(dashboard)

        # Bind close event
        dashboard.protocol("WM_DELETE_WINDOW", lambda: self._remove_popup(dashboard))

        # File operations group
        file_group_frame = self.view.create_frame(buttons_frame)
        file_group_frame.pack(side=tk.LEFT, padx=5)

        file_label = self.view.create_label(
            file_group_frame, "File Operations:", font=("Arial", 10, "bold")
        )
        file_label.pack(side=tk.LEFT, padx=2)

        file_buttons_frame = self.view.create_frame(file_group_frame)
        file_buttons_frame.pack(side=tk.LEFT)

        # Open button
        open_button = self.view.create_button(
            file_buttons_frame,
            "Open Selected",
            lambda: self.open_selected_file(
                dashboard, recent_files_listbox, recent_files
            ),
            width=15,
        )
        open_button.pack(side=tk.LEFT, padx=5)

        # New file button
        new_button = self.view.create_button(
            file_buttons_frame,
            "New File",
            lambda: self.create_new_file(dashboard),
            width=15,
        )
        new_button.pack(side=tk.LEFT, padx=5)

        # Navigation group
        nav_group_frame = self.view.create_frame(buttons_frame)
        nav_group_frame.pack(side=tk.LEFT, padx=5)

        nav_label = self.view.create_label(
            nav_group_frame, "Navigation:", font=("Arial", 10, "bold")
        )
        nav_label.pack(side=tk.LEFT, padx=2)

        nav_buttons_frame = self.view.create_frame(nav_group_frame)
        nav_buttons_frame.pack(side=tk.LEFT)

        # Browse button
        browse_button = self.view.create_button(
            nav_buttons_frame,
            "Browse Files",
            lambda: self.browse_files(dashboard),
            width=15,
        )
        browse_button.pack(side=tk.LEFT, padx=5)

        # Open Folder button
        open_folder_button = self.view.create_button(
            nav_buttons_frame,
            "Open Folder",
            lambda: self.open_folder_dialog(dashboard),
            width=15,
        )
        open_folder_button.pack(side=tk.LEFT, padx=5)

        # History management
        history_group_frame = self.view.create_frame(buttons_frame)
        history_group_frame.pack(side=tk.RIGHT, padx=5)

        history_label = self.view.create_label(
            history_group_frame, "History Management:", font=("Arial", 10, "bold")
        )
        history_label.pack(side=tk.LEFT, padx=2)

        history_buttons_frame = self.view.create_frame(history_group_frame)
        history_buttons_frame.pack(side=tk.LEFT)

        # Clear history button
        clear_button = self.view.create_button(
            history_buttons_frame, "Clear History", self.clear_history, width=15
        )
        clear_button.pack(side=tk.LEFT, padx=5)

        # Bind double click to open file
        recent_files_listbox.bind(
            "<Double-1>",
            lambda event: self.open_selected_file(
                dashboard, recent_files_listbox, recent_files
            ),
        )

        # Bind ESC to close dashboard
        dashboard.bind("<Escape>", lambda event: dashboard.destroy())

    def open_selected_file(self, dashboard, listbox, recent_files):
        """Open the selected files from the history dashboard"""
        selection = listbox.curselection()
        if selection:
            dashboard.destroy()

            # Process selected files
            files_to_open = []
            invalid_files = []

            # First collect all valid files and identify invalid ones
            for index in selection:
                if 0 <= index < len(recent_files):
                    file_path = recent_files[index]
                    if os.path.exists(file_path):
                        files_to_open.append(file_path)
                    else:
                        invalid_files.append(file_path)
                        # Remove non-existent file from recent files
                        self.recent_files_manager.remove_from_recent_files(file_path)

            # Show error message for invalid files
            if invalid_files:
                if len(invalid_files) == 1:
                    messagebox.showerror("Error", f"File not found: {invalid_files[0]}")
                else:
                    messagebox.showerror(
                        "Error", f"Files not found: {', '.join(invalid_files)}"
                    )

            # Open all valid files
            for file_path in files_to_open:
                self.open_file(file_path)

            # If no files were opened and there are still recent files, show dashboard again
            if not files_to_open and self.recent_files_manager.get_recent_files():
                self.show_history_dashboard()
            elif not files_to_open and not self.recent_files_manager.get_recent_files():
                self.open_file_dialog()

    def create_new_file(self, dashboard):
        """Create a new file"""
        dashboard.destroy()
        self.new_tab()
        messagebox.showinfo(
            "New File", "New file created. Use 'Save As' to save your work."
        )

    def browse_files(self, dashboard):
        """Browse for files"""
        dashboard.destroy()
        self.open_file_dialog()

    def open_folder_dialog(self, dashboard=None):
        """Open folder selection dialog and open all tsv/csv/txt files in the selected folder"""
        folder_path = self.view.get_directory_path_dialog(
            "Select Folder containing TSV/CSV/TXT Files"
        )

        if folder_path:
            # Close dashboard if provided
            if dashboard:
                dashboard.destroy()

            # Define supported file extensions
            supported_extensions = [".tsv", ".csv", ".txt"]
            files_opened = False

            # Iterate through all files in the selected folder
            for filename in os.listdir(folder_path):
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext in supported_extensions:
                    file_path = os.path.join(folder_path, filename)
                    self.open_file(file_path)
                    files_opened = True

            if not files_opened:
                messagebox.showinfo(
                    "Info", "No TSV/CSV/TXT files found in the selected folder."
                )

            return files_opened

        return False

    def clear_history(self):
        """Clear the recent files history"""
        if messagebox.askyesno(
            "Confirm", "Are you sure you want to clear all recent file history?"
        ):
            self.recent_files_manager.clear_recent_files()
            # If history dashboard is open, refresh it
            # This would require tracking the dashboard state, which is beyond the scope here

    def toggle_auto_backup(self):
        """Toggle auto backup functionality"""
        self.backup_enabled = not self.backup_enabled
        self.backup_var.set(self.backup_enabled)
        status = "enabled" if self.backup_enabled else "disabled"
        messagebox.showinfo("Auto Backup", f"Auto backup has been {status}")

    def activate_search(self):
        """Activate search functionality in the current tab"""
        # This would focus the search box in the current tab
        pass

    def show_help(self):
        """Show the help window"""
        # Create help window
        help_window, help_text = self.view.create_help_window()

        # Add this popup to the active popups list
        self.active_popups.append(help_window)

        # Bind close event
        help_window.protocol(
            "WM_DELETE_WINDOW", lambda: self._remove_popup(help_window)
        )

        # Configure help text
        help_text.config(state=tk.NORMAL)

        # Add help content
        help_content = """
        LACCS TSV Editor
        Version: 1.0
        
        A simple yet powerful editor for TSV, CSV, and text files.
        
        Features:
        - Tabbed interface for working with multiple files
        - Support for large files with lazy loading
        - Real-time search with fuzzy matching
        - Basic editing operations (add, edit, delete rows)
        - Auto backup functionality
        - Recent files history
        
        Keyboard Shortcuts:
        Ctrl+N: New file
        Ctrl+O: Open file
        Ctrl+S: Save file
        Ctrl+Shift+S: Save As
        Ctrl+W: Close tab
        Ctrl+F: Search
        Ctrl+H: Show help
        
        For more information, visit our documentation.
        """

        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)

        # Add close button
        button_frame = self.view.create_frame(help_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        close_button = self.view.create_button(
            button_frame, "Close", help_window.destroy, width=10
        )
        close_button.pack(side=tk.RIGHT, padx=5)

    def cancel_all_operations(self):
        """Cancel all operations and close all popups"""
        # Create a copy to iterate over to avoid modification during iteration
        popups_to_close = list(self.active_popups)
        for popup in popups_to_close:
            self._remove_popup(popup)

    def _remove_popup(self, popup):
        """Remove a popup from the active popups list and destroy it"""
        if popup in self.active_popups:
            self.active_popups.remove(popup)

        # Destroy the popup window
        try:
            if popup.winfo_exists():
                popup.destroy()
        except Exception as e:
            print(f"Error destroying popup: {e}")

    def update_title(self):
        """Update the window title based on the current file"""
        base_title = "LACCS TSV Editor"

        if self.current_tab_controller:
            if self.current_tab_controller.model.filename:
                filename = os.path.basename(self.current_tab_controller.model.filename)
                modified = "*" if self.current_tab_controller.model.modified else ""
                self.view.set_window_title(f"{filename}{modified} - {base_title}")
            else:
                modified = "*" if self.current_tab_controller.model.modified else ""
                self.view.set_window_title(f"Untitled{modified} - {base_title}")
        else:
            self.view.set_window_title(base_title)

    def update_status_bar(self, message):
        """Update the status bar with a message"""
        # This is a placeholder for updating a status bar
        pass
