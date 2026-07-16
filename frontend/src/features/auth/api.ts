import { userSchema } from '#/features/auth/schema'
import type { LoginInput, User } from '#/features/auth/types'
import { ApiError, apiFetch } from '#/lib/api'

/** Valida as credenciais. Em caso de sucesso o backend seta o cookie httpOnly de sessão —
 *  não há token na resposta, e o frontend nunca guarda um. */
export async function login(input: LoginInput): Promise<void> {
  await apiFetch<void>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export async function logout(): Promise<void> {
  await apiFetch<void>('/api/auth/logout', { method: 'POST' })
}

/** Identidade do usuário logado, ou `null` se não há sessão.
 *
 *  401 aqui não é falha: é a resposta normal de quem não está logado. Traduzir pra `null`
 *  mantém "não logado" como um estado, não como um erro — e é o que impede esta query de
 *  disparar o redirecionamento global de 401 (`providers.tsx`) num laço. */
export async function getMe(): Promise<User | null> {
  try {
    return userSchema.parse(await apiFetch<unknown>('/api/me'))
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null
    throw error
  }
}
