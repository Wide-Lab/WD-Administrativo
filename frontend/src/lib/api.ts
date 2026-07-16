// Cliente de fetch da aplicação. Todo caminho é relativo (`/api/*`): em dev o rewrite do
// Next leva pro FastAPI, em produção o nginx de borda. Nenhum componente conhece a URL do
// backend.

/** Erro de uma resposta não-2xx, já traduzido do corpo do backend. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

/** O `core` do backend responde erro como `{code, message, details}`; o FastAPI responde
 *  erro de validação como `{detail}`. Aceita os dois e nunca deixa o parse derrubar a UI. */
async function toApiError(response: Response): Promise<ApiError> {
  let code = 'http_error'
  let message = 'Não foi possível concluir a operação. Tente novamente.'

  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null) {
      const payload = body as { code?: unknown; message?: unknown; detail?: unknown }
      if (typeof payload.code === 'string') code = payload.code
      if (typeof payload.message === 'string') message = payload.message
      else if (typeof payload.detail === 'string') message = payload.detail
    }
  } catch {
    // Resposta sem corpo JSON (502 do proxy, timeout): fica a mensagem genérica.
  }

  return new ApiError(response.status, code, message)
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    // A sessão é um cookie httpOnly — sem isto ela não viaja e nada autentica.
    credentials: 'include',
    headers: {
      ...(init?.body === undefined ? {} : { 'Content-Type': 'application/json' }),
      ...init?.headers,
    },
  })

  if (!response.ok) throw await toApiError(response)

  // 204 (logout, troca de senha) não tem corpo pra desserializar.
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T
  }

  return (await response.json()) as T
}
