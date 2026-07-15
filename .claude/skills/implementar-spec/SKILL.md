---
name: implementar-spec
description: Use when the user asks to implement, build, or continue work on a numbered spec from .claude/specs/ in the Superapp Widelab (apps/administrativo) project — e.g. "implementa a fundação do backend", "bora fazer a spec 03", "continua o login".
---

# Implementar spec

Executa uma spec existente em `.claude/specs/` até seus critérios de aceite passarem, de
verdade — não até "parece pronto".

## Passo a passo

1. **Leia a spec inteira antes de escrever código**, junto com toda spec listada em
   `Depende de:`. As specs descrevem intenção, não necessariamente o estado do repo — o
   projeto começou só com specs, sem `backend/` nem `frontend/`. Confirme o que já existe
   lendo os diretórios (e `git log`, se houver), não confiando no texto. Se uma dependência
   ainda não está no código, **pare e avise o usuário** antes de prosseguir.
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
   - Specs que citam testes: escreva os casos citados antes de rodar `npm run test`.
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
pode estar desatualizada, não o código. Ao terminar, se a implementação mudou uma decisão,
atualize a spec e o índice de `00-visao-geral.md`.

## Não faça

- Não expanda escopo "já que estou aqui" — um campo a mais no schema, uma opção não pedida.
  Se parecer necessário, é uma spec nova (`nova-spec`), não um adendo silencioso.
- Não marque um critério de aceite como cumprido sem tê-lo observado rodando.
- Não introduza autorização no token de sessão, nem tenant em header — são decisões travadas.
