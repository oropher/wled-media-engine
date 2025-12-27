import json
from pathlib import Path

class ConfigService:
    def __init__(self):
        # Camino correcto: desde /app/app/services a /app/data/config.json
        # __file__ = /app/app/services/config.py
        # parent = /app/app/services
        # parent.parent = /app/app
        # parent.parent.parent = /app
        self.config_path = Path(__file__).parent.parent.parent / "data" / "config.json"
    
    def load(self):
        """Carga la configuración desde el archivo JSON"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        return {}
    
    def save(self, config: dict):
        """Guarda la configuración en el archivo JSON"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return config
    
    def get(self, key: str, default=None):
        """Obtiene un valor específico de la configuración"""
        config = self.load()
        keys = key.split('.')
        value = config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def set(self, key: str, value):
        """Establece un valor específico en la configuración"""
        config = self.load()
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
        self.save(config)
        return config

config_service = ConfigService()
