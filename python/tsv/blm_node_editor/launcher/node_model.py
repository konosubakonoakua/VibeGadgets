import os
import csv
import os
import sys
import tkinter as tk
from tkinter import filedialog


class NodeModel:
    def __init__(self):
        # Initialize with default path - priority to executable directory
        self.tsv_file = None
        self._initialize_default_path()
        self.node_data = []
        self.headers = []
        self.node_statuses = {}
        # Flag to track if user has selected a custom file path
        self.user_selected_path = False
        self.non_local_nodes = []
        self.node_credentials = {}
        self.node_params = {}  # Store node parameters for service startup

    def _initialize_default_path(self):
        """Initialize default path for NODES.tsv with priority to executable directory"""
        # Initialize variables first to prevent NameError if try block fails
        current_dir = os.getcwd()
        exe_dir = os.path.dirname(sys.executable)

        try:
            # Priority 1: Check for file in the current working directory
            current_dir_path = os.path.join(current_dir, "FileDB", "NODES.tsv")
            if os.path.exists(current_dir_path):
                self.tsv_file = current_dir_path
                return

            # Priority 2: Check for file in the same directory as the executable
            exe_same_dir_path = os.path.join(exe_dir, "FileDB", "NODES.tsv")
            if os.path.exists(exe_same_dir_path):
                self.tsv_file = exe_same_dir_path
                return

            # If file not found, set path to the expected location but don't create dialog here
            # File selection will be handled in load_node_data which has access to main window
            self.tsv_file = os.path.join(current_dir, "FileDB", "NODES.tsv")

        except Exception:
            # Fallback in case of any error: Set path to current working directory's FileDB first, then executable directory
            if os.path.exists(os.path.join(current_dir, "FileDB")):
                self.tsv_file = os.path.join(current_dir, "FileDB", "NODES.tsv")
            else:
                self.tsv_file = os.path.join(exe_dir, "FileDB", "NODES.tsv")

    def select_external_nodes_file(self, parent=None):
        """Allow user to select an external NODES.tsv file

        Args:
            parent: Optional parent window for the file dialog. If not provided,
                    the dialog will use the default window.

        Returns:
            tuple: (success_flag, message)
        """
        try:
            # Open file dialog for TSV files
            file_path = filedialog.askopenfilename(
                title="Select NODES.tsv File",
                filetypes=[("TSV files", "*.tsv"), ("All files", "*.*")],
                parent=parent,
            )

            if file_path:
                self.tsv_file = file_path
                self.user_selected_path = True
                return True, f"Selected file: {file_path}"
            else:
                return False, "File selection cancelled"
        except Exception as e:
            return False, f"Error selecting file: {str(e)}"

    def load_node_data(self, parent=None):
        """Load node data from TSV file

        Args:
            parent: Optional parent window for dialogs that might be shown
                    during the loading process.

        Returns:
            tuple: (success_flag, message)
        """
        try:
            # Check if the file exists before attempting to open it
            if not os.path.exists(self.tsv_file):
                # If user has selected a custom path but it doesn't exist, ask them to select again
                if self.user_selected_path:
                    result, message = self.select_external_nodes_file(parent=parent)
                    if not result:
                        return False, f"Failed to select valid file: {message}"
                    # Try to load with the new path
                    return self.load_node_data(parent=parent)
                return (
                    False,
                    f"Failed to read file: [Errno 2] No such file or directory: '{self.tsv_file}'",
                )

            with open(self.tsv_file, "r", encoding="utf-8") as file:
                reader = csv.reader(file, delimiter="\t")
                lines = list(reader)

            if not lines:
                return False, "File is empty"

            # First line is headers (remove # sign)
            self.headers = [h.lstrip("#") for h in lines[0]]

            # Load data rows (skip header and empty rows)
            self.node_data = []
            for row in lines[1:]:
                if any(row):  # Skip empty rows
                    self.node_data.append(row)

            return True, "Successfully loaded node data"
        except Exception as e:
            return False, f"Failed to read file: {str(e)}"

    def save_node_data(self, data):
        """Save node data to TSV file"""
        try:
            # Ensure directory exists if saving to user-selected path
            if self.user_selected_path:
                directory = os.path.dirname(self.tsv_file)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)

            with open(self.tsv_file, "w", encoding="utf-8", newline="") as file:
                writer = csv.writer(file, delimiter="\t")
                # Write header row (add # sign)
                writer.writerow(["#" + h for h in self.headers])
                # Write data rows
                for row in data:
                    writer.writerow(row)

            return True, "Data has been successfully saved"
        except Exception as e:
            return False, f"Failed to save file: {str(e)}"

    def update_non_local_nodes(self, tree_columns, tree_items):
        """Update list of non-local nodes"""
        self.non_local_nodes = []

        # Get indexes of local_ip and node_name columns
        ip_col_index = -1
        name_col_index = -1

        for i, col in enumerate(tree_columns):
            if col.lower() == "local_ip":
                ip_col_index = i
            elif col.lower() == "node_name":
                name_col_index = i

        if ip_col_index == -1 or name_col_index == -1:
            return False, "Error: Could not find required columns"

        # Extract nodes (include localhost)
        for item in tree_items:
            values = list(item)
            if len(values) > max(ip_col_index, name_col_index):
                ip = values[ip_col_index]
                name = values[name_col_index]
                # Skip only nodes with empty IP
                if ip and ip.strip().lower() != "none":
                    self.non_local_nodes.append((name, ip))
                    # Update node status mapping
                    if name not in self.node_statuses:
                        self.node_statuses[name] = {"status": "Unknown"}

        return True, f"{len(self.non_local_nodes)} non-local nodes found"

    def update_node_status(self, node_name, status):
        """Update node status"""
        if node_name not in self.node_statuses:
            self.node_statuses[node_name] = {}
        self.node_statuses[node_name]["status"] = status

    def get_node_status(self, node_name):
        """Get node status"""
        if node_name in self.node_statuses:
            return self.node_statuses[node_name].get("status", "Unknown")
        return "Unknown"

    def get_node_credentials(self, node_name):
        if node_name not in self.node_credentials:
            self.node_credentials[node_name] = {"username": "root", "password": "imp"}
        return (
            self.node_credentials[node_name]["username"],
            self.node_credentials[node_name]["password"],
        )

    def set_node_credentials(self, node_name, username, password):
        self.node_credentials[node_name] = {"username": username, "password": password}

    def get_node_params(self, node_name):
        """Get node parameters for service startup"""
        if node_name not in self.node_params:
            # Set default parameters
            default_node_name = "BDBLM00"
            self.node_params[node_name] = {
                "node_name": default_node_name,
                "device_name": f"HIAF:{default_node_name}",
                "laccs_path": "/opt/LACCS#",  # LACCS installation path
                "ch00": "CH00",
                "ch01": "CH01",
                "ch02": "CH02",
                "ch03": "CH03",
                "ch04": "CH04",
                "ch05": "CH05",
            }
        return self.node_params[node_name]

    def set_node_params(self, node_name, params):
        """Set node parameters for service startup"""
        if node_name not in self.node_params:
            self.node_params[node_name] = {}
        self.node_params[node_name].update(params)
