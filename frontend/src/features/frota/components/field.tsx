import type { ReactNode } from 'react'

import { Label } from '#/components/ui/label'

/** Rótulo + controle + erro, com o `aria-describedby` já ligado.
 *
 *  Existe porque os quatro formulários da frota repetem a mesma tríade dezenas de vezes, e porque
 *  o `id` do erro precisa casar com o `aria-describedby` do controle — que é exatamente o tipo de
 *  ligação que se esquece quando é copiada à mão. Aqui ela se esquece uma vez só.
 *
 *  O controle é `children` e não um `<Input>` embutido: os campos da frota são input, select e
 *  textarea, e embutir um forçaria três variantes do mesmo componente. */
export function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string
  label: string
  error?: string
  hint?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-sm text-danger">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-sm text-muted">
          {hint}
        </p>
      ) : null}
    </div>
  )
}

/** As props de acessibilidade de um controle com erro. Um objeto e não três atributos soltos
 *  porque os três andam juntos — e porque `aria-describedby` apontando pra um id que não existe é
 *  um bug silencioso que só um leitor de tela revela. */
export function fieldProps(id: string, error?: string, hasHint = false) {
  return {
    id,
    'aria-invalid': error !== undefined,
    'aria-describedby': error ? `${id}-error` : hasHint ? `${id}-hint` : undefined,
  }
}
