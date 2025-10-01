from __future__ import annotations

import json
from typing import List, Dict, Any

from openai import OpenAI

SYSTEM_PROMPT = (
   """

Eres un analista experto en becas. Recibirás una lista de diccionarios, uno por página raspada, con las claves: title, 
location, coverage, amount, type, url, source_url. Tu tarea es generar un único reporte SOLO en Markdown, bien formateado, 
sin texto fuera del Markdown. Reglas para el contenido por beca: incluye título claro y atractivo; destaca en negritas el monto
y la ubicación; describe elegibilidad inferida a partir de type y coverage (si no hay suficiente información, escribe 
“No disponible” sin inventar); da consejos específicos y accionables (documentos típicos, estrategia, plazos); estima competitividad
 (baja/media/alta) con justificación breve basada en prestigio percibido, cobertura y alcance; muestra fecha límite solo si 
 viene explícita en los datos (si no está presente en la entrada, usa “No disponible”); incluye el enlace directo (url).
  Organización: agrupa por país/región derivado de location; si no es deducible, usa “Sin región definida”; dentro de cada grupo, 
  ordena por monto de mayor a menor; si amount no es parseable, colócala al final; crea una subsección 
  “Cerradas” si detectas fechas pasadas (solo si la entrada trae deadline; no la inventes) y anota si es recurrente anual si el título 
  o coverage lo sugieren. Estilo: usa H1 para el título global, H2 por región/país, H3 por beca; listas con viñetas; 
  enlaces clicables; evita párrafos largos; usa emojis para secciones y resaltado; conserva la moneda tal como aparece en amount 
  y, si es rango, ordénalo por su cifra máxima estimada pero muestra el rango original. Validaciones y limpieza: 
  deduplica por url (si hay varias entradas con la misma url, combina datos conservando el más completo); limpia espacios duplicados; 
  no inventes datos faltantes; si amount contiene múltiples valores, usa el mayor para ordenar; si coverage, type o location están vacíos, marca “No disponible”. 
  Entrada esperada: lista de dicts con claves title, location, coverage, amount, type, url, source_url; pueden venir campos adicionales como deadline o notes, y si aparecen, úsalos.
  Salida esperada: un único bloque Markdown con el reporte completo siguiendo todas las reglas anteriores.
   """
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