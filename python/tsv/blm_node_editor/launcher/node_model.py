import os
import csv
import os


class NodeModel:
    def __init__(self):
        # Get TSV file path
        self.tsv_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "FileDB",
            "NODES.tsv",
        )
        self.node_data = []
        self.headers = []
        self.node_statuses = {}
        self.non_local_nodes = []
        self.node_credentials = {}
        self.node_params = {}  # Store node parameters for service startup

    def load_node_data(self):
        """Load node data from TSV file"""
        try:
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
