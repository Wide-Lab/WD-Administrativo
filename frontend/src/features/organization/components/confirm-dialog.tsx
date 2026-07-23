'use client'

import { useEffect, useRef, type ReactNode } from 'react'

import { Button } from '#/components/ui/button'

/** Confirmação modal para as ações desta feature que **não** têm volta pelo produto.
 *
 *  Sobre o `<dialog>` nativo, e não sobre Radix: o projeto usa shadcn/Radix, mas
 *  `@radix-ui/react-dialog` não está instalado, e as duas coisas que um modal precisa acertar —
 *  prender o foco e fechar no Esc — o `showModal()` entrega do navegador, sem dependência nova.
 *  Trocar por `<Dialog>` do shadcn depois é substituir este arquivo, não mexer em quem o chama.
 *
 *  **Confirmação não é guard.** Nada aqui impede nada: o backend permite o que permite, e um
 *  diálogo é honestidade sobre a consequência — não um cadeado. Quem usa isto hoje é a revogação
 *  de convite; o outro caso, a auto-edição de vínculo, deixou de existir quando o backend passou
 *  a recusá-la com 422 — e aí o certo passou a ser esconder o controle, não confirmá-lo. Ver
 *  `member-row-form.tsx`. */
export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  destructive = false,
  isPending = false,
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  description: ReactNode
  confirmLabel: string
  destructive?: boolean
  isPending?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const ref = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = ref.current
    if (dialog === null) return

    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  if (!open) return null

  return (
    <dialog
      ref={ref}
      aria-labelledby="confirm-dialog-title"
      // O Esc do navegador dispara `cancel`; sem isto o `open` do React ficaria dessincronizado
      // do DOM e o diálogo não reabriria.
      onCancel={(event) => {
        event.preventDefault()
        if (!isPending) onCancel()
      }}
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-lg border border-line bg-surface p-0 text-text backdrop:bg-bg/70"
    >
      <div className="space-y-2 p-6">
        <h2 id="confirm-dialog-title" className="text-lg font-semibold tracking-tight">
          {title}
        </h2>
        <div className="text-sm text-muted">{description}</div>
      </div>
      <div className="flex justify-end gap-2 px-6 pb-6">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isPending}>
          Cancelar
        </Button>
        <Button
          type="button"
          variant={destructive ? 'destructive' : 'primary'}
          onClick={onConfirm}
          disabled={isPending}
        >
          {isPending ? 'Aplicando…' : confirmLabel}
        </Button>
      </div>
    </dialog>
  )
}
