/**
 * As sete capabilities da frota — espelho de `frota/domain/permissions.py`.
 *
 * **Toda diferença de tela sai daqui, e nenhuma sai de `persona`.** O motivo está na spec:
 * `company_admin` e `manager` recebem grants idênticos da frota e são personas diferentes,
 * enquanto o que separa o `collaborator` é capability. Ramificar por persona acertaria por
 * acidente hoje e erraria no primeiro papel novo.
 *
 * As strings são namespaced por `frota.` porque o `register_module` do backend recusa a subida de
 * quem sair do namespace — o prefixo não é convenção, é regra imposta na inicialização.
 *
 * Vale a regra do `Can`: **esconder é ergonomia, o guard é do backend.** Cada uma destas tem um
 * `require_permission` do outro lado, e quem chamar a rota na mão leva 403 igual.
 */
export const FrotaPermissions = {
  /** Ver a lista de veículos. `collaborator` **tem** — ele precisa escolher o carro. */
  VEHICLES_READ: 'frota.vehicles.read',
  VEHICLES_WRITE: 'frota.vehicles.write',
  /** Sem o `collaborator`: ele lança em nome de si mesmo, e a lista de condutores não é dele. */
  DRIVERS_READ: 'frota.drivers.read',
  DRIVERS_WRITE: 'frota.drivers.write',
  /** Ver os usos de **toda** a Empresa — e o que decide o escopo do `GET /usos`. */
  USAGES_READ: 'frota.usages.read',
  USAGES_WRITE: 'frota.usages.write',
  /** Lançar e encerrar uso em que o condutor é você. **Não** inclui apagar. */
  USAGES_WRITE_OWN: 'frota.usages.write_own',
} as const

/** Uma capability do kernel, e não da frota: o select de vínculo do condutor a consulta.
 *
 *  Fica aqui porque é a única do `access` que esta feature usa, e porque a ausência dela é caso
 *  normal — `manager` tem `drivers.write` e pode não ter `members.read`. */
export const MEMBERS_READ = 'members.read'
