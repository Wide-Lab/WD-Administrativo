import { describe, expect, it } from 'vitest'

import { cn } from './utils'

describe('cn', () => {
  it('junta classes e descarta valores falsy', () => {
    expect(cn('a', false && 'b', undefined, 'c')).toBe('a c')
  })

  it('resolve conflitos do tailwind mantendo a última classe', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4')
  })
})
