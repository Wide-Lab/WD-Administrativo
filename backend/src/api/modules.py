"""Os módulos de negócio que a plataforma sabe oferecer mas que ainda não têm código — hoje, só
`refeicoes`.

**Este arquivo é provisório e some.** Um descritor pertence ao módulo que ele descreve, e é lá
que ele vai morar quando `refeicoes` (fase 2) existir: `modules/refeicoes/module.py` declara o
seu, com router, e `mount_routes` troca a linha daqui pela de lá. Enquanto isso, ele vive aqui,
no ponto de composição — que não é `core` e não finge ser um módulo.

**A `frota` já fez essa mudança** (spec 10): o descritor dela saiu daqui e virou
`modules/frota/module.py`, com `router` e `grants` de verdade. É o precedente que `refeicoes`
vai seguir — e a prova de que o caminho de saída anunciado pela `05` funciona.

Por que existir antes do módulo: entitlement precisa de uma chave pra ligar, e a plataforma
precisa saber o que sabe vender. Sem isto, `PUT /modulos/refeicoes` recusaria a chave e a
`05` entregaria um mecanismo sem nada pra mecanizar. Com isto, a venda de Refeições já pode
ser registrada antes de Refeições existir — que é exatamente o que "ligar um flag, sem deploy"
promete.

Note o que **não** está aqui: capability nenhuma. `refeicoes` declara `grants={}` — módulo que
ainda não concede nada, que é a verdade dele até a fase 2. Uma capability de módulo é design do
módulo (`catalog.write`, `invoices.approve_hr` são exemplos da spec, não decisões tomadas), e
chutá-la agora seria fazer fase 2 num placeholder."""

from src.core.modules import ModuleDescriptor, ModuleNav

REFEICOES = ModuleDescriptor(
    key="refeicoes",
    name="Refeições",
    personas=["company_admin", "collaborator", "partner"],
    grants={},
    nav=ModuleNav(label="Refeições", path="/refeicoes"),
)
"""Fase 2 — tickets, catálogo por convênio, split e fatura. Sem `router`: só a chave existe."""
