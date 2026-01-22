# Network Monitor (MVP)

O Network Monitor é um MVP para monitoramento de rede local. O backend expõe APIs
para registrar dispositivos, armazenar amostras de tráfego e salvar credenciais
do roteador. A interface web (React) apresenta um painel com métricas e permite
configurar o IP e as credenciais do roteador.

## Componentes

- Backend: FastAPI + SQLAlchemy
- Banco de dados: PostgreSQL
- Frontend: React + Vite

## Estrutura do repositório

```
app/
  main.py        # API FastAPI
  db.py          # Conexão com o PostgreSQL
  models.py      # Modelos SQLAlchemy
  schemas.py     # Modelos Pydantic
  crud.py        # Operações de banco
  snmp.py        # Placeholder para coleta SNMP
web/             # Interface web em React
requirements.txt
```

## Requisitos

- Python 3.9+
- Node.js 18+
- PostgreSQL

## Configuração do banco de dados

1. Crie o banco com codificação UTF-8 (exemplo):

```
CREATE DATABASE network_monitor ENCODING 'UTF8';
```

2. Ajuste o arquivo `.env` na raiz do projeto:

```
DATABASE_URL=postgresql+psycopg2://usuario:senha@localhost:5432/network_monitor
DB_CLIENT_ENCODING=UTF8
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

3. As tabelas são criadas automaticamente na primeira execução da API
   (SQLAlchemy `create_all`).

## Backend (FastAPI)

1. Crie e ative o ambiente virtual:

```
python -m venv .venv
```

Windows (PowerShell):

```
.venv\Scripts\Activate.ps1
```

Linux/macOS:

```
source .venv/bin/activate
```

2. Instale as dependências:

```
pip install -r requirements.txt
```

3. Execute a API:

```
uvicorn app.main:app --reload
```

4. Endereços úteis:

- API: `http://127.0.0.1:8000`
- Healthcheck: `http://127.0.0.1:8000/health`
- Documentação Swagger: `http://127.0.0.1:8000/docs`
- Página de configuração do roteador: `http://127.0.0.1:8000/setup`

## Frontend (React)

1. Ajuste a URL da API em `web/.env`:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
```

2. Instale e execute:

```
cd web
npm install
npm run dev
```

3. Acesse:

- `http://localhost:5173`

## Funcionalidades principais

- Cadastro de dispositivos (IP, MAC e nome amigável).
- Registro de amostras de tráfego por dispositivo.
- Cadastro e atualização de credenciais do roteador.
- Painel web com indicadores e filtro de tráfego por dispositivo.

## Principais endpoints da API

- `GET /health`
- `GET /devices`
- `POST /devices`
- `PATCH /devices/{device_id}`
- `GET /traffic`
- `POST /traffic`
- `GET /router-config`
- `PUT /router-config`

## Codificação de caracteres (padrão brasileiro)

- Os arquivos do projeto estão em UTF-8 para preservar acentos.
- O cliente do banco usa UTF-8 via `DB_CLIENT_ENCODING` no `.env`.

## Observação de segurança

As credenciais do roteador são armazenadas em texto puro neste MVP.
