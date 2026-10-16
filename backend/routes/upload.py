import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from backend.services import data_service, ocr_service

router = APIRouter()

CARPETA_TEMP = Path(__file__).resolve().parents[2] / "uploads" / "temporal"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


@router.post("/api/upload")
async def subir_fotos(fotos: list[UploadFile] = File(...), giro: str = Form("auto")):
    CARPETA_TEMP.mkdir(parents=True, exist_ok=True)
    filas, errores, giros = [], [], {}
    for foto in fotos:
        ext = Path(foto.filename or "").suffix.lower()
        if ext not in EXTENSIONES:
            errores.append(f"{foto.filename}: formato no soportado")
            continue
        ruta = CARPETA_TEMP / f"{uuid.uuid4().hex}{ext}"
        ruta.write_bytes(await foto.read())
        try:
            filas_foto, grados = ocr_service.leer_foto(ruta, giro)
            giros[foto.filename] = grados
            for raw in filas_foto:
                fila = data_service.preparar_fila_para_pantalla(raw)
                fila["foto"] = foto.filename
                filas.append(fila)
        except Exception as e:
            errores.append(f"{foto.filename}: {e}")
        finally:
            ruta.unlink(missing_ok=True)   # la foto no se guarda
    return {"filas": filas, "errores": errores, "giros": giros}