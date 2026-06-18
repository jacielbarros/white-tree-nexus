"""FastAPI app: CORS, rate limiting, handlers de erro genéricos, health check, routers.

Erros NUNCA vazam stack/tabela/existência cross-tenant (FR-034).
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from wtnapp import settings
from wtnapp.database.database import engine
from wtnapp.limiter import limiter
from wtnapp.models import Base
from wtnapp.routers import auth, bootstrap, invitations, me, memberships, organizations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Alembic é a fonte de verdade do schema; create_all mantém paridade em dev/test.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="White Tree Nexus API",
    version="0.1.0",
    description="Plataforma SaaS multi-tenant de Gestão de SGSI (ISO/IEC 27001:2022).",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(IntegrityError)
async def _integrity_handler(_request: Request, _exc: IntegrityError) -> JSONResponse:
    logger.warning("IntegrityError", exc_info=True)
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "Conflito de dados."})


@app.exception_handler(Exception)
async def _unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.error("Erro não tratado", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno."},
    )


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db():
    from wtnapp.database.database import SessionLocal

    session = SessionLocal()
    try:
        session.execute(text("SELECT 1"))
        return {"status": "ok", "db": "ok"}
    finally:
        session.close()


app.include_router(bootstrap.router)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(invitations.router)
app.include_router(memberships.router)
app.include_router(me.router)
