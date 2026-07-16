import { describe, expect, it } from 'vitest'

import { loginErrorMessage } from '#/features/auth/lib/login-error'
import { ApiError } from '#/lib/api'

describe('loginErrorMessage', () => {
  it('não revela qual credencial falhou no 401', () => {
    const message = loginErrorMessage(new ApiError(401, 'unauthorized', 'Invalid credentials.'))
    expect(message).toBe('E-mail ou senha incorretos.')
    expect(message).not.toMatch(/senha está|e-mail não existe|não cadastrado/i)
  })

  it('orienta a repetir quando o servidor falha', () => {
    expect(loginErrorMessage(new ApiError(500, 'persistence_error', 'boom'))).toMatch(
      /tente de novo/i,
    )
  })

  it('trata falha de rede sem jargão', () => {
    expect(loginErrorMessage(new TypeError('Failed to fetch'))).toMatch(/conectar/i)
  })

  it('repassa a mensagem do backend em erros de negócio', () => {
    expect(loginErrorMessage(new ApiError(403, 'forbidden', 'Usuário desativado.'))).toBe(
      'Usuário desativado.',
    )
  })
})
