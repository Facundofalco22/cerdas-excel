import io

from PIL import Image, ImageOps

LADO_MAX = 2000  # px; suficiente para letra manuscrita sin pasarse de peso


def abrir_imagen(ruta):
    """Abre la foto aplicando la rotación que guarda el celular (EXIF)."""
    img = Image.open(ruta)
    return ImageOps.exif_transpose(img).convert("RGB")


def giro_por_forma(img):
    """Plan B sin internet: la planilla es horizontal, así que si la foto
    está vertical probablemente esté acostada hacia la derecha."""
    return 90 if img.height > img.width else 0


def rotar(img, grados):
    """Gira la imagen 'grados' en sentido antihorario (0, 90, 180 o 270)."""
    grados = int(grados) % 360
    return img.rotate(grados, expand=True) if grados else img


def a_jpeg(img, lado_max=LADO_MAX, calidad=92):
    """Devuelve (bytes_jpeg, 'image/jpeg') con la imagen achicada si es muy grande."""
    copia = img.copy()
    copia.thumbnail((lado_max, lado_max))
    buf = io.BytesIO()
    copia.save(buf, format="JPEG", quality=calidad)
    return buf.getvalue(), "image/jpeg"