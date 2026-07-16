"""Os módulos de negócio que a plataforma sabe oferecer — hoje, só como chaves.

**Este arquivo é provisório e some.** Um descritor pertence ao módulo que ele descreve, e é
lá que ele vai morar quando `refeicoes` (fase 2) e `frota` (fase 3) existirem:
`modules/refeicoes/module.py` declara o seu, com router, e `mount_routes` troca a linha daqui
pela de lá. Enquanto isso, eles vivem aqui, no ponto de composição — que não é `core` e não
finge ser um módulo.

Por que existir antes do módulo: entitlement precisa de uma chave pra ligar, e a plataforma
precisa saber o que sabe vender. Sem isto, `PUT /modulos/refeicoes` recusaria a chave e a
`05` entregaria um mecanismo sem nada pra mecanizar. Com isto, a venda de Refeições já pode
ser registrada antes de Refeições existir — que é exatamente o que "ligar um flag, sem deploy"
promete.

Note o que **não** está aqui: `permissions`. Uma capability de módulo é design do módulo
(`catalog.write`, `invoices.approve_hr` são exemplos da spec, não decisões tomadas), e chutá-la
agora seria fazer fase 2 num placeholder. Ver `Como ficou` na `backend/05`."""

from src.core.modules import ModuleDescriptor, ModuleNav

REFEICOES = ModuleDescriptor(
    key="refeicoes",
    name="Refeições",
    personas=["company_admin", "collaborator", "partner"],
    permissions=[],
    nav=ModuleNav(label="Refeições", path="/refeicoes"),
)
"""Fase 2 — tickets, catálogo por convênio, split e fatura. Sem `router`: só a chave existe."""

FROTA = ModuleDescriptor(
    key="frota",
    name="Frota",
    personas=["company_admin", "collaborator"],
    permissions=[],
    nav=ModuleNav(label="Frota", path="/frota"),
)
"""Fase 3 — veículos, registro de uso, relatórios. Sem `router`: só a chave existe."""
