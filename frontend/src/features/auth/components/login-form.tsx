'use client'

import { useState, type FormEvent } from 'react'

import { loginErrorMessage } from '#/features/auth/lib/login-error'
import { loginSchema } from '#/features/auth/schema'
import type { LoginInput } from '#/features/auth/types'
import { useLogin } from '#/features/auth/use-login'
import { Button } from '#/components/ui/button'
import { Input } from '#/components/ui/input'
import { Label } from '#/components/ui/label'

type FieldErrors = Partial<Record<keyof LoginInput, string>>

export function LoginForm() {
  const [values, setValues] = useState<LoginInput>({ email: '', password: '' })
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const login = useLogin()

  function update<K extends keyof LoginInput>(field: K, value: LoginInput[K]) {
    setValues((current) => ({ ...current, [field]: value }))
    // Uma tentativa nova apaga o veredito da anterior — erro velho ao lado de campo já
    // corrigido faz a pessoa duvidar do que está lendo.
    setFieldErrors((current) => ({ ...current, [field]: undefined }))
    if (login.isError) login.reset()
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const parsed = loginSchema.safeParse(values)
    if (!parsed.success) {
      const { fieldErrors: errors } = parsed.error.flatten()
      setFieldErrors({ email: errors.email?.[0], password: errors.password?.[0] })
      return
    }

    setFieldErrors({})
    login.mutate(parsed.data)
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {login.isError ? (
        <p
          role="alert"
          className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-text"
        >
          {loginErrorMessage(login.error)}
        </p>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="email">E-mail</Label>
        <Input
          id="email"
          type="email"
          inputMode="email"
          autoComplete="username"
          autoFocus
          placeholder="voce@empresa.com"
          value={values.email}
          onChange={(event) => update('email', event.target.value)}
          aria-invalid={fieldErrors.email !== undefined}
          aria-describedby={fieldErrors.email ? 'email-error' : undefined}
          disabled={login.isPending}
        />
        {fieldErrors.email ? (
          <p id="email-error" className="text-sm text-danger">
            {fieldErrors.email}
          </p>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Senha</Label>
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          value={values.password}
          onChange={(event) => update('password', event.target.value)}
          aria-invalid={fieldErrors.password !== undefined}
          aria-describedby={fieldErrors.password ? 'password-error' : undefined}
          disabled={login.isPending}
        />
        {fieldErrors.password ? (
          <p id="password-error" className="text-sm text-danger">
            {fieldErrors.password}
          </p>
        ) : null}
      </div>

      {/* `isPending` segue verdadeiro depois do sucesso, enquanto o redirecionamento
          acontece — o botão não volta a "Entrar" só pra sumir da tela em seguida. */}
      <Button type="submit" size="lg" className="w-full" disabled={login.isPending}>
        {login.isPending ? 'Entrando…' : 'Entrar'}
      </Button>
    </form>
  )
}
