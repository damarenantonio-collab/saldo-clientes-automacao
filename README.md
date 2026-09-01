# Saldo Clientes — Automação

Dois e-mails automáticos, a partir de duas planilhas consolidadas do
escritório inteiro (fontes diferentes, independentes uma da outra):

- **`main.py`** — saldo em conta corrente, todo dia, a partir de
  `Saldo_em_CC_BTG.xlsx`.
- **`vencimentos_mensal.py`** — vencimentos de renda fixa do mês, uma
  vez por mês (dia 1, via gatilho mensal do Agendador de Tarefas), a
  partir de `Vencimentos_RF.xlsx`.

Os dois são multi-banker: cada planilha já traz o responsável de cada
linha (coluna "Responsável"), então cada boletim manda um e-mail por
banker, cada um só com os seus próprios clientes — hoje Eduardo Rego,
Viviane Brandão e Antonio Carvalho.

## Como o banker é identificado

As duas planilhas seguem o mesmo princípio: uma aba **"Export"** com
uma coluna **"Responsável"** trazendo o nome do banker daquela linha.
`src/bankers.slugify_banker()` transforma esse nome num `banker_id`
(minúsculo, sem acento, espaço vira underscore):

```
"Eduardo Rego"     -> eduardo_rego
"Viviane Brandão"  -> viviane_brandao
"Antonio Carvalho" -> antonio_carvalho
```

Esse `banker_id` precisa existir em `config/bankers.csv` com um e-mail
cadastrado — se um responsável aparecer numa das planilhas sem estar
em `bankers.csv`, ele entra na lista de pendências e o responsável
pela automação é avisado por e-mail (veja `alerta_email`), mas nada é
enviado pra esse banker até você cadastrá-lo. Isso vale pra quantos
responsáveis as planilhas tiverem — crescer o time não exige mudar
código, só adicionar uma linha em `bankers.csv`.

## Boletim de saldo (main.py)

1. Você baixa a planilha consolidada de saldo (manualmente, por
   enquanto) e salva sempre no mesmo caminho — ex:
   `C:/Saldo/Saldo_em_CC_BTG.xlsx`.
2. Ao rodar `python main.py`, o script lê a aba "Export", agrupa por
   responsável, e envia um e-mail por banker com só as contas dele.

### Formato da planilha de saldo

| coluna              | descrição                                  |
|---------------------|----------------------------------------------|
| `Conta BTG`          | número da conta                              |
| `Nome do Cliente`    | nome/código do cliente                       |
| `Saldo`              | saldo em conta corrente (não investido) — aceita negativo |
| `Responsável`        | nome do banker — vira o `banker_id`          |

Um mesmo cliente pode aparecer em mais de uma linha, se tiver mais de
uma conta — cada linha vira uma linha na tabela do e-mail.

## Boletim de vencimentos (vencimentos_mensal.py)

Lê a aba **"Export"** da planilha consolidada de vencimentos e envia,
uma vez por mês, a lista de ativos de renda fixa que vencem naquele
mês — um e-mail por responsável, cada um só com os vencimentos dos
seus próprios clientes. Se um responsável não tiver nenhum vencimento
no mês, ele recebe o e-mail mesmo assim, só sem tabela (avisando que
não há vencimento naquele mês) — em vez de ficar em silêncio, o que
poderia parecer que a automação esqueceu dele.

### Formato da planilha de vencimentos

| coluna              | uso                                              |
|----------------------|--------------------------------------------------|
| `Conta BTG`           | número da conta (usado internamente, não aparece na tabela) |
| `Nome do Cliente`     | nome/código do cliente                            |
| `Descrição`           | tipo do ativo (ex: `CDB`, `LCI`, `TESOURO DIRETO - NTN-B`) |
| `Valor Líquido`       | valor mostrado na tabela                          |
| `Data Vencimento`     | data de vencimento — usada pra filtrar o mês      |
| `Responsável`         | nome do banker — vira o `banker_id`               |

`Data Movimentação` existe na planilha mas não é usada.

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
bankers.

Isso é implementado sem nenhuma lógica especial: o campo `email` em
`bankers.csv` é o endereço de **entrega** da automação, que pode ser
diferente do e-mail do próprio banker — o `banker_nome` (usado na
saudação, "Bom dia Fulano") continua sendo o do banker de verdade. Ou
seja, a linha de um banker em `bankers.csv` pode legitimamente apontar
pra caixa de outra pessoa; não é um erro de configuração.

```csv
banker_id,banker_nome,email
fulano_silva,Fulano Silva,revisor@suaempresa.com.br
beltrano_souza,Beltrano Souza,revisor@suaempresa.com.br
ciclano_nunes,Ciclano Nunes,revisor@suaempresa.com.br
```

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

## Anexo em Excel

Além da tabela como imagem no corpo, cada e-mail vem com um `.xlsx`
anexado de verdade (`src/anexo_excel.py`), com os mesmos dados daquele
banker — útil pra quem quer abrir numa planilha própria em vez de só
olhar a imagem. Só tem os dados desse banker (mesmo `grupo.clientes`
já filtrado), então a mesma garantia de acesso por banker vale aqui.

- Saldo: `saldo_<banker_id>_<data>.xlsx`, colunas Cliente/Conta/Saldo.
- Vencimentos: `vencimentos_<banker_id>_<ano-mês>.xlsx`,
  colunas Cliente/Produto/Vencimento/Valor Líquido — só é anexado
  quando o banker tem vencimento naquele mês (senão o e-mail já vem
  sem tabela nenhuma, e sem anexo também).

No `--dry-run`, o `.xlsx` é gravado em `saida_teste/` junto do `.html`,
pra conferir antes de enviar de verdade.

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
   banker é identificado" acima pra saber o `banker_id` de cada um.
4. Copie `config/settings.example.yaml` → `config/settings.yaml` e
   ajuste:
   - `saldos_xlsx`: caminho da planilha consolidada de saldo;
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

1. Baixe/atualize a planilha de saldo e salve no caminho configurado em
   `saldos_xlsx` **antes** do horário agendado (isso ainda é manual).
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
   No campo **"Meses"**, marque todos os 12 (se ficar em branco, a
   tarefa não dispara em nenhum mês).
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
| `banker_id`    | identificador do banker — derivado do nome em "Responsável" nas planilhas (veja "Como o banker é identificado") |
| `banker_nome`  | nome usado na saudação do e-mail ("Bom dia \<primeiro nome\>") — sempre o do banker de verdade |
| `email`        | endereço de **entrega** — pode ser o do próprio banker, ou o de uma caixa de revisão que encaminha manualmente depois (veja "Revisão manual antes de chegar ao banker") |

## Histórico

Com `manter_historico: true` (padrão), a cada envio real do **boletim
de saldo** é gravada uma linha por banker em
`historico/envios_diarios.csv` com data, banker, quantidade de contas e
saldo total — **sem** detalhe por cliente. O boletim de vencimentos não
tem histórico próprio ainda (veja "Próximos passos possíveis").

## Próximos passos possíveis

- Automatizar o download das duas planilhas do portal do BTG: hoje é
  manual porque automatizar o login exigiria guardar a senha do banco
  na máquina, sem opção de e-mail/relatório agendado nem API — avaliado
  e propositalmente deixado de fora por enquanto (risco de segurança e
  de violar termos de uso do BTG). Reconsiderar se o BTG passar a
  oferecer exportação agendada por e-mail ou API oficial.
- Trocar o código do cliente por um nome legível no e-mail — é só
  fornecer um mapeamento código → nome e ajustar `email_builder.py` /
  `email_builder_vencimentos.py`.
- Histórico de envios pro boletim de vencimentos (hoje só o de saldo tem).
