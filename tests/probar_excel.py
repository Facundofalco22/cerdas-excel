from datetime import datetime

from backend.models.datos_cerdo import DatosCerdo
from backend.services.excel_service import guardar_registros

datos = [
    # cerda existente: servicio nuevo
    DatosCerdo(cerda=2020, fecha_servicio=datetime(2026, 2, 18), padrillo="539"),
    # cerda que no gestó
    DatosCerdo(cerda=1998, fecha_servicio=datetime(2026, 8, 1), padrillo="077", no_gesto=True),
    # cerda nueva (no existe en el Excel)
    DatosCerdo(cerda=9999, fecha_servicio=datetime(2026, 9, 1), padrillo="123",
               fecha_parto_probable=datetime(2026, 12, 24)),
]
print(guardar_registros(datos))
