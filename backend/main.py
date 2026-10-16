import base64
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

RAIZ = Path(__file__).resolve().parents[1]
load_dotenv(RAIZ / ".env")          # lee ANTHROPIC_API_KEY, APP_USER, APP_PASSWORD...

from backend.routes import excel, upload  # noqa: E402

app = FastAPI(title="Cerdas - El Fortín")


@app.middleware("http")
async def proteger_con_clave(request: Request, call_next):
    """Si están definidas APP_USER y APP_PASSWORD, pide usuario y contraseña.
    Es obligatorio en internet: sin esto cualquiera podría usar la app y gastar tu saldo."""
    usuario, clave = os.getenv("APP_USER"), os.getenv("APP_PASSWORD")
    if usuario and clave:
        ok = False
        auth = request.headers.get("authorization", "")
        if auth.startswith("Basic "):
            try:
                u, _, p = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
                ok = (secrets.compare_digest(u.encode(), usuario.encode())
                      and secrets.compare_digest(p.encode(), clave.encode()))
            except Exception:
                ok = False
        if not ok:
            return Response("Acceso restringido", status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Cerdas El Fortin"'})
    return await call_next(request)


app.include_router(upload.router)
app.include_router(excel.router)
app.mount("/", StaticFiles(directory=RAIZ / "frontend", html=True), name="frontend")