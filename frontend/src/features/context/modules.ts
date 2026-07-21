/**
 * Os metadados de navegação dos módulos de negócio, chaveados pela chave do módulo.
 *
 * **Este arquivo encolhe até sumir**, pelo mesmo motivo que o `src/api/modules.py` do backend:
 * um descritor pertence ao módulo que ele descreve. `frota` já saiu daqui — o descritor dela mora
 * em `features/frota/module.ts` e este catálogo o **compõe**, que era o caminho anunciado desde a
 * `05`. `refeicoes` fica como declaração solta até a fase 2, e o catálogo continua existindo
 * depois disso: alguém tem de montar a lista.
 *
 * **Por que o label e o path moram aqui, e não vêm do backend.** A spec `frontend/04` supõe que
 * a nav venha "dos descritores expostos no contexto", mas o `GET /api/organizacoes/{orgId}/me`
 * devolve `modules` como **lista de chaves** — os `ModuleNav` do descritor só saem pelo
 * `GET /api/organizacoes/{orgId}/modulos`, que a `backend/05` fechou para `platform_admin`.
 * Um `collaborator` leva 403 lá, e é justamente ele quem precisa do menu.
 *
 * O que **não** se perde com isso: a promessa comercial. Ligar `refeicoes` para uma Empresa faz
 * o item aparecer **sem deploy de frontend**, porque quem decide a visibilidade continua sendo
 * o entitlement (a chave em `modules`) — este catálogo só diz como o item se chama. E as telas
 * do módulo têm de existir no frontend de qualquer forma: um label vindo do servidor apontaria
 * para uma rota que só um deploy cria.
 */

import { UtensilsCrossed } from 'lucide-react'

import type { NavIcon } from '#/features/context/nav'
import type { Persona } from '#/features/context/types'
import { FROTA_MODULE } from '#/features/frota/module'

export type ModuleNavDescriptor = {
  /** A chave estável do módulo — a mesma que o backend usa em rota e entitlement. */
  key: string
  label: string
  /** Relativo à organização ativa; quem prefixa o `orgId` é a `nav.ts`. */
  path: string
  /** As personas que o módulo atende. Espelha `ModuleDescriptor.personas`. */
  personas: readonly Persona[]
  /** Espelha `ModuleNav.icon` — o componente em vez do nome, porque um nome exigiria um mapa
   *  nome→ícone em algum lugar, e esse mapa é o "toque a casca" que o catálogo evita. */
  icon: NavIcon
}

export const MODULE_CATALOG: readonly ModuleNavDescriptor[] = [
  {
    key: 'refeicoes',
    label: 'Refeições',
    path: '/refeicoes',
    personas: ['company_admin', 'collaborator', 'partner'],
    icon: UtensilsCrossed,
  },
  FROTA_MODULE,
]
