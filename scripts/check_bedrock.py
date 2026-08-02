"""Simple Bedrock access check using local AWS credentials (~/.aws or env).

Usage (from repo root, with API venv / .env loaded):

  cd fde-forge-ai
  set -a && source .env && set +a
  source apps/api/.venv/bin/activate
  PYTHONPATH=apps/api:. python -m scripts.check_bedrock

Exit 0 = Bedrock Converse works. Exit 1 = credentials / IAM / model issue.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))


def main() -> int:
    from botocore.exceptions import BotoCoreError, ClientError

    from app.ai.providers.bedrock_provider import (
        has_aws_credentials,
        resolve_bedrock_model_id,
    )
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    region = (settings.aws_region or "us-east-1").strip()
    model = resolve_bedrock_model_id(
        settings.bedrock_model_id or "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region,
    )

    print("=== FDE Forge AI · Bedrock access check ===")
    print(f"BEDROCK_ENABLED: {settings.bedrock_enabled}")
    print(f"Region:          {region}")
    print(f"Model:           {model}")
    print(f"Credentials:     {'yes' if has_aws_credentials() else 'NO'}")

    if not settings.bedrock_enabled:
        print("FAIL: set BEDROCK_ENABLED=true in .env")
        return 1
    if not has_aws_credentials() and not (
        settings.aws_access_key_id and settings.aws_secret_access_key
    ):
        print("FAIL: no AWS credentials. Run: aws configure  (region us-east-1)")
        return 1

    import boto3

    client_kwargs: dict = {"region_name": region}
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id.strip()
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.strip()

    client = boto3.client("bedrock-runtime", **client_kwargs)
    try:
        response = client.converse(
            modelId=model,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Reply with exactly: BEDROCK_OK"}],
                }
            ],
            inferenceConfig={"maxTokens": 32, "temperature": 0},
        )
    except (ClientError, BotoCoreError) as exc:
        print(f"FAIL: Bedrock Converse error: {exc}")
        print("Check IAM: bedrock:InvokeModel on this model/region.")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: unexpected error: {exc}")
        return 1

    parts = []
    for block in response.get("output", {}).get("message", {}).get("content") or []:
        if isinstance(block, dict) and block.get("text"):
            parts.append(str(block["text"]))
    text = "\n".join(parts).strip()
    usage = response.get("usage") or {}
    print("OK: Bedrock Converse succeeded")
    print(f"Reply: {text[:200]!r}")
    print(f"Usage: {json.dumps(usage)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
