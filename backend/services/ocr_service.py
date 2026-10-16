"""Lee una foto de la planilla manuscrita usando Claude (visión)."""
import base64
import json
import os
import re

import anthropic

from backend.utils import image_utils

MODELO = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

PROMPT = """Esta es la foto de una planilla manuscrita de un criadero de cerdos, titulada
"PLANILLA DE SERVICIOS - PARTOS - DESTETES". Cada renglón con datos es un servicio de una cerda.

Las columnas de la planilla, de izquierda a derecha, son:
CERDA | FECHA SERVIC. | PADRILLO | FECHA P.P. | CATEGOR. | FECHA PARTO | JAULA | L.N.V. | L.N.T. | FECHA DESTET | L. DESTE | OBSERVACION

Cómo pasarlas a los campos que tenés que devolver:
- CERDA -> cerda (número entero, por ejemplo 1896)
- FECHA SERVIC. -> fecha_servicio
- PADRILLO -> padrillo
- FECHA P.P. (parición probable) -> fecha_parto_probable
- FECHA PARTO -> fecha_parto
- L.N.V. (lechones nacidos vivos) -> nacidos_vivos
- L.N.T. (lechones nacidos totales) -> nacidos_totales
- FECHA DESTET -> fecha_destete
- L. DESTE (lechones destetados) -> destetados
- IGNORÁ las columnas CATEGOR., JAULA y OBSERVACION: no hay que devolverlas.

Reglas:
- Si la foto está girada, leela en la orientación en la que el texto se lee derecho.
- Una comilla doble (") o una rayita en una celda significa "igual que el renglón de arriba":
  copiá el valor del renglón anterior que tenga el dato escrito. Pasa mucho con la fecha de
  servicio y el padrillo.
- A la izquierda de algunas cerdas hay anotaciones como "2°s" o "3°s" (número de servicio):
  no son parte del número de cerda, ignoralas.
- Un renglón marcado con resaltador VERDE significa que la cerda NO gestó: poné no_gesto=true.
  En ese caso devolvé solo cerda, fecha_servicio y padrillo; dejá en null la fecha de parto,
  los lechones y el destete, aunque haya algo escrito en esas celdas.
- Los renglones vacíos no se devuelven. Ignorá los encabezados, el título y las notas sueltas
  (por ejemplo, lo escrito en rojo al margen).
- Escribí las fechas como DD/MM/AAAA (por ejemplo "27-3-2026" pasa a "27/03/2026").
- No inventes datos. Si una celda está vacía o no se lee, poné null.
- Si dudás de algún número o fecha, poné dudoso=true y explicá en "nota" cuál y por qué.
- El padrillo es texto: conservá ceros a la izquierda (por ejemplo "078") y aclaraciones
  (por ejemplo "3419 abuelo").
- Devolvé los renglones en el orden en que aparecen, de arriba hacia abajo.
Respondé usando la herramienta registrar_filas. Si no podés usarla, respondé solo con un JSON {"filas": [...]} con los mismos campos, sin texto adicional."""

FECHA = {"type": ["string", "null"]}
ENTERO = {"type": ["integer", "null"]}

HERRAMIENTA = {
    "name": "registrar_filas",
    "description": "Registra las filas leídas de la planilla.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filas": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "cerda": ENTERO,
                        "fecha_servicio": FECHA,
                        "padrillo": {"type": ["string", "null"]},
                        "fecha_parto_probable": FECHA,
                        "fecha_parto": FECHA,
                        "nacidos_vivos": ENTERO,
                        "nacidos_totales": ENTERO,
                        "fecha_destete": FECHA,
                        "destetados": ENTERO,
                        "no_gesto": {"type": "boolean"},
                        "dudoso": {"type": "boolean"},
                        "nota": {"type": ["string", "null"]},
                    },
                    "required": ["cerda", "no_gesto"],
                },
            }
        },
        "required": ["filas"],
    },
}


class ErrorOCR(Exception):
    pass


PROMPT_GIRO = """Esta foto muestra una planilla o tabla manuscrita que puede estar girada.
¿Cuántos grados hay que girar la foto en sentido ANTIHORARIO para que el texto quede derecho,
con el título y los encabezados de las columnas arriba, y se lea normalmente?
- Si el texto se ve acostado y se lee de ARRIBA hacia ABAJO: 90
- Si el texto se ve acostado y se lee de ABAJO hacia ARRIBA: 270
- Si el texto está cabeza abajo: 180
- Si ya se lee derecho: 0
Respondé solamente con un número: 0, 90, 180 o 270."""


def detectar_giro(img):
    """Le pregunta al modelo cuánto hay que girar la foto. Si falla, usa la forma de la foto."""
    try:
        datos, tipo = image_utils.a_jpeg(img, lado_max=1000, calidad=80)
        imagen = base64.standard_b64encode(datos).decode()
        r = anthropic.Anthropic().messages.create(
            model=MODELO,
            max_tokens=20,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": tipo, "data": imagen}},
                    {"type": "text", "text": PROMPT_GIRO},
                ],
            }],
        )
        texto = "".join(b.text for b in r.content if b.type == "text")
        m = re.search(r"\b(0|90|180|270)\b", texto)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return image_utils.giro_por_forma(img)


def _json_desde_texto(texto):
    """Plan B: si el modelo contesta con texto, busca el JSON adentro."""
    m = re.search(r"\{.*\}|\[.*\]", texto, re.DOTALL)
    if not m:
        return None
    try:
        dato = json.loads(m.group(0))
    except ValueError:
        return None
    return dato.get("filas", []) if isinstance(dato, dict) else dato


def leer_foto(ruta, giro="auto"):
    """Devuelve (filas, grados_girados). giro="auto" endereza la foto sola."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise ErrorOCR("Falta la clave ANTHROPIC_API_KEY en el archivo .env")

    img = image_utils.abrir_imagen(ruta)
    grados = detectar_giro(img) if str(giro) == "auto" else int(giro)
    img = image_utils.rotar(img, grados)
    datos, tipo = image_utils.a_jpeg(img)
    imagen = base64.standard_b64encode(datos).decode()
    try:
        cliente = anthropic.Anthropic()
        r = cliente.messages.create(
            model=MODELO,
            max_tokens=8000,
            tools=[HERRAMIENTA],
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": tipo, "data": imagen}},
                    {"type": "text", "text": PROMPT},
                ],
            }],
        )
    except anthropic.APIError as e:
        raise ErrorOCR(f"Error al consultar el modelo: {e}") from e

    for bloque in r.content:
        if bloque.type == "tool_use":
            filas = bloque.input.get("filas", [])
            if isinstance(filas, str):  # a veces llega como texto
                filas = _json_desde_texto(filas) or []
            return filas, grados

    # Plan B: el modelo contestó con texto en vez de usar la herramienta
    texto = "".join(b.text for b in r.content if b.type == "text")
    filas = _json_desde_texto(texto)
    if filas is None:
        raise ErrorOCR("El modelo no devolvió filas: " + texto[:200])
    return filas, grados