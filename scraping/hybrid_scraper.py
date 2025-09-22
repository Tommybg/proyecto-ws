"""
Scraper para sitios populares de becas.
Utiliza un scraper simple y unificado para todos los sitios.
"""

from typing import List, Dict, Any, Optional
import time

from .scraper import _construir_driver
from .site_scrapers import obtener_scraper_para_url, SITIOS_POPULARES_BECAS


def obtener_sitios_populares() -> Dict[str, str]:
    """Devuelve diccionario de sitios populares de becas"""
    return SITIOS_POPULARES_BECAS.copy()


def raspar_sitios_populares(
    sitios_seleccionados: List[str], 
    headless: bool = True,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Raspa sitios populares de becas seleccionados usando scraper simple
    """
    driver = _construir_driver(headless=headless)
    resultados: List[Dict[str, Any]] = []
    
    try:
        urls = [SITIOS_POPULARES_BECAS[sitio] for sitio in sitios_seleccionados if sitio in SITIOS_POPULARES_BECAS]
        
        for i, url in enumerate(urls):
            if progress_callback:
                progress_callback(f"Procesando sitio {i+1}/{len(urls)}: {sitios_seleccionados[i] if i < len(sitios_seleccionados) else 'Desconocido'}")
            
            try:
                # Obtener scraper simple para el sitio
                scraper_sitio = obtener_scraper_para_url(url, driver)
                
                if progress_callback:
                    progress_callback(f"Scrapeando {url}")
                
                # Usar scraping del sitio
                resultados_sitio = scraper_sitio.raspar(url)
                
                # Marcar resultados con metadatos
                for resultado in resultados_sitio:
                    resultado['scraping_method'] = 'tailored'
                    resultado['scraper_type'] = scraper_sitio.__class__.__name__
                
                resultados.extend(resultados_sitio)
                
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Error procesando {url}: {str(e)}")
                continue
            
            # Pequeña pausa entre solicitudes para ser respetuoso
            time.sleep(1)
    
    finally:
        driver.quit()
    
    return resultados


# Alias en inglés para compatibilidad
get_popular_sites = obtener_sitios_populares

def scrape_popular_sites(selected_sites: List[str], headless: bool = True, progress_callback=None) -> List[Dict[str, Any]]:
    """Wrapper de compatibilidad que traduce parámetros del inglés al español"""
    return raspar_sitios_populares(
        sitios_seleccionados=selected_sites,
        headless=headless, 
        progress_callback=progress_callback
    )
