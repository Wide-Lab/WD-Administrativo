import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

export function Input({ className, type, ...props }: ComponentProps<'input'>) {
  return (
    <input
      type={type}
      className={cn(
        'flex h-10 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-text',
        'placeholder:text-muted',
        'transition-[color,border-color,box-shadow] duration-150',
        'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-danger aria-invalid:focus-visible:ring-danger/40',
        'file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-text',
        className,
      )}
      {...props}
    />
  )
}
