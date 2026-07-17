import type { ReactNode } from 'react'

import { Wordmark } from '#/components/layout/wordmark'
import { LedgerBackdrop } from '#/features/auth/components/ledger-backdrop'
import { cn } from '#/lib/utils'

/** A moldura das telas públicas de entrada — cartão central sobre `bg`, com a marca acima.
 *
 *  É a composição que o `/entrar` fixou na spec 03, e as duas telas do onboarding são irmãs
 *  dele: quem chega aqui está no mesmo lugar da jornada (fora, querendo entrar) e deve ver a
 *  mesma casa. A `LedgerBackdrop` vem da feature `auth` de propósito, e não copiada: é a mesma
 *  folha de registro desbotando sob o cartão que a substitui.
 *
 *  O `/entrar` não foi movido pra cá. Ele compõe as mesmas três peças inline, e reescrevê-lo
 *  seria mexer numa tela entregue pra ganhar três linhas. */
export function OnboardingShell({
  children,
  width = 'sm',
}: {
  children: ReactNode
  /** O aceite é um formulário curto; o auto-cadastro tem o dobro de campos e respira melhor. */
  width?: 'sm' | 'md'
}) {
  return (
    <main className="relative flex min-h-dvh items-center justify-center px-6 py-12">
      <LedgerBackdrop />

      <div className={cn('relative w-full space-y-8', width === 'sm' ? 'max-w-sm' : 'max-w-md')}>
        <div className="flex justify-center">
          <Wordmark />
        </div>

        {children}
      </div>
    </main>
  )
}
