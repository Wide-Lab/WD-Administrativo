'use client'

import Link from 'next/link'

import { Button } from '#/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { Skeleton } from '#/components/ui/skeleton'
import { ROLE_LABEL } from '#/features/context/lib/labels'
import { AcceptInvitationForm } from '#/features/onboarding/components/accept-invitation-form'
import { OnboardingShell } from '#/features/onboarding/components/onboarding-shell'
import { invitationErrorMessage } from '#/features/onboarding/lib/onboarding-error'
import { useInvitation } from '#/features/onboarding/use-invitation'

/** A tela de aceite de convite — o caminho de entrada do Colaborador e do staff da Empresa, que
 *  não se auto-cadastram (backend 06).
 *
 *  Três estados, e o token da URL decide qual: carregando, convite que não abre (404/410), e o
 *  formulário. Nenhum deles conta se o e-mail já tinha conta — nem o de erro, nem o de sucesso.
 *
 *  Não há guarda de sessão aqui: a rota é pública porque quem vai aceitar ainda não tem sessão.
 *  Quem já está logado e abre o link também não é barrado — o token é de um e-mail, não de uma
 *  sessão, e é o backend que decide o que fazer com ele. */
export function InvitationScreen({ token }: { token: string }) {
  const { invitation, isLoading, error } = useInvitation(token)

  if (isLoading) {
    return (
      <OnboardingShell>
        <Card aria-busy>
          <CardHeader>
            <span className="sr-only">Abrindo o convite…</span>
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-4 w-full" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-56 w-full" />
          </CardContent>
        </Card>
      </OnboardingShell>
    )
  }

  // Convite que não abre. A saída é pedir outro a quem convidou — e é a única saída honesta:
  // esta tela não tem como emitir um convite novo, e um botão de "reenviar" mentiria (não há
  // rota pra isso; ver o que a `backend/06` não entregou).
  if (invitation === null) {
    return (
      <OnboardingShell>
        <Card>
          <CardHeader>
            <CardTitle>Convite indisponível</CardTitle>
            <CardDescription>{invitationErrorMessage(error)}</CardDescription>
          </CardHeader>
          <CardContent>
            {/* Quem chegou aqui pode já ter conta — e o convite vencido não a tranca pra fora.
                O link não afirma que ela existe: é a mesma porta que qualquer visitante vê. */}
            <Button asChild variant="secondary" className="w-full">
              <Link href="/entrar">Já tem uma conta? Entrar</Link>
            </Button>
          </CardContent>
        </Card>
      </OnboardingShell>
    )
  }

  return (
    <OnboardingShell>
      <Card>
        <CardHeader>
          <CardTitle>Aceitar convite</CardTitle>
          <CardDescription>
            Você foi convidado para{' '}
            <span className="font-medium text-text">{invitation.organization_name}</span> como{' '}
            <span className="font-medium text-text">{ROLE_LABEL[invitation.role]}</span>. Defina uma
            senha para entrar.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AcceptInvitationForm token={token} invitation={invitation} />
        </CardContent>
      </Card>
    </OnboardingShell>
  )
}
