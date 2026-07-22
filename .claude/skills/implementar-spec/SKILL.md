---
name: implementar-spec
description: Use when the user asks to implement, build, or continue work on a numbered spec from .claude/specs/ in the Superapp Widelab (apps/administrativo) project — e.g. "implementa a fundação do backend", "bora fazer a spec 03", "continua o login".
---

# Implementar spec

Executa uma spec existente em `.claude/specs/` até seus critérios de aceite passarem, de
verdade — não até "parece pronto".

## Passo a passo

1. **Leia a spec inteira antes de escrever código.** Uma spec é uma pasta:
   `<backend|frontend>/NN-nome/spec.md` é a decisão, e `como-ficou.md` (quando existe) é o que
   de fato aconteceu. Leia os dois de toda spec listada em `Depende de:` — e nas dependências
   já implementadas o **`como-ficou.md` é o mais importante dos dois**, porque é ele que
   registra onde o código divergiu do texto. Cada `spec.md` declara `Estado:` no topo, e
   `00-visao-geral.md` tem o índice; use-os como mapa, mas **confirme lendo os diretórios e o
   `git log`** — spec é intenção, não retrato do repo. Se uma dependência ainda não está no
   código, **pare e avise o usuário** antes de prosseguir.
2. Releia `Fora de escopo`. É tão vinculante quanto o resto da spec: não implemente nada
   listado ali, mesmo que pareça extensão natural.
3. Implemente seguindo a arquitetura do `CLAUDE.md`:
   - **Backend hexagonal** — `modules/<mod>/{domain,application,adapters}`; `application`
     recebe repositório via `Depends`, nunca importa `adapters`; **módulo não importa outro
     módulo**; app de negócio depende só de `core` + contracts do kernel (`current_user`,
     `current_organization`, `require_permission`, `require_module`); adicionar módulo é uma
     linha em `mount_routes`, sem tocar `core`. Schema **só** via Alembic; tabelas
     `snake_case` sem `T0xx`.
   - **Frontend** — `features/<domínio>` (schema zod → types `z.infer` → api → hooks TanStack
     Query → components → lib); alias `#/*`; rotas Next em português; a org ativa é o `{orgId}`
     da URL, nunca header.
   - Onde a spec dá um trecho de código, esse trecho é o **contrato**: pode adaptar nomes
     locais, mas não a forma (assinatura, payload, nome de campo, formato de rota).
4. Depois de implementar, **verifique cada item de `Critérios de aceite` individualmente**:
   - Rodando o comando ou requisição que o critério descreve e observando o resultado real
     (não assumindo que passa porque o código parece certo). Endpoints: suba o servidor e faça
     a requisição de verdade (`curl -i`), incluindo os casos de **403** (papel/tenant/módulo
     errado) e **401** (sem sessão) que as specs deste projeto cobram.
   - Critérios de frontend com interação visual (foco, responsividade, `prefers-reduced-motion`)
     exigem `npm run dev` + browser real — não declare cumprido por leitura de código.
   - **Backend: todo critério de aceite testável vira teste em `backend/tests/` e roda com `uv
     run pytest`, na mesma entrega.** `curl` uma vez prova que funcionou hoje; teste prova que
     continua funcionando. Frontend: specs que citam testes, escreva os casos citados antes de
     `npm run test`.
5. Rode as verificações estáticas que se aplicam (backend: `uv run ruff check .` + `uv run
   mypy src`; frontend: `npm run typecheck` + `npm run lint`). Se as skills de projeto `run`/
   `verify` já existirem, use-as; senão, use as globais `/run` e `/verify`. Passar lint e
   typecheck **não** é o mesmo que a spec estar implementada.
6. Reporte ao usuário **critério por critério**: quais passaram e como foram verificados. Se
   algum não passou ou não pôde ser verificado (ex.: sem browser disponível), diga isso
   explicitamente — não declare sucesso genérico.

## Quando a spec e o código divergem

Se, ao ler a spec, você perceber que o código já foi além dela ou diverge de propósito, pare
e confirme com o usuário antes de "corrigir" o código de volta pra bater com o texto — a spec
pode estar desatualizada, não o código.

Ao terminar, registre o resultado **na pasta da spec**, no formato da casa:

- No `spec.md`, atualize **só** a linha `Estado:` do topo — `✅ implementada (<hash>, <data>)`,
  terminando com `Ver [`como-ficou.md`](./como-ficou.md).` **O resto do `spec.md` não se
  toca:** ele é a decisão registrada, e reescrevê-lo pra bater com o código apaga a única prova
  do que se pensava antes de implementar.
- Crie (ou aumente) o **`como-ficou.md`** irmão, listando toda divergência entre o texto e o
  código, **com o porquê**. Uma spec implementada não vira documentação do código nem é
  reescrita pra fingir que acertou de primeira: `spec.md` é a decisão, `como-ficou.md` é o que
  aconteceu, e a distância entre os dois é o aprendizado — as duas coisas ficam. Se um critério
  de aceite deixou de valer com o tempo (ex.: "`src/modules/` vazio", verdade só até a spec
  seguinte), diga isso no `como-ficou.md` em vez de apagá-lo do `spec.md`.

  O `como-ficou.md` começa assim, pra ficar legível sozinho:

  ```markdown
  # NN — Título da spec — Como ficou

  Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
  é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
  aconteceu — e a divergência entre os dois é o aprendizado.

  ## Como ficou
  ...
  ```
- Atualize o **`Índice de specs`** e o estado da fase em `00-visao-geral.md`. Ali é onde o estado
  mora: o que a spec entregou, o que ficou de dívida e o que ela bloqueia ou destrava.
- No `CLAUDE.md`, atualize **só a tabela de specs** (o ✅/📋) e, se a entrega mudou onde o código
  vive ou criou uma regra nova, o `Mapa do repositório` e as `Convenções`. **Não** descreva ali o
  que a spec entregou, nem contagem de teste ou de rota: o `CLAUDE.md` é mapa e regra, e estado
  duplicado nele envelhece e passa a mentir. Se a vontade for escrever um parágrafo de "agora o
  sistema faz X", ele vai pro `Como ficou` ou pro `Índice de specs`, não pro `CLAUDE.md`.

## Não faça

- Não expanda escopo "já que estou aqui" — um campo a mais no schema, uma opção não pedida.
  Se parecer necessário, é uma spec nova (`nova-spec`), não um adendo silencioso.
- Não marque um critério de aceite como cumprido sem tê-lo observado rodando.
- Não introduza autorização no token de sessão, nem tenant em header — são decisões travadas.
