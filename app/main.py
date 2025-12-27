from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.health import router as health_router
from pathlib import Path

app = FastAPI(title="WLED Media Engine")

app.include_router(health_router)

# Obtener la ruta absoluta del directorio static
static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")