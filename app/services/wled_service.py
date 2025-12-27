import aiohttp
import json
from PIL import Image
import io
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger(__name__)


class WledService:
    def __init__(self, ip: str, port: int, protocol: str = "http", image_id: str = None, should_continue: dict = None):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.base_url = f"{protocol}://{ip}:{port}"
        self.image_id = image_id
        self.should_continue = should_continue or {}  # Dict para controlar si continuar
    
    async def send_image(self, image_path: Path, matrix_width: int, matrix_height: int, rotation: int = 0, mirror_v: bool = False, mirror_h: bool = False, animation_loop: bool = False, animation_frame_delay: int = None):
        """Envía una imagen al WLED como datos de pixels. Si es GIF animado, envía todos los frames."""
        try:
            logger.info(f"send_image called with: animation_loop={animation_loop}, animation_frame_delay={animation_frame_delay}")
            # Abrir imagen
            img = Image.open(image_path)
            is_gif_animated = image_path.suffix.lower() == '.gif' and hasattr(img, 'n_frames') and img.n_frames > 1
            
            if is_gif_animated:
                # Procesar GIF animado frame por frame
                logger.info(f"Procesando GIF animado con {img.n_frames} frames")
                frames_data = []
                
                try:
                    for frame_idx in range(img.n_frames):
                        img.seek(frame_idx)
                        duration = img.info.get('duration', 100)
                        
                        # Procesar el frame
                        frame = img.convert('RGB')
                        
                        # Aplicar transformaciones
                        if rotation == 90:
                            frame = frame.rotate(90, expand=False)
                        elif rotation == 180:
                            frame = frame.rotate(180, expand=False)
                        elif rotation == 270:
                            frame = frame.rotate(270, expand=False)
                        
                        if mirror_v:
                            frame = frame.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                        
                        if mirror_h:
                            frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                        
                        # Redimensionar
                        frame = frame.resize((matrix_width, matrix_height), Image.Resampling.LANCZOS)
                        
                        # Extraer pixels
                        pixels = []
                        for y in range(matrix_height):
                            for x in range(matrix_width):
                                r, g, b = frame.getpixel((x, y))
                                pixels.append([r, g, b])
                        
                        frames_data.append({"pixels": pixels, "duration": max(duration, 50)})  # Mínimo 50ms
                except EOFError:
                    pass
                
                # Enviar frames
                logger.info(f"Enviando {len(frames_data)} frames a WLED (loop={animation_loop}, delay={animation_frame_delay}ms)")
                async with aiohttp.ClientSession() as session:
                    loop_count = 0
                    max_loops = 10  # Máximo 10 iteraciones del loop para evitar bloqueos indefinidos
                    
                    while True:
                        # Verificar si debe continuar
                        if self.image_id and self.image_id not in self.should_continue:
                            logger.info(f"Animación {self.image_id} detenida por usuario")
                            break
                        
                        # Si está pausada (False), esperar
                        if self.image_id and self.should_continue.get(self.image_id) is False:
                            logger.info(f"Animación {self.image_id} pausada")
                            await asyncio.sleep(0.5)  # Verificar cada 500ms si se reanuda
                            continue
                        
                        for frame_num, frame_data in enumerate(frames_data):
                            # Revisar nuevamente si debe continuar en cada frame
                            if self.image_id and self.image_id not in self.should_continue:
                                logger.info(f"Animación {self.image_id} detenida en frame {frame_num}")
                                break
                            
                            try:
                                # Usar el delay configurado o el del GIF
                                if animation_frame_delay is not None:
                                    frame_delay = animation_frame_delay / 1000.0
                                else:
                                    frame_delay = frame_data["duration"] / 1000.0
                                
                                payload = {
                                    "on": True,
                                    "bri": 255,
                                    "effect": 0,
                                    "seg": [{
                                        "i": frame_data["pixels"]
                                    }]
                                }
                                
                                async with session.post(
                                    f"{self.base_url}/json",
                                    json=payload,
                                    timeout=aiohttp.ClientTimeout(total=5)
                                ) as resp:
                                    if resp.status != 200:
                                        logger.warning(f"Frame {frame_num} error: {resp.status}")
                                
                                # Esperar el delay antes del siguiente frame
                                await asyncio.sleep(frame_delay)
                            
                            except Exception as e:
                                logger.error(f"Error enviando frame {frame_num}: {str(e)}")
                        
                        # Si no es loop infinito, terminar después de una iteración
                        if not animation_loop:
                            break
                        
                        # Si es loop infinito, limitar a max_loops para evitar bloqueos
                        loop_count += 1
                        if loop_count >= max_loops:
                            break
                
                return True, f"Animación enviada a WLED ({len(frames_data)} frames)"
            
            else:
                # Imagen estática
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Aplicar rotación
                if rotation == 90:
                    img = img.rotate(90, expand=False)
                elif rotation == 180:
                    img = img.rotate(180, expand=False)
                elif rotation == 270:
                    img = img.rotate(270, expand=False)
                
                # Aplicar mirror vertical
                if mirror_v:
                    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                
                # Aplicar mirror horizontal
                if mirror_h:
                    img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                
                # Redimensionar a matriz
                img = img.resize((matrix_width, matrix_height), Image.Resampling.LANCZOS)
                
                # Obtener colores de cada pixel
                pixels = []
                for y in range(matrix_height):
                    for x in range(matrix_width):
                        r, g, b = img.getpixel((x, y))
                        pixels.append([r, g, b])
                
                # Enviar a WLED
                async with aiohttp.ClientSession() as session:
                    try:
                        payload = {
                            "on": True,
                            "bri": 255,
                            "effect": 0,
                            "seg": [{
                                "i": pixels
                            }]
                        }
                        
                        async with session.post(
                            f"{self.base_url}/json",
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as resp:
                            if resp.status == 200:
                                return True, "Imagen enviada a WLED correctamente"
                            else:
                                return False, f"Error del servidor WLED: {resp.status}"
                    except aiohttp.ClientError as e:
                        return False, f"Error de conexión: {str(e)}"
        
        except Exception as e:
            logger.error(f"Error procesando imagen: {str(e)}")
            return False, f"Error procesando imagen: {str(e)}"


def get_wled_config_from_file(config_path: Path) -> dict:
    """Obtiene la configuración de WLED del archivo config.json"""
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
            return config.get("wled", {})
    except:
        return {}
