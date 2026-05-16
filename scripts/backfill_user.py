"""
Preenche o campo `user` de todas as transações que ainda não têm usuário.
Rode APÓS adicionar a coluna no Supabase:
    ALTER TABLE transactions ADD COLUMN user text;
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / "bot" / ".env")
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

import httpx

BASE = os.environ.get("BACKEND_URL", "http://localhost:8000")
KEY = os.environ.get("API_SECRET_KEY", "")
HEADERS = {"X-API-Key": KEY, "Content-Type": "application/json"}

def main():
    with httpx.Client(base_url=BASE, headers=HEADERS, timeout=30) as c:
        offset = 0
        total_updated = 0
        while True:
            res = c.get("/api/transactions/", params={"limit": 100, "offset": offset})
            res.raise_for_status()
            data = res.json()
            items = data["items"]
            if not items:
                break
            for tx in items:
                if not tx.get("user"):
                    patch = c.patch(f"/api/transactions/{tx['id']}", json={"user": "Arthur"})
                    patch.raise_for_status()
                    total_updated += 1
                    print(f"  ✓ {tx['date']} {tx['description']} ({tx['amount']})")
            offset += len(items)
            if offset >= data["total"]:
                break

    print(f"\nPronto! {total_updated} transações atualizadas.")

if __name__ == "__main__":
    main()
