import { describe, expect, it } from 'vitest'

import { safeNextPath } from '#/features/auth/lib/next-path'

describe('safeNextPath', () => {
  it('preserva caminho interno', () => {
    expect(safeNextPath('/organizacoes/abc/me')).toBe('/organizacoes/abc/me')
  })

  it('preserva query string do destino', () => {
    expect(safeNextPath('/faturas?status=analise')).toBe('/faturas?status=analise')
  })

  it('cai no fallback quando não há destino', () => {
    expect(safeNextPath(null)).toBe('/')
    expect(safeNextPath(undefined)).toBe('/')
    expect(safeNextPath('')).toBe('/')
  })

  it('recusa URL absoluta', () => {
    expect(safeNextPath('https://evil.example')).toBe('/')
  })

  it('recusa protocol-relative', () => {
    expect(safeNextPath('//evil.example')).toBe('/')
  })

  it('recusa barra invertida disfarçada de caminho', () => {
    expect(safeNextPath('/\\evil.example')).toBe('/')
  })

  it('respeita o fallback informado', () => {
    expect(safeNextPath(null, '/entrar')).toBe('/entrar')
  })
})
