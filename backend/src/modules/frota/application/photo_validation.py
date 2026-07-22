"""O que a foto precisa ser antes de qualquer coisa tocar o motor.

Três recusas, três respostas distintas — e a distinção importa, porque cada uma manda a pessoa
fazer uma coisa diferente:

| Situação | Resposta | O que a tela diz |
| --- | --- | --- |
| acima de 8 MB | **413** | "a foto ficou grande demais" |
| `content-type` fora da lista | **415** | "esse formato não serve" |
| bytes que não decodificam, ou acima de 50 MP | **422** | "tire outra foto" |

Mora na `application` e não em `domain/rules.py` porque decodificar imagem é Pillow, e o
`rules.py` é função de dados pra dados, sem biblioteca de infra. Os **limites** ficam lá; o que
os aplica, aqui."""

import io

from src.core.exceptions import (
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
    ValidationAppError,
)
from src.modules.frota.domain.rules import (
    ALLOWED_PHOTO_TYPES,
    MAX_PHOTO_BYTES,
    MAX_PHOTO_PIXELS,
)

__all__ = ["ensure_valid_photo"]


def ensure_valid_photo(content: bytes, content_type: str) -> None:
    """Recusa a foto que não deve nem ser guardada. Nada é gravado antes desta função passar.

    A ordem é a mais barata primeiro: tamanho é um `len`, `content-type` é um `in`, e só depois
    disso o Pillow toca os bytes. Decodificar antes de olhar o tamanho é o que a bomba de
    descompressão espera que o servidor faça.

    Raises:
        PayloadTooLargeError:
            Se a foto passar de 8 MB.
        UnsupportedMediaTypeError:
            Se o `content-type` não for JPEG, PNG ou WebP.
        ValidationAppError:
            Se os bytes não decodificarem como imagem, ou se a imagem decodificada passar de
            50 MP.
    """

    if len(content) > MAX_PHOTO_BYTES:
        raise PayloadTooLargeError(
            f"A foto passou de {MAX_PHOTO_BYTES // (1024 * 1024)} MB. "
            "Reduza a imagem e tente de novo."
        )

    if content_type not in ALLOWED_PHOTO_TYPES:
        raise UnsupportedMediaTypeError(
            f"Formato '{content_type}' não aceito. Envie a foto como JPEG, PNG ou WebP."
        )

    _ensure_decodable(content)


def _ensure_decodable(content: bytes) -> None:
    """Que os bytes sejam mesmo uma imagem, e de tamanho sensato.

    O `content-type` é o que o cliente **afirma**, e afirmar é grátis: um `application/zip`
    rotulado `image/jpeg` passaria pelo `in` acima. Quem confere é o decodificador.

    O teto de 50 MP é anti-bomba de descompressão: 8 MB de PNG viram gigabytes na memória se o
    servidor decodificar sem olhar. O `Image.open` do Pillow lê **só o cabeçalho** — as dimensões
    saem dali, antes de qualquer pixel ser alocado, que é o que torna a checagem barata."""

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(content)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationAppError(
            "Não consegui abrir essa imagem — o arquivo parece corrompido. Tire outra foto."
        ) from exc

    if width * height > MAX_PHOTO_PIXELS:
        raise ValidationAppError(
            f"A imagem tem {width}x{height} pixels, acima do limite de "
            f"{MAX_PHOTO_PIXELS // 1_000_000} MP. Reduza a resolução e tente de novo."
        )
