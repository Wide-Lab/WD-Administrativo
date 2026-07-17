import Link from 'next/link'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { OnboardingShell } from '#/features/onboarding/components/onboarding-shell'
import { RegisterPartnerForm } from '#/features/onboarding/components/register-partner-form'

export const metadata = {
  title: 'Cadastro de parceiro · Superapp Widelab',
}

/** A única rota pública que **cria** uma organização, e a única criação que não passa por um
 *  `platform_admin`: o Parceiro é organização de primeiro nível e se cadastra sozinho (backend
 *  06). Colaborador e staff não têm tela equivalente, e não é esquecimento — eles são
 *  convidados, e é o que separa os dois caminhos de entrada. */
export default function CadastroParceiroPage() {
  return (
    <OnboardingShell width="md">
      <Card>
        <CardHeader>
          <CardTitle>Criar conta de parceiro</CardTitle>
          <CardDescription>
            Cadastre seu negócio e a sua conta de administrador. As Empresas que trabalham com você
            fazem o convênio depois — é ato delas.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <RegisterPartnerForm />
        </CardContent>
      </Card>

      <p className="text-center text-sm text-muted">
        Já tem uma conta?{' '}
        <Link href="/entrar" className="text-primary-fg underline-offset-4 hover:underline">
          Entrar
        </Link>
      </p>
    </OnboardingShell>
  )
}
