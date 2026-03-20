"""Quick LLM endpoint ping — calls the model every second."""

import os
import time
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

client = OpenAI(
    api_key=os.environ["LLM_API_KEY"],
    base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
)
model = os.environ.get("LLM_MODEL_NAME", "gpt-4o-mini")

print(f"Pinging {client.base_url} with model={model}\n")

TOTAL = 30

for i in range(1, TOTAL + 1):
    t0 = time.time()
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Di 'hola' y nada más."}],
            max_tokens=10,
        )
        text = r.choices[0].message.content.strip()
        ms = int((time.time() - t0) * 1000)
        print(f"[{i}] {ms}ms → {text}")
    except Exception as e:
        ms = int((time.time() - t0) * 1000)
        print(f"[{i}] {ms}ms → ERROR: {e}")
    if i < TOTAL:
        time.sleep(5)
