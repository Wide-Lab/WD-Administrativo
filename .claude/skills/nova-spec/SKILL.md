---
name: nova-spec
description: Use when the user asks to plan, spec out, or design a new piece of work for the Superapp Widelab (apps/administrativo) before writing code — e.g. "cria uma spec para X", "vamos planejar o app de refeições", "como vamos especificar isso".
---

# Nova spec

Escreve uma spec nova em `.claude/specs/` para o Superapp Widelab, seguindo exatamente o
formato já estabelecido pelas specs existentes. Leia `.claude/specs/00-visao-geral.md`
inteiro antes de escrever qualquer coisa — ele contém as decisões já tomadas e adiadas que
toda spec nova precisa respeitar ou justificar explicitamente por que está mudando.

## Onde o arquivo vai

`.claude/specs/frontend/NN-nome-curto.md` ou `.claude/specs/backend/NN-nome-curto.md`. `NN`
é o próximo número livre naquela pasta, sequencial. Um **app de negócio** (Refeições, Carro)
é um módulo próprio: suas specs entram numerando a partir do fim da fila da pasta
correspondente e o módulo pluga no núcleo pelo contrato de `backend/05-modulos-e-entitlements.md`
(descritor + rotas sob `/api/organizacoes/{orgId}/<chave>`), sem tocar `core`. Se a spec não
pertence a nenhuma das duas pastas (infra, ambas as pontas), pergunte ao usuário onde ela
mora antes de criar o arquivo.

Depois de criar o arquivo, adicione uma linha no índice de `.claude/specs/00-visao-geral.md`
(seção "Índice de specs"), na posição certa da ordem de implementação — cada spec ali declara
suas dependências, então a ordem importa.

## Estrutura obrigatória

```markdown
# NN — Título curto

**Depende de:** outra(s) spec(s) por nome de arquivo, ou "nada".
**Entrega:** uma frase objetiva do artefato final — módulo, endpoint, tela, componente.

## Objetivo

1–3 frases. Qual pergunta do usuário essa spec responde, não uma lista de features.

## Fora de escopo

O que deliberadamente não entra, e por quê (ganha spec própria depois, ou foi decidido não
fazer). Toda spec do projeto tem essa seção; é o que impede escopo de crescer silenciosamente
durante a implementação.

## [corpo específico da spec]

Decisões técnicas com a razão junto, não só a conclusão. Trechos de código só quando o formato
exato importa (schema, assinatura de função, payload) — não pseudocódigo. Prefira tabela a
prosa para: campos de um schema, papéis, mapeamento de estado, rotas.

## Critérios de aceite

Lista numerada, cada item verificável observando o sistema rodando (uma requisição, uma tela,
um output de comando) — não "o código está limpo".
```

## Convenções do projeto que a spec tem que respeitar

Antes de escrever, confira que a spec nova não contradiz estas (todas em `00-visao-geral.md`):

- **Kernel `auth`+`access`; apps de negócio dependem só de `core` + contracts do kernel**
  (`current_user`, `current_organization`, `require_permission`, `require_module`), nunca um
  módulo do outro. Backend hexagonal; adicionar módulo não toca `core`.
- **Tenant no path** (`/api/organizacoes/{orgId}/...`), nunca header/sessão. **Rotas em
  português**; nomes de tabela/coluna/enum em inglês `snake_case`, sem `T0xx`. Schema só via
  Alembic.
- **Entitlement por tenant** com negação padrão e `require_module` → 403 no backend.
- **Organização tem tipo único e imutável**; integridade de convênio no banco.

## Tom e nível de detalhe — copie das specs existentes

Leia pelo menos duas specs existentes (uma de frontend, uma de backend) antes de escrever,
pra calibrar o tom. Características a reproduzir:

- **Toda decisão não óbvia tem o "porquê" ao lado**, não só o "o quê" (ex.: `backend/02` explica
  por que a sessão é HS256 e não RS256; `backend/03` por que tenant no path e não header).
- **"Fora de escopo" cita specs por nome de arquivo**, pra quem ler daqui a três semanas não
  redescobrir o raciocínio.
- Escrita em português, direta, sem "provavelmente"/"talvez" — a spec é uma decisão, não um
  brainstorm. Se algo está genuinamente em aberto, isso vira **pergunta ao usuário** antes de
  escrever a spec, não ambiguidade dentro dela.
- Números e limiares explícitos (TTL de sessão, contraste, política de senha) — nunca
  "razoável".

## Antes de terminar

Releia "Decisões tomadas" de `00-visao-geral.md` e confirme que nada na spec nova a contradiz.
Se contradiz de propósito, diga isso **explicitamente ao usuário** — mudar uma decisão já
tomada é escolha do usuário, não algo pra spec decidir sozinha.

Não implemente a spec nesta skill. Pra isso, use `implementar-spec` depois que o usuário
aprovar o texto.
