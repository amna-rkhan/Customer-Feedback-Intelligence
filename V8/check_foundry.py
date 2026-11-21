import os
from urllib.parse import urlparse
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "").strip()
key = os.getenv("AZURE_INFERENCE_CREDENTIAL", "").strip()

print("Endpoint host :", urlparse(endpoint).netloc)
print("Endpoint path :", repr(urlparse(endpoint).path))
print("Deployment    :", repr(deployment))
print("Key length    :", len(key))

client = OpenAI(base_url=endpoint.rstrip("/") + "/openai/v1/", api_key=key, timeout=60)
try:
    r = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "user", "content": "Say hello in 3 words."}],
        max_completion_tokens=50,
    )
    print("SUCCESS:", r.choices[0].message.content)
except Exception as exc:
    print("FAILED:", type(exc).__name__)
    print("HTTP status:", getattr(exc, "status_code", "n/a"))
    print("Message:", getattr(exc, "message", str(exc))[:400])
