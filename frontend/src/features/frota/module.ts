/**
 * O descritor de navegação da frota — o espelho no frontend de `src/modules/frota/module.py`.
 *
 * **Ele sai do catálogo e vem pra cá** porque o módulo existe agora. O `features/context/modules.ts`
 * sempre disse de si mesmo que era provisório e que cada módulo traria o seu quando nascesse; a
 * frota é o primeiro a cumprir isso, e o catálogo passa a **compor** em vez de declarar.
 *
 * Os campos espelham o `ModuleDescriptor` do backend um a um (`key`, `personas`, `nav.label`,
 * `nav.path`). Divergir aqui não quebra nada alto: o item do menu apontaria pra uma rota que não
 * existe, ou não apareceria pra quem tem o módulo. Por isso os valores ficam ao lado da feature
 * que os usa, e não num arquivo que ninguém abre ao mexer na frota.
 */

import { Car } from 'lucide-react'

import type { ModuleNavDescriptor } from '#/features/context/modules'

/** A chave estável — a mesma de `MODULE_KEY` no backend, e a que o entitlement carrega. */
export const FROTA_KEY = 'frota'

/** O prefixo das rotas da frota dentro da organização ativa. Quem lhe põe o `orgId` na frente é
 *  a `nav.ts` (no menu) e o `frotaPath` abaixo (nas abas). */
export const FROTA_PATH = '/frota'

export const FROTA_MODULE: ModuleNavDescriptor = {
  key: FROTA_KEY,
  label: 'Frota',
  path: FROTA_PATH,
  // Espelha `personas=["company_admin", "collaborator"]` do descritor. `partner` não está lá:
  // frota é módulo de Empresa.
  personas: ['company_admin', 'collaborator'],
  icon: Car,
}

/** Uma rota da frota, absoluta, dentro da organização ativa.
 *
 *  `subPath` vazio é a home do módulo (Viagens). As quatro telas vivem sob o **mesmo** item de
 *  menu — a casca monta um item por módulo, e a navegação interna é do módulo, em abas. */
export function frotaPath(orgId: string, subPath = ''): string {
  return `/organizacoes/${encodeURIComponent(orgId)}${FROTA_PATH}${subPath}`
}
