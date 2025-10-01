# 🎓 Scholarship Scraper (Streamlit + Selenium + OpenAI)

Aplicación simple para extraer información básica de páginas de becas (pegas 1 o varias URLs), y generar un reporte organizado en Markdown con ayuda de un modelo LLM. La interfaz es con Streamlit y permite previsualizar y descargar el Markdown.

## Características
- 🧭 Ingresas 1 o más URLs (una por línea) en el sidebar
- 🧾 Scraping genérico con Selenium + BeautifulSoup (funciona en muchos sitios)
- 🤖 Generación de Markdown con OpenAI (modelo seleccionable)
- 👁️ Vista previa en la app y botón de descarga `.md`

## Requisitos
- Python 3.10+
- Navegador basado en Chromium (Chrome recomendado). También puedes usar Brave (ver notas).

## Instalación
```bash
python -m venv proy_env
source proy_env/bin/activate  # Windows: proy_env\Scripts\activate
pip install -r requirements.txt
```

## Configuración
1) Crea un archivo `.env` en la raíz con tu API Key de OpenAI:
```
OPENAI_API_KEY=tu_api_key
```
2) Opcional (si usas Brave en lugar de Chrome): exporta la ruta al binario para Selenium.
   - macOS:
```
export CHROME_PATH="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
```

## Ejecutar la aplicación
```bash
streamlit run app.py
```

## Uso (en la app)
1) En el sidebar:
   - Pega 1+ URLs de páginas de becas (una por línea)
   - Activa “Usar navegador headless” si no quieres abrir ventana
   - (Opcional) ajusta “Límite de páginas” (reservado para futuras mejoras)
   - Selecciona el modelo de OpenAI
2) Presiona “Ejecutar scraping y resumen”.
3) Revisa la vista previa del Markdown.
4) Descarga el archivo `.md` con el botón de descarga.

Notas:
- Funciona con una sola URL o varias (recomendado 5–10 para mejores agrupaciones del LLM).
- Si alguna URL requiere login o interacción avanzada, es posible que el heurístico genérico no capture todo.

## Estructura del proyecto
```
/Users/tommygoat/Desktop/web-scraping-project/
├─ app.py                     # Aplicación principal (Streamlit)
├─ requirements.txt           # Dependencias
├─ README.md                  # Este documento
├─ scraping/
│  ├─ __init__.py
│  └─ scraper.py              # Scraper genérico (punto de entrada usado por la app)
└─ utils/
   ├─ __init__.py
   └─ openai_client.py        # Cliente OpenAI para generar el Markdown
```

## Cómo funciona (breve)
- `app.py` recoge URLs → llama a `scrape_scholarship_pages(...)` → pasa los resultados a `generate_markdown_summary(...)` → muestra/descarga Markdown.
- `scraping/scraper.py` usa Selenium para abrir cada URL y BeautifulSoup para extraer heurísticamente: título, ubicación, cobertura, monto, tipo y link canónico.
- `utils/openai_client.py` formatea con un prompt y devuelve Markdown listo.

## Problemas comunes
- Chrome/Brave no encontrado: instala Chrome o exporta `CHROME_PATH` apuntando al binario de Brave.
- Driver: `webdriver-manager` gestiona ChromeDriver automáticamente; tener el navegador actualizado ayuda.
- API Key: asegúrate de definir `OPENAI_API_KEY` en `.env` antes de ejecutar la app.

## Licencia
MIT
