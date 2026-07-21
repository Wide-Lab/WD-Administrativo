'use client'

import type { ReactNode } from 'react'

import { ModuleGuard } from '#/features/context/components/module-guard'
import { FrotaTabs } from '#/features/frota/components/frota-tabs'

/**
 * A casca das quatro telas da frota.
 *
 * O `ModuleGuard` vive **aqui**, e não em cada página, porque o entitlement é o mesmo pras quatro:
 * quem não contratou `frota` não passa em nenhuma, e o guard no layout garante isso sem depender
 * de alguém lembrar de repeti-lo na tela nova. Quem tenta a rota na mão leva 403 do
 * `require_module` de qualquer forma — o guard evita a ida, não a substitui.
 *
 * As abas ficam dentro do guard pelo mesmo motivo que o `ModuleGuard` não renderiza os filhos
 * enquanto carrega: um menu de módulo não contratado não deve piscar na tela.
 */
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <ModuleGuard moduleKey="frota" label="Frota">
      <div className="space-y-6">
        <FrotaTabs />
        {children}
      </div>
    </ModuleGuard>
  )
}
