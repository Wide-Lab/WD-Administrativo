import { describe, expect, it } from 'vitest'

import {
  EMPTY_USAGE_FILTERS,
  endOfDay,
  hasAnyUsageFilter,
  isoDatePart,
  overlapFilters,
  readUsageFilters,
  startOfDay,
  usageFiltersToApiQuery,
  usageFiltersToQueryString,
  usageFiltersToSearchParams,
  type UsageFilters,
} from '#/features/frota/lib/filters'
import { mileageParamsToQueryString, readMileageParams } from '#/features/frota/lib/mileage-params'

const VEICULO = '018f0000-0000-7000-8000-000000000001'
const CONDUTOR = '018f0000-0000-7000-8000-000000000002'

describe('readUsageFilters', () => {
  it('lê os cinco parâmetros com os nomes que o backend usa', () => {
    const filters = readUsageFilters(
      new URLSearchParams(
        `veiculo=${VEICULO}&condutor=${CONDUTOR}&de=2026-07-01&ate=2026-07-31&abertos=true`,
      ),
    )

    expect(filters).toEqual({
      vehicleId: VEICULO,
      driverId: CONDUTOR,
      from: '2026-07-01',
      until: '2026-07-31',
      onlyOpen: true,
    })
  })

  it('URL sem filtro nenhum devolve o vazio, e não `undefined` espalhado', () => {
    expect(readUsageFilters(new URLSearchParams())).toEqual(EMPTY_USAGE_FILTERS)
  })

  it('parâmetro presente e vazio é ausência — senão o backend o leria como valor', () => {
    const filters = readUsageFilters(new URLSearchParams('veiculo=&de=&ate=   '))

    expect(filters.vehicleId).toBeNull()
    expect(filters.from).toBeNull()
    expect(filters.until).toBeNull()
  })

  it('só `true` e `1` ligam `abertos` — `?abertos=false` não pode ligar o filtro', () => {
    expect(readUsageFilters(new URLSearchParams('abertos=true')).onlyOpen).toBe(true)
    expect(readUsageFilters(new URLSearchParams('abertos=1')).onlyOpen).toBe(true)
    expect(readUsageFilters(new URLSearchParams('abertos=false')).onlyOpen).toBe(false)
    expect(readUsageFilters(new URLSearchParams('abertos=')).onlyOpen).toBe(false)
    expect(readUsageFilters(new URLSearchParams('abertos=sim')).onlyOpen).toBe(false)
  })
})

describe('usageFiltersToSearchParams', () => {
  it('filtro ausente não aparece na URL — `?veiculo=&de=` é ruído pra quem copia', () => {
    expect(usageFiltersToSearchParams(EMPTY_USAGE_FILTERS).toString()).toBe('')
  })

  it('`abertos=false` também some, porque `false` é o padrão', () => {
    expect(usageFiltersToSearchParams({ ...EMPTY_USAGE_FILTERS, onlyOpen: false }).toString()).toBe(
      '',
    )
    expect(
      usageFiltersToSearchParams({ ...EMPTY_USAGE_FILTERS, onlyOpen: true }).get('abertos'),
    ).toBe('true')
  })
})

describe('ler e montar são inversas — é o que faz a URL sobreviver ao F5 (critério 7)', () => {
  const casos: UsageFilters[] = [
    EMPTY_USAGE_FILTERS,
    { ...EMPTY_USAGE_FILTERS, vehicleId: VEICULO },
    { ...EMPTY_USAGE_FILTERS, from: '2026-07-01', until: '2026-07-31' },
    {
      vehicleId: VEICULO,
      driverId: CONDUTOR,
      from: '2026-07-01',
      until: '2026-07-31',
      onlyOpen: true,
    },
  ]

  it.each(casos)('vai e volta sem perder nada (%#)', (filters) => {
    expect(readUsageFilters(usageFiltersToSearchParams(filters))).toEqual(filters)
  })
})

describe('usageFiltersToQueryString', () => {
  it('sem filtro, string vazia — e não um `?` solto na barra de endereço', () => {
    expect(usageFiltersToQueryString(EMPTY_USAGE_FILTERS)).toBe('')
  })

  it('com filtro, começa com `?`', () => {
    expect(usageFiltersToQueryString({ ...EMPTY_USAGE_FILTERS, vehicleId: VEICULO })).toBe(
      `?veiculo=${VEICULO}`,
    )
  })
})

describe('hasAnyUsageFilter', () => {
  it('distingue lista filtrada de lista inteira — os dois vazios da tela são diferentes', () => {
    expect(hasAnyUsageFilter(EMPTY_USAGE_FILTERS)).toBe(false)
    expect(hasAnyUsageFilter({ ...EMPTY_USAGE_FILTERS, onlyOpen: true })).toBe(true)
    expect(hasAnyUsageFilter({ ...EMPTY_USAGE_FILTERS, from: '2026-07-01' })).toBe(true)
  })
})

describe('o período vira instante antes de ir pro backend', () => {
  /** O mesmo instante que as bordas do dia devem produzir, montado pelo caminho longo — assim o
   *  teste não presume o fuso de quem roda a suíte, só que ele é um só. */
  const localInstant = (
    year: number,
    month: number,
    day: number,
    hour = 0,
    minute = 0,
    second = 0,
    ms = 0,
  ) => new Date(year, month - 1, day, hour, minute, second, ms).toISOString()

  it('`ate` cobre o dia inteiro — senão toda viagem do próprio dia sumiria da lista', () => {
    expect(startOfDay('2026-07-20')).toBe(localInstant(2026, 7, 20))
    expect(endOfDay('2026-07-20')).toBe(localInstant(2026, 7, 20, 23, 59, 59, 999))
  })

  it('a query da API usa os mesmos nomes da URL, com a hora acrescentada', () => {
    const query = usageFiltersToApiQuery({
      vehicleId: VEICULO,
      driverId: null,
      from: '2026-07-01',
      until: '2026-07-31',
      onlyOpen: false,
    })

    expect(query.get('veiculo')).toBe(VEICULO)
    expect(query.get('de')).toBe(localInstant(2026, 7, 1))
    expect(query.get('ate')).toBe(localInstant(2026, 7, 31, 23, 59, 59, 999))
    expect(query.get('condutor')).toBeNull()
    expect(query.get('abertos')).toBeNull()
  })

  it('**com** fuso na string — sem ele o backend responde 422, e antes calava em UTC', () => {
    expect(startOfDay('2026-07-20')).toMatch(/Z$/)
    expect(endOfDay('2026-07-20')).toMatch(/Z$/)
  })

  it('as bordas são o dia de quem filtra, não o de Greenwich', () => {
    // Vale em qualquer fuso: o intervalo de um dia tem 24h menos 1ms, e não é UTC-alinhado por
    // acidente do fuso do runner.
    const from = new Date(startOfDay('2026-07-20')).getTime()
    const until = new Date(endOfDay('2026-07-20')).getTime()

    expect(until - from).toBe(24 * 60 * 60 * 1000 - 1)
  })
})

describe('isoDatePart', () => {
  it('corta a data de um `datetime-local` sem passar por `Date`', () => {
    expect(isoDatePart('2026-07-20T08:30')).toBe('2026-07-20')
    expect(isoDatePart('2026-07-20')).toBe('2026-07-20')
  })

  it('devolve `null` no que não é data', () => {
    expect(isoDatePart('')).toBeNull()
    expect(isoDatePart('ontem')).toBeNull()
  })
})

describe('overlapFilters — o atalho do 409 de sobreposição (critério 2)', () => {
  it('recorta o veículo e o dia da viagem recusada', () => {
    const filters = overlapFilters(VEICULO, '2026-07-20T08:00', '2026-07-20T12:00')

    expect(filters.vehicleId).toBe(VEICULO)
    expect(filters.from).toBe('2026-07-20')
    expect(filters.until).toBe('2026-07-20')
    expect(filters.driverId).toBeNull()
  })

  it('numa viagem aberta, o intervalo é o dia da saída', () => {
    const filters = overlapFilters(VEICULO, '2026-07-20T08:00')

    expect(filters.from).toBe('2026-07-20')
    expect(filters.until).toBe('2026-07-20')
  })

  it('cobre a virada de dia quando a viagem atravessa a meia-noite', () => {
    const filters = overlapFilters(VEICULO, '2026-07-20T22:00', '2026-07-21T03:00')

    expect(filters.from).toBe('2026-07-20')
    expect(filters.until).toBe('2026-07-21')
  })

  it('a URL que ele monta é a mesma que a tela lê de volta — o atalho não pode divergir', () => {
    const filters = overlapFilters(VEICULO, '2026-07-20T08:00', '2026-07-20T12:00')
    const url = usageFiltersToQueryString(filters)

    expect(readUsageFilters(new URLSearchParams(url))).toEqual(filters)
  })
})

describe('readMileageParams — o relatório abre no mês corrente (critério 9)', () => {
  const agora = new Date(2026, 6, 20) // 20/07/2026, hora local

  it('sem parâmetros, o período é o mês corrente inteiro', () => {
    const params = readMileageParams(new URLSearchParams(), agora)

    expect(params.from).toBe('2026-07-01')
    expect(params.until).toBe('2026-07-31')
    expect(params.groupBy).toBe('veiculo')
  })

  it('acha o último dia de um mês de 30, e de fevereiro bissexto', () => {
    expect(readMileageParams(new URLSearchParams(), new Date(2026, 3, 10)).until).toBe('2026-04-30')
    expect(readMileageParams(new URLSearchParams(), new Date(2024, 1, 10)).until).toBe('2024-02-29')
  })

  it('lê o que a URL traz', () => {
    const params = readMileageParams(
      new URLSearchParams('de=2026-01-01&ate=2026-03-31&agrupar_por=condutor'),
      agora,
    )

    expect(params).toEqual({ from: '2026-01-01', until: '2026-03-31', groupBy: 'condutor' })
  })

  it('data malformada cai no mês corrente — a URL vem colada de e-mail e editada à mão', () => {
    const params = readMileageParams(new URLSearchParams('de=ontem&ate='), agora)

    expect(params.from).toBe('2026-07-01')
    expect(params.until).toBe('2026-07-31')
  })

  it('`agrupar_por` fora dos dois valores do backend vira `veiculo`, o default da rota', () => {
    expect(readMileageParams(new URLSearchParams('agrupar_por=vehicle'), agora).groupBy).toBe(
      'veiculo',
    )
    expect(readMileageParams(new URLSearchParams('agrupar_por=condutor'), agora).groupBy).toBe(
      'condutor',
    )
  })

  it('ler e montar são inversas, com os três sempre presentes', () => {
    const params = { from: '2026-01-01', until: '2026-03-31', groupBy: 'condutor' as const }
    const url = mileageParamsToQueryString(params)

    expect(url.startsWith('?')).toBe(true)
    expect(readMileageParams(new URLSearchParams(url), agora)).toEqual(params)
  })
})
