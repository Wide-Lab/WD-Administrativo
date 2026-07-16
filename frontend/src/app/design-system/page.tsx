import { Badge } from '#/components/ui/badge'
import { Button } from '#/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '#/components/ui/card'
import { Input } from '#/components/ui/input'
import { Skeleton } from '#/components/ui/skeleton'

// Vitrine do design system (spec 02). É uma superfície de verificação — a rota
// `/` recebe o login de verdade na spec 03.
const swatches = [
  ['bg', 'bg-bg'],
  ['surface', 'bg-surface'],
  ['surface-2', 'bg-surface-2'],
  ['line', 'bg-line'],
  ['text', 'bg-text'],
  ['muted', 'bg-muted'],
  ['primary', 'bg-primary'],
  ['primary-2', 'bg-primary-2'],
  ['success', 'bg-success'],
  ['warning', 'bg-warning'],
  ['danger', 'bg-danger'],
] as const

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-4">
      <h2 className="text-sm font-semibold tracking-wide text-muted uppercase">{title}</h2>
      {children}
    </section>
  )
}

export default function Page() {
  return (
    <main className="mx-auto max-w-4xl space-y-12 px-6 py-16">
      <header className="space-y-2">
        <p className="text-sm text-muted">Superapp Widelab</p>
        <h1 className="text-3xl font-bold tracking-tight">Design system</h1>
        <p className="max-w-prose text-muted">
          Tema escuro, superfícies em camadas, azul como ação primária. Todos os tokens vêm de uma
          paleta única em <code className="font-mono text-primary-fg">styles.css</code>.
        </p>
      </header>

      <Section title="Paleta">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {swatches.map(([name, bg]) => (
            <div key={name} className="space-y-2">
              <div className={`h-14 rounded-md border border-line ${bg}`} />
              <p className="font-mono text-xs text-muted">{name}</p>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Botões">
        <div className="flex flex-wrap items-center gap-3">
          <Button>Começar agora</Button>
          <Button variant="secondary">Secundário</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Excluir</Button>
          <Button variant="link">Saiba mais</Button>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button size="sm">Pequeno</Button>
          <Button size="md">Médio</Button>
          <Button size="lg">Grande</Button>
          <Button disabled>Desabilitado</Button>
        </div>
      </Section>

      <Section title="Formulário">
        <div className="grid max-w-sm gap-3">
          <Input placeholder="voce@empresa.com" />
          <Input type="password" placeholder="Senha" />
          <Input aria-invalid placeholder="Campo com erro" />
        </div>
      </Section>

      <Section title="Estados (badges)">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Padrão</Badge>
          <Badge variant="muted">Rascunho</Badge>
          <Badge variant="primary">Financeiro</Badge>
          <Badge variant="warning">Em análise</Badge>
          <Badge variant="success">A receber</Badge>
          <Badge variant="danger">Recusada</Badge>
        </div>
      </Section>

      <Section title="Card & números tabulares">
        <div className="grid gap-4 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Fatura de junho</CardTitle>
              <CardDescription>Refeições · Restaurante do Zé</CardDescription>
            </CardHeader>
            <CardContent className="space-y-1">
              <p className="font-mono text-3xl font-semibold tabular-nums">R$ 12.480,00</p>
              <p className="font-mono text-sm text-muted tabular-nums">1.204 tickets · 30 dias</p>
            </CardContent>
            <CardFooter className="gap-3">
              <Button size="sm">Aprovar</Button>
              <Button size="sm" variant="secondary">
                Revisar
              </Button>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Carregando…</CardTitle>
              <CardDescription>Exemplo de skeleton</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-10 w-full" />
            </CardContent>
          </Card>
        </div>
      </Section>
    </main>
  )
}
