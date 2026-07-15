import type { NextConfig } from 'next'

const config: NextConfig = {
  output: 'standalone',
  async rewrites() {
    // Em dev, o Next reescreve /api/* pro backend (API_URL). Em produção quem roteia
    // /api/* é o nginx de borda, então sem API_URL não há rewrite — e o build não quebra.
    const apiUrl = process.env.API_URL
    if (!apiUrl) return []
    return [{ source: '/api/:path*', destination: `${apiUrl}/api/:path*` }]
  },
}

export default config
