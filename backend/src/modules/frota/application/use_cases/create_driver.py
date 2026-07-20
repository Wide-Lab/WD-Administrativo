from src.modules.frota.application.dtos.commands import CreateDriverCommand
from src.modules.frota.application.ports.unit_of_work import FrotaUnitOfWorkProtocol
from src.modules.frota.domain.entities import Driver, NewDriver


class CreateDriverUseCase:
    def __init__(self, uow: FrotaUnitOfWorkProtocol) -> None:
        self._uow = uow

    async def execute(self, command: CreateDriverCommand) -> Driver:
        """Cadastra um condutor na Empresa ativa.

        **A frota não valida que o `user_id` é membro da Empresa**, e é decisão: validar exigiria
        ler `memberships`, que é do `access`, e a alternativa (uma porta nova no `core`) gastaria
        privilégio de kernel numa conveniência. Um `user_id` obsoleto não vaza nada — pra
        alcançar qualquer rota daqui o chamador já precisa de vínculo ativo e do entitlement, e
        um condutor apontando pra quem não é mais membro nunca é alcançado. Quem escolhe o
        `user_id` é a tela do gestor, a partir do `GET .../membros` que a `04` já entrega.

        Returns:
            Driver:
                O condutor criado.

        Raises:
            ConflictError:
                Se este `user_id` já for condutor nesta Empresa.
        """

        async with self._uow as uow:
            driver = await uow.drivers.create(
                NewDriver(
                    name=command.name,
                    user_id=command.user_id,
                    license_number=command.license_number,
                    license_category=command.license_category,
                    license_expires_at=command.license_expires_at,
                    status=command.status,
                )
            )
            await uow.commit()
            return driver
