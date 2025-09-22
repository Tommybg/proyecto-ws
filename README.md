# 🎓 Buscador de Becas - Sitios Populares

Aplicación simplificada para buscar becas en sitios populares usando scrapers optimizados. La herramienta extrae información de becas y genera resúmenes organizados en Markdown usando IA (OpenAI). Interfaz construida con Streamlit completamente en español.

## Características
- 🎯 **Scrapers Optimizados** para sitios populares de becas
- 🤖 **Resúmenes con IA** usando modelos de OpenAI
- 📊 **Análisis Detallado** del rendimiento del scraping
- 💾 **Reportes Descargables** en formato Markdown
- 🇪🇸 **Interfaz en Español** completamente traducida

## Sitios Populares Incluidos
- Scholarship America
- Fastweb
- College Board
- Scholarships.com
- Cappex
- Unigo
- Niche
- Peterson's
- GoCollege
- ScholarshipPoints

## Requisitos
- Python 3.10+
- Google Chrome instalado

## Instalación
```bash
python -m venv proy_env
source proy_env/bin/activate  # Windows: proy_env\Scripts\activate
pip install -r requirements.txt
```

## Configuración
1. Crea un archivo `.env` en la raíz con tu API Key de OpenAI:
   ```
   OPENAI_API_KEY=tu_api_key
   ```

## Ejecutar la aplicación
```bash
streamlit run app.py
```

## Uso
1. **Selecciona sitios populares** en la barra lateral
2. **Configura las opciones** (navegador invisible, límite de páginas)
3. **Haz clic en "Iniciar Búsqueda"**
4. **Descarga el reporte** generado en formato Markdown

## Ventajas del Enfoque de Sitios Populares
- **Mayor precisión**: Scrapers específicamente diseñados para cada sitio
- **Mejor rendimiento**: Optimizados para la estructura de cada sitio web
- **Menos errores**: Menor probabilidad de fallos comparado con scraping genérico
- **Actualizaciones focalizadas**: Fácil mantenimiento de scrapers específicos

## Estructura del proyecto
```
/Users/tommygoat/Desktop/web-scraping-project/
├─ app.py                     # Aplicación principal Streamlit
├─ requirements.txt           # Dependencias del proyecto
├─ README.md                  # Documentación
├─ .env                       # Variables de entorno (API Keys)
├─ scraping/
│  ├─ __init__.py
│  ├─ hybrid_scraper.py         # Lógica para sitios populares
│  ├─ scraper.py                # Funciones básicas de scraping
│  └─ site_scrapers.py          # Scrapers específicos por sitio
└─ utils/
   ├─ __init__.py
   └─ openai_client.py          # Cliente para generar resúmenes con IA
```

## Problemas comunes
- **ChromeDriver**: Si no coincide con tu versión de Chrome, `webdriver-manager` lo gestiona automáticamente
- **API Key**: Asegúrate de configurar correctamente `OPENAI_API_KEY` en el archivo `.env`
- **Prompts de IA**: Puedes ajustar los prompts en `utils/openai_client.py` según tus necesidades

## Licencia
MIT
