"""Porta de armazenamento de arquivo binário.

**Nasce no `core`, dentro da spec do primeiro cliente** — exatamente como `core/notifications/`
nasceu na spec 06, e é a mesma categoria: infra, não tabela de módulo. Por isso ela **não ganha
linha em `mount_routes`** e não é um dos cinco registros de porta de kernel; o `core` a resolve
sozinho a partir da config, como faz com o `EmailSender`.

Está aqui, e não em `modules/frota/`, porque Refeições vai querer anexo de nota fiscal, e duas
histórias de arquivo no mesmo produto é como a dívida de `PageResponse` começou. O custo de
acertar de primeira é uma pasta.

**A chave nunca vem do cliente** — quem a monta é o servidor. Aceitar chave do cliente seria
entregar leitura e escrita arbitrárias no bucket."""

import asyncio
import logging
from pathlib import Path
from typing import Annotated, Any, Protocol

from fastapi import Depends

from src.core.config import get_config
from src.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

_CONTENT_TYPE_SUFFIX = ".content-type"
"""O sidecar do adaptador local.

`odometer_readings` **não** guarda o `content-type` — quem o guarda é o storage, que é quem o
devolve no `get`. No S3 ele é metadado do objeto; num diretório, não existe metadado, então vira
um arquivo ao lado. Inferi-lo da extensão seria adivinhar, e o `get` promete o tipo gravado."""


class ObjectNotFoundError(NotFoundError):
    """A chave não existe no storage.

    Existe pra que `get` de chave inexistente levante **o erro do contrato**, e não um
    `FileNotFoundError` (local) ou um `ClientError` (S3): quem consome a porta não pode precisar
    saber qual adaptador está do outro lado pra tratar o caso mais comum de todos."""

    message = "Object not found."


class ObjectStorage(Protocol):
    """Guardar, ler e apagar bytes por chave. Três verbos, e nada de URL pré-assinada.

    Presigned foi decidido **fora** (spec 11): ela vaza uma URL que funciona por fora do
    `require_module` e do vínculo de tenant durante todo o TTL. O volume aqui — uma foto por
    viagem, vista raramente — não paga esse risco, então todo byte sai pela API, atrás dos
    guards."""

    async def put(self, key: str, content: bytes, content_type: str) -> None: ...

    async def get(self, key: str) -> tuple[bytes, str]: ...

    async def delete(self, key: str) -> None: ...


class LocalDirectoryStorage:
    """O adaptador de dev e de teste: um diretório no disco.

    É o gêmeo do `LoggingEmailSender` — `docker compose up db` continua subindo sem MinIO, e a
    suíte roda contra um `tmp_path` sem serviço nenhum. Todo I/O sai por `asyncio.to_thread`
    porque o event loop não pode parar esperando disco."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    def _path_of(self, key: str) -> Path:
        """A chave resolvida dentro da raiz, **recusando qualquer coisa que saia dela**.

        A chave é sempre montada pelo servidor, então isto nunca deveria disparar. É defesa em
        profundidade contra o dia em que alguém a monte a partir de algo que o cliente digitou:
        `../../etc` num `open()` custa o processo inteiro, e o custo de recusá-lo é um `if`."""

        target = (self._root / key).resolve()
        if not target.is_relative_to(self._root.resolve()):
            raise ValueError(f"Chave de storage fora da raiz: {key!r}")
        return target

    def _write(self, key: str, content: bytes, content_type: str) -> None:
        target = self._path_of(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        target.with_name(target.name + _CONTENT_TYPE_SUFFIX).write_text(
            content_type,
            encoding="utf-8",
        )

    def _read(self, key: str) -> tuple[bytes, str]:
        target = self._path_of(key)
        try:
            content = target.read_bytes()
        except FileNotFoundError as exc:
            raise ObjectNotFoundError(f"Objeto não encontrado: {key}") from exc

        sidecar = target.with_name(target.name + _CONTENT_TYPE_SUFFIX)
        content_type = (
            sidecar.read_text(encoding="utf-8").strip()
            if sidecar.exists()
            else "application/octet-stream"
        )
        return content, content_type

    def _remove(self, key: str) -> None:
        target = self._path_of(key)
        target.unlink(missing_ok=True)
        target.with_name(target.name + _CONTENT_TYPE_SUFFIX).unlink(missing_ok=True)

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await asyncio.to_thread(self._write, key, content, content_type)

    async def get(self, key: str) -> tuple[bytes, str]:
        return await asyncio.to_thread(self._read, key)

    async def delete(self, key: str) -> None:
        """Apagar chave que não existe **não** é erro — o `missing_ok` é intencional.

        Quem chama isto é a purga de leituras órfãs, que apaga linha e objeto: se o objeto já
        sumiu, insistir num erro só faria a purga parar no meio e deixar a linha pra trás."""

        await asyncio.to_thread(self._remove, key)


class S3ObjectStorage:
    """O adaptador de produção: API S3, contra MinIO ou contra a AWS.

    **S3-compatível, e não S3**: o produto é vendido self-hosted, e amarrar a AWS contradiz
    isso — daí o `endpoint_url` configurável. O `nginx` não expõe o bucket: ele não é público, e
    todo byte sai pela API, atrás dos guards."""

    def __init__(
        self,
        *,
        bucket: str,
        endpoint_url: str | None,
        access_key: str | None,
        secret_key: str | None,
        region: str,
    ) -> None:
        import aioboto3

        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    def _client(self) -> Any:
        return self._session.client("s3", endpoint_url=self._endpoint_url)

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        async with self._client() as client:
            await client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )

    async def get(self, key: str) -> tuple[bytes, str]:
        from botocore.exceptions import ClientError

        async with self._client() as client:
            try:
                response = await client.get_object(Bucket=self._bucket, Key=key)
            except ClientError as exc:
                code = exc.response.get("Error", {}).get("Code")
                if code in {"NoSuchKey", "404", "NoSuchBucket"}:
                    raise ObjectNotFoundError(f"Objeto não encontrado: {key}") from exc
                raise

            content = await response["Body"].read()
            return content, response.get("ContentType") or "application/octet-stream"

    async def delete(self, key: str) -> None:
        """O `delete_object` do S3 é idempotente — chave inexistente responde 204. Mesmo
        contrato do adaptador local, e pelo mesmo motivo."""

        async with self._client() as client:
            await client.delete_object(Bucket=self._bucket, Key=key)


def get_object_storage() -> ObjectStorage:
    """O storage que a config manda — **sem** `set_*_factory` e sem linha em `mount_routes`.

    É a mesma resolução do `get_email_sender`: infra não é tabela de módulo, então o `core` a
    escolhe sozinho. Um app de negócio pede `ObjectStorageDep` e pronto."""

    config = get_config()

    if config.STORAGE_BACKEND == "s3":
        return S3ObjectStorage(
            bucket=config.S3_BUCKET,
            endpoint_url=config.S3_ENDPOINT_URL,
            access_key=config.S3_ACCESS_KEY,
            secret_key=config.S3_SECRET_KEY,
            region=config.S3_REGION,
        )

    return LocalDirectoryStorage(config.STORAGE_LOCAL_DIR)


ObjectStorageDep = Annotated[ObjectStorage, Depends(get_object_storage)]
