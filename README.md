# Saldo Clientes — Automação

Dois e-mails automáticos, de fontes diferentes:

- **`main.py`** — saldo em conta corrente, todo dia, a partir do Excel
  do BTG (`Saldo_em_CC_BTG.xlsx`, aba "Saldo Diário"). Hoje só a
  Viviane tem esse boletim.
- **`vencimentos_mensal.py`** — vencimentos de renda fixa do mês, uma
  vez por mês (dia 1, via gatilho mensal do Agendador de Tarefas), a
  partir da planilha consolidada do escritório inteiro
  (`Vencimentos_RF.xlsx`, aba "Export"). Um e-mail por responsável
  (banker) — hoje Eduardo Rego, Viviane Brandão e Antonio Carvalho.

São fontes de dados diferentes e independentes uma da outra — não é
preciso que um cliente apareça nas duas pra funcionar.

## Boletim de saldo (main.py)

1. Você baixa o Excel do BTG (manualmente, por enquanto) e salva sempre
   no mesmo caminho — ex: `C:/Saldo/Saldo_em_CC_BTG.xlsx`.
2. `settings.yaml` aponta pra esse caminho (`saldos_xlsx`) e diz qual é
   o `banker_id` responsável por todo o arquivo (`banker_padrao`).
3. Ao rodar `python main.py`, o script lê a aba "Saldo Diário", monta um
   e-mail com todas as contas do arquivo, e envia pro e-mail do banker
   correspondente.

### Formato do Excel do BTG

O script lê a aba **"Saldo Diário"**, que tem estas colunas (o nome
exato pode variar um pouco entre exportações — o script tolera isso):

| coluna              | descrição                                  |
|---------------------|----------------------------------------------|
| `Conta do BTG`       | número da conta                              |
| `Código do Cliente`  | código do cliente (ex: `AOAK_MA`) — o BTG não exporta o nome completo aqui, só o código |
| `Saldo`              | saldo em conta corrente (não investido)      |

Um mesmo código de cliente pode aparecer em mais de uma linha, se tiver
mais de uma conta — cada linha vira uma linha na tabela do e-mail.

### Um único banker (por enquanto)

O BTG não exporta quem é o responsável por cada cliente nessa
planilha — então `banker_padrao`, em `settings.yaml`, é atribuído a
toda linha do arquivo. Se um dia esse boletim precisar cobrir mais de
um banker, o jeito é o mesmo já usado no boletim de vencimentos (veja
"Como o banker é identificado" abaixo): crie (ou peça pro BTG) um
export do saldo que já traga o responsável de cada conta, e adapte
`src/saldos.py` pra derivar `banker_id` direto dessa coluna, em vez do
`banker_padrao` fixo.

## Boletim de vencimentos (vencimentos_mensal.py)

Lê a aba **"Export"** da planilha consolidada de vencimentos do
escritório e envia, uma vez por mês, a lista de ativos de renda fixa
que vencem naquele mês — um e-mail por responsável, cada um só com os
vencimentos dos seus próprios clientes. Se um responsável não tiver
nenhum vencimento no mês, ele recebe o e-mail mesmo assim, só sem
tabela (avisando que não há vencimento naquele mês) — em vez de ficar
em silêncio, o que poderia parecer que a automação esqueceu dele.

### Formato da planilha de vencimentos

| coluna              | uso                                              |
|----------------------|--------------------------------------------------|
| `Conta BTG`           | número da conta (usado internamente, não aparece na tabela) |
| `Nome do Cliente`     | nome/código do cliente                            |
| `Descrição`           | tipo do ativo (ex: `CDB`, `LCI`, `TESOURO DIRETO - NTN-B`) |
| `Valor Líquido`       | valor mostrado na tabela                          |
| `Data Vencimento`     | data de vencimento — usada pra filtrar o mês      |
| `Responsável`         | nome do banker — vira o `banker_id` (veja abaixo) |

`Data Movimentação` existe na planilha mas não é usada.

### Como o banker é identificado

Diferente do saldo, essa planilha **já traz o responsável de cada
linha** — não precisa de `banker_padrao` nem de mapeamento manual.
`src/vencimentos.py` deriva o `banker_id` direto do nome em
"Responsável", normalizando pra minúsculo/sem acento/com underscore:

```
"Eduardo Rego"    -> eduardo_rego
"Viviane Brandão" -> viviane_brandao
"Antonio Carvalho" -> antonio_carvalho
```

Esse `banker_id` precisa existir em `config/bankers.csv` com um
e-mail cadastrado — se um responsável aparecer na planilha (em
qualquer mês) sem estar em `bankers.csv`, ele entra na lista de
pendências e o responsável pela automação é avisado por e-mail (veja
`alerta_email`), mas nada é enviado pra esse banker até você
cadastrá-lo. Isso vale pra quantos responsáveis a planilha tiver —
crescer o time não exige mudar código, só adicionar uma linha em
`bankers.csv`.

### Qual mês é mostrado

O e-mail mostra os vencimentos **do mês em que é enviado** (não do mês
seguinte) — ex: enviado em setembro, mostra vencimentos de setembro.
O script não tem checagem de dia nenhuma — ele envia sempre que é
chamado; quem decide a cadência é o gatilho **Mensalmente** do
Agendador de Tarefas (veja "Agendando" abaixo). Isso pressupõe que a
planilha `Vencimentos_RF.xlsx` esteja atualizada até lá — como ela só
muda uma vez por mês (diferente do saldo, que é diário), basta
atualizá-la perto do início do mês, antes do dia agendado.

Pra testar com um mês específico (útil porque o mês atual pode não ter
nenhum vencimento nos seus dados de teste):

```
python vencimentos_mensal.py --dry-run --mes 9 --ano 2026
```

## Revisão manual antes de chegar ao banker (relay)

Por definição do family office, o e-mail não vai direto para o banker
final — ele passa primeiro por uma caixa de revisão (hoje, o e-mail
profissional de quem administra a automação), e essa pessoa encaminha
manualmente para o banker depois. Isso é permanente, não uma etapa de
teste a ser removida depois. Vale pros dois boletins, e pra todos os
bankers — inclusive Eduardo Rego, não só a Viviane.

Isso é implementado sem nenhuma lógica especial: o campo `email` em
`bankers.csv` é o endereço de **entrega** da automação, que pode ser
diferente do e-mail do próprio banker — o `banker_nome` (usado na
saudação, "Bom dia Fulano") continua sendo o do banker de verdade. Ou
seja, a linha de um banker em `bankers.csv` pode legitimamente apontar
pra caixa de outra pessoa; não é um erro de configuração.

```csv
banker_id,banker_nome,email
vbrandao,Viviane,acarvalho@hortocapital.com.br
eduardo_rego,Eduardo Rego,acarvalho@hortocapital.com.br
viviane_brandao,Viviane Brandão,acarvalho@hortocapital.com.br
antonio_carvalho,Antonio Carvalho,acarvalho@hortocapital.com.br
```

(repare que `vbrandao` — usado pelo boletim de saldo — e
`viviane_brandao` — derivado da planilha de vencimentos — são a mesma
pessoa, com `banker_id`s diferentes porque vêm de fontes de dados
diferentes; isso é normal, não precisa unificar.)

Se um dia quiser que a automação envie direto pro banker (pulando a
revisão manual), é só trocar o `email` daquela linha pelo e-mail do
próprio banker — mas isso é opcional, não o destino "final" do projeto.

## Tabela como imagem (não editável)

Nenhuma tabela vai como HTML no e-mail — vem como imagem PNG
(`src/tabela_imagem.py` pro saldo, `src/tabela_vencimentos_imagem.py`
pros vencimentos, ambos usando `src/imagem_util.py`, gerada com Pillow),
embutida no e-mail como anexo inline (`Content-ID`, referenciado via
`cid:` no HTML — é o jeito que funciona de forma confiável no Outlook,
diferente de imagem em base64 direto no HTML). O texto é HTML normal,
em tamanho 11 (`font-size:11pt`), montado por `src/email_base.py`
(compartilhado pelos dois boletins — `email_builder.py` e
`email_builder_vencimentos.py` só passam o texto e a imagem
específicos de cada um).

Isso é proposital: como imagem, o conteúdo não pode ser editado por
quem recebe o e-mail antes de encaminhar — diferente de uma tabela em
texto/HTML, que pode ter célula ou valor alterado.

A imagem usa a mesma fonte do texto (Georgia). O gerador procura
`C:/Windows/Fonts/georgia.ttf` (padrão no Windows) e cai pra uma fonte
serifada genérica se não encontrar — então funciona em qualquer
máquina, mas fica visualmente mais fiel no Windows.

## Como o acesso por banker é garantido

Vale para os dois boletins — ambos usam o mesmo `src/agrupador.py`.

- O agrupamento (`src/agrupador.py`) nunca produz um "grupo" com dados
  de mais de um banker — cada e-mail é montado a partir de um
  subconjunto já filtrado do arquivo original.
- Cada envio (`src/notify.py`) manda **um e-mail por vez**, com `To`
  contendo só o e-mail daquele banker — nunca em lote, nunca com
  CC/BCC juntando vários bankers.
- Se um `banker_id` não existir em `bankers.csv` (ou não tiver e-mail
  cadastrado), os clientes dele **não são enviados para ninguém**
  nessa execução (em vez de arriscar mandar pro lugar errado) — o
  responsável pela automação é avisado por e-mail separadamente (veja
  `alerta_email` em `settings.yaml`).
- Uma checagem interna (`_validar_sem_vazamento`) garante que toda linha
  do arquivo original aparece em exatamente um grupo (ou na lista de
  pendências) antes de qualquer envio — se algo não bater, a execução é
  interrompida sem enviar nada.
- Por padrão, os logs de execução (`logs/execucao.log` e
  `logs/execucao_vencimentos.log`) **não** contêm código de cliente,
  conta, saldo nem valor de vencimento — só contagens e nomes de banker
  (configurável em `log_dados_sensiveis`, só pra depuração pontual).

## Instalação (Windows)

1. Instale o [Python](https://www.python.org/downloads/windows/) (marque
   "Add python.exe to PATH" no instalador), se ainda não tiver.
2. Dê duplo clique em **`instalar.bat`**.
3. Copie `config/bankers.example.csv` → `config/bankers.csv` e preencha
   com os bankers reais (`banker_id`, nome, e-mail) — veja "Como o
   banker é identificado" acima pra saber o `banker_id` de cada
   responsável do boletim de vencimentos.
4. Copie `config/settings.example.yaml` → `config/settings.yaml` e
   ajuste:
   - `saldos_xlsx`: caminho de onde você salva o Excel de saldo do BTG;
   - `banker_padrao`: o `banker_id` do boletim de saldo;
   - `vencimentos_xlsx`: caminho da planilha consolidada de vencimentos;
   - `email:` com os dados de SMTP da empresa — **deixe
     `modo_teste.ativo: true`** enquanto estiver testando (veja abaixo).

## Testando antes de ativar de verdade

Mesmo padrão pros dois boletins — dois passos, em ordem:

1. **`testar.bat`** / **`testar_vencimentos.bat`** (dry-run) — não usam
   SMTP nenhum; gravam o HTML em `saida_teste/` pra você abrir no
   navegador e conferir o conteúdo.
2. **`atualizar.bat`** / **`vencimentos_mensal.bat`** com
   `modo_teste.ativo: true` — usam o SMTP de verdade, mas redirecionam
   todos os e-mails para o endereço em `modo_teste.enviar_para`, com um
   aviso no topo do e-mail dizendo pra quem ele seria enviado de
   verdade. Isso valida a configuração de SMTP de ponta a ponta sem
   expor dado de cliente pros bankers reais.

Só depois de conferir os dois, mude `modo_teste.ativo` para `false` em
`settings.yaml` para começar o envio real — que continua indo pro
endereço configurado em `bankers.csv` (veja "Revisão manual antes de
chegar ao banker" acima), só sem o banner de aviso.

## Rodando manualmente

```
python main.py                                    # saldo: envio normal
python main.py --dry-run                          # saldo: só grava HTML

python vencimentos_mensal.py                       # vencimentos: envio normal (mês atual)
python vencimentos_mensal.py --dry-run              # vencimentos: só grava HTML
python vencimentos_mensal.py --dry-run --mes 9 --ano 2026   # simula outro mês
```

Ou dê duplo clique em `atualizar.bat` / `testar.bat` /
`vencimentos_mensal.bat` / `testar_vencimentos.bat`.

## Agendando a execução automática (Windows Task Scheduler)

São **duas tarefas separadas** — os boletins são independentes.

### Saldo (todo dia)

1. Baixe o Excel do BTG e salve no caminho configurado em `saldos_xlsx`
   **antes** do horário agendado (isso ainda é manual).
2. Agendador de Tarefas → "Criar Tarefa Básica" → gatilho **Diariamente**.
3. Ação: "Iniciar um programa".
   - Programa/script: `C:\Automacoes\...\atualizar.bat`
   - Adicionar argumentos: `silencioso`
   - Iniciar em: a pasta do projeto

### Vencimentos (mensal)

1. A planilha consolidada de vencimentos (`vencimentos_xlsx`) só
   precisa ser atualizada uma vez por mês — mas precisa estar
   atualizada **antes** do horário agendado abaixo.
2. Agendador de Tarefas → "Criar Tarefa Básica" → gatilho
   **Mensalmente** → marque o dia 1 (ou o dia do mês que preferir) →
   escolha um horário depois que a planilha já estiver atualizada.
3. Ação: "Iniciar um programa".
   - Programa/script: `C:\Automacoes\...\vencimentos_mensal.bat`
   - Adicionar argumentos: `silencioso`
   - Iniciar em: a pasta do projeto

Se o dia escolhido cair num fim de semana ou feriado, o Agendador
dispara mesmo assim (não existe ajuste automático pro próximo dia
útil) — escolha um dia do mês que dificilmente vai colidir com isso,
ou ajuste manualmente quando acontecer.

Nas duas, na aba **Geral** das Propriedades da tarefa, use **"Executar
somente quando o usuário estiver conectado"** (evita o erro de logon
0x8007**0569** comum com contas de domínio corporativas rodando "estando
conectado ou não").

## Formato de `config/bankers.csv`

| coluna         | descrição                          |
|----------------|--------------------------------------|
| `banker_id`    | identificador do banker — pro saldo é o valor de `banker_padrao`; pros vencimentos é derivado do nome em "Responsável" (veja "Como o banker é identificado") |
| `banker_nome`  | nome usado na saudação do e-mail ("Bom dia \<primeiro nome\>") — sempre o do banker de verdade |
| `email`        | endereço de **entrega** — pode ser o do próprio banker, ou o de uma caixa de revisão que encaminha manualmente depois (veja "Revisão manual antes de chegar ao banker") |

## Histórico

Com `manter_historico: true` (padrão), a cada envio real do **boletim
de saldo** é gravada uma linha por banker em
`historico/envios_diarios.csv` com data, banker, quantidade de contas e
saldo total — **sem** detalhe por cliente. O boletim de vencimentos não
tem histórico próprio ainda (veja "Próximos passos possíveis").

## Próximos passos possíveis

- Automatizar o download dos dois arquivos (saldo e vencimentos), se o
  BTG/sistema interno tiver exportação agendável, eliminando o passo
  manual antes do Agendador de Tarefas rodar.
- Trocar o código do cliente por um nome legível no boletim de saldo —
  é só fornecer um mapeamento código → nome e ajustar `email_builder.py`.
- Estender o boletim de saldo pra múltiplos bankers, do mesmo jeito que
  o de vencimentos já faz (veja "Um único banker (por enquanto)" acima).
- Anexar o saldo/vencimentos em Excel além do corpo do e-mail.
- Histórico de envios pro boletim de vencimentos (hoje só o de saldo tem).
