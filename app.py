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
    st.caption("Selecciona la fuente y ejecuta el scraping.")

    # Seleccionamos de donde queremos sacar las becas
    source = st.selectbox(
        "Fuente de becas",
        options=["Ambos", "DAAD (Alemania)", "Scholarship America (USA)"],
        index=0,
        help="DAAD: Becas alemanas | Scholarship America: Becas estadounidenses"
    )

    if source == "Genérico":
        urls_text = st.text_area(
            label="URLs de becas (1 por línea)",
            height=180,
            placeholder="https://ejemplo1.com/beca\nhttps://ejemplo2.org/scholarship",
        )
    else:
        st.info(f"📄 Scraping automático desde: {source}")
        urls_text = ""  # Empty for specialized scrapers

    use_headless = st.toggle("Usar navegador headless", value=True)
    
    if source == "DAAD (Alemania)":
        max_pages = st.number_input("Límite de páginas DAAD (0=auto)", min_value=0, max_value=50, value=0, disabled=True)
        st.caption("DAAD usa límite interno fijo")
    elif source == "Scholarship America (USA)":
        max_pages = st.number_input("Límite de páginas Scholarship America (0=auto)", min_value=0, max_value=50, value=0)
    else:  # Ambos
        max_pages = st.number_input("Límite de páginas Scholarship America (0=auto)", min_value=0, max_value=50, value=0)
        st.caption("Aplica solo a Scholarship America")

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
    if not default_api_key:
        st.warning("Configura OPENAI_API_KEY en .env.")
        st.stop()

    # Validate source selection
    if source == "Genérico":
        urls = [u.strip() for u in urls_text.splitlines() if u.strip()]
        if not urls:
            st.warning("Por favor, ingresa al menos una URL.")
            st.stop()
    else:
        urls = []  # Empty for specialized scrapers

    effective_api_key = default_api_key

    with st.status("Ejecutando scraping...", expanded=True) as status:
        status_message = f"Ejecutando scraping desde: {source}"
        if source == "DAAD (Alemania)":
            status_message += " (Becas alemanas)"
        elif source == "Scholarship America (USA)":
            status_message += " (Becas estadounidenses)"
        elif source == "Ambos":
            status_message += " (Becas alemanas y estadounidenses)"
            
        st.write(status_message)
        
        try:
            start = time.time()
            scholarships = scrape_scholarship_pages(
                urls=urls,
                headless=use_headless,
                max_pages=max_pages or None,
                source=source,
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
    st.info("Selecciona una fuente en el sidebar y presiona 'Ejecutar scraping y resumen'.")
