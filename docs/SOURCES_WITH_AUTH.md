# Fontes com credenciais

O **core do findata-br é 100% sem auth** — BCB, CVM, B3, IBGE, IPEA e Tesouro
Nacional rodam apenas com `pip install findata-br`. As fontes documentadas
neste arquivo são **opt-in**, exigem credenciais que você (operador da
instância) traz, e ficam silenciadas até você configurá-las.

## Princípios de design

1. **Zero credenciais embutidas.** O projeto nunca armazena, nunca
   compartilha, nunca embute API keys de ninguém.
2. **Cada operador traz as suas.** Quem instala o findata-br e quer ANBIMA,
   SUSEP, etc. abre conta com o provedor e passa as credenciais via env var.
3. **Fail-clean quando ausente.** Sem credenciais, as rotas retornam
   `503 Service Unavailable` com mensagem dizendo qual env var setar — nunca
   `401`, nunca crash.
4. **Tokens cacheados em processo.** OAuth2 client_credentials flow é feito
   uma vez; o token vive em memória até ~60s antes de expirar.
5. **Arquitetura genérica.** O módulo `findata.auth` serve qualquer fonte
   futura — basta uma subclasse de `OAuth2ClientCredentials` e um
   `load_<fonte>_credentials()` que lê env vars.

## Fontes implementadas

### ANBIMA

[ANBIMA Data API](https://developers.anbima.com.br) — gateway Sensedia.

**Como obter credenciais:**

1. Cadastre-se em <https://developers.anbima.com.br>
2. Crie um app
3. Subscreva ele aos produtos que você quer (Preços e Índices, Renda Fixa,
   Fundos, etc.)
4. Pegue o `client_id` e `client_secret` da app

**Configurar:**

```bash
export ANBIMA_CLIENT_ID="seu-client-id"
export ANBIMA_CLIENT_SECRET="seu-client-secret"
```

Ou no `.env` do deploy (já no `.gitignore`):

```dotenv
ANBIMA_CLIENT_ID=seu-client-id
ANBIMA_CLIENT_SECRET=seu-client-secret
```

**Verificar se está OK:**

```bash
findata anbima status
# → ANBIMA credentials configured
```

ou via API:

```bash
curl http://localhost:8000/anbima/status
# {"configured": true}
```

**Rotas disponíveis** (todas exigem credenciais):

| Rota | Dado |
|---|---|
| `GET /anbima/ima?family=IMA-B` | Índices IMA (família IMA-B, IMA-S, IRF-M, etc.) |
| `GET /anbima/ihfa` | Índice de Hedge Funds (IHFA) |
| `GET /anbima/ida` | Índices de Debêntures (IDA) |
| `GET /anbima/ettj` | Estrutura a Termo da Taxa de Juros (curva zero) |
| `GET /anbima/status` | Diz se as credenciais estão configuradas (sem expor) |

**CLI equivalente:**

```bash
findata anbima ima -i IMA-B -d 2026-04-22
findata anbima ihfa
findata anbima ettj
findata anbima status
```

**Quirks da API ANBIMA** (já tratados internamente, documentados pra
contributors):

- Token endpoint: `POST /oauth/access-token` (não `/oauth/token`).
- Header de auth: `access_token: <token>` (não `Authorization: Bearer`).
- Header obrigatório adicional: `client_id: <client_id>`.
- "Access denied for this environment" → seu app não está subscrito ao
  produto. Entre no developer portal e ative.

### Próximas fontes (planejadas, não implementadas)

| Fonte | Tipo | Trigger pra implementar |
|---|---|---|
| **SUSEP** | OAuth2 (provável) | Issue ou PR da comunidade |
| **BNDES Open Banking** | API key | Issue ou PR |
| **CETIP / B3 Balcão** | API key + IP whitelist | Sob demanda |

Cada nova fonte segue o mesmo padrão: módulo em `findata/sources/<fonte>/`,
router em `findata/api/routers/<fonte>.py`, env vars `<FONTE>_CLIENT_ID`/`<FONTE>_CLIENT_SECRET`
ou equivalentes, comportamento `503 → 401 → success` consistente.

## Como adicionar uma nova fonte com auth

1. **`src/findata/sources/<fonte>/credentials.py`** — função
   `load_<fonte>_credentials()` que lê env vars e levanta
   `MissingCredentialsError` quando ausentes.
2. **`src/findata/sources/<fonte>/client.py`** — subclasse de
   `OAuth2ClientCredentials` com `_token_url`, `header_name` e
   `header_prefix` certos pro provider.
3. **`src/findata/api/routers/<fonte>.py`** — router FastAPI usando o
   helper `_safely` que traduz exceções em HTTP responses.
4. **`tests/test_<fonte>.py`** — testes mockados via `respx` que verificam
   503 quando creds ausentes + happy path com env vars setadas.
5. **PR com link pro developer portal** do provedor pra reviewers
   conferirem o ToS.
