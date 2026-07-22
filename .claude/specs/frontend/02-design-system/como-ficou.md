# 02 — Design system — Como ficou

Registro pós-implementação. A decisão original está em [`spec.md`](./spec.md), e **não**
é reescrita pra bater com o código: o texto de lá é o que foi decidido, este é o que
aconteceu — e a divergência entre os dois é o aprendizado.

## Como ficou

Todos os critérios batem. O que mudou em relação à tabela de paleta:

- **Quatro tokens de contraste entraram**, filhos diretos do critério 5 e da regra "`primary`
  não vai em texto pequeno":
  - `primary-fg` (`#7aa2ff`) — o azul **de texto/link**, clareado pra passar AA sobre `bg`.
    `primary` (`#2f6bff`) ficou restrito a **preenchimento e ícones**, como a regra mandava.
  - `on-primary` (`#f4f8ff`) — texto/ícone **sobre** preenchimento primário.
  - `on-accent` (`#0b0f17`) — texto sobre preenchimento claro (`success`/`warning`), onde
    texto claro reprovaria.
  - `ring` — alias de `primary`, isolado num token próprio pra o anel de foco poder mudar sem
    arrastar a ação primária junto.
- **Duas camadas, não uma:** `--palette-*` (hex, `:root`) → `@theme inline` (utilidades do
  Tailwind via `var()`). O `inline` é deliberado: mantém as utilidades apontando pra variável
  em vez de congelar o hex, o que deixa um tema futuro (ex.: claro) ser só redeclarar
  `--palette-*` num escopo, sem recompilar. A spec dizia "tema escuro, sem alternância" nesta
  fase — continua verdade; isto é só o caminho deixado aberto.
- **`/design-system`** é a vitrine viva dos primitivos (button, input, card, badge, skeleton),
  não prevista na spec. É onde se confere foco, motion e contraste sem caçar tela.
- Geist + Geist Mono via `@fontsource-variable`, raios como tokens (`--radius-*`), como
  especificado.
