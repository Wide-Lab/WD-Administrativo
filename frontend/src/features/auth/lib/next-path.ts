/** Sanitiza o `?next=` antes de navegar pra ele.
 *
 *  Sem isto, `/entrar?next=https://evil.example` faria o próprio login carimbar um redirect
 *  pra fora do domínio (open redirect) logo depois de autenticar. Só caminho interno passa:
 *  começa com uma barra e não com duas (`//host` é protocol-relative e sai do site). */
export function safeNextPath(next: string | null | undefined, fallback = '/'): string {
  if (!next) return fallback
  if (!next.startsWith('/')) return fallback
  if (next.startsWith('//')) return fallback
  // `\` é normalizado pra `/` por alguns navegadores — `/\evil.example` viraria externo.
  if (next.startsWith('/\\')) return fallback
  return next
}
