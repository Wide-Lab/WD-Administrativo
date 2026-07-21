'use client'

import { ShieldAlert } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '#/components/ui/card'

/** A tela que não é desta pessoa.
 *
 *  Irmã do `ModuleUnavailable` do `ModuleGuard`, e pela mesma razão de tom: não acusa ninguém de
 *  invasão. O caso comum não é ataque — é um link colado de outra pessoa, ou um papel que mudou
 *  com a aba aberta.
 *
 *  **Esconder a tela não é o que protege nada**, e vale dizer aqui porque estes dois casos são
 *  diferentes entre si: em Pessoas, o backend nega de verdade (403 em `members.read`) e isto é o
 *  eco de uma negação real; em Parceiros, o `GET .../convenios` exige só o vínculo, e quem digita
 *  a URL alcança o dado — isto ali é só "esta tela não é sua", ergonomia declarada. Ver
 *  `KERNEL_NAV` em `features/context/nav.ts`. */
export function AccessDenied({ title, description }: { title: string; description: string }) {
  return (
    <Card className="mx-auto mt-12 max-w-lg">
      <CardHeader className="items-start">
        <span className="mb-2 inline-flex size-10 items-center justify-center rounded-md bg-surface-2 text-muted">
          <ShieldAlert className="size-5" aria-hidden />
        </span>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent />
    </Card>
  )
}
