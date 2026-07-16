from functools import lru_cache

from src.core.config import get_config
from src.core.security.jwt import JwtTokenEncoder


@lru_cache(maxsize=1)
def get_jwt_encoder() -> JwtTokenEncoder:
    config = get_config()
    return JwtTokenEncoder(
        secret_key=config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )
