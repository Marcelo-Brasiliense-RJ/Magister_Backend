"""Snippet de embed <iframe> para o widget do tutor.

O widget e servido pelo frontend em /embed?token=<embed_token>. O backend
so entrega o snippet + o token publico (nao ha segredo aqui).
"""

import os


def build_embed_payload(embed_token: str) -> dict:
    base = os.getenv("WIDGET_BASE_URL", "http://localhost:5173")
    embed_url = f"{base}/embed?token={embed_token}"
    snippet = (
        f'<iframe src="{embed_url}" width="400" height="600" '
        f'style="border:0" title="Magister"></iframe>'
    )
    return {"embed_token": embed_token, "embed_url": embed_url, "snippet": snippet}
