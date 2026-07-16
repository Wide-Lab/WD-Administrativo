'use client'

import { PackageX } from 'lucide-react'
import type { ReactNode } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'
import { useOrgContext } from '#/features/context/use-org-context'

/** A rota de um módulo que esta Empresa não contratou.
 *
 *  Não é erro nem culpa de quem clicou: é um serviço que o tenant não tem. O texto não convida
 *  a "tentar de novo" e não diz "acesso negado" — quem resolve é quem compra, não quem navega. */
function ModuleUnavailable({ label }: { label: string }) {
  return (
    <Card className="mx-auto mt-12 max-w-lg">
      <CardHeader className="items-start">
        <span className="mb-2 inline-flex size-10 items-center justify-center rounded-md bg-surface-2 text-muted">
          <PackageX className="size-5" aria-hidden />
        </span>
        <CardTitle>Módulo não disponível</CardTitle>
        <CardDescription>
          {label} não está habilitado para esta organização. Fale com a Widelab para contratar.
        </CardDescription>
      </CardHeader>
      <CardContent />
    </Card>
  )
}

/** Guarda a rota de um módulo pelo entitlement do tenant.
 *
 *  Só renderiza `children` com o módulo habilitado — e é isso que garante o critério 3 da spec:
 *  as chamadas do módulo saem de dentro dos filhos, então elas nunca chegam a ser disparadas.
 *  Checar depois de montar (e desmontar no erro) já teria batido no backend.
 *
 *  Enquanto o contexto carrega, não renderiza nada: montar otimista dispararia exatamente a
 *  chamada que este guard existe pra impedir. */
export function ModuleGuard({
  moduleKey,
  label,
  children,
}: {
  moduleKey: string
  label: string
  children: ReactNode
}) {
  const { modules, isLoading } = useOrgContext()

  if (isLoading) return null
  if (!modules.includes(moduleKey)) return <ModuleUnavailable label={label} />

  return <>{children}</>
}
