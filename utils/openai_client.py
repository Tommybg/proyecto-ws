from __future__ import annotations

import json
from typing import List, Dict, Any

from openai import OpenAI

SYSTEM_PROMPT = (
    "Eres un experto asesor de becas que analiza oportunidades educativas. "
    "Recibe una lista de becas y crea un reporte completo en Markdown con:"
    "\n\n**POR CADA BECA:**"
    "\n- Título claro y llamativo"
    "\n- Monto y ubicación destacados"
    "\n- Análisis de quién puede aplicar"
    "\n- Consejos específicos de aplicación"
    "\n- Nivel de competitividad estimado"
    "\n- Fecha límite (si está disponible)"
    "\n- Enlace directo"
    "\n\n**ORGANIZACIÓN:**"
    "\n- Agrupa por país/región cuando sea posible"
    "\n- Ordena por monto (mayor a menor)"
    "\n- Usa emojis para hacer más visual"
    "\n- Incluye una sección de 'Recomendaciones Generales' al final"
    "\n\nResponde SOLO en Markdown bien formateado."
)


def generate_markdown_summary(
    scholarships: List[Dict[str, Any]],
    openai_api_key: str,
    model: str = "gpt-4.1-2025-04-14",
) -> str:
    client = OpenAI(api_key=openai_api_key)

    user_content = (
        "Crea un resumen en Markdown de estas becas. Si hay campos vacíos, "
        "mantén la estructura.\n\n"
        + json.dumps(scholarships, ensure_ascii=False, indent=2)
    )

    # Ajuste mínimo: uso de client.chat.completions.create y acceso a .message.content
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    markdown = response.choices[0].message.content or ""
    return markdown