'use client'

import { Suspense } from 'react'

import { MileageScreen } from '#/features/frota/components/mileage-screen'

/** Quilometragem. `Suspense` pelo mesmo motivo da tela de viagens: o período vive na URL. */
export default function Page() {
  return (
    <Suspense fallback={null}>
      <MileageScreen />
    </Suspense>
  )
}
