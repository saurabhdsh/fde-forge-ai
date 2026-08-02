# Bedrock + OpenAI for FDE Forge AI

FDE Forge AI supports **OpenAI** and **AWS Bedrock** (Claude via Converse). Which one runs depends on the machine.

| Machine | Default | How |
|---------|---------|-----|
| **This Mac (dev)** | OpenAI | `BEDROCK_ENABLED=false`, `AI_DEFAULT_PROVIDER=openai`, set `OPENAI_API_KEY` |
| **TCS Mac (Bedrock)** | Bedrock only | Run `./setup.sh` — **SQLite + local uploads**, no Docker/Homebrew. Uses `~/.aws`. |
| **AWS EC2 (Docker)** | Bedrock only | Run `./setup.sh` (detects Docker, scales workers). Use instance IAM role — no keys in `.env`. |

## Quick Bedrock access check (Mac)

Before generating domain courses (which can take several minutes), verify credentials:

```bash
cd fde-forge-ai
set -a && source .env && set +a
source apps/api/.venv/bin/activate
PYTHONPATH=apps/api:. python -m scripts.check_bedrock
```

Or while the API is running (signed in), open:

`GET /api/v1/ai/bedrock/check` → http://localhost:8000/docs

You should see `"ok": true` and a short `BEDROCK_OK` reply. If this fails, course generation will also fail/timeout.

## Verified Bedrock model

| Setting | Value |
|---------|--------|
| Region | `us-east-1` |
| Model | `us.anthropic.claude-sonnet-4-5-20250929-v1:0` |
| Embeddings | Prefer OpenAI embeddings when key present; else Titan `amazon.titan-embed-text-v2:0` |
| IAM | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` |

---

## This Mac (no Bedrock credentials)

`.env` should look like:

```bash
OPENAI_API_KEY=sk-...
AI_DEFAULT_PROVIDER=openai
DEFAULT_LLM_PROVIDER=openai
BEDROCK_ENABLED=false
ENABLED_LLM_PROVIDERS=openai,bedrock
```

```bash
docker compose up -d api web
curl -s http://localhost:8000/api/v1/health | jq .
# expect: default_llm_provider=openai, bedrock_enabled=false
```

---

## TCS Mac (Bedrock configured)

On the Mac that already has Working AWS Bedrock:

1. Confirm CLI:
   ```bash
   aws sts get-caller-identity
   aws bedrock-runtime converse \
     --model-id "us.anthropic.claude-sonnet-4-5-20250929-v1:0" \
     --messages '[{"role":"user","content":[{"text":"Hi"}]}]' \
     --region us-east-1
   ```
2. In project `.env`:
   ```bash
   BEDROCK_ENABLED=true
   AI_DEFAULT_PROVIDER=bedrock
   DEFAULT_LLM_PROVIDER=bedrock
   ENABLED_LLM_PROVIDERS=openai,bedrock
   BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0
   AWS_REGION=us-east-1
   OPENAI_API_KEY=...   # optional fallback only
   # Do not put AWS keys in git — use ~/.aws
   ```
3. Compose mounts `${HOME}/.aws` into API/worker. Then:
   ```bash
   docker compose up -d --build api worker web
   curl -s http://localhost:8000/api/v1/health | jq .
   # after login:
   curl -s http://localhost:8000/api/v1/ai/providers -b cookies.txt | jq .
   ```

---

## AWS (EC2 / ECS)

- Attach instance/task role with InvokeModel.
- Same Bedrock env as TCS Mac; **omit** `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`.

Courses, Assessment, Coding, and resume extraction go through `AIGateway`. If Bedrock is enabled but IAM fails and OpenAI is configured, the gateway falls back to OpenAI.
