import type { ComponentProps } from 'react'

import { cn } from '#/lib/utils'

// `animate-pulse` é zerado pelo bloco prefers-reduced-motion em styles.css.
export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('animate-pulse rounded-md bg-surface-2', className)} {...props} />
}
