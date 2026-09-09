import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config import get_settings
from app.database import SessionLocal, engine
from app.dependencies import require_admin
from app.models import Base, ServerState
from app.routers import clients, playlist, sync, videos

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("playlist_manager")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        logger.error(
            "Не удалось открыть базу данных. Проверьте права на каталог проекта "
            "(запустите: chown -R <service_user>:<group> <каталог_проекта>) "
            "или укажите абсолютный путь в DATABASE_URL. Ошибка: %s",
            e,
        )
        raise
    with SessionLocal() as session:
        if session.get(ServerState, 1) is None:
            session.add(ServerState(id=1, playlist_revision=1))
            session.commit()
    logger.info("База данных инициализирована")
    yield


app = FastAPI(title="Video Playlist Manager", lifespan=lifespan)

_settings = get_settings()
_origins = _settings.cors_origins_list()
_allow_credentials = True
if "*" in _origins:
    # Браузеры запрещают credentials вместе с wildcard origin
    _allow_credentials = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("%s %s -> %s (%.1f ms)", request.method, request.url.path, response.status_code, duration_ms)
        return response
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.exception("Ошибка при обработке %s %s (%.1f ms)", request.method, request.url.path, duration_ms)
        raise


@app.exception_handler(RequestValidationError)
async def validation_exc_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(HTTPException)
async def http_exc_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """JSON для HTTPException; заголовки (WWW-Authenticate) нужны для Basic Auth в браузере."""
    hdrs = dict(exc.headers) if exc.headers else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=hdrs)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.error("Необработанное исключение: %s", exc, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(videos.router)
app.include_router(playlist.router)
app.include_router(sync.router)
app.include_router(clients.router)


@app.get("/")
def index(
    request: Request,
    _: None = Depends(require_admin),
):
    """Главная страница админки (Jinja2 + Bootstrap)."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "has_auth": bool(get_settings().admin_username)},
    )


if __name__ == "__main__":
    import uvicorn

    s = get_settings()
    uvicorn.run(
        "app.main:app",
        host=s.host,
        port=s.port,
        reload=s.debug,
        log_level="info",
    )
