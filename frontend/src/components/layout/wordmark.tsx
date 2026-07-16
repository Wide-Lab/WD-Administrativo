import { cn } from '#/lib/utils'

/** Marca da plataforma. O ponto é a única peça em preenchimento primário — o mesmo azul do
 *  botão de ação, ligando marca e ação sem repetir o gradiente. */
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cn('inline-flex items-baseline gap-2 text-text', className)}>
      <span className="text-lg font-semibold tracking-tight">Widelab</span>
      <span
        aria-hidden
        className="size-1.5 rounded-full bg-linear-to-r from-primary to-primary-2"
      />
      <span className="text-lg font-light tracking-tight text-muted">Superapp</span>
    </span>
  )
}
