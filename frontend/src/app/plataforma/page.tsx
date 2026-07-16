import { Card, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'

/** A home da persona Plataforma — placeholder, como as outras.
 *
 *  A lista de tenants e a tela de entitlements moram aqui quando chegarem: hoje o `/eu` de cada
 *  organização já diz o que ela contratou, e ligar módulo é `PUT /api/organizacoes/{orgId}/modulos/{chave}`
 *  ou a CLI. Abrir um tenant específico é navegar pra `/organizacoes/{orgId}` — o seletor de
 *  organização é a `frontend/05`, e adivinhá-lo aqui seria fazer a spec seguinte por engano. */
export default function Page() {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Plataforma</h1>
        <p className="text-sm text-muted">
          A Widelab como operadora: tenants, convênios e módulos vendidos.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">A operação chega aqui</CardTitle>
          <CardDescription>
            Esta área é cross-tenant e não tem organização ativa. A lista de tenants e a gestão de
            entitlements ganham tela nas próximas entregas; para abrir uma organização, navegue
            para <code className="font-mono text-xs">/organizacoes/&#123;orgId&#125;</code>.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  )
}
