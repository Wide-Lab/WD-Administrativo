import { describe, expect, it } from 'vitest'

import {
  formatMoment,
  isDriverUserConflict,
  isNotADriver,
  isOverlapConflict,
  isPlateConflict,
  overlapMessage,
  translateCloseUsageError,
  translateDriverError,
  translateUsageError,
  translateVehicleError,
} from '#/features/frota/lib/frota-error'
import { ApiError } from '#/lib/api'

/**
 * **As mensagens abaixo são as do backend, copiadas literalmente** de
 * `frota/adapters/db/repository.py` (`_USAGE_CONFLICTS`), de
 * `application/use_cases/create_usage.py` e de `application/usage_scope.py`.
 *
 * É de propósito, e é o que dá valor a este arquivo: a tradução casa em trecho de frase porque o
 * `code` do backend é do *tipo* do erro (`conflict`) e não do caso, então os cinco 409 de
 * `vehicle_usages` chegam indistinguíveis por código. Se alguém reescrever uma dessas frases lá,
 * um teste daqui fica vermelho — que é exatamente onde eu quero descobrir, em vez de na tela do
 * usuário, com a mensagem caindo no campo errado.
 */
const BACKEND = {
  overlap: 'Este veículo já tem uma viagem registrada que se sobrepõe a este período.',
  period: 'A hora de volta tem que ser depois da hora de saída.',
  odometer: 'O hodômetro final não pode ser menor que o inicial.',
  closedTogether: 'Encerrar uma viagem exige hora de volta e hodômetro final juntos.',
  fkVehicle: 'Veículo não encontrado nesta Empresa.',
  fkDriver: 'Condutor não encontrado nesta Empresa.',
  future:
    'A data de saída não pode estar no futuro. O sistema registra a viagem que aconteceu, não a que vai acontecer.',
  vehicleInactive: "O veículo ABC1D23 está 'inactive' e não pode receber uma viagem nova.",
  driverInactive: 'O condutor João da Silva está inativo e não pode receber uma viagem nova.',
  notADriver:
    'Você não está cadastrado como condutor nesta Empresa, então não pode lançar uma viagem em seu próprio nome. Peça ao gestor da frota para cadastrá-lo.',
  otherDriver: 'Você só pode lançar viagens em seu próprio nome.',
  plateCreate: "Já existe um veículo com a placa 'ABC1D23' nesta Empresa.",
  plateUpdate: 'Já existe um veículo com esta placa nesta Empresa.',
  driverUser: 'Esta pessoa já está cadastrada como condutor nesta Empresa.',
  alreadyClosed: 'Esta viagem já foi encerrada. Para corrigir os dados dela, use a edição.',
}

const conflict = (message: string) => new ApiError(409, 'conflict', message)
const invalid = (message: string) => new ApiError(422, 'validation_error', message)
const forbidden = (message: string) => new ApiError(403, 'forbidden', message)

describe('isOverlapConflict — o 409 mais importante da spec', () => {
  it('reconhece a sobreposição de período', () => {
    expect(isOverlapConflict(conflict(BACKEND.overlap))).toBe(true)
  })

  it('não confunde os outros 409 de `vehicle_usages` com ela', () => {
    expect(isOverlapConflict(conflict(BACKEND.period))).toBe(false)
    expect(isOverlapConflict(conflict(BACKEND.odometer))).toBe(false)
    expect(isOverlapConflict(conflict(BACKEND.alreadyClosed))).toBe(false)
    expect(isOverlapConflict(conflict(BACKEND.plateCreate))).toBe(false)
  })

  it('status diferente de 409 nunca é sobreposição', () => {
    expect(isOverlapConflict(invalid(BACKEND.overlap))).toBe(false)
    expect(isOverlapConflict(new TypeError('Failed to fetch'))).toBe(false)
  })
})

describe('translateUsageError — cada caso no seu campo', () => {
  it('a sobreposição é do formulário, não de um campo — o dado que colide não está na tela', () => {
    const result = translateUsageError(conflict(BACKEND.overlap), {
      vehicleLabel: 'ABC1D23',
      startedAt: '2026-07-20T08:00',
      endedAt: '2026-07-20T12:00',
    })

    expect(result.field).toBeNull()
    // Critério 2: a mensagem nomeia o veículo e o período que o usuário tentou.
    expect(result.message).toContain('ABC1D23')
    expect(result.message).toContain('20/07/2026 08:00')
    expect(result.message).toContain('20/07/2026 12:00')
  })

  it('a data futura vai pro campo de data, não pra um toast', () => {
    expect(translateUsageError(invalid(BACKEND.future)).field).toBe('startedAt')
  })

  it('veículo inativo e veículo inexistente vão pro select de veículo', () => {
    expect(translateUsageError(invalid(BACKEND.vehicleInactive)).field).toBe('vehicleId')
    expect(translateUsageError(invalid(BACKEND.fkVehicle)).field).toBe('vehicleId')
    expect(translateUsageError(conflict(BACKEND.fkVehicle)).field).toBe('vehicleId')
  })

  it('condutor inativo e condutor inexistente vão pro select de condutor', () => {
    expect(translateUsageError(invalid(BACKEND.driverInactive)).field).toBe('driverId')
    expect(translateUsageError(invalid(BACKEND.fkDriver)).field).toBe('driverId')
  })

  it('a ordem dos instantes cai na chegada, e o hodômetro invertido no hodômetro', () => {
    expect(translateUsageError(conflict(BACKEND.period)).field).toBe('endedAt')
    expect(translateUsageError(conflict(BACKEND.odometer)).field).toBe('endOdometer')
  })

  it('o 403 de apontar outro condutor não deveria acontecer pela tela — e por isso aparece inteiro', () => {
    const result = translateUsageError(forbidden(BACKEND.otherDriver))

    expect(result.field).toBeNull()
    expect(result.message).toBe(BACKEND.otherDriver)
  })

  it('quem não é condutor cadastrado ouve o motivo e a quem pedir, não "erro ao salvar"', () => {
    const result = translateUsageError(invalid(BACKEND.notADriver))

    expect(result.field).toBeNull()
    expect(result.message).toContain('gestor da frota')
  })

  it('falha de rede fala de conexão; 5xx não culpa o lançamento', () => {
    expect(translateUsageError(new TypeError('Failed to fetch')).message).toContain('conexão')
    expect(translateUsageError(new ApiError(500, 'x', 'boom')).message).toContain('servidor')
  })

  it('sem o rótulo do veículo a frase degrada e continua verdadeira', () => {
    expect(translateUsageError(conflict(BACKEND.overlap), {}).message).toContain('Este veículo')
  })
})

describe('overlapMessage — a frase composta pela tela', () => {
  it('com os dois instantes, diz o intervalo', () => {
    expect(
      overlapMessage({
        vehicleLabel: 'ABC1D23',
        startedAt: '2026-07-20T08:00',
        endedAt: '2026-07-20T12:00',
      }),
    ).toContain('entre 20/07/2026 08:00 e 20/07/2026 12:00')
  })

  it('numa viagem aberta, diz "a partir de" — não há fim a nomear', () => {
    expect(overlapMessage({ vehicleLabel: 'ABC1D23', startedAt: '2026-07-20T08:00' })).toContain(
      'a partir de 20/07/2026 08:00',
    )
  })

  it('sem nada, ainda diz o que aconteceu', () => {
    expect(overlapMessage({})).toContain('nesse período')
  })
})

describe('formatMoment', () => {
  it('formata o valor do `datetime-local` sem passar por `Date`, que deslocaria o fuso', () => {
    expect(formatMoment('2026-07-20T08:30')).toBe('20/07/2026 08:30')
    expect(formatMoment('2026-01-01T00:00:00')).toBe('01/01/2026 00:00')
  })

  it('devolve a entrada quando ela não é um instante', () => {
    expect(formatMoment('ontem')).toBe('ontem')
  })
})

describe('translateVehicleError — a placa duplicada vai pro campo placa', () => {
  it('reconhece as duas frases do backend (criar e editar)', () => {
    expect(translateVehicleError(conflict(BACKEND.plateCreate)).field).toBe('plate')
    expect(translateVehicleError(conflict(BACKEND.plateUpdate)).field).toBe('plate')
    expect(isPlateConflict(conflict(BACKEND.plateCreate))).toBe(true)
  })

  it('repassa a mensagem do backend, que nomeia a placa', () => {
    expect(translateVehicleError(conflict(BACKEND.plateCreate)).message).toContain('ABC1D23')
  })

  it('o que não é conflito de placa é do formulário', () => {
    expect(translateVehicleError(new ApiError(500, 'x', 'boom')).field).toBeNull()
  })
})

describe('translateDriverError', () => {
  it('a pessoa já vinculada a outro condutor vai pro select de acesso', () => {
    expect(translateDriverError(conflict(BACKEND.driverUser)).field).toBe('userId')
    expect(isDriverUserConflict(conflict(BACKEND.driverUser))).toBe(true)
  })

  it('o resto é do formulário', () => {
    expect(translateDriverError(invalid('qualquer coisa')).field).toBeNull()
  })
})

describe('translateCloseUsageError', () => {
  it('"já foi encerrada" é do formulário — a saída é recarregar, não corrigir um campo', () => {
    const result = translateCloseUsageError(conflict(BACKEND.alreadyClosed))

    expect(result.field).toBeNull()
    expect(result.message).toContain('já foi encerrada')
  })

  it('a ordem dos instantes e o hodômetro invertido caem nos campos do diálogo', () => {
    expect(translateCloseUsageError(conflict(BACKEND.period)).field).toBe('endedAt')
    expect(translateCloseUsageError(conflict(BACKEND.odometer)).field).toBe('endOdometer')
  })
})

describe('isNotADriver', () => {
  it('só o 422 de "não está cadastrado como condutor" conta', () => {
    expect(isNotADriver(invalid(BACKEND.notADriver))).toBe(true)
    expect(isNotADriver(forbidden(BACKEND.otherDriver))).toBe(false)
    expect(isNotADriver(invalid(BACKEND.future))).toBe(false)
  })
})
