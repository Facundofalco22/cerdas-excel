from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.services import data_service, excel_service

router = APIRouter()


@router.post("/api/guardar")
def guardar(filas: list[dict]):
    datos, errores = [], []
    for i, fila in enumerate(filas, start=1):
        try:
            datos.append(data_service.fila_a_datos(fila))
        except ValueError as e:
            errores.append(f"Fila {i} (cerda {fila.get('cerda') or '?'}): {e}")
    if errores:
        raise HTTPException(status_code=422, detail=errores)
    if not datos:
        raise HTTPException(status_code=422, detail=["No hay filas para guardar"])
    if not excel_service.archivo_activo().exists():
        raise HTTPException(status_code=422, detail=["Primero cargá el Excel completo (botón \"Cargar Excel completo\")."])
    excel_service.guardar_registros(datos)
    return {"ok": True, "guardadas": len(datos)}


@router.get("/api/descargar")
def descargar():
    ruta = excel_service.archivo_activo()
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="No hay ningún Excel para descargar")
    return FileResponse(ruta, filename="planilla_actualizada.xlsx",
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@router.get("/api/excel/estado")
def estado():
    return excel_service.estado()


@router.post("/api/excel/cargar")
async def cargar(archivo: UploadFile = File(...)):
    if not (archivo.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Tiene que ser un archivo .xlsx")
    try:
        resumen = excel_service.cargar_excel(await archivo.read())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, **resumen}


@router.post("/api/excel/reiniciar")
def reiniciar():
    excel_service.reiniciar()
    return {"ok": True}


@router.get("/api/cerda/{nro}")
def buscar(nro: int):
    try:
        return excel_service.buscar_cerda(nro)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))