import { ChevronDown } from 'lucide-react'
import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

/** Um `<select>` nativo, e não o de Radix.
 *
 *  A escolha é deliberada: o seletor de veículo/condutor é usado no celular, de pé, e o nativo
 *  abre a roleta do sistema — que é mais rápida e mais acessível que qualquer listbox que eu
 *  desenhe. Radix Select entraria se precisássemos de busca, grupos ou conteúdo rico na opção;
 *  não é o caso de nenhuma tela desta entrega.
 *
 *  A seta é desenhada por fora (`appearance-none` + ícone absoluto) porque a nativa não aceita
 *  cor de token, e o hex dela viria do sistema operacional. */
export function Select({ className, children, ...props }: ComponentProps<'select'>) {
  return (
    <div className="relative">
      <select
        className={cn(
          'flex h-10 w-full appearance-none rounded-md border border-line bg-surface px-3 py-2 pr-9 text-sm text-text',
          'transition-[color,border-color,box-shadow] duration-150',
          'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'aria-invalid:border-danger aria-invalid:focus-visible:ring-danger/40',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden
        className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted"
      />
    </div>
  )
}
