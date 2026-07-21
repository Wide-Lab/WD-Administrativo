'use client'

import { Suspense } from 'react'

import { UsagesScreen } from '#/features/frota/components/usages-screen'

/** Viagens — a home do módulo.
 *
 *  `Suspense` porque a tela lê `useSearchParams` (os filtros **são** a URL), e o Next exige o
 *  limite pra poder renderizar o resto da página sem esperar a query string. */
export default function Page() {
  return (
    <Suspense fallback={null}>
      <UsagesScreen />
    </Suspense>
  )
}
