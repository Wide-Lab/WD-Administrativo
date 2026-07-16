/** O último `orgId` visitado, e a única coisa que esta feature guarda no navegador.
 *
 *  **Não é a organização ativa** — essa é sempre o `orgId` da URL, e nada aqui a decide. Isto
 *  serve a um caso só: logo após o login não há `orgId` no path, e alguém precisa dizer pra
 *  onde ir. Um palpite, portanto, não uma fonte de verdade: quem valida se ele ainda vale é
 *  `homePathFor`, contra os vínculos do `/me/contexto`.
 *
 *  Guardar isto num store de "org ativa" seria a versão errada desta feature: passaria a haver
 *  duas respostas pra "onde estou" — a URL e o store — e elas divergiriam no primeiro link
 *  colado. */

const STORAGE_KEY = 'widelab.last-org'

/** `localStorage` não é garantido: não existe no SSR, e o acesso **lança** quando cookies de
 *  terceiros/armazenamento estão bloqueados (Safari privado, iframe). Um palpite de rota não
 *  vale derrubar a casca, então toda falha vira "não lembro". */
export function readLastOrgId(): string | null {
  if (typeof window === 'undefined') return null

  try {
    return window.localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function rememberOrgId(orgId: string): void {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(STORAGE_KEY, orgId)
  } catch {
    // Sem persistência, o pós-login cai no primeiro vínculo — degrada, não quebra.
  }
}

/** Esquece a última organização. A área da Plataforma é cross-tenant e não tem `orgId`: quem
 *  está lá não está em organização nenhuma, e é isso que o pós-login precisa saber. */
export function forgetLastOrgId(): void {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // idem.
  }
}
