from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path
import json
from datetime import datetime
import uuid
from PIL import Image
import io
import logging
import base64
from app.services.wled_service import WledService, get_wled_config_from_file

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])

ASSETS_DIR = Path(__file__).parent.parent.parent / "data" / "assets"

# Control global de animaciones activas
active_animations = {}  # {image_id: True/False}

def process_gif(image_data: bytes, matrix_width: int, matrix_height: int) -> bytes:
    """Procesa un GIF redimensionándolo manteniendo la animación"""
    try:
        gif = Image.open(io.BytesIO(image_data))
        
        # Obtener información del GIF
        frames = []
        durations = []
        
        try:
            while True:
                durations.append(gif.info.get('duration', 100))
                
                # Redimensionar frame manteniendo aspect ratio
                img_aspect = gif.width / gif.height
                matrix_aspect = matrix_width / matrix_height
                
                if img_aspect > matrix_aspect:
                    new_height = matrix_height
                    new_width = int(new_height * img_aspect)
                else:
                    new_width = matrix_width
                    new_height = int(new_width / img_aspect)
                
                resized = gif.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Crear canvas con fondo
                frame = Image.new('RGB', (matrix_width, matrix_height), (0, 0, 0))
                x = (matrix_width - new_width) // 2
                y = (matrix_height - new_height) // 2
                frame.paste(resized, (x, y))
                
                frames.append(frame)
                gif.seek(gif.tell() + 1)
        except EOFError:
            pass
        
        # Guardar como GIF animado
        output = io.BytesIO()
        frames[0].save(
            output,
            format='GIF',
            save_all=True,
            append_images=frames[1:] if len(frames) > 1 else [],
            duration=durations,
            loop=0,
            optimize=False
        )
        return output.getvalue()
    except Exception as e:
        raise Exception(f"Error procesando GIF: {str(e)}")

@router.post("")
async def upload_image(image: UploadFile = File(...), name: str = Form(...), is_gif: str = Form(default="false")):
    """Guarda una imagen procesada"""
    try:
        # Asegurar que la carpeta existe
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generar ID único para la imagen
        image_id = str(uuid.uuid4())[:8]
        
        contents = await image.read()
        
        # Detectar si es GIF por el content-type o por el parámetro
        is_gif_file = is_gif.lower() == "true" or image.content_type == "image/gif"
        
        logger.info(f"Upload request: name={name}, is_gif_param={is_gif}, content_type={image.content_type}, is_gif_file={is_gif_file}")
        
        # Cargar configuración para obtener dimensiones de matriz
        config_path = ASSETS_DIR.parent / "config.json"
        matrix_width, matrix_height = 20, 20
        
        if config_path.exists():
            with open(config_path, "r") as f:
                config = json.load(f)
                matrix_width = config.get("matrix", {}).get("width", 20)
                matrix_height = config.get("matrix", {}).get("height", 20)
        
        # Procesar según tipo
        if is_gif_file:
            image_data = process_gif(contents, matrix_width, matrix_height)
            image_filename = f"{image_id}_{name}.gif"
            image_format = "gif"
        else:
            image_data = contents
            image_filename = f"{image_id}_{name}.png"
            image_format = "png"
        
        # Guardar imagen
        image_path = ASSETS_DIR / image_filename
        with open(image_path, "wb") as f:
            f.write(image_data)
        
        # Guardar metadata
        metadata = {
            "id": image_id,
            "name": name,
            "filename": image_filename,
            "format": image_format,
            "uploaded_at": datetime.now().isoformat()
        }
        
        metadata_path = ASSETS_DIR / f"{image_id}_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "success": True,
            "message": "Imagen guardada exitosamente",
            "data": {
                "id": image_id,
                "filename": image_filename
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/images")
async def get_images():
    """Obtiene la lista de imágenes cargadas"""
    try:
        if not ASSETS_DIR.exists():
            return {"success": True, "data": []}
        
        images = []
        
        # Buscar archivos de metadata
        for metadata_file in ASSETS_DIR.glob("*_metadata.json"):
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                images.append(metadata)
            except:
                pass
        
        return {
            "success": True,
            "data": images
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{image_id}")
async def delete_image(image_id: str):
    """Elimina una imagen"""
    try:
        # Buscar y eliminar imagen y metadata
        for file in ASSETS_DIR.glob(f"{image_id}_*"):
            file.unlink()
        
        return {
            "success": True,
            "message": "Imagen eliminada exitosamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{image_id}")
async def get_image_preview(image_id: str):
    """Obtiene la preview de una imagen"""
    try:
        # Buscar archivos PNG o GIF (no metadata)
        for pattern in [f"{image_id}_*.gif", f"{image_id}_*.png"]:
            for file in ASSETS_DIR.glob(pattern):
                if not str(file).endswith("_metadata.json"):
                    return FileResponse(file, media_type="image/gif" if file.suffix == ".gif" else "image/png")
        
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_image(filename: str):
    """Descarga una imagen"""
    try:
        file_path = ASSETS_DIR / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        return FileResponse(file_path, filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-to-wled/{image_id}")
async def send_to_wled(image_id: str):
    """Envía una imagen al WLED"""
    try:
        logger.info(f"Attempting to send image {image_id} to WLED")
        
        # Obtener configuración de WLED y matriz
        config_path = ASSETS_DIR.parent / "config.json"
        logger.info(f"Config path: {config_path}, exists: {config_path.exists()}")
        
        if not config_path.exists():
            logger.error("Config file not found")
            raise HTTPException(status_code=400, detail="Configuración no encontrada")
        
        with open(config_path, "r") as f:
            config = json.load(f)
        
        wled_config = config.get("wled", {})
        matrix_config = config.get("matrix", {})
        
        logger.info(f"WLED config: {wled_config}")
        logger.info(f"Matrix config: {matrix_config}")
        
        if not wled_config.get("ip"):
            logger.error("WLED IP not configured")
            raise HTTPException(status_code=400, detail="WLED no configurado")
        
        matrix_width = matrix_config.get("width", 20)
        matrix_height = matrix_config.get("height", 20)
        
        # Buscar archivo de imagen
        image_file = None
        logger.info(f"Looking for image files for ID: {image_id}")
        
        for file in ASSETS_DIR.glob(f"{image_id}_*.gif"):
            if not str(file).endswith("_metadata.json"):
                image_file = file
                logger.info(f"Found GIF: {image_file}")
                break
        
        if not image_file:
            for file in ASSETS_DIR.glob(f"{image_id}_*.png"):
                if not str(file).endswith("_metadata.json"):
                    image_file = file
                    logger.info(f"Found PNG: {image_file}")
                    break
        
        if not image_file:
            logger.error(f"Image not found for ID: {image_id}")
            raise HTTPException(status_code=404, detail="Imagen no encontrada")
        
        # Enviar a WLED
        logger.info(f"Sending {image_file} to WLED at {wled_config.get('ip')}:{wled_config.get('port', 80)}")
        
        wled = WledService(
            ip=wled_config.get("ip"),
            port=wled_config.get("port", 80),
            protocol=wled_config.get("protocol", "http")
        )
        
        rotation = wled_config.get("rotation", 0)
        mirror_v = wled_config.get("mirror_v", False)
        mirror_h = wled_config.get("mirror_h", False)
        logger.info(f"Applying rotation: {rotation}°, mirror_v: {mirror_v}, mirror_h: {mirror_h}")
        
        success, message = await wled.send_image(image_file, matrix_width, matrix_height, rotation, mirror_v, mirror_h)
        
        logger.info(f"WLED result: success={success}, message={message}")
        
        if success:
            return {
                "success": True,
                "message": message
            }
        else:
            raise HTTPException(status_code=500, detail=message)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending to WLED: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
@router.get("/{image_id}/frames")
async def get_image_frames(image_id: str):
    """Obtiene todos los frames de una imagen GIF en base64"""
    try:
        # Buscar la imagen
        image_file = None
        for file in ASSETS_DIR.glob(f"{image_id}_*"):
            if str(file).endswith(".gif") and not str(file).endswith("_metadata.json"):
                image_file = file
                logger.info(f"Found GIF: {image_file}")
                break
        
        if not image_file:
            # Buscar PNG
            for file in ASSETS_DIR.glob(f"{image_id}_*.png"):
                if not str(file).endswith("_metadata.json"):
                    image_file = file
                    logger.info(f"Found PNG: {image_file}")
                    break
        
        if not image_file:
            raise HTTPException(status_code=404, detail="Imagen no encontrada")
        
        # Extraer frames
        img = Image.open(image_file)
        frames = []
        
        if image_file.suffix.lower() == '.gif' and hasattr(img, 'n_frames') and img.n_frames > 1:
            # Es una animación GIF
            try:
                for i in range(img.n_frames):
                    img.seek(i)
                    duration = img.info.get('duration', 100)
                    
                    # Convertir a RGB si es necesario
                    frame = img.convert('RGB')
                    
                    # Convertir a base64
                    buffered = io.BytesIO()
                    frame.save(buffered, format="PNG")
                    frame_base64 = base64.b64encode(buffered.getvalue()).decode()
                    
                    frames.append({
                        "data": f"data:image/png;base64,{frame_base64}",
                        "duration": duration
                    })
            except EOFError:
                pass
        else:
            # Es una imagen estática
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            frame_base64 = base64.b64encode(buffered.getvalue()).decode()
            
            frames.append({
                "data": f"data:image/png;base64,{frame_base64}",
                "duration": 100
            })
        
        return {
            "success": True,
            "is_animated": len(frames) > 1,
            "frames": frames
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting frames: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

async def run_animation_background(image_id: str, image_file: Path, matrix_width: int, matrix_height: int, rotation: int, mirror_v: bool, mirror_h: bool, animation_loop: bool, animation_frame_delay: int, wled_ip: str, wled_port: int, wled_protocol: str):
    """Ejecuta la animación en background sin bloquear el servidor"""
    try:
        wled = WledService(
            ip=wled_ip,
            port=wled_port,
            protocol=wled_protocol,
            image_id=image_id,
            should_continue=active_animations
        )
        await wled.send_image(
            image_file, 
            matrix_width, 
            matrix_height, 
            rotation, 
            mirror_v, 
            mirror_h,
            animation_loop,
            animation_frame_delay
        )
    except Exception as e:
        logger.error(f"Error en animación background: {str(e)}")
    finally:
        # Limpiar la entrada de animaciones activas
        if image_id in active_animations:
            del active_animations[image_id]


@router.post("/{image_id}/animate")
async def animate_image(image_id: str, body: dict = Body(...), background_tasks: BackgroundTasks = None):
    """Envía frames de una animación GIF al WLED"""
    try:
        action = body.get("action", "play")  # play, pause, stop
        
        # Obtener configuración WLED y animación
        config_path = ASSETS_DIR.parent / "config.json"
        if not config_path.exists():
            raise HTTPException(status_code=400, detail="Configuración no encontrada")
        
        with open(config_path, "r") as f:
            config = json.load(f)
            matrix_width = config.get("matrix", {}).get("width", 20)
            matrix_height = config.get("matrix", {}).get("height", 20)
        
        wled_config = get_wled_config_from_file(config_path)
        animation_config = config.get("animation", {"loop": False, "frame_delay": None})
        
        logger.info(f"Animation config loaded: {animation_config}")
        
        # Buscar la imagen
        image_file = None
        for file in ASSETS_DIR.glob(f"{image_id}_*"):
            if str(file).endswith(".gif") and not str(file).endswith("_metadata.json"):
                image_file = file
                break
        
        if not image_file:
            raise HTTPException(status_code=404, detail="Imagen GIF no encontrada")
        
        # Manejar acciones
        if action == "stop":
            # Eliminar de animaciones activas para detener
            if image_id in active_animations:
                del active_animations[image_id]
            return {"success": True, "message": "Animación detenida"}
        
        elif action == "pause":
            # Pausar: establece a False pero no elimina
            active_animations[image_id] = False
            return {"success": True, "message": "Animación pausada"}
        
        elif action == "play":
            # Obtener parámetros de transformación
            rotation = wled_config.get("rotation", 0)
            mirror_v = wled_config.get("mirror_v", False)
            mirror_h = wled_config.get("mirror_h", False)
            animation_loop = animation_config.get("loop", False)
            animation_frame_delay = animation_config.get("frame_delay", None)
            
            logger.info(f"Sending animation in background: image_id={image_id}, loop={animation_loop}, delay={animation_frame_delay}")
            
            # Marcar como activa
            active_animations[image_id] = True
            
            # Ejecutar animación en background sin bloquear
            if background_tasks:
                background_tasks.add_task(
                    run_animation_background,
                    image_id,
                    image_file,
                    matrix_width,
                    matrix_height,
                    rotation,
                    mirror_v,
                    mirror_h,
                    animation_loop,
                    animation_frame_delay,
                    wled_config.get("ip"),
                    wled_config.get("port", 80),
                    wled_config.get("protocol", "http")
                )
                return {"success": True, "message": "Animación iniciada en background"}
            
            # Fallback si no hay background_tasks (no debería pasar)
            return {"success": False, "message": "No se pudo iniciar la animación"}
        
        return {"success": False, "message": f"Acción desconocida: {action}"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error animating: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
