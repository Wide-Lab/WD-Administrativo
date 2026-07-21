'use client'

import { Suspense } from 'react'

import { PeopleScreen } from '#/features/organization/components/people-screen'

/** Membros e convites da organização ativa — abas de uma tela só (`frontend/08`).
 *
 *  O `Suspense` é exigência do `useSearchParams` no App Router: sem ele o build marca a rota
 *  inteira como dinâmica. A aba e o filtro de status vivem na URL, então a tela lê search params
 *  de propósito. */
export default function Page() {
  return (
    <Suspense fallback={null}>
      <PeopleScreen />
    </Suspense>
  )
}
