import { describe, expect, it } from 'vitest'
import type { z } from 'zod'

import { PASSWORD_MIN_LENGTH } from '#/features/auth/schema'
import { acceptInvitationSchema, registerPartnerSchema } from '#/features/onboarding/schema'

/** O critério 3 da spec pede que as telas que definem senha usem "o mesmo componente e a mesma
 *  validação zod". O componente é o `PasswordFields`; a validação é a `passwordFieldsShape`, e é
 *  o que estes testes prendem — pelo **comportamento**, não pela identidade do objeto.
 *
 *  Os dois schemas passam pela mesma bateria porque é assim que a divergência apareceria: alguém
 *  compõe um formulário novo à mão, ele passa a aceitar sete caracteres, e nada mais no projeto
 *  reclama. */

const acceptBase = { name: 'Ana', password: 'senha-boa', passwordConfirmation: 'senha-boa' }

const registerBase = {
  companyName: 'Restaurante Gomes',
  adminName: 'Ana',
  adminEmail: 'ana@gomes.com.br',
  password: 'senha-boa',
  passwordConfirmation: 'senha-boa',
}

/** A mensagem que caiu num campo, ou `null` se ele passou. */
function errorOn(schema: z.ZodTypeAny, value: unknown, field: string): string | null {
  const parsed = schema.safeParse(value)
  if (parsed.success) return null

  return parsed.error.issues.find((issue) => issue.path[0] === field)?.message ?? null
}

const shortPassword = 'a'.repeat(PASSWORD_MIN_LENGTH - 1)
const minimalPassword = 'a'.repeat(PASSWORD_MIN_LENGTH)

const FORMS: ReadonlyArray<[string, z.ZodTypeAny, Record<string, unknown>]> = [
  ['aceite de convite', acceptInvitationSchema, acceptBase],
  ['cadastro de parceiro', registerPartnerSchema, registerBase],
]

describe('política de senha compartilhada', () => {
  it.each(FORMS)('%s recusa senha curta demais', (_name, schema, base) => {
    const message = errorOn(
      schema,
      { ...base, password: shortPassword, passwordConfirmation: shortPassword },
      'password',
    )

    expect(message).toContain(`${PASSWORD_MIN_LENGTH} caracteres`)
  })

  it.each(FORMS)('%s aceita senha no limite exato da política', (_name, schema, base) => {
    const value = { ...base, password: minimalPassword, passwordConfirmation: minimalPassword }

    expect(schema.safeParse(value).success).toBe(true)
  })

  it.each(FORMS)(
    '%s culpa a confirmação, não a senha, quando as duas não batem',
    (_name, schema, base) => {
      const value = { ...base, password: 'senha-boa', passwordConfirmation: 'senha-boaa' }

      expect(schema.safeParse(value).success).toBe(false)
      expect(errorOn(schema, value, 'passwordConfirmation')).toBe('As senhas não conferem.')
      expect(errorOn(schema, value, 'password')).toBeNull()
    },
  )

  it.each(FORMS)('%s exige a confirmação preenchida', (_name, schema, base) => {
    const value = { ...base, passwordConfirmation: '' }

    expect(errorOn(schema, value, 'passwordConfirmation')).not.toBeNull()
  })
})

describe('acceptInvitationSchema', () => {
  it('não exige nome: quem já tem conta já tem nome, e a tela não sabe qual é o caso', () => {
    const parsed = acceptInvitationSchema.safeParse({
      password: minimalPassword,
      passwordConfirmation: minimalPassword,
    })

    expect(parsed.success).toBe(true)
  })

  it('não pede e-mail: ele é do convite, não do formulário', () => {
    const parsed = acceptInvitationSchema.safeParse(acceptBase)

    expect(parsed.success).toBe(true)
    expect(parsed.success && 'email' in parsed.data).toBe(false)
  })
})

describe('registerPartnerSchema', () => {
  it('exige o nome do parceiro e o nome do admin — o backend cria os dois na mesma transação', () => {
    const value = { ...registerBase, companyName: '   ', adminName: '' }

    expect(errorOn(registerPartnerSchema, value, 'companyName')).toBe('Informe o nome do parceiro.')
    expect(errorOn(registerPartnerSchema, value, 'adminName')).toBe('Informe seu nome.')
  })

  it('recusa e-mail malformado antes da viagem até o backend', () => {
    const value = { ...registerBase, adminEmail: 'ana@' }

    expect(errorOn(registerPartnerSchema, value, 'adminEmail')).toBe(
      'Esse e-mail não parece válido.',
    )
  })

  it('CNPJ é opcional — o campo é `document`, texto livre, e o backend não o cobra', () => {
    expect(registerPartnerSchema.safeParse(registerBase).success).toBe(true)
    expect(registerPartnerSchema.safeParse({ ...registerBase, document: '' }).success).toBe(true)
    expect(
      registerPartnerSchema.safeParse({ ...registerBase, document: '12.345.678/0001-90' }).success,
    ).toBe(true)
  })

  it('apara o espaço em volta do nome antes de mandar', () => {
    const parsed = registerPartnerSchema.safeParse({
      ...registerBase,
      companyName: '  Restaurante Gomes  ',
    })

    expect(parsed.success && parsed.data.companyName).toBe('Restaurante Gomes')
  })
})
