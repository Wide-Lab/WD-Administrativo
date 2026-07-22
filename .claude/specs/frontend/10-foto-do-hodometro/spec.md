# 10 — Foto do hodômetro

**Estado:** 📋 escrita, não implementada.
**Depende de:** `backend/11-leitura-de-hodometro/spec.md` (as duas rotas, o `current_odometer` e o
`plausivel` — **bloqueante**, nada aqui existe sem ela), `frontend/07-telas-da-frota/spec.md` (os
dois diálogos que esta spec altera), `frontend/02-design-system/spec.md` (os tokens).
**Entrega:** o botão de câmera nos diálogos de lançar e encerrar viagem, o hodômetro pré-preenchido
com a última leitura do veículo, e a foto visível na viagem depois.

## Objetivo

Dar gesto ao que a `backend/11` tornou possível: a pessoa está de pé ao lado do carro, com o
celular na mão, e o hodômetro entra no formulário sem ela digitar dígito nenhum. E fechar, de
quebra, a ergonomia que a `frontend/07` teve que deixar passar — o campo de hodômetro que nascia
vazio quando o sistema já sabia o número.

## Fora de escopo

- **Recorte na tela.** Foi cogitado e **descartado** — ver `backend/11`, "A decisão do motor". O
  recorte era o preço pra viabilizar o caminho sem IA; o motor escolhido lê o painel inteiro e
  distingue o total do parcial sozinho, então o recorte viraria um gesto a mais por viagem sem
  nada em troca. Se um dia o motor voltar a precisar, volta com ele.
- **Preencher `started_at`/`ended_at` a partir da foto.** Decidido fora na `backend/11`: a API não
  lê EXIF e não vai ler. Os dois campos seguem digitados, com o `nowForInput()` de valor inicial
  que a `07` já usa.
- **Galeria de fotos do veículo, ou tela de auditoria de leituras.** A foto aparece **na viagem**,
  que é onde ela significa alguma coisa. Uma tela que lista fotos soltas é arquivo, não produto.
- **Testes de componente.** Continuam sendo dívida com spec própria — e esta entrega a agrava de
  novo, com upload, estado assíncrono e um caminho de erro que não é de rede. Ver a nota no fim.
- **Corrigir a foto de uma viagem já lançada.** `PATCH /usos/{id}` não aceita referência de
  leitura (`backend/11`), então não há rota. Trocar a foto errada é caso raro o bastante pra
  esperar quem peça.

## O hodômetro deixa de nascer vazio

Independente de câmera, e é a metade mais barata desta spec: `VehicleResponse` agora traz
`current_odometer`, então escolher o veículo **pré-preenche** o campo de hodômetro de saída.

Isso fecha o item que a `frontend/07` pôs em "Fora de escopo" com o motivo certo — ela recusou
derivá-lo de `GET /usos` no navegador pra não criar uma segunda contabilidade de quilometragem na
tela. Agora o número vem do backend, e a tela só o mostra.

**Pré-preenchido, nunca travado.** Lançamento retroativo é o caso normal da frota (`backend/10`), e
numa viagem de terça lançada na sexta o hodômetro atual está **errado** — ele já andou. O valor é
sugestão inicial, o campo é editável, e trocar de veículo **substitui** o valor enquanto a pessoa
não tiver digitado nada; depois que ela digitou, não sobrescreve mais. Sobrescrever o que a pessoa
acabou de digitar é o tipo de ajuda que faz perder confiança na tela.

No diálogo de **encerrar**, o campo continua nascendo vazio: o hodômetro de chegada é justamente o
que ainda não se sabe, e sugerir o da saída convidaria a confirmar sem olhar.

## O botão de câmera

Nos **dois** diálogos (`usage-form-dialog` e `close-usage-dialog`), ao lado do campo de hodômetro
correspondente. No de lançamento ele fica junto do hodômetro de **saída**; o de chegada, quando a
pessoa já lança a viagem encerrada, ganha o seu.

```tsx
<input type="file" accept="image/jpeg,image/png,image/webp" capture="environment" />
```

`capture="environment"` abre a câmera traseira direto no celular e é ignorado no desktop, onde
vira um seletor de arquivo comum. **Nada de `getUserMedia`**: a câmera nativa já resolve foco,
flash e HDR melhor que qualquer coisa que a gente montasse, e não pede permissão persistente.

O `accept` não lista HEIC porque o backend o recusa (415) — e não precisa listar: a redução abaixo
reencoda tudo pra JPEG antes de subir.

**O botão só habilita depois do veículo escolhido.** A rota é aninhada no veículo
(`POST /veiculos/{id}/hodometro/leituras`), então sem ele não há o que chamar — e é o mesmo veículo
que dá o prior. Sem escolha, o botão fica desabilitado com o motivo dito: "Escolha o veículo
primeiro".

### A foto é reduzida no navegador antes de subir

Para **1600px** no lado maior, reencodada em JPEG a 85% de qualidade, via `<canvas>`. Três motivos,
e nenhum é micro-otimização: a foto de 12 MP de um celular passa dos 8 MB que o backend recusa
(413); quem está de pé ao lado do carro está no 4G e paga o upload; e o HEIC do iPhone vira JPEG
no caminho, que é o que faz o `accept` acima bastar.

Mora em `features/frota/lib/image.ts`, **função pura sobre um `File`**, com teste na própria
entrega — a regra que a `07` firmou e que segurou 112 dos 180 testes puros do projeto.

## O que a tela mostra depois de ler

Três estados, e o desenho dos três sai de uma regra só: **a leitura é sugestão, nunca valor.** O
campo permanece editável em todos, e nada é enviado sem a pessoa confirmar no botão do formulário.

| Resposta | O que aparece |
| --- | --- |
| `valor` lido, `plausivel: true` | Campo preenchido. Abaixo: *"Lemos 45.210 no seu hodômetro. O último registrado foi 45.180 — 30 km a mais."* |
| `valor` lido, `plausivel: false` | Campo preenchido **e** um aviso em `warning`: *"Lemos 45.210, mas o último registrado foi 48.900. Confira antes de lançar."* Não impede o envio. |
| `valor: null` | Campo intocado, e a mensagem: *"Não consegui ler o hodômetro nessa foto. Digite o número — a foto fica guardada do mesmo jeito."* |

O terceiro estado é o que decide se a funcionalidade é confiável. Ele **não é erro** — é 201 no
backend, a foto foi guardada, e a frase diz isso pra pessoa não tirar outra foto achando que
perdeu a primeira.

**O aviso de `plausivel: false` nunca vira bloqueio.** A `backend/10` decidiu que divergência de
hodômetro é aviso e não trava ("travar faria o usuário inventar um número"), e um `if` no
formulário desfaria essa decisão pela porta dos fundos — o mesmo raciocínio do "cadeado pintado"
que o `Can` proíbe.

Enquanto sobe e lê, o botão mostra "Lendo…" e o campo de hodômetro fica desabilitado. Os outros
campos **não** — quem quiser preencher a finalidade enquanto espera, preenche.

### Erros que não são "não consegui ler"

413, 415, 422 e 429 são traduzidos por `translateReadingError` em
`features/frota/lib/frota-error.ts`, ao lado dos que a `07` já traduz. Cada um vira uma frase que
diz o que fazer — 413 é "a foto ficou grande demais, tente de novo" (e não deveria acontecer, com
a redução no cliente), 429 é "muitas leituras seguidas, espere um minuto". Nenhum deles limpa o
que a pessoa já digitou no formulário.

## A foto na viagem, depois

Na lista de viagens (`usages-screen`), uma viagem com foto ganha um ícone discreto na linha. Clicar
abre a imagem num diálogo, servida por `GET /usos/{id}/hodometro/{saida|chegada}` — bytes pela
API, não URL pública (`backend/11`).

Como a rota exige sessão e escopo, a imagem entra por `fetch` + `URL.createObjectURL`, e a URL de
objeto é **revogada ao fechar o diálogo**. Um `<img src="/api/...">` cru também funcionaria, mas
deixaria o erro de 404/403 virar ícone quebrado em vez de mensagem.

O ícone só aparece se houver foto — e viagem sem foto é o caso majoritário por muito tempo, porque
a foto é opcional e as viagens antigas não têm nenhuma.

## Capabilities: nenhuma nova, nenhum `Can` novo

Quem pode lançar viagem pode fotografar, e é a mesma capability (`backend/11` não criou nenhuma).
O botão aparece em todo diálogo que a pessoa já consegue abrir — se ela chegou no formulário, tem
`usages.write` ou `write_own`. Um `<Can>` a mais aqui seria um cadeado numa porta que já está
trancada.

## Critérios de aceite

1. Escolher um veículo no diálogo de lançar viagem **pré-preenche** o hodômetro de saída com o
   `current_odometer` dele. Trocar de veículo troca o valor; depois que a pessoa **digitou** algo
   no campo, trocar de veículo **não** sobrescreve o que ela digitou.
2. O botão de câmera fica **desabilitado** enquanto não há veículo escolhido, e diz por quê.
3. Uma foto de 12 MP escolhida no seletor sobe com **no máximo 1600px** no lado maior e como
   `image/jpeg` — verificável no payload da requisição. A função de redução tem teste unitário na
   mesma entrega.
4. Com a leitura respondendo `valor` e `plausivel: true`, o campo é preenchido e a frase mostra o
   valor lido, o último registrado e o delta. O campo continua **editável**, e digitar por cima
   substitui o valor sem drama.
5. Com `plausivel: false`, o aviso aparece em `warning` e **o botão de lançar continua
   habilitado** — a viagem é lançada com o número divergente se a pessoa insistir.
6. Com `valor: null`, o campo **não** é preenchido, a mensagem diz que a foto foi guardada mesmo
   assim, e o formulário segue utilizável.
7. Durante a leitura, o botão mostra "Lendo…" e só o campo de hodômetro fica desabilitado —
   finalidade e observações continuam editáveis.
8. Lançar a viagem depois de uma leitura envia `leitura_saida_id`; lançar **sem** ter fotografado
   envia o corpo sem o campo, e o 201 acontece igual.
9. O diálogo de **encerrar** tem o mesmo botão, o campo de chegada **não** é pré-preenchido, e a
   leitura bem-sucedida preenche `end_odometer` e envia `leitura_chegada_id`.
10. Uma viagem com foto mostra o ícone na lista; clicar abre a imagem num diálogo. Fechar o
    diálogo **revoga** a object URL. Viagem sem foto não mostra ícone.
11. 413, 415, 422 e 429 viram frases em português que dizem o que fazer, e **nenhum** deles limpa
    os campos já preenchidos do formulário.
12. `npm run typecheck`, `lint` e `build` limpos; os tipos da resposta de leitura saem de
    `z.infer` do schema zod, nunca escritos à mão.

---

**Nota de dívida.** Esta entrega agrava a dívida de teste de componente pela terceira vez seguida
(`06`, `07`/`08`, e agora), e desta vez com o pior perfil até aqui: upload, estado assíncrono e
três caminhos de resposta que não são erro de rede. A regra da função pura cobre a redução de
imagem e a tradução de erro; **não cobre** o estado do diálogo, que é onde o custo vai aparecer.
Quem escrever a spec de teste de componente tem aqui o segundo melhor argumento depois do
formulário de viagem da `07` — e agora eles são o mesmo arquivo.
