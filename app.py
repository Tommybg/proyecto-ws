import os
import io
import time
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv

from scraping.scraper import scrape_scholarship_pages
from utils.openai_client import generate_markdown_summary

load_dotenv()

st.set_page_config(page_title="Scholarship Scraper", page_icon="🎓", layout="wide")

# Sidebar
with st.sidebar:
    st.title("🎓 Scholarship Scraper")
    st.caption("Ingresa URLs (una por línea), luego ejecuta el scraping.")

    urls_text = st.text_area(
        label="URLs de becas (1 por línea)",
        height=180,
        placeholder="https://ejemplo1.com/beca\nhttps://ejemplo2.org/scholarship",
    )

    use_headless = st.toggle("Usar navegador headless", value=True)
    max_pages = st.number_input("Límite de páginas por sitio (0=auto)", min_value=0, max_value=50, value=0)

    default_api_key = os.getenv("OPENAI_API_KEY", "")

    model = st.selectbox(
        "Modelo",
        options=[
            "gpt-4.1-2025-04-14",
            "gpt-4.1-mini-2025-04-14",
        ],
        index=0,
    )

    run_button = st.button("🚀 Ejecutar scraping y resumen")

st.title("Resultados de becas")

if run_button:
    urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
    if not urls:
        st.warning("Por favor, ingresa al menos una URL.")
        st.stop()

    if not default_api_key:
        st.warning("Configura OPENAI_API_KEY en .env.")
        st.stop()

    effective_api_key = default_api_key

    with st.status("Ejecutando scraping...", expanded=True) as status:
        st.write(f"Se recibieron {len(urls)} URL(s)")
        try:
            start = time.time()
            scholarships = scrape_scholarship_pages(
                urls=urls,
                headless=use_headless,
                max_pages=max_pages or None,
            )
            st.write(f"Scraping completado. Se extrajeron {len(scholarships)} registros.")
            status.update(label="Generando resumen con OpenAI...", state="running")

            markdown = generate_markdown_summary(
                scholarships=scholarships,
                openai_api_key=effective_api_key,
                model=model,
            )
            elapsed = time.time() - start
            status.update(label=f"Listo en {elapsed:0.1f}s", state="complete")
        except Exception as e:
            status.update(label="Falló el proceso", state="error")
            st.exception(e)
            st.stop()

    st.subheader("Vista previa del Markdown")
    st.markdown(markdown)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"becas_{timestamp}.md"
    md_bytes = markdown.encode("utf-8")

    st.download_button(
        label="💾 Descargar Markdown",
        data=md_bytes,
        file_name=file_name,
        mime="text/markdown",
        use_container_width=True,
    )

else:
    st.info("Ingresa URLs en el sidebar y presiona 'Ejecutar scraping y resumen'.")
