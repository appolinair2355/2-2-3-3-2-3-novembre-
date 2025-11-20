import os, yaml, json, hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List

class YAMLDataManager:
    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self.config_file = self.data_dir / "bot_config.yaml"
        self.predictions_file = self.data_dir / "predictions.yaml"
        self.auto_predictions_file = self.data_dir / "auto_predictions.yaml"
        self.message_log_file = self.data_dir / "message_log.yaml"
        self._init_files()

    def _init_files(self):
        defaults = {self.config_file: {}, self.predictions_file: [], self.auto_predictions_file: {}, self.message_log_file: []}
        for file_path, default_content in defaults.items():
            if not file_path.exists():
                self._save_yaml(file_path, default_content)

    def _load_yaml(self, file_path: Path) -> Any:
        try:
            return yaml.safe_load(file_path.read_text(encoding="utf-8")) or {} if file_path.exists() else {}
        except Exception as e:
            print(f"❌ Erreur chargement {file_path} : {e}")
            return {}

    def _save_yaml(self, file_path: Path, data: Any):
        try:
            file_path.write_text(yaml.dump(data, allow_unicode=True, default_flow_style=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"❌ Erreur sauvegarde {file_path} : {e}")

    def set_config(self, key: str, value: Any):
        cfg = self._load_yaml(self.config_file)
        cfg[key] = {"value": value, "updated_at": datetime.now().isoformat()}
        self._save_yaml(self.config_file, cfg)

    def get_config(self, key: str, default=None):
        cfg = self._load_yaml(self.config_file)
        return cfg.get(key, {}).get("value", default)

    def mark_message_processed(self, content: str, channel_id: int):
        log = self._load_yaml(self.message_log_file)
        if not isinstance(log, list): log = []
        h = hashlib.sha256(f"{channel_id}:{content}".encode()).hexdigest()
        if any(m.get("message_hash") == h for m in log): return
        log.append({"message_hash": h, "channel_id": channel_id, "content": content, "processed_at": datetime.now().isoformat()})
        if len(log) > 1000: log = log[-1000:]
        self._save_yaml(self.message_log_file, log)

    def is_message_processed(self, content: str, channel_id: int) -> bool:
        log = self._load_yaml(self.message_log_file)
        if not isinstance(log, list): return False
        h = hashlib.sha256(f"{channel_id}:{content}".encode()).hexdigest()
        return any(m.get("message_hash") == h for m in log)

yaml_manager = YAMLDataManager()
def init_database(): return yaml_manager
      
