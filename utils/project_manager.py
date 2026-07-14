import json
import os

class ProjectManager:
    """
    Manages loading and saving configuration parameters into .toolbox files.
    """
    @staticmethod
    def save_project(filepath: str, config: dict) -> bool:
        try:
            if not filepath.endswith(".toolbox"):
                filepath += ".toolbox"
            with open(filepath, "w") as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            print(f"Failed to save project: {e}")
            return False
            
    @staticmethod
    def load_project(filepath: str) -> dict:
        try:
            if not os.path.exists(filepath):
                return None
            with open(filepath, "r") as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Failed to load project: {e}")
            return None
