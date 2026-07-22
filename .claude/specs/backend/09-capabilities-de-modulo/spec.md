# 09 — Capabilities de módulo

**Estado:** ✅ implementada (2026-07-20) — fecha o furo que a `05` registrou e destrava a
`backend/10`. 86 testes (69 + 17). Ver [`como-ficou.md`](./como-ficou.md).
**Depende de:** `backend/04-membros-e-autorizacao/spec.md` (o `PermissionReader`, o
`require_permission`, o mapa `PERMISSIONS_BY_ROLE`), `backend/05-modulos-e-entitlements/spec.md`
(o `ModuleDescriptor`, o registry, o `mount_module`), `backend/07-testes/spec.md` (a suíte que os
critérios abaixo estendem).
**Entrega:** o mecanismo que faz uma capability declarada por um módulo de negócio chegar a um
papel — o furo que a `05` registrou no próprio `Como ficou` e que trava o primeiro endpoint do
primeiro app de negócio.

## Objetivo

Hoje um módulo declara `permissions=["catalog.write"]` no descritor e **isso não liga em nada**:
quem decide quem tem o quê é `PERMISSIONS_BY_ROLE`, que é do `access`, e módulo não importa
módulo. Um `require_permission("catalog.write")` negaria todo mundo, pra sempre. Esta spec faz o
descritor declarar **papel→capabilities** em vez de uma lista plana, e o `PermissionReader` somar
os descritores do registry ao mapa do kernel — de forma que um app de negócio continue plugando
com **uma linha** em `mount_routes` e **zero** mudança em `core` pra autorizar as próprias rotas.

## Fora de escopo

- **Qualquer app de negócio.** Frota é a `backend/10`; esta spec entrega só o mecanismo, provado
  por um módulo de teste descartável — a mesma receita que a `04` e a `05` usaram pra provar
  `require_permission` e `mount_module`.
- **Capability configurável por tenant.** Papel→permissão segue **fixo e em código**, como a
  `04` decidiu. Uma Empresa que queira que o seu `manager` não veja relatório de frota não é caso
  do produto agora; se um dia for, é papel customizável por tenant — migração deliberada, com
  spec própria, não um `if` aqui.
- **Papel novo.** Nenhum papel entra nem sai; `ROLES_BY_ORGANIZATION_TYPE` não muda, e portanto o
  `CHECK` gerado de `memberships` não muda. Módulo declara o que os papéis **existentes** podem
  fazer nele.
- **Expor as capabilities de módulo no `/me`.** O `GET /api/organizacoes/{orgId}/me` já devolve
  `permissions`, e elas passarão a incluir as de módulo automaticamente — mas **desenhar a tela**
  a partir disso é da spec de frontend da frota (`frontend/07`).
- **Como o Parceiro alcança um módulo.** Segue em aberto desde a `05`: `require_module` nega toda
  organização que não é Empresa. Frota não tem Parceiro, então a `10` não esbarra nisso; quem vai
  esbarrar é Refeições, e é lá que a decisão nasce.

## Sem migration

Nada aqui toca o schema. Permissão é **código** — nunca houve tabela de permissão, e continua não
havendo. `memberships.role` e o `CHECK` gerado a partir de `ROLES_BY_ORGANIZATION_TYPE` seguem
idênticos, porque nenhum papel muda. Logo: **nenhuma revisão de Alembic**, e o `alembic check`
continua limpo.

> **A segunda metade dessa frase é falsa, e já era quando foi escrita** — a primeira se sustentou.
> `alembic check` não estava limpo desde a `0003`. Ver o último item do `Como ficou`.

## O descritor passa a declarar papel→capabilities

`ModuleDescriptor.permissions` — hoje `Sequence[Permission]` — vira um mapa, e o campo plano
volta como propriedade derivada:

```python
type ModuleRole = str
"""O papel a que o módulo concede uma capability. `str` pelo mesmo motivo que `ModulePersona`:
`Role` é enum do `access`, e o `core` não importa módulo."""


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    key: ModuleKey
    name: str
    personas: Sequence[ModulePersona]
    grants: Mapping[ModuleRole, frozenset[Permission]]
    nav: ModuleNav
    router: APIRouter | None = field(default=None, compare=False)

    @property
    def permissions(self) -> frozenset[Permission]:
        """O catálogo: toda capability que este módulo declara, sem quem a recebe."""
```

`ModuleRole` é `str` e não `Role` porque a alternativa é o `core` importar o enum do `access` — a
seta apontando pra fora, o erro que a `04` evitou ao fazer `Permission` ser `str` e a `05`
repetiu em `ModulePersona`. O preço é que um papel inexistente só é detectável pelo `access`; a
seção "Validação na subida" abaixo é o que faz esse preço ser pago **na subida**, não em runtime.

`grants` e não `permissions` para o mapa porque o nome antigo passou a significar outra coisa —
a lista plana era catálogo, o mapa é concessão. Manter o nome com semântica nova faria toda
leitura de código da `05` mentir.

## Capability de módulo é namespaced pela chave do módulo

**Regra:** toda capability declarada em `grants` tem que começar com `<chave-do-módulo>.`.
`frota` declara `frota.vehicles.write`, não `vehicles.write`. Quem não cumprir **não sobe**:
`register_module` levanta `RuntimeError`.

São três problemas resolvidos por uma regra:

1. **Escalada de privilégio.** Sem isso, um módulo declara `grants={"collaborator":
   {"organizations.write"}}` e um Colaborador qualquer passa a provisionar tenant. O mecanismo
   desta spec **soma** ao mapa do kernel, então sem a regra ele é uma porta pra qualquer módulo
   se dar permissão de plataforma — por malícia ou por copiar-colar. Com ela, o espaço de nomes
   do kernel é inalcançável por construção: `organizations.write` não começa com `frota.`.
2. **Colisão entre módulos.** Frota e Refeições vão os dois querer `reports.read`. Sem prefixo,
   quem registrasse por último venceria, e um `manager` de frota ganharia relatório de refeições
   de brinde.
3. **Legibilidade no ponto de uso.** `require_permission("frota.vehicles.write")` diz de quem é
   a regra sem abrir o descritor.

A checagem é mecânica (`permission.startswith(f"{descriptor.key}.")`) e mora em
`register_module`, não em `mount_module`: registrar é o ato que põe o descritor no mapa que o
`PermissionReader` vai somar, e é lá que a invariante tem que valer.

Pra não obrigar ninguém a repetir a chave, o descritor ganha um helper:

```python
FROTA.permission("vehicles.write")  # → "frota.vehicles.write"
```

## Validação na subida, não em runtime

Como `ModuleRole` é `str`, um `grants={"colaborador": ...}` (em português, ou com typo) não
casaria com papel nenhum e **concederia silenciosamente nada** — o pior modo de falha possível:
403 em produção, e ninguém sabe por quê. O `access` valida os nomes, porque é ele o dono de
`Role`:

`validate_module_grants()` — exportada pelo `access`, chamada **uma vez** no fim de
`mount_routes`, depois de todos os `mount_module`. Ela varre `registered_modules()` e levanta
`RuntimeError` se um descritor conceder a:

| Caso | Por quê |
|---|---|
| um papel que não existe em `Role` | typo; o silêncio é a falha |
| `platform_admin` | ver abaixo — módulo não concede à Plataforma |

Isto é a mesma divisão de trabalho do resto do projeto, um andar acima: o `core` impede o que
consegue enxergar (o namespace), o `access` impede o que só ele enxerga (o papel), e as duas
falhas acontecem na subida — um container que sobe com autorização errada é pior do que um
container que não sobe.

O `mount_routes` do `access` não ganha uma quinta linha de porta: `validate_module_grants()` é
uma chamada de verificação, não o registro de um `Reader`. O teto de quatro portas que a `05`
declarou segue de pé.

## Módulo não concede a `platform_admin`

`require_permission` afrouxa pra `platform_admin`; `require_module` **não** afrouxa pra ninguém
(`05`). Se um módulo pudesse conceder a `platform_admin`, a assimetria quebraria pelo lado de
dentro: a Widelab teria capability num módulo cujo entitlement ela mesma não pode ter — a
organização `platform` não é `company`, e a FK de `module_entitlements` a impede de contratar.
Seria uma permissão que nunca passa do `require_module` que vem antes dela: código morto que
parece privilégio.

Então `grants` com chave `platform_admin` é erro de subida, e o `PermissionReader` **não** soma
capability de módulo à parcela de plataforma. Concretamente, no `SqlAlchemyMembershipReader`:

| Fonte | Kernel (`PERMISSIONS_BY_ROLE`) | Módulos (`grants`) |
|---|---|---|
| papel do vínculo em `organization_id` | soma | **soma** |
| `platform_admin` (cross-tenant) | soma | **não soma** |

A Widelab conserta vínculo e vende módulo. Ela não opera a frota do cliente.

## Onde a soma acontece

`SqlAlchemyMembershipReader.get_permissions` — o único lugar. Ele já é o tradutor
(o `core` pergunta capability, o `access` responde a partir de papel); ganha uma segunda fonte
para a parcela do vínculo:

```python
granted |= permissions_for(role) | module_permissions_for(role)
```

`module_permissions_for(role)` mora em `access/domain/permissions.py`, ao lado de
`permissions_for`, e varre `registered_modules()` do `core`. **O `access` importar
`src.core.modules` é legal e não é exceção**: módulo importa `core` à vontade; o que é proibido é
o contrário, e módulo importar módulo. A seta segue apontando pra dentro — o `core` continua sem
saber que papel existe, e Frota continua sem saber que `access` existe.

Nenhuma assinatura de porta muda: `PermissionReader.get_permissions` tem a mesma forma, e
`require_permission` não é tocado. Um app de negócio autoriza as próprias rotas com o mesmo
`require_permission(...)` que o kernel usa — que é exatamente a promessa da `05`.

## O que muda em quem já existe

`src/api/modules.py` — os descritores placeholder de `refeicoes` e `frota` trocam
`permissions=[]` por `grants={}`. Um mapa vazio é módulo que ainda não declara nada, que é a
verdade dos dois até as fases 2 e 3. `GET /api/organizacoes/{orgId}/modulos` segue devolvendo o
catálogo pela propriedade `permissions` derivada, sem mudança de payload.

## Testes — na mesma entrega

Duas camadas, e a divisão importa porque metade disto é regra pura:

- **`tests/unit/`** (sem Docker) — a validação do namespace, a validação de papel, a recusa de
  `platform_admin`, e `module_permissions_for` somando os descritores. É regra pura sobre um
  registry em memória.
- **`tests/integration/`** — o caminho completo por requisição, com um **módulo de teste
  descartável** (chave `smoke`, com uma rota atrás de `require_module` + `require_permission`),
  registrado pela app de teste. É o que prova que a capability chega ao 200.

**Armadilha de implementação:** `_modules` do registry é **global de processo**, e um teste que
registra um módulo falso vaza pros seguintes — inclusive fazendo `GET /modulos` de outro teste
listar o `smoke`. A suíte precisa de uma fixture que salve e restaure o registry em volta desses
testes; sem ela, a ordem dos testes vira parte do resultado.

## Critérios de aceite

1. Um módulo de teste declara `grants={"manager": {"smoke.reports.read"}}` e uma rota atrás de
   `require_module("smoke") + require_permission("smoke.reports.read")`. Com o entitlement ligado
   na Empresa, um `manager` recebe **200** naquela rota — a capability chegou ao papel sem
   nenhuma linha em `PERMISSIONS_BY_ROLE`.
2. Na mesma rota e com o mesmo entitlement, um `collaborator` (a quem o módulo não concede)
   recebe **403**; sem sessão, **401**.
3. Com o entitlement **desligado**, o mesmo `manager` do critério 1 recebe **403** — a capability
   de módulo não passa por cima do `require_module`, e a ordem das duas negações continua a da
   `05`.
4. `GET /api/organizacoes/{orgId}/me` como aquele `manager` traz `smoke.reports.read` em
   `permissions`, ao lado das capabilities de kernel do papel; como `collaborator`, não traz.
5. Registrar um descritor cuja `grants` contém uma capability **fora do namespace** da chave
   (ex.: `frota` concedendo `organizations.write`, ou `reports.read` sem prefixo) levanta
   `RuntimeError` em `register_module` — a app **não sobe**.
6. `validate_module_grants()` levanta `RuntimeError` quando um descritor concede a um papel
   inexistente (ex.: `"colaborador"`) e quando concede a `platform_admin`; com todos os
   descritores válidos, é no-op.
7. Um `platform_admin` **não** recebe as capabilities de módulo na soma: numa Empresa com o
   módulo `smoke` ligado e sem vínculo próprio, ele segue com as permissões de kernel de
   plataforma e **sem** `smoke.reports.read` — verificável pelo `permissions` do
   `GET /api/organizacoes/{orgId}/me`.
8. `refeicoes` e `frota` seguem registrados e vendáveis com `grants={}`: `PUT
   /api/organizacoes/{orgId}/modulos/frota` continua ligando o flag, e `GET .../modulos` devolve
   o catálogo com a lista de capabilities vazia para os dois.
9. `mypy src tests` limpo e `ruff check .` limpo com o descritor novo — em especial, nenhum
   `type: ignore` nascido da troca de `Sequence` por `Mapping`.
