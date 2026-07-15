import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

const buttonVariants = cva(
  cn(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium',
    'transition-[color,background-color,box-shadow,filter] duration-150',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
    'disabled:pointer-events-none disabled:opacity-50',
    '[&_svg]:size-4 [&_svg]:shrink-0',
  ),
  {
    variants: {
      variant: {
        // Azul preenche a ação primária: gradiente primary → primary-2.
        primary:
          'bg-linear-to-r from-primary to-primary-2 text-on-primary shadow-sm hover:brightness-110 active:brightness-95',
        // Ação secundária: superfície elevada com borda `line`.
        secondary: 'border border-line bg-surface-2 text-text hover:bg-line active:bg-surface',
        outline: 'border border-line bg-transparent text-text hover:bg-surface-2',
        ghost: 'bg-transparent text-text hover:bg-surface-2',
        destructive:
          'bg-danger text-on-primary shadow-sm hover:brightness-110 active:brightness-95',
        link: 'text-primary-fg underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 gap-1.5 px-3 text-xs',
        md: 'h-10 px-4',
        lg: 'h-11 px-6 text-base',
        icon: 'size-10',
      },
    },
    defaultVariants: { variant: 'primary', size: 'md' },
  },
)

export type ButtonProps = ComponentProps<'button'> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
  }

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />
}

export { buttonVariants }
