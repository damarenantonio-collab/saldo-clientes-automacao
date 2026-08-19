# Saldo Clientes — Automação

Envia, todo dia, um e-mail para cada banker do family office com o saldo
em conta **apenas** dos seus próprios clientes. Nenhum banker recebe ou
vê dados de clientes de outro banker.

## Como funciona (resumo)

1. Você mantém um arquivo `config/saldos.csv` com uma linha por cliente:
   qual banker é responsável (`banker_id`), nome do cliente, conta e
   saldo. Normalmente esse arquivo é exportado do seu custodiante/
   backoffice todo dia.
2. Você mantém um arquivo `config/bankers.csv` com o e-mail de cada
   banker.
3. Ao rodar `python main.py`, o script:
   - agrupa as linhas de `saldos.csv` por `banker_id`;
   - para cada banker, monta um e-mail HTML só com as linhas dele;
   - envia esse e-mail só para o endereço daquele banker.

## Como o acesso por banker é garantido

- O agrupamento (`src/agrupador.py`) nunca produz um "grupo" com dados
  de mais de um banker — cada e-mail é montado a partir de um
  subconjunto já filtrado do arquivo original.
- Cada envio (`src/notify.py`) manda **um e-mail por vez**, com `To`
  contendo só o e-mail daquele banker — nunca em lote, nunca com
  CC/BCC juntando vários bankers.
- Se um `banker_id` aparecer em `saldos.csv` sem e-mail cadastrado em
  `bankers.csv`, os clientes dele **não são enviados para ninguém**
  nessa execução (em vez de arriscar mandar pro lugar errado) — o
  responsável pela automação é avisado por e-mail separadamente (veja
  `alerta_email` em `settings.yaml`).
- Uma checagem interna (`_validar_sem_vazamento`) garante que toda linha
  do arquivo original aparece em exatamente um grupo (ou na lista de
  pendências) antes de qualquer envio — se algo não bater, a execução é
  interrompida sem enviar nada.
- Por padrão, os logs de execução (`logs/execucao.log`) **não** contêm
  nome de cliente, conta nem saldo — só contagens e nomes de banker
  (configurável em `log_dados_sensiveis`, só pra depuração pontual).

## Instalação (Windows)

1. Instale o [Python](https://www.python.org/downloads/windows/) (marque
   "Add python.exe to PATH" no instalador), se ainda não tiver.
2. Dê duplo clique em **`instalar.bat`**.
3. Copie `config/saldos.example.csv` → `config/saldos.csv` e
   `config/bankers.example.csv` → `config/bankers.csv`, e preencha com
   os dados reais (ou aponte `saldos_csv`/`bankers_csv` em
   `settings.yaml` para os arquivos que já existem no seu ambiente).
4. Copie `config/settings.example.yaml` → `config/settings.yaml` e
   preencha os dados de SMTP da empresa em `email:` — **deixe
   `email.modo_teste.ativo: true`** enquanto estiver testando (veja
   abaixo).

## Testando antes de ativar de verdade

Existem dois passos de teste, em ordem, antes de mandar e-mail real pro
banker:

1. **`testar.bat`** (dry-run) — não usa SMTP nenhum; grava o HTML de
   cada banker em `saida_teste/<banker_id>.html` pra você abrir no
   navegador e conferir o conteúdo.
2. **`atualizar.bat` com `modo_teste.ativo: true`** — usa o SMTP de
   verdade, mas redireciona todos os e-mails (de todos os bankers) para
   o endereço em `modo_teste.enviar_para`, com um aviso no topo do
   e-mail dizendo pra quem ele seria enviado de verdade. Isso valida a
   configuração de SMTP de ponta a ponta sem expor dado de cliente pros
   bankers reais.

Só depois de conferir os dois, mude `modo_teste.ativo` para `false` em
`settings.yaml` para começar o envio real.

## Rodando manualmente

```
python main.py              # envio normal (real ou modo teste, conforme settings.yaml)
python main.py --dry-run    # não envia nada, só grava HTML em saida_teste/
```

Ou dê duplo clique em `atualizar.bat` / `testar.bat`.

## Agendando a execução automática (Windows Task Scheduler)

1. Abra o **Agendador de Tarefas** do Windows → "Criar Tarefa Básica".
2. Defina o gatilho (ex: todo dia, num horário depois que o arquivo de
   saldos do custodiante já estiver disponível).
3. Ação: "Iniciar um programa".
   - Programa/script: caminho completo até `atualizar.bat`
     (ex: `C:\Automacoes\saldo-clientes-automacao\atualizar.bat`)
   - Adicionar argumentos: `silencioso`
   - Iniciar em: a pasta do projeto (ex:
     `C:\Automacoes\saldo-clientes-automacao`)
4. Salve. A tarefa vai rodar sozinha, sem abrir janela nem esperar
   clique.

## Formato de `config/saldos.csv`

| coluna      | descrição                                              |
|-------------|---------------------------------------------------------|
| `banker_id` | identificador do banker responsável (chave usada para casar com `bankers.csv`) |
| `cliente`   | nome do cliente (ou razão social)                        |
| `conta`     | número da conta                                          |
| `saldo`     | saldo em conta (numérico)                                |

## Formato de `config/bankers.csv`

| coluna         | descrição                          |
|----------------|--------------------------------------|
| `banker_id`    | mesmo identificador usado em `saldos.csv` |
| `banker_nome`  | nome exibido no e-mail                |
| `email`        | endereço de e-mail do banker          |

## Histórico

Com `manter_historico: true` (padrão), a cada envio real é gravada uma
linha por banker em `historico/envios_diarios.csv` com data, banker,
quantidade de clientes e saldo total — **sem** detalhe por cliente —
para auditoria de que os e-mails foram enviados.

## Próximos passos possíveis

- Trocar a fonte de `saldos.csv` por uma consulta direta a uma API do
  custodiante ou a um banco de dados interno (o resto do fluxo não
  muda — só a função que carrega o DataFrame em `src/saldos.py`).
- Anexar o saldo em Excel além do corpo do e-mail.
- Enviar uma cópia consolidada (todos os clientes) para um gestor/sócio,
  como um envio adicional e explicitamente separado dos e-mails por
  banker — não reaproveitando o mesmo grupo, para manter o mesmo
  princípio de "cada e-mail é montado para um destinatário específico".
