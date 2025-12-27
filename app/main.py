from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.health import router as health_router
from app.api.config import router as config_router
from app.api.upload import router as upload_router
from pathlib import Path

app = FastAPI(title="WLED Media Engine")

# Registrar routers de API
app.include_router(health_router)
app.include_router(config_router)
app.include_router(upload_router)

# Montar static files en /static
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Servir index.html por defecto
@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    return FileResponse(index_file)