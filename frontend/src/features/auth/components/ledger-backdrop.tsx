/** Pauta de folha de registro atrás do login.
 *
 *  O superapp nasce pra aposentar o papel: o ticket de refeição acertado à mão uma vez por
 *  mês e a folha de uso da frota preenchida à caneta. A pauta é esse papel — desbotando sob
 *  o cartão que o substitui. É a única licença poética da tela; o resto é disciplina.
 *
 *  Desenhada só com o token `line` (nenhum hex novo) e mascarada num radial pra não encostar
 *  nas bordas. `black`/`transparent` na máscara são alfa, não cor de tema. */
export function LedgerBackdrop() {
  const fade = 'radial-gradient(115% 85% at 50% 42%, black 0%, transparent 70%)'

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 opacity-60"
      style={{
        backgroundImage:
          'repeating-linear-gradient(to bottom, var(--palette-line) 0 1px, transparent 1px 28px)',
        maskImage: fade,
        WebkitMaskImage: fade,
      }}
    />
  )
}
