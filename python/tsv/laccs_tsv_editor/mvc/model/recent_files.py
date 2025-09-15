import os
import json


class RecentFilesManager:
    """Model for managing recently opened files"""

    def __init__(self, config_path, max_recent_files=10):
        self.recent_files = []
        self.max_recent_files = max_recent_files
        self.config_path = config_path

        # Create directory if it doesn't exist
        config_dir = os.path.dirname(config_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)

        # Load recent files from config
        self.load_recent_files()

    def load_recent_files(self):
        """Load recently opened files from configuration with deduplication"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    loaded_files = json.load(f)

                    # Deduplicate while preserving LRU order (first occurrence keeps position)
                    seen = set()
                    self.recent_files = []
                    for file_path in loaded_files:
                        if file_path not in seen and os.path.exists(file_path):
                            seen.add(file_path)
                            self.recent_files.append(file_path)

                    # Ensure we don't exceed max_recent_files
                    if len(self.recent_files) > self.max_recent_files:
                        self.recent_files = self.recent_files[: self.max_recent_files]
            except Exception as e:
                print(f"Error loading recent files: {str(e)}")
                self.recent_files = []
        else:
            self.recent_files = []

    def save_recent_files(self):
        """Save recently opened files to configuration"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.recent_files, f)
        except Exception as e:
            print(f"Error saving recent files: {str(e)}")

    def add_to_recent_files(self, file_path):
        """Add a file path to recent files list"""
        if not os.path.exists(file_path):
            return

        # Remove if already exists to keep only the most recent occurrence
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)

        # Add to the beginning of the list
        self.recent_files.insert(0, file_path)

        # Keep only the max number of recent files
        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[: self.max_recent_files]

        # Save the updated list
        self.save_recent_files()

    def remove_from_recent_files(self, file_path):
        """Remove a file path from recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
            self.save_recent_files()

    def clear_recent_files(self):
        """Clear all recent files"""
        self.recent_files = []
        self.save_recent_files()

    def get_recent_files(self):
        """Get the list of recent files"""
        # Ensure all files in the list still exist
        valid_files = []
        for file_path in self.recent_files:
            if os.path.exists(file_path):
                valid_files.append(file_path)

        # Update the list if any files were removed
        if len(valid_files) != len(self.recent_files):
            self.recent_files = valid_files
            self.save_recent_files()

        return self.recent_files

    def is_file_in_recent(self, file_path):
        """Check if a file is in the recent files list"""
        return file_path in self.recent_files
