# 02 — Design system

**Depende de:** `frontend/01-fundacao.md`.
**Entrega:** os tokens de cor, tipografia, foco e motion do superapp — a base visual que
todas as telas (login, casca, personas) consomem.

## Objetivo

Cravar a linguagem visual derivada do protótipo (`planolabbeneficios.lovable.app`): tema
escuro, superfícies em camadas, **azul como cor de ação primária**. Diferente da Central
(onde o acento marca *posição/foco* e é proibido em superfície), aqui o azul **pode**
preencher botão primário — é uma plataforma de produto, não uma bancada de instrumentos.

## Fora de escopo

Componentes de domínio e telas — são das specs seguintes. Aqui é só o sistema: tokens,
tipografia, primitivos shadcn base (button, input, card, badge, skeleton) estilizados.

## Paleta (proposta, derivada do protótipo — precisa do seu aval)

> Extraída à mão dos screenshots; ajuste fino de hex é decisão de vocês. Nomeada por papel,
> não por matiz, pra trocar sem renomear.

| Token | Hex | Papel |
|---|---|---|
| `bg` | `#0B0F17` | fundo da aplicação (navy quase preto) |
| `surface` | `#141A24` | cards, painéis |
| `surface-2` | `#1B2230` | superfície elevada / hover |
| `line` | `#232B39` | bordas 1px |
| `text` | `#E7EAF2` | texto principal (nunca branco puro) |
| `muted` | `#8A93A6` | texto secundário |
| `primary` | `#2F6BFF` | ação primária, links, seleção |
| `primary-2` | `#22D3EE` | fim do gradiente do botão primário (azul→ciano) |
| `success` | `#22C55E` | "a receber", pronto p/ pagamento |
| `warning` | `#F59E0B` | em análise |
| `danger` | `#EF4444` | erro/destrutivo |

Os passos do "como funciona" (azul/roxo/âmbar/verde) e os pontos do workflow de faturas
(âmbar=RH, azul=financeiro, verde=pago) são **estados semânticos**, não uma sexta cor de
marca — mapeiam pra `primary`/`warning`/`success`.

## Tipografia

Fonte da casa: **Geist** (`@fontsource-variable/geist`), `Geist Mono` para números
tabulares (valores, quilometragem, saldos). Sem fonte display separada nesta fase — títulos
são Geist em peso alto. Escala modular contida; números financeiros sempre com
`font-variant-numeric: tabular-nums`.

## Regras

- **Tema escuro, sem alternância** nesta fase (o protótipo é nativamente escuro).
- **Azul preenche a ação primária** (botão principal, com gradiente `primary`→`primary-2`,
  como o "Começar agora"). Ações secundárias são `surface-2` com borda `line`.
- **Profundidade por luminosidade**, cards com borda 1px `line`; sombra é discreta e opcional,
  não é o mecanismo principal de elevação.
- **Anel de foco visível** em `primary`, sempre — acessibilidade não é opcional.
- **Motion contido**, desliga com `prefers-reduced-motion: reduce`.
- Contraste AA obrigatório: `muted` sobre `bg` passa 4,5:1; `primary` em texto pequeno é
  evitado (usa `text`), reservado a preenchimento e ícones.

## Critérios de aceite

1. Os tokens existem como variáveis CSS/Tailwind e nenhuma tela usa hex solto fora deles.
2. Botão primário, secundário, input, card, badge e skeleton existem estilizados e batem com
   o protótipo.
3. Foco é visível em todos os interativos; `prefers-reduced-motion` zera as animações.
4. Números financeiros usam `tabular-nums`.
5. Contraste AA verificado nos pares texto/fundo do sistema.
