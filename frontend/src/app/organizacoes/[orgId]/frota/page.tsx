'use client'

import { ModuleGuard } from '#/features/context/components/module-guard'
import { ModulePlaceholder } from '#/features/context/components/module-placeholder'

/** Frota — fase 3. Mesma casca guardada de Refeições; o conteúdo é do módulo. */
export default function Page() {
  return (
    <ModuleGuard moduleKey="frota" label="Frota">
      <ModulePlaceholder name="Frota" phase="fase 3" />
    </ModuleGuard>
  )
}
