import { cn } from '#/lib/utils'

// Placeholder vazio — o conteúdo real (login) chega na spec 03.
// Usa o alias `#/*` e o `cn()` de propósito, pra provar que ambos resolvem no build.
export default function Page() {
  return <main className={cn()} />
}
