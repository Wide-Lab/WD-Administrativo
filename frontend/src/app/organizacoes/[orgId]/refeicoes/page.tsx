'use client'

import { ModuleGuard } from '#/features/context/components/module-guard'
import { ModulePlaceholder } from '#/features/context/components/module-placeholder'

/** Refeições — fase 2. Hoje só a casca guardada pelo entitlement: quem monta o conteúdo é o
 *  módulo, quando ele existir, e é ele que herda este `ModuleGuard`. */
export default function Page() {
  return (
    <ModuleGuard moduleKey="refeicoes" label="Refeições">
      <ModulePlaceholder name="Refeições" phase="fase 2" />
    </ModuleGuard>
  )
}
