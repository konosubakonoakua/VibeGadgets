import os
import csv
import json
import datetime
import os

class TSVFile:
    """Model for handling TSV file operations and data manipulation"""
    
    def __init__(self):
        self.data = []
        self.headers = []
        self.filename = None
        self.modified = False
        self.is_large_file = False
        self.lazy_load_threshold = 10  # Default threshold in MB
        self.file_size_threshold = self.lazy_load_threshold * 1024 * 1024  # Default 10MB threshold in bytes
        self.total_rows = 0
        self.loaded_chunks = {}
        self.chunk_size = 100000  # Load 100000 rows per chunk
        self.currently_visible_range = (0, 0)
        
        # Default template data
        self.template = {
            "node_name": "none",
            "local_ip": "192.168.138.138",
            "cluster": "cluster_huizhou",
            "remote_ip": "none",
            "connect_to_nodes": "none",
            "node_type": "compute",
            "data_save_switch": "off",
        }
        
        # Format templates for different file types
        self.format_templates = {
            # PV (Process Variable) format template
            "pv": {
                "node_name": "",
                "pv_name": "",
                "pv_type": "c",
                "cv_name": "",
                "action": "publish",
                "is_readonly": "1",
                "pv_length": "512000",
                "pv_scan_period": "2",
                "precision": "12",
                "unit": "none"
            },
            # Command format template
            "command": {
                "node_name": "",
                "command_name": "",
                "module": "control",
                "command": "call",
                "parameters": "",
                "input_cvs": "none",
                "output_cvs": "none",
                "is_sync": "1",
                "is_check": "1"
            },
            # CV (Control Variable) format template
            "cv": {
                "node_name": "",
                "cv_name": "",
                "cv_type": "d",
                "cv_max_length": "1",
                "set_events": "none",
                "sync_events": "none",
                "update_events": "none",
                "update_period": "-1",
                "cv_code_type": "0"
            },
            # Event format template
            "event": {
                "node_name": "",
                "event_name": "",
                "commands": "",
                "is_lock": "0"
            },
            # Ion format template
            "ion": {
                "ion_name": "",
                "ion_mass_num": "",
                "ion_proton_num": "",
                "ion_charge_num": "1",
                "mass_in_MeV": ""
            }
        }
        
    def detect_format_and_set_template(self):
        """Detect file format based on headers and set appropriate template"""
        # Get headers in lowercase for case-insensitive comparison
        headers_lower = [h.lower().strip() for h in self.headers]
        
        # Check for PV format
        if "pv_name" in headers_lower and "pv_type" in headers_lower:
            self.template = self.format_templates["pv"].copy()
        # Check for Command format
        elif "command_name" in headers_lower and "module" in headers_lower:
            self.template = self.format_templates["command"].copy()
        # Check for CV format
        elif "cv_name" in headers_lower and "cv_type" in headers_lower:
            self.template = self.format_templates["cv"].copy()
        # Check for Event format
        elif "event_name" in headers_lower and "commands" in headers_lower:
            self.template = self.format_templates["event"].copy()
        # Check for Ion format
        elif "ion_name" in headers_lower and "ion_mass_num" in headers_lower:
            self.template = self.format_templates["ion"].copy()
        # Otherwise, keep the default template
        else:
            # Ensure template has all headers
            for header in self.headers:
                if header not in self.template:
                    self.template[header] = ""
    
    def load_data(self, file_path):
        """Load data from TSV file with lazy loading support for large files"""
        self.filename = file_path
        file_size = os.path.getsize(file_path)
        self.is_large_file = file_size > self.file_size_threshold
        
        # Read headers first
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            try:
                self.headers = next(reader)  # Read the first row as headers
                # Count total rows for large files
                if self.is_large_file:
                    self.total_rows = 1  # Count the header row
                    for _ in reader:
                        self.total_rows += 1
            except StopIteration:
                # Empty file, set default headers
                self.headers = ['Column 1']
                self.total_rows = 0
        
        # Detect file format and set appropriate template
        self.detect_format_and_set_template()
        
        if not self.is_large_file:
            # Normal load for smaller files
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter='\t')
                next(reader)  # Skip headers
                self.data = list(reader)
                self.total_rows = len(self.data)
        else:
            # For large files, just read the headers and leave data loading to chunks
            self.data = []
            
            # Display message about large file loading
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()  # Hide the main window
            messagebox.showinfo("Info", f"Loading large file: {os.path.basename(file_path)}\n" \
                               f"Size: {file_size/1024/1024:.2f}MB, Total rows: {self.total_rows}\n" \
                               f"Using lazy loading to improve performance.")
            root.destroy()
        
        self.modified = False
    
    def load_chunk(self, start_row, num_rows):
        """Load a specific chunk of data from the file"""
        if not self.filename:
            return []
        
        result = []
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter='\t')
                # Skip headers
                next(reader)
                
                # Skip to the start row
                for _ in range(start_row):
                    try:
                        next(reader)
                    except StopIteration:
                        break
                
                # Read num_rows rows
                for _ in range(num_rows):
                    try:
                        row = next(reader)
                        result.append(row)
                    except StopIteration:
                        break
        except Exception as e:
            print(f"Error loading data chunk: {str(e)}")
        
        return result
    
    def save_data(self):
        """Save data to the current file"""
        if not self.filename:
            return False
        
        try:
            with open(self.filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(self.headers)
                writer.writerows(self.data)
            self.modified = False
            return True
        except Exception as e:
            print(f"Error saving data: {str(e)}")
            return False
    
    def save_as_data(self, new_file_path):
        """Save data to a new file path"""
        try:
            with open(new_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter='\t')
                writer.writerow(self.headers)
                writer.writerows(self.data)
            self.filename = new_file_path
            self.modified = False
            return True
        except Exception as e:
            print(f"Error saving as: {str(e)}")
            return False
    
    def create_backup(self):
        """Create a backup of the current file"""
        if not self.filename:
            return None
        
        try:
            # Create backup directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(self.filename), '.backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.basename(self.filename)
            name, ext = os.path.splitext(base_name)
            backup_filename = f"{name}_{timestamp}{ext}"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy file contents
            with open(self.filename, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            
            return backup_path
        except Exception as e:
            print(f"Error creating backup: {str(e)}")
            return None
    
    def restore_from_backup(self, backup_path):
        """Restore file from backup"""
        if not os.path.exists(backup_path):
            return False
        
        try:
            # Copy backup contents to original file
            with open(backup_path, 'rb') as src, open(self.filename, 'wb') as dst:
                dst.write(src.read())
            
            # Reload the data
            self.load_data(self.filename)
            return True
        except Exception as e:
            print(f"Error restoring backup: {str(e)}")
            return False
    
    def add_row(self, row_data):
        """Add a new row to the data"""
        if not row_data:
            return False
        
        # Ensure row_data has the same length as headers
        while len(row_data) < len(self.headers):
            row_data.append('')
        
        self.data.append(row_data)
        self.modified = True
        return True
    
    def edit_row(self, row_index, row_data):
        """Edit an existing row"""
        if 0 <= row_index < len(self.data):
            # Ensure row_data has the same length as headers
            while len(row_data) < len(self.headers):
                row_data.append('')
            
            self.data[row_index] = row_data
            self.modified = True
            return True
        return False
    
    def delete_row(self, row_index):
        """Delete a row from the data"""
        if 0 <= row_index < len(self.data):
            del self.data[row_index]
            self.modified = True
            return True
        return False
    
    def search_data(self, search_term, threshold=70, search_column="All Columns"):
        """Search data with fuzzy matching"""
        from fuzzywuzzy import fuzz
        
        search_data = []
        search_term_lower = search_term.lower()
        
        if self.is_large_file:
            # For large files, search directly from the file
            try:
                with open(self.filename, "r", encoding='utf-8') as f:
                    reader = csv.reader(f, delimiter="\t")
                    next(reader)  # Skip header
                    
                    for row in reader:
                        if not row:  # Skip empty rows
                            continue
                        
                        if search_column == "All Columns":
                            row_text = " ".join(str(cell) for cell in row).lower()
                            score = fuzz.partial_ratio(search_term_lower, row_text)
                        else:
                            if search_column in self.headers:
                                column_index = self.headers.index(search_column)
                                if column_index < len(row):
                                    cell_value = str(row[column_index]).lower()
                                    score = fuzz.partial_ratio(search_term_lower, cell_value)
                                else:
                                    score = 0
                            else:
                                score = 0
                        
                        if score >= threshold:
                            search_data.append(row)
            except Exception as e:
                print(f"Error during search in lazy load mode: {str(e)}")
        else:
            # For normal mode, search in memory data
            for row in self.data:
                if search_column == "All Columns":
                    row_text = " ".join(str(cell) for cell in row).lower()
                    score = fuzz.partial_ratio(search_term_lower, row_text)
                else:
                    if search_column in self.headers:
                        column_index = self.headers.index(search_column)
                        if column_index < len(row):
                            cell_value = str(row[column_index]).lower()
                            score = fuzz.partial_ratio(search_term_lower, cell_value)
                        else:
                            score = 0
                    else:
                        score = 0
                
                if score >= threshold:
                    search_data.append(row)
        
        return search_data