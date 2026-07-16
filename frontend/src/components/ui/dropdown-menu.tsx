'use client'

/** O menu suspenso — primitivo shadcn sobre o Radix, no formato dos outros de `components/ui`.
 *
 *  A `02-design-system` entregou button/input/card/badge/skeleton e parou ali; este entra com o
 *  seletor de organização (`frontend/05`), que precisa de um controle de escolha entre opções
 *  mutuamente exclusivas. Radix em vez de um `<div>` com `onClick` porque o que ele traz não é
 *  aparência: foco preso no menu, navegação por seta, `Esc` pra fechar, `aria-checked` no item
 *  marcado e colisão com a borda da janela. */

import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import { Check } from 'lucide-react'
import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

export const DropdownMenu = DropdownMenuPrimitive.Root
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger
export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup

export function DropdownMenuContent({
  className,
  sideOffset = 6,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 min-w-56 overflow-hidden rounded-md border border-line bg-surface p-1 shadow-lg',
          className,
        )}
        {...props}
      />
    </DropdownMenuPrimitive.Portal>
  )
}

export function DropdownMenuLabel({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Label>) {
  return (
    <DropdownMenuPrimitive.Label
      className={cn('px-2 py-1.5 text-xs font-medium text-muted', className)}
      {...props}
    />
  )
}

export function DropdownMenuSeparator({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Separator>) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cn('-mx-1 my-1 h-px bg-line', className)}
      {...props}
    />
  )
}

/** O item de escolha. `RadioItem` e não `Item` porque as opções são mutuamente exclusivas — é
 *  o que dá `aria-checked` de graça e faz o leitor de tela anunciar qual está ativa. */
export function DropdownMenuRadioItem({
  className,
  children,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.RadioItem>) {
  return (
    <DropdownMenuPrimitive.RadioItem
      className={cn(
        'relative flex cursor-pointer select-none items-center gap-3 rounded-sm py-2 pr-2 pl-8 text-sm',
        // Sem `outline-none`: o item não desenha anel próprio, então vale o anel de foco global
        // do `styles.css`. O `data-[highlighted]` é o hover/seta do Radix, que não é foco.
        'transition-colors data-[highlighted]:bg-surface-2',
        'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
        className,
      )}
      {...props}
    >
      <span className="absolute left-2 flex size-4 items-center justify-center">
        <DropdownMenuPrimitive.ItemIndicator>
          <Check className="size-4 text-primary-fg" />
        </DropdownMenuPrimitive.ItemIndicator>
      </span>
      {children}
    </DropdownMenuPrimitive.RadioItem>
  )
}
