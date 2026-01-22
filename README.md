# Network Monitor (MVP)

Este repositório inicia um MVP para monitoramento da rede local usando um **backend em Python** com **FastAPI** e **PostgreSQL**.
A proposta é permitir:

- Descoberta/registro de dispositivos (IP/MAC).
- Atribuição de nomes amigáveis aos dispositivos.
- Armazenamento de amostras de tráfego por dispositivo (coletadas via SNMP/port mirroring em um coletor separado).

## Por que esta abordagem?

- **SNMP** (no roteador/switch gerenciável) é uma fonte confiável para estatísticas por dispositivo.
- **PostgreSQL** armazena o inventário de dispositivos e as métricas históricas.
- **FastAPI** facilita expor APIs para um painel web/desktop/móvel.

## Estrutura

```
app/
  main.py        # API FastAPI
  db.py          # Conexão com o PostgreSQL
  models.py      # Modelos SQLAlchemy
  schemas.py     # Modelos Pydantic
  crud.py        # Operações de banco
  snmp.py        # Placeholder para coleta SNMP
requirements.txt
```

## Configuração rápida

1. Crie um banco e defina a variável `DATABASE_URL`, por exemplo:

```
export DATABASE_URL="postgresql+psycopg2://usuario:senha@localhost:5432/network_monitor"
```

2. Instale as dependências:

```
pip install -r requirements.txt
```

3. Execute a API:

```
uvicorn app.main:app --reload
```

A API estará em `http://127.0.0.1:8000`.

## Interface de configuração do roteador

Abra `http://127.0.0.1:8000/setup` para inserir o IP do roteador, usuário e senha.
Esses dados são salvos na tabela `router_config` para o coletor SNMP/integração
posterior usar como credenciais de acesso.

> Observação: neste MVP as credenciais são armazenadas em texto puro. Em produção,
> use um cofre de segredos ou criptografia em repouso.

## Próximos passos sugeridos

- Adicionar um coletor SNMP real (ex.: `pysnmp`) para gravar amostras em `traffic_samples`.
- Implementar descoberta automática de dispositivos (ARP scan ou via SNMP).
- Criar dashboard web (React/Vue) ou app desktop/mobile consumindo a API.
