'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'

/** O outro lado do `ModuleGuard`: o módulo **está** habilitado, e ainda não tem tela.
 *
 *  Existe pra que a guarda de entitlement seja verificável hoje — sem uma rota de módulo, o
 *  critério 3 da spec não teria como ser observado. Some quando o módulo real chegar (fases
 *  2/3), e é a única coisa nesta casca que uma fase seguinte apaga em vez de estender. */
export function ModulePlaceholder({ name, phase }: { name: string; phase: string }) {
  return (
    <div className="space-y-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{name}</h1>
        <p className="text-sm text-muted">Habilitado para esta organização.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Em construção</CardTitle>
          <CardDescription>
            Esta organização contratou {name}, e as telas chegam na {phase}. O que existe hoje é a
            casca: o menu e esta rota só aparecem porque o módulo está habilitado aqui.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  )
}
