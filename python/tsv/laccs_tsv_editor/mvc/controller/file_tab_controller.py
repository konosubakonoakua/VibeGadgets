import tkinter as tk
from tkinter import messagebox
import os


class FileTabController:
    """Controller for managing a single file tab"""

    def __init__(self, model, view, parent_controller=None):
        self.model = model  # TSVFile model
        self.view = view  # The view component for this tab
        self.parent_controller = parent_controller

        # UI elements
        self.tab_frame = None
        self.tree = None
        self.search_var = None
        self.threshold_var = None
        self.search_column_var = None
        self.edit_window = None

        # Selection state
        self.selection_mode = False
        self.selection_start = -1
        self.selection_end = -1

        # Initialize lazy loading parameters
        self.current_chunk = 0
        self.chunk_size = 1000
        self.visible_rows = set()

        # Setup the tab
        self.setup_tab()

    def setup_tab(self):
        """Setup the tab UI and bindings"""
        # Create tab frame
        tab_name = (
            os.path.basename(self.model.filename) if self.model.filename else "Untitled"
        )
        self.tab_frame = self.view.create_tab(tab_name)

        # Create search widgets
        self.search_var, self.threshold_var, self.search_column_var, _ = (
            self.view.create_search_widgets(self.tab_frame)
        )

        # Bind search events
        self.search_var.trace_add("write", lambda *args: self.real_time_search())
        self.threshold_var.trace_add("write", lambda *args: self.real_time_search())

        # If there's data, create table
        if self.model.headers:
            self.create_table()

    def create_table(self):
        """Create the table widget and populate with data"""
        # Create table widgets
        self.tree, _ = self.view.create_table_widgets(
            self.tab_frame, self.model.headers
        )

        # Bind events
        self.bind_events()

        # Populate the table
        self.populate_table()

    def bind_events(self):
        """Bind events to the table widget"""
        # Mouse events
        self.tree.bind("<Button-1>", self.handle_mouse_click)
        self.tree.bind("<Double-1>", self.handle_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<MouseWheel>", self.on_mouse_wheel)

        # Key events
        self.tree.bind("<KeyPress>", self.on_key_press)

        # Configure event for scrolling
        self.tree.bind("<Configure>", self.on_tree_configure)

    def populate_table(self, search_data=None):
        """Populate the table with data, supporting lazy loading"""
        if search_data is not None:
            # If search data is provided, use that
            self.view.populate_table(self.tree, search_data, self.model.headers)
        else:
            # Otherwise, load from model or file
            if self.model.is_large_file:
                # For large files, load only visible chunk
                chunk_data = self.model.load_chunk(
                    self.current_chunk * self.chunk_size, self.chunk_size
                )
                self.view.populate_table(self.tree, chunk_data, self.model.headers)
                # Update visible rows
                self.update_visible_rows()
            else:
                # For small files, load all data
                self.view.populate_table(self.tree, self.model.data, self.model.headers)

    def handle_mouse_click(self, event):
        """Handle mouse click events"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            if item:
                # Convert item to integer index
                try:
                    idx = int(item)

                    if self.selection_mode:
                        # In selection mode
                        if self.selection_start == -1:
                            # First selection
                            self.selection_start = idx
                            self.selection_end = idx
                        else:
                            # Update selection end
                            self.selection_end = idx

                        # Highlight selected items
                        self.highlight_selection()
                except ValueError:
                    pass

    def handle_double_click(self, event):
        """Handle double click events"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            # Edit the clicked cell
            self.edit_cell(event)

    def show_context_menu(self, event):
        """Show context menu on right click"""
        # Select the item under the cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)

            # Create context menu
            context_menu = tk.Menu(self.tab_frame, tearoff=0)
            context_menu.add_command(label="Copy", command=self.copy_rows)
            context_menu.add_command(label="Cut", command=self.cut_rows)
            context_menu.add_command(label="Paste", command=self.paste_rows)
            context_menu.add_separator()
            context_menu.add_command(label="Edit", command=lambda: self.edit_row(event))
            context_menu.add_command(label="Delete", command=self.delete_row)

            # Show menu at click position
            context_menu.post(event.x_root, event.y_root)

            # Cleanup menu after selection
            context_menu.bind("<Unmap>", lambda e: context_menu.destroy())

    def real_time_search(self):
        """Perform real-time search based on search box input"""
        search_term = self.search_var.get().strip()
        if not search_term:
            self.populate_table()
            return

        # Get search parameters
        threshold = self.threshold_var.get()
        search_column = self.search_column_var.get()

        # Perform search
        search_data = self.model.search_data(search_term, threshold, search_column)

        # Update table with search results
        self.populate_table(search_data)

    def edit_row(self, event, edit_cell=False):
        """Edit the selected row(s)"""
        selection = self.tree.selection()
        if not selection:
            return

        # For multiple selection, we'll only edit the first item
        item = selection[0]
        try:
            idx = int(item)

            if self.model.is_large_file:
                # For large files, we need to find the actual row in the file
                # This is a simplified approach - in a real app, you'd need a way to map
                # the current view to the actual file position
                messagebox.showinfo(
                    "Info", "Editing not supported for large files in this version"
                )
                return

            # Get the row data
            if 0 <= idx < len(self.model.data):
                row_data = self.model.data[idx]

                # Create edit window
                self.edit_window, entry_vars, ok_button = self.view.create_edit_window(
                    "Edit Row", self.model.headers, row_data
                )

                # Configure OK button command
                ok_button.config(command=lambda: self._save_edit(idx, entry_vars))
        except ValueError:
            pass

    def edit_cell(self, event):
        """Edit the clicked cell"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)

            if item and column:
                try:
                    # Convert item to integer index
                    idx = int(item)
                    # Convert column to integer index (strip '#')
                    col_idx = int(column[1:]) - 1

                    if self.model.is_large_file:
                        messagebox.showinfo(
                            "Info",
                            "Editing not supported for large files in this version",
                        )
                        return

                    # Get the row data
                    if 0 <= idx < len(self.model.data) and 0 <= col_idx < len(
                        self.model.headers
                    ):
                        row_data = self.model.data[idx].copy()

                        # Create edit window
                        self.edit_window, entry_vars, ok_button = (
                            self.view.create_edit_window(
                                "Edit Cell",
                                [self.model.headers[col_idx]],
                                [row_data[col_idx]],
                            )
                        )

                        # Configure OK button command
                        ok_button.config(
                            command=lambda: self._save_cell_edit(
                                idx, col_idx, entry_vars
                            )
                        )
                except ValueError:
                    pass

    def _save_edit(self, idx, entry_vars):
        """Save edited row data"""
        # Collect data from entry fields
        new_data = [var.get() for var in entry_vars]

        # Save to model
        if self.model.edit_row(idx, new_data):
            # Update view
            self.populate_table()

            # Close edit window
            if self.edit_window and self.edit_window.winfo_exists():
                self.edit_window.destroy()
                self.edit_window = None

    def _save_cell_edit(self, row_idx, col_idx, entry_vars):
        """Save edited cell data"""
        if not self.model.is_large_file and 0 <= row_idx < len(self.model.data):
            # Get current row data
            row_data = self.model.data[row_idx].copy()

            # Update the specific cell
            if 0 <= col_idx < len(entry_vars):
                row_data[col_idx] = entry_vars[0].get()

                # Save to model
                if self.model.edit_row(row_idx, row_data):
                    # Update view
                    self.populate_table()

                    # Close edit window
                    if self.edit_window and self.edit_window.winfo_exists():
                        self.edit_window.destroy()
                        self.edit_window = None

    def add_row(self):
        """Add a new row to the table using format-specific template"""
        # Prepare row data with template values
        row_data = []
        for header in self.model.headers:
            # Use template value if available, otherwise empty string
            row_data.append(self.model.template.get(header, ""))
        
        # Create edit window with template data
        self.edit_window, entry_vars, ok_button = self.view.create_edit_window(
            "Add Row", self.model.headers, row_data
        )

        # Configure OK button command
        ok_button.config(command=lambda: self._save_new_row(entry_vars))

    def _save_new_row(self, entry_vars):
        """Save a new row"""
        # Collect data from entry fields
        new_data = [var.get() for var in entry_vars]

        # Save to model
        if self.model.add_row(new_data):
            # Update view
            self.populate_table()

            # Close edit window
            if self.edit_window and self.edit_window.winfo_exists():
                self.edit_window.destroy()
                self.edit_window = None

    def delete_row(self):
        """Delete the selected row(s)"""
        selection = self.tree.selection()
        if not selection:
            return

        # Ask for confirmation
        if not messagebox.askyesno(
            "Confirm Delete", "Are you sure you want to delete the selected row(s)?"
        ):
            return

        # For now, we'll only delete the first selected row
        # In a real app, you'd handle multiple selections
        item = selection[0]
        try:
            idx = int(item)

            if self.model.is_large_file:
                messagebox.showinfo(
                    "Info", "Deleting not supported for large files in this version"
                )
                return

            # Delete from model
            if self.model.delete_row(idx):
                # Update view
                self.populate_table()
        except ValueError:
            pass

    def copy_rows(self):
        """Copy selected rows to clipboard"""
        # Implementation would go here
        pass

    def cut_rows(self):
        """Cut selected rows to clipboard"""
        # Implementation would go here
        pass

    def paste_rows(self):
        """Paste rows from clipboard"""
        # Implementation would go here
        pass

    def toggle_selection_mode(self):
        """Toggle selection mode"""
        self.selection_mode = not self.selection_mode
        if not self.selection_mode:
            # Clear selection when exiting selection mode
            self.selection_start = -1
            self.selection_end = -1
            self.clear_selection_highlight()

        # Update UI to indicate selection mode status
        if self.parent_controller:
            self.parent_controller.update_status_bar(
                f"Selection Mode: {'On' if self.selection_mode else 'Off'}"
            )

    def highlight_selection(self):
        """Highlight selected rows"""
        # Clear previous highlights
        self.clear_selection_highlight()

        # Determine selection range
        start = min(self.selection_start, self.selection_end)
        end = max(self.selection_start, self.selection_end)

        # Highlight rows in the range
        for i in range(start, end + 1):
            item = str(i)
            if item in self.tree.get_children():
                self.tree.item(item, tags=("selected",))

        # Configure selected tag style
        self.tree.tag_configure("selected", background="#cce5ff")

    def clear_selection_highlight(self):
        """Clear selection highlights"""
        for item in self.tree.get_children():
            self.tree.item(item, tags=())

    def on_mouse_wheel(self, event):
        """Handle mouse wheel events for scrolling"""
        # This is a placeholder for advanced scrolling handling
        # that would work with the lazy loading mechanism
        pass

    def on_key_press(self, event):
        """Handle key press events"""
        # This is a placeholder for keyboard navigation and shortcuts
        pass

    def on_tree_configure(self, event):
        """Handle treeview configure events"""
        # This is a placeholder for handling resizing events
        pass

    def update_visible_rows(self):
        """Update the set of visible rows"""
        # This would be used with the lazy loading mechanism to determine
        # which parts of the file need to be loaded
        pass
