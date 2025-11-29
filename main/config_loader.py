import json
from pathlib import Path
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent / "config.json"
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        required_fields = ["app", "settings"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field '{field}' in config.json")
        
        required_app_fields = ["name", "version", "github_repo"]
        for field in required_app_fields:
            if field not in config["app"]:
                raise ValueError(f"Missing required field 'app.{field}' in config.json")
        
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(
            "config.json not found! Please create a config.json file in the same directory as main.py"
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config.json: {e}")

def get_api_url(config: Dict[str, Any]) -> str:
    repo = config["app"]["github_repo"]
    return f"https://api.github.com/repos/{repo}/releases/latest"

def get_app_info(config: Dict[str, Any]) -> Dict[str, str]:
    return {
        "name": config["app"]["name"],
        "version": config["app"]["version"],
        "author": config["app"].get("author", "Unknown")
    }