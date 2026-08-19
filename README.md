# Saldo Clientes — Automação

Dois boletins por e-mail, a partir do mesmo Excel que o BTG
disponibiliza (`Saldo_em_CC_BTG.xlsx`):

- **`main.py`** — saldo em conta corrente, todo dia (aba "Saldo Diário").
- **`vencimentos_mensal.py`** — vencimentos de renda fixa do mês, uma
  vez por mês, no primeiro dia útil (aba "Vencimentos RF").

Hoje há um único banker e todos os clientes são dele; a estrutura já
está pronta para, no futuro, separar por banker sem reescrever nada
(veja "Múltiplos bankers" abaixo). Os dois boletins compartilham
configuração (`settings.yaml`, `bankers.csv`, SMTP) e o mesmo estilo
visual (fonte, cores, tabela como imagem) — o que muda é só o conteúdo.

## Boletim de saldo (main.py) — como funciona (resumo)

1. Você baixa o Excel do BTG (manualmente, por enquanto) e salva sempre
   no mesmo caminho — ex: `C:/Saldo/Saldo_em_CC_BTG.xlsx`.
2. `settings.yaml` aponta pra esse caminho (`saldos_xlsx`) e diz qual é
   o `banker_id` responsável por todo o arquivo (`banker_padrao`).
3. `config/bankers.csv` tem o e-mail de cada banker (hoje, uma linha só).
4. Ao rodar `python main.py`, o script lê a aba "Saldo Diário", monta um
   e-mail HTML com todas as contas do arquivo, e envia pro e-mail do
   banker correspondente.

## Formato do Excel do BTG

O script lê a aba **"Saldo Diário"**, que tem estas colunas (o nome
exato pode variar um pouco entre exportações — o script tolera isso):

| coluna              | descrição                                  |
|---------------------|----------------------------------------------|
| `Conta do BTG`       | número da conta                              |
| `Código do Cliente`  | código do cliente (ex: `AOAK_MA`) — o BTG não exporta o nome completo aqui, só o código |
| `Saldo`              | saldo em conta corrente (não investido)      |

Um mesmo código de cliente pode aparecer em mais de uma linha, se tiver
mais de uma conta — cada linha vira uma linha na tabela do e-mail.

A planilha do BTG também traz outras abas (`Base BTG` com o patrimônio
total, `Vencimentos RF` com o detalhe de renda fixa) que **não** são
usadas por este boletim — ele lê só o saldo em conta corrente.

## Boletim de vencimentos (vencimentos_mensal.py) — como funciona

Lê a aba **"Vencimentos RF"** da mesma planilha do BTG e envia, uma vez
por mês, a lista de ativos de renda fixa que vencem naquele mês —
Cliente, Ativo, Emissor, Vencimento e Valor Líquido (curva cliente).
Se nenhum ativo vencer no mês, o e-mail ainda é enviado, só que sem
tabela (avisando que não há vencimento naquele mês) — em vez de ficar
em silêncio, o que poderia parecer que a automação quebrou.

Colunas lidas da aba (nomes toleram pequena variação, igual ao saldo):

| coluna                          | uso                                    |
|----------------------------------|------------------------------------------|
| `Conta BTG`                      | número da conta                          |
| `Código do Cliente`               | código do cliente                        |
| `Emissor`                         | nome do emissor do ativo                 |
| `Ativo`                           | identificador do ativo (ex: `CDB-CDB1234AB1D`) |
| `Vencimento`                      | data de vencimento — usada pra filtrar o mês |
| `Valor Líquido - Curva Cliente`   | valor mostrado na tabela                 |

### Qual mês é enviado

O e-mail sai no **primeiro dia útil do mês** e mostra os vencimentos
**daquele mesmo mês** (não do mês seguinte). O Agendador de Tarefas do
Windows não tem um gatilho nativo de "primeiro dia útil" — a solução é
agendar `vencimentos_mensal.bat` pra rodar **todo dia útil** (segunda a
sexta) e deixar o próprio script decidir se hoje é o dia certo
(`eh_primeiro_dia_util()` em `vencimentos_mensal.py`, considera só
fins de semana — não considera feriados). Nos outros dias, ele sai sem
enviar nada e sem erro — é esperado ver isso quase todo dia no
`logs/tarefa_agendada_vencimentos.log`.

Pra testar com um mês específico (útil porque o mês atual pode não ter
nenhum vencimento nos seus dados de teste):

```
python vencimentos_mensal.py --dry-run --mes 9 --ano 2026
```

E pra forçar o envio real ignorando a checagem de dia útil (ex: você
esqueceu de rodar no dia certo e quer mandar mesmo assim):

```
python vencimentos_mensal.py --forcar
```

### Testando e agendando

Mesmo padrão do boletim de saldo:

1. **`testar_vencimentos.bat`** (dry-run) — grava o HTML em
   `saida_teste/vencimentos-<banker_id>.html`.
2. **`vencimentos_mensal.bat` com `modo_teste.ativo: true`** — envio
   real, redirecionado pro seu endereço de teste.

No Agendador de Tarefas, a única diferença pro boletim de saldo é o
gatilho: em vez de "Diariamente", use **"Semanalmente"**, repetir toda
semana, marcando **segunda a sexta**. A Ação é a mesma ideia, só
trocando o programa:
- Programa/script: `C:\Automacoes\...\vencimentos_mensal.bat`
- Adicionar argumentos: `silencioso`
- Iniciar em: a pasta do projeto

## Revisão manual antes de chegar ao banker (relay)

Por definição do family office, o e-mail não vai direto para o banker
final — ele passa primeiro por uma caixa de revisão (hoje, o e-mail
profissional de quem administra a automação), e essa pessoa encaminha
manualmente para o banker depois. Isso é permanente, não uma etapa de
teste a ser removida depois.

Isso é implementado sem nenhuma lógica especial: o campo `email` em
`bankers.csv` é o endereço de **entrega** da automação, que pode ser
diferente do e-mail do próprio banker — o `banker_nome` (usado na
saudação, "Bom dia Fulano") continua sendo o do banker de verdade. Ou
seja, a linha de um banker em `bankers.csv` pode legitimamente apontar
pra caixa de outra pessoa; não é um erro de configuração.

```csv
banker_id,banker_nome,email
vbrandao,Viviane,acarvalho@hortocapital.com.br
```

Se um dia quiser que a automação envie direto pro banker (pulando a
revisão manual), é só trocar esse `email` pelo e-mail do próprio
banker — mas isso é opcional, não o destino "final" do projeto.

## Múltiplos bankers (quando precisar)

Hoje `banker_padrao` em `settings.yaml` é atribuído a toda linha do
Excel, porque só existe um banker. Quando houver mais de um:

1. Crie `config/clientes_banker.csv` com duas colunas: `codigo_cliente`,
   `banker_id`.
2. Em `src/saldos.py`, troque a linha `df["banker_id"] = banker_padrao`
   por um `merge` desse DataFrame com o mapeamento código → banker
   (usando `cliente` como chave), e trate cliente sem mapeamento como
   pendência.

O resto do fluxo (agrupamento por banker em `src/agrupador.py`, envio
individual em `src/notify.py`, checagem de que ninguém recebe dado de
outro banker) já funciona para qualquer quantidade de bankers — não
precisa mudar.

## Tabela como imagem (não editável)

Em nenhum dos dois boletins a tabela vai como HTML no e-mail — vem como
imagem PNG (`src/tabela_imagem.py` pro saldo, `src/tabela_vencimentos_imagem.py`
pros vencimentos, ambos usando `src/imagem_util.py`, gerada com Pillow),
embutida no e-mail como anexo inline (`Content-ID`, referenciado via
`cid:` no HTML — é o jeito que funciona de forma confiável no Outlook,
diferente de imagem em base64 direto no HTML). O texto acima e abaixo
da tabela é HTML normal, em tamanho 11 (`font-size:11pt`), montado por
`src/email_base.py` (compartilhado pelos dois boletins — `email_builder.py`
e `email_builder_vencimentos.py` só passam o texto e a imagem específicos
de cada um).

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
   com o(s) banker(s) reais (`banker_id`, nome, e-mail).
4. Copie `config/settings.example.yaml` → `config/settings.yaml` e
   ajuste:
   - `saldos_xlsx`: caminho completo de onde você salva o Excel baixado
     do BTG;
   - `banker_padrao`: o `banker_id` (precisa ser um dos cadastrados em
     `bankers.csv`);
   - `email:` com os dados de SMTP da empresa — **deixe
     `modo_teste.ativo: true`** enquanto estiver testando (veja abaixo).

## Testando antes de ativar de verdade

Existem dois passos de teste, em ordem, antes de mandar e-mail real pro
banker:

1. **`testar.bat`** (dry-run) — não usa SMTP nenhum; grava o HTML em
   `saida_teste/<banker_id>.html` pra você abrir no navegador e conferir
   o conteúdo.
2. **`atualizar.bat` com `modo_teste.ativo: true`** — usa o SMTP de
   verdade, mas redireciona todos os e-mails para o endereço em
   `modo_teste.enviar_para`, com um aviso no topo do e-mail dizendo pra
   quem ele seria enviado de verdade. Isso valida a configuração de
   SMTP de ponta a ponta sem expor dado de cliente pros bankers reais.

Só depois de conferir os dois, mude `modo_teste.ativo` para `false` em
`settings.yaml` para começar o envio real — que continua indo pro
endereço configurado em `bankers.csv` (veja "Revisão manual antes de
chegar ao banker" acima), só sem o banner de aviso.

## Rodando manualmente

```
python main.py              # envio normal (real ou modo teste, conforme settings.yaml)
python main.py --dry-run    # não envia nada, só grava HTML em saida_teste/
```

Ou dê duplo clique em `atualizar.bat` / `testar.bat`.

## Agendando a execução automática (Windows Task Scheduler)

1. Baixe o Excel do BTG e salve no caminho configurado em `saldos_xlsx`
   **antes** do horário agendado (isso ainda é manual — veja "Próximos
   passos possíveis" sobre automatizar o download).
2. Abra o **Agendador de Tarefas** do Windows → "Criar Tarefa Básica".
3. Defina o gatilho (ex: todo dia, num horário depois que você já tiver
   salvo o Excel do dia).
4. Ação: "Iniciar um programa".
   - Programa/script: caminho completo até `atualizar.bat`
     (ex: `C:\Automacoes\saldo-clientes-automacao\atualizar.bat`)
   - Adicionar argumentos: `silencioso`
   - Iniciar em: a pasta do projeto (ex:
     `C:\Automacoes\saldo-clientes-automacao`)
5. Salve. A tarefa vai rodar sozinha, sem abrir janela nem esperar
   clique.

## Formato de `config/bankers.csv`

| coluna         | descrição                          |
|----------------|--------------------------------------|
| `banker_id`    | identificador do banker (usado em `banker_padrao`, e futuramente em `clientes_banker.csv`) |
| `banker_nome`  | nome usado na saudação do e-mail ("Bom dia \<nome\>") — sempre o do banker de verdade |
| `email`        | endereço de **entrega** — pode ser o do próprio banker, ou o de uma caixa de revisão que encaminha manualmente depois (veja "Revisão manual antes de chegar ao banker") |

## Histórico

Com `manter_historico: true` (padrão), a cada envio real é gravada uma
linha por banker em `historico/envios_diarios.csv` com data, banker,
quantidade de contas e saldo total — **sem** detalhe por cliente — para
auditoria de que os e-mails foram enviados.

## Próximos passos possíveis

- Automatizar o download do Excel do BTG (se o BTG tiver uma API ou
  portal com exportação agendável), eliminando o passo manual antes do
  Agendador de Tarefas rodar.
- Trocar o código do cliente por um nome legível no e-mail — é só
  fornecer um mapeamento código → nome e ajustar `email_builder.py`.
- Separar por múltiplos bankers (veja seção acima).
- Anexar o saldo em Excel além do corpo do e-mail.
- `eh_primeiro_dia_util()` (em `vencimentos_mensal.py`) considera só
  fins de semana, não feriados — se o dia 1º útil "de calendário" cair
  num feriado, o e-mail sai nesse feriado mesmo. Dá pra plugar uma
  lista de feriados (ex: biblioteca `holidays`) se isso incomodar.
