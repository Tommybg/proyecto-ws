import os
import io
import time
from datetime import datetime
from typing import List, Dict, Any

import streamlit as st
from dotenv import load_dotenv

from scraping.hybrid_scraper import (
    get_popular_sites, 
    scrape_popular_sites
)
from utils.openai_client import generate_markdown_summary

load_dotenv()

st.set_page_config(page_title="🎓 Buscador de Becas", page_icon="🎓", layout="wide")

# Barra lateral
with st.sidebar:
    st.title("🎓 Buscador de Becas")
    st.caption("Busca becas en los sitios más populares")
    
    st.divider()
    
    # Selección de sitios populares
    st.subheader("Sitios Populares")
    popular_sites = get_popular_sites()
    selected_sites = st.multiselect(
        "Selecciona los sitios de becas a explorar:",
        options=list(popular_sites.keys()),
        default=list(popular_sites.keys())[:5],  # Seleccionar primeros 5 por defecto
        help="Estos sitios tienen scrapers optimizados para mayor precisión"
    )
    
    if selected_sites:
        with st.expander("📍 Vista previa de URLs seleccionadas", expanded=False):
            for site in selected_sites:
                st.write(f"**{site}:** {popular_sites[site]}")
    
    # Configuraciones
    st.subheader("⚙️ Configuración")
    use_headless = st.toggle("Navegador invisible", value=True, help="Scraping más rápido sin interfaz del navegador")
    max_pages = st.number_input("Límite de páginas (0=automático)", min_value=0, max_value=50, value=0)
    
    # Configuración OpenAI
    default_api_key = os.getenv("OPENAI_API_KEY", "")
    model = "gpt-4.1-2025-04-14"
    
    st.divider()
    
    # Botón de acción
    run_button = st.button(
        "🚀 Iniciar Búsqueda", 
        type="primary", 
        use_container_width=True,
        help="Comenzar la búsqueda de becas y el resumen con IA"
    )
# Área de contenido principal
st.title("🎓 Resultados de Búsqueda de Becas")

if run_button:
    # Validar selección de sitios
    if not selected_sites:
        st.warning("⚠️ Por favor selecciona al menos un sitio popular.")
        st.stop()
    
    # Obtener URLs a procesar
    popular_sites = get_popular_sites()
    urls_to_process = [popular_sites[site] for site in selected_sites]
    mode_description = f"Seleccionados {len(selected_sites)} sitios populares"
    
    # Validar clave API
    if not default_api_key:
        st.error("🔑 Por favor configura OPENAI_API_KEY en tu archivo .env")
        st.stop()
        st.stop()
    
    # Seguimiento del progreso
    progress_messages = []
    error_info = None
    
    def progress_callback(message):
        progress_messages.append(message)
        return message
    
    # Ejecutar scraping
    with st.status(f"🚀 Procesando {len(urls_to_process)} URLs...", expanded=True) as status:
        st.write(f"📊 **{mode_description}**")
        st.write(f"🔄 URLs a procesar: {len(urls_to_process)}")
        
        try:
            start = time.time()
            
            # Usar scraping de sitios populares
            scholarships = scrape_popular_sites(
                selected_sites=selected_sites,
                headless=use_headless,
                progress_callback=progress_callback
            )
            
            # Mostrar estadísticas de scraping
            total_scholarships = len(scholarships)
            tailored_count = sum(1 for s in scholarships if s.get('scraping_method') == 'tailored')
            general_count = sum(1 for s in scholarships if s.get('scraping_method') == 'general')
            
            st.write(f"✅ **¡Scraping completado exitosamente!**")
            st.write(f"🎯 Total de becas encontradas: **{total_scholarships}**")
            st.write(f"📊 Scraping optimizado: **{tailored_count}** | Scraping general: **{general_count}**")
            
            if total_scholarships == 0:
                st.warning("⚠️ No se encontraron becas. Esto puede deberse a:")
                st.write("- Sitios que requieren login o tienen protección anti-bot")
                st.write("- URLs que apuntan a páginas de búsqueda en lugar de becas específicas")
                st.write("- Problemas temporales del sitio")
                st.stop()
            
            status.update(label="🤖 Generando resumen con IA...", state="running")
            
            # Generar resumen con IA
            markdown = generate_markdown_summary(
                scholarships=scholarships,
                openai_api_key=default_api_key
            )
            
            elapsed = time.time() - start
            status.update(label=f"✨ ¡Completado! ({elapsed:.1f}s total)", state="complete")
            
        except Exception as e:
            status.update(label="❌ Error en el scraping", state="error")
            st.error(f"**Ocurrió un error:** {str(e)}")
            st.stop()
    
    # Mostrar información de depuración si hubo un error
    if progress_messages:
        with st.expander("🔍 Información de Depuración"):
            st.write("**Mensajes de Progreso:**")
            for msg in progress_messages:
                st.write(f"- {msg}")

    # Mostrar resultados
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Vista Previa del Reporte de Becas")
    
    with col2:
        # Sección de descarga
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"becas_{timestamp}.md"
        md_bytes = markdown.encode("utf-8")
        
        st.download_button(
            label="💾 Descargar Reporte",
            data=md_bytes,
            file_name=file_name,
            mime="text/markdown",
            type="primary",
            use_container_width=True,
        )
    
    # Mostrar estadísticas detalladas
    with st.expander("📊 Estadísticas de Scraping", expanded=False):
        stat_col1, stat_col2, stat_col3 = st.columns(3)
        
        with stat_col1:
            st.metric("Total de Becas", total_scholarships)
            st.metric("URLs Procesadas", len(urls_to_process))
        
        with stat_col2:
            st.metric("Scraping Optimizado", f"{tailored_count}/{total_scholarships}")
            accuracy_rate = (tailored_count / total_scholarships * 100) if total_scholarships > 0 else 0
            st.metric("Tasa de Precisión", f"{accuracy_rate:.1f}%")
        
        with stat_col3:
            st.metric("Tiempo de Procesamiento", f"{elapsed:.1f}s")
            avg_time = elapsed / len(urls_to_process) if urls_to_process else 0
            st.metric("Tiempo Promedio/URL", f"{avg_time:.1f}s")
        
        # Mostrar desglose de scrapers
        if scholarships:
            st.write("**Uso de Scrapers:**")
            scraper_stats = {}
            for scholarship in scholarships:
                scraper_type = scholarship.get('scraper_type', 'Desconocido')
                scraper_stats[scraper_type] = scraper_stats.get(scraper_type, 0) + 1
            
            for scraper, count in scraper_stats.items():
                st.write(f"- {scraper}: {count} becas")
    
    # Mostrar markdown principal
    st.markdown(markdown)
    
    # Vista de datos raw (opcional)
    if st.checkbox("🔍 Mostrar Datos Raw (para depuración)"):
        st.json(scholarships)

else:
    # Pantalla de bienvenida
    st.markdown("""
    ### 👋 ¡Bienvenido al Buscador de Becas!
    
    Esta herramienta te ayuda a encontrar y organizar oportunidades de becas usando scraping potenciado por IA.
        
    **🚀 Inicio Rápido:**
    1. Selecciona los sitios populares en la barra lateral
    2. Configura tu clave API de OpenAI en el archivo .env
    3. Haz clic en "Iniciar Búsqueda"
    
    ---
    """)
