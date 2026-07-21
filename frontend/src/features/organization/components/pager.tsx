'use client'

import { ChevronLeft, ChevronRight } from 'lucide-react'

import { Button } from '#/components/ui/button'

/** Paginação das três listagens. O backend devolve `total`, `page` e `page_size`, e é o `total`
 *  que separa "acabou" de "tem mais" — sem ele a última página só se descobre pedindo uma vazia.
 *
 *  Some quando cabe tudo numa página, que é o caso da esmagadora maioria dos tenants. */
export function Pager({
  page,
  pageSize,
  total,
  onPageChange,
  disabled = false,
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  disabled?: boolean
}) {
  const lastPage = Math.max(1, Math.ceil(total / pageSize))

  if (total <= pageSize) return null

  const first = (page - 1) * pageSize + 1
  const last = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between gap-4 border-t border-line px-2 py-3 text-sm">
      <p className="text-muted">
        {first}–{last} de {total}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page - 1)}
          disabled={disabled || page <= 1}
        >
          <ChevronLeft aria-hidden />
          Anterior
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => onPageChange(page + 1)}
          disabled={disabled || page >= lastPage}
        >
          Próxima
          <ChevronRight aria-hidden />
        </Button>
      </div>
    </div>
  )
}
