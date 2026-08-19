# Saldo Clientes — Automação

Envia por e-mail o saldo em conta corrente dos clientes, a partir do
Excel que o BTG disponibiliza (`Saldo_em_CC_BTG.xlsx`, aba "Saldo
Diário"). Hoje há um único banker e todos os clientes são dele; a
estrutura já está pronta para, no futuro, separar por banker sem
reescrever nada (veja "Múltiplos bankers" abaixo).

## Como funciona (resumo)

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
usadas por esta automação — ela lê só o saldo em conta corrente.

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

## Como o acesso por banker é garantido

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
- Por padrão, os logs de execução (`logs/execucao.log`) **não** contêm
  código de cliente, conta nem saldo — só contagens e nomes de banker
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
