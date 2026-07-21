import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

export function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(
        'flex min-h-20 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-text',
        'placeholder:text-muted',
        'transition-[color,border-color,box-shadow] duration-150',
        'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40',
        'disabled:cursor-not-allowed disabled:opacity-50',
        'aria-invalid:border-danger aria-invalid:focus-visible:ring-danger/40',
        className,
      )}
      {...props}
    />
  )
}
