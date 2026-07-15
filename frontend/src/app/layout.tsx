import type { Metadata } from 'next'
import type { ReactNode } from 'react'

import { Providers } from './providers'
import '../styles.css'

export const metadata: Metadata = {
  title: 'Superapp Widelab',
  description: 'Plataforma multi-tenant da Widelab.',
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
