# Provisionar o Supabase e ligar a ingestão

Passo a passo do primeiro deploy. Feito uma vez; depois a ingestão roda sozinha.

## 1. Criar o projeto Supabase

1. Entre em <https://supabase.com> e crie um projeto (recomendo **dois**: um
   `aquarius-dev` e um `aquarius-prod`, como previsto na Onda 0).
2. Guarde a **database password** que o painel pede na criação.
3. Escolha uma região próxima (ex.: São Paulo / `sa-east-1`).

## 2. Aplicar o schema (migrations 0001–0006)

**Jeito mais simples (SQL Editor):**
1. No painel do projeto → **SQL Editor** → *New query*.
2. Cole o conteúdo de [`deploy_all.sql`](deploy_all.sql) (é a concatenação, na
   ordem, das 6 migrations) e rode. Cria todo o schema + a camada ouro.

**Jeito com CLI (opcional, melhor para mudanças futuras):**
```bash
cd codigo
npx supabase link --project-ref <ref-do-projeto>
npx supabase db push
```
> Para mudanças DEPOIS do primeiro deploy, crie sempre uma migration NOVA em
> `supabase/migrations/` (nunca edite as antigas) — é o padrão do projeto.

## 3. Pegar as credenciais

No painel → **Project Settings → API**:
- **Project URL** → vira `SUPABASE_URL`
- **service_role key** (secção *Project API keys*) → vira `SUPABASE_SERVICE_KEY`
  - ⚠️ é a chave que ignora RLS. Só em servidor/CI, **nunca** no app cliente.

## 4. Ligar a ingestão automática

No repositório GitHub → **Settings → Secrets and variables → Actions → New
repository secret**, crie os dois:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`

Pronto: o workflow `ingestao.yml` roda 2×/dia (06h/18h BRT) e mantém a base
fresca. Para rodar na hora, use **Actions → Ingestão diária da Câmara → Run
workflow**.

## 5. (Opcional) Rodar localmente uma vez

```bash
cd codigo/services/ingestao
pip install -r requirements.txt
export SUPABASE_URL=...  SUPABASE_SERVICE_KEY=...
python run_ingestao.py
```

## Checagem rápida depois

No painel → **Table Editor**: as tabelas de prata (`proposicao`, `votacao`,
`profiles`, …) devem encher; em **Database → Views**, as views `*_publico` da
camada ouro devem existir e retornar dado (sem PII).
