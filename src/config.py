import yaml
from pathlib import Path

class ConfigLoader:
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = Path(config_path)
        self.config = self._load()
    
    def _load(self):
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with self.config_path.open() as f:
            cfg = yaml.safe_load(f)
        return cfg
    
    def get(self, key, default=None):
        return self.config.get(key, default)
