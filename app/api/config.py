from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.config import config_service

router = APIRouter(prefix="/api/config", tags=["config"])

class ConfigUpdate(BaseModel):
    matrix_width: int = None
    matrix_height: int = None
    wled_ip: str = None
    wled_port: int = None
    wled_protocol: str = None
    wled_rotation: int = None
    wled_mirror_v: bool = None
    wled_mirror_h: bool = None
    animation_loop: bool = None
    animation_frame_delay: int = None  # en ms

@router.get("/")
async def get_config():
    """Obtiene la configuración actual"""
    try:
        config = config_service.load()
        # Asegurar estructura correcta
        if "matrix" not in config:
            config["matrix"] = {"width": 20, "height": 20}
        if "wled" not in config:
            config["wled"] = {"ip": "192.168.1.100", "port": 80, "protocol": "http", "rotation": 0, "mirror_v": False, "mirror_h": False}
        if "animation" not in config:
            config["animation"] = {"loop": False, "frame_delay": 100}
        return {
            "success": True,
            "data": config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def update_config(config: ConfigUpdate):
    """Actualiza la configuración"""
    try:
        current_config = config_service.load()
        
        # Asegurar estructura correcta
        if "matrix" not in current_config:
            current_config["matrix"] = {"width": 20, "height": 20}
        if "wled" not in current_config:
            current_config["wled"] = {"ip": "192.168.1.100", "port": 80, "protocol": "http", "rotation": 0, "mirror_v": False, "mirror_h": False}
        if "animation" not in current_config:
            current_config["animation"] = {"loop": False, "frame_delay": 100}
        
        # Actualizar matriz
        if config.matrix_width is not None:
            current_config["matrix"]["width"] = config.matrix_width
        if config.matrix_height is not None:
            current_config["matrix"]["height"] = config.matrix_height
        
        # Actualizar WLED
        if config.wled_ip is not None:
            current_config["wled"]["ip"] = config.wled_ip
        if config.wled_port is not None:
            current_config["wled"]["port"] = config.wled_port
        if config.wled_protocol is not None:
            current_config["wled"]["protocol"] = config.wled_protocol
        if config.wled_rotation is not None:
            current_config["wled"]["rotation"] = config.wled_rotation
        if config.wled_mirror_v is not None:
            current_config["wled"]["mirror_v"] = config.wled_mirror_v
        if config.wled_mirror_h is not None:
            current_config["wled"]["mirror_h"] = config.wled_mirror_h
        
        # Actualizar animación
        if config.animation_loop is not None:
            current_config["animation"]["loop"] = config.animation_loop
        if config.animation_frame_delay is not None:
            current_config["animation"]["frame_delay"] = max(50, config.animation_frame_delay)  # Mínimo 50ms
        
        config_service.save(current_config)
        
        return {
            "success": True,
            "message": "Configuración guardada exitosamente",
            "data": current_config
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
