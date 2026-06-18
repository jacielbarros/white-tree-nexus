"""JWT HS512 + revogação de `jti` no Redis (fail-open). Ver research R2/R3."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from wtnapp import settings

logger = logging.getLogger(__name__)

_redis_client = None
_redis_unavailable = False

# Backend em memória para testes (REDIS_URL="memory://") — revogação determinística
# sem depender de Redis real, mantendo a semântica fail-open quando REDIS_URL="".
_MEMORY_URL = "memory://"
_memory_denylist: set[str] = set()


def _use_memory() -> bool:
    return settings.REDIS_URL == _MEMORY_URL


def reset_memory_denylist() -> None:
    """Limpa a denylist em memória (uso em testes)."""
    _memory_denylist.clear()


def _get_redis():
    """Cliente Redis lazy. Retorna None se REDIS_URL vazio/memory:// ou indisponível (fail-open)."""
    global _redis_client, _redis_unavailable
    if not settings.REDIS_URL or _use_memory() or _redis_unavailable:
        return None
    if _redis_client is None:
        try:
            import redis

            _redis_client = redis.from_url(settings.REDIS_URL)
            _redis_client.ping()
        except Exception:
            logger.warning("Redis indisponível; revogação de jti em modo fail-open", exc_info=True)
            _redis_unavailable = True
            return None
    return _redis_client


def create_access_token(
    *, user_id: uuid.UUID, tenant_ids: list[uuid.UUID], super_admin: bool = False
) -> tuple[str, str, int]:
    """Retorna (token, jti, expires_in_segundos)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.TOKEN_EXPIRY_MINUTES)
    jti = str(uuid.uuid4())
    claims = {
        "sub": str(user_id),
        "tenant_ids": [str(t) for t in tenant_ids],
        "sa": super_admin,
        "iss": settings.JWT_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": jti,
    }
    token = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, int((exp - now).total_seconds())


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        return None


def revoke_jti(jti: str, ttl_seconds: int) -> None:
    if _use_memory():
        _memory_denylist.add(jti)
        return
    r = _get_redis()
    if r is None:
        logger.warning("logout sem revogação persistente de jti (fail-open)")
        return
    try:
        r.setex(f"jti:revoked:{jti}", max(ttl_seconds, 1), "1")
    except Exception:
        logger.warning("falha ao revogar jti no Redis (fail-open)", exc_info=True)


def is_jti_revoked(jti: str) -> bool:
    if _use_memory():
        return jti in _memory_denylist
    r = _get_redis()
    if r is None:
        return False  # fail-open: disponibilidade > segurança absoluta em falha de infra
    try:
        return r.exists(f"jti:revoked:{jti}") == 1
    except Exception:
        logger.warning("falha ao consultar revogação de jti (fail-open)", exc_info=True)
        return False
