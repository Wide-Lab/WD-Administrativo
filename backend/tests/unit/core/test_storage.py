"""O `LocalDirectoryStorage` contra um diretório de verdade — sem Docker e sem serviço nenhum.

É esse "sem serviço nenhum" que justifica o adaptador existir: ele é o gêmeo do
`LoggingEmailSender`, e é o que faz `docker compose up db` continuar bastando pra dev e a suíte
inteira rodar sem MinIO."""

from pathlib import Path

import pytest

from src.core.storage import LocalDirectoryStorage, ObjectNotFoundError

CHAVE = "01890000-0000-7000-8000-000000000001/frota/hodometro/abc.jpg"


class TestPutEGet:
    async def test_o_que_entra_e_o_que_sai(self, tmp_path: Path) -> None:
        storage = LocalDirectoryStorage(tmp_path)

        await storage.put(CHAVE, b"bytes-da-foto", "image/jpeg")

        assert await storage.get(CHAVE) == (b"bytes-da-foto", "image/jpeg")

    async def test_o_content_type_sobrevive_ao_round_trip(self, tmp_path: Path) -> None:
        """`odometer_readings` **não** guarda o `content-type` — quem o guarda é o storage, e é
        ele que o devolve pro `GET .../hodometro/{saida|chegada}` servir os bytes com o tipo
        certo. Inferi-lo da extensão seria adivinhar."""

        storage = LocalDirectoryStorage(tmp_path)

        await storage.put(CHAVE, b"png", "image/png")

        _, content_type = await storage.get(CHAVE)
        assert content_type == "image/png"

    async def test_cria_os_diretorios_do_prefixo(self, tmp_path: Path) -> None:
        """A chave começa pelo `organization_id` e tem três níveis; nenhum deles existe antes."""

        storage = LocalDirectoryStorage(tmp_path)

        await storage.put(CHAVE, b"x", "image/jpeg")

        assert (tmp_path / CHAVE).is_file()

    async def test_sobrescrever_a_mesma_chave_funciona(self, tmp_path: Path) -> None:
        storage = LocalDirectoryStorage(tmp_path)

        await storage.put(CHAVE, b"primeiro", "image/jpeg")
        await storage.put(CHAVE, b"segundo", "image/png")

        assert await storage.get(CHAVE) == (b"segundo", "image/png")


class TestGetDeChaveInexistente:
    async def test_levanta_o_erro_do_contrato(self, tmp_path: Path) -> None:
        """**Não** um `FileNotFoundError` cru: quem consome a porta não pode precisar saber qual
        adaptador está do outro lado pra tratar o caso mais comum de todos."""

        storage = LocalDirectoryStorage(tmp_path)

        with pytest.raises(ObjectNotFoundError):
            await storage.get(CHAVE)

    async def test_o_erro_carrega_a_chave(self, tmp_path: Path) -> None:
        storage = LocalDirectoryStorage(tmp_path)

        with pytest.raises(ObjectNotFoundError, match="abc.jpg"):
            await storage.get(CHAVE)


class TestDelete:
    async def test_apaga_bytes_e_content_type(self, tmp_path: Path) -> None:
        storage = LocalDirectoryStorage(tmp_path)
        await storage.put(CHAVE, b"x", "image/jpeg")

        await storage.delete(CHAVE)

        assert not (tmp_path / CHAVE).exists()
        assert not list(tmp_path.rglob("*.content-type"))

    async def test_apagar_o_que_nao_existe_nao_e_erro(self, tmp_path: Path) -> None:
        """Quem chama isto é a purga de leituras órfãs. Se o objeto já sumiu, insistir num erro
        só faria a purga parar no meio e deixar a linha pra trás."""

        storage = LocalDirectoryStorage(tmp_path)

        await storage.delete(CHAVE)  # não levanta


class TestChaveForaDaRaiz:
    async def test_recusa_travessia_de_diretorio(self, tmp_path: Path) -> None:
        """A chave é sempre montada pelo servidor, então isto nunca deveria disparar — é defesa
        em profundidade contra o dia em que alguém a monte a partir de algo que o cliente digitou.

        `../../etc/passwd` num `open()` custa o processo inteiro; recusá-lo custa um `if`."""

        storage = LocalDirectoryStorage(tmp_path / "raiz")

        with pytest.raises(ValueError, match="fora da raiz"):
            await storage.put("../fora.jpg", b"x", "image/jpeg")
