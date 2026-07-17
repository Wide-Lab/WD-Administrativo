import { InvitationScreen } from '#/features/onboarding/components/invitation-screen'

export const metadata = {
  title: 'Aceitar convite · Superapp Widelab',
}

/** O token é opaco e vem do e-mail — é ele, e não uma sessão, que autoriza a tela.
 *
 *  A página só o desembrulha do path (no App Router, `params` é uma promessa) e entrega pra
 *  casca cliente: quem busca o convite é o TanStack Query, no navegador, como todo dado deste
 *  frontend. Buscá-lo aqui no servidor colocaria o token no HTML e faria o Next querer
 *  pré-renderizar uma rota que só existe por link. */
export default async function ConvitePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params

  return <InvitationScreen token={token} />
}
