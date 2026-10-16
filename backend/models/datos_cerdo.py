from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DatosCerdo:
    cerda: int
    fecha_servicio: Optional[datetime] = None
    padrillo: Optional[str] = None
    fecha_parto_probable: Optional[datetime] = None
    fecha_parto: Optional[datetime] = None
    nacidos_vivos: Optional[int] = None
    nacidos_totales: Optional[int] = None
    fecha_destete: Optional[datetime] = None
    destetados: Optional[int] = None
    no_gesto: bool = False  # fila en verde en la foto
