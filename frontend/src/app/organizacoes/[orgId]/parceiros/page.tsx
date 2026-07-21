'use client'

import { AgreementsScreen } from '#/features/organization/components/agreements-screen'

/** Os convênios da organização ativa (`frontend/08`).
 *
 *  Uma rota, dois sentidos de leitura: numa Empresa é "Parceiros", num Parceiro é "Empresas
 *  atendidas". O mesmo `GET .../convenios` dos dois lados — só o rótulo sabe de que lado se
 *  está. */
export default function Page() {
  return <AgreementsScreen />
}
