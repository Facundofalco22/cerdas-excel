"""Convierte entre lo que lee el OCR, lo que ve/edita el usuario y DatosCerdo."""
from datetime import datetime

from backend.models.datos_cerdo import DatosCerdo

FORMATOS = ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%d-%m-%y", "%Y-%m-%d"]
CAMPOS_FECHA = ["fecha_servicio", "fecha_parto_probable", "fecha_parto", "fecha_destete"]
CAMPOS_ENTERO = ["nacidos_vivos", "nacidos_totales", "destetados"]


def parsear_fecha(texto):
    """'18/02/2026' -> datetime. Devuelve None si está vacío; ValueError si no se entiende."""
    if texto is None:
        return None
    if isinstance(texto, datetime):
        return texto
    t = str(texto).strip()
    if not t:
        return None
    for f in FORMATOS:
        try:
            return datetime.strptime(t, f)
        except ValueError:
            pass
    raise ValueError(f"fecha no válida: '{t}'")


def fecha_a_texto(dt):
    return dt.strftime("%d/%m/%Y") if dt else ""


def _entero(valor):
    if valor in (None, ""):
        return None
    return int(valor)


def preparar_fila_para_pantalla(raw):
    """Fila cruda del OCR -> fila lista para mostrar y corregir en la web."""
    fila = {"cerda": raw.get("cerda"), "padrillo": raw.get("padrillo") or "",
            "no_gesto": bool(raw.get("no_gesto")), "dudoso": bool(raw.get("dudoso")),
            "nota": raw.get("nota") or ""}
    for c in CAMPOS_FECHA:
        valor = raw.get(c)
        try:
            fila[c] = fecha_a_texto(parsear_fecha(valor))
        except ValueError:
            fila[c] = str(valor)          # se muestra tal cual para que la corrijan
            fila["dudoso"] = True
            fila["nota"] = (fila["nota"] + " " if fila["nota"] else "") + f"Revisar {c}."
    for c in CAMPOS_ENTERO:
        fila[c] = raw.get(c)
    return fila


def fila_a_datos(fila):
    """Fila confirmada desde la web -> DatosCerdo. Lanza ValueError con el motivo."""
    try:
        cerda = int(fila.get("cerda"))
    except (TypeError, ValueError):
        raise ValueError("falta el número de cerda")
    datos = {"cerda": cerda, "no_gesto": bool(fila.get("no_gesto"))}
    padrillo = fila.get("padrillo")
    datos["padrillo"] = str(padrillo).strip() if padrillo not in (None, "") else None
    for c in CAMPOS_FECHA:
        datos[c] = parsear_fecha(fila.get(c))
    for c in CAMPOS_ENTERO:
        try:
            datos[c] = _entero(fila.get(c))
        except ValueError:
            raise ValueError(f"{c} tiene que ser un número")
    if datos["fecha_servicio"] is None and datos["fecha_parto"] is None:
        raise ValueError("no tiene fecha de servicio ni de parto")
    return DatosCerdo(**datos)
