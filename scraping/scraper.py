from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

#import de scraper especifico para DAAD
from scraping_esp.wscraper_daad import scrape_daad_scholarships

@dataclass
class Beca:
    """Clase que representa una beca"""
    title: str       # Título de la beca
    location: str    # Ubicación/país
    coverage: str    # Qué cubre la beca
    amount: str      # Monto
    type: str        # Tipo de beca
    url: str         # URL de detalles
    source_url: str  # URL origen


# Expresiones regulares y pistas para extracción de datos
REGEX_DINERO = re.compile(r"(?i)(\$|USD|EUR|MXN|\€|\£)\s?([\d,.]+)")
PISTAS_UBICACION = [
    "location", "ubicación", "país", "country", "ciudad", "lugar"
]
PISTAS_TIPO = [
    "tipo", "type", "undergraduate", "postgraduate", "master", "phd", "licenciatura", "maestría", "doctorado"
]
PISTAS_COBERTURA = [
    "cubre", "coverage", "benefits", "incluye", "apoyo", "stipend"
]


def _construir_driver(headless: bool = True) -> webdriver.Chrome:
    """Construye y configura el driver de Chrome"""
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def _extraer_texto(elemento) -> str:
    """Extrae y limpia texto de un elemento HTML"""
    texto = elemento.get_text(" ", strip=True)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _adivinar_monto(texto: str) -> str:
    """Busca patrones de dinero en el texto"""
    m = REGEX_DINERO.search(texto)
    return m.group(0) if m else ""


def _buscar_por_pistas(soup: BeautifulSoup, pistas: List[str]) -> str:
    """Busca información usando palabras clave"""
    texto_inferior = soup.get_text(" ", strip=True).lower()
    for pista in pistas:
        if pista in texto_inferior:
            # Devuelve la oración o fragmento alrededor de la pista
            idx = texto_inferior.find(pista)
            inicio = max(0, idx - 80)
            fin = min(len(texto_inferior), idx + 160)
            fragmento = soup.get_text(" ", strip=True)[inicio:fin]
            return re.sub(r"\s+", " ", fragmento)
    return ""


def _mejor_titulo(soup: BeautifulSoup) -> str:
    """Encuentra el mejor título en la página""" 
    # Recorre estos posibles selectores en orden de prioridad
    for selector in ["h1", "h2", "title", "meta[property='og:title']"]:
        el = soup.select_one(selector)
        if el:
            if el.name == "meta":
                contenido = el.get("content", "").strip()
                if contenido:
                    return contenido
            texto = _extraer_texto(el)
            if len(texto) > 4:
                return texto
    # Si no encuentra en h1, h2, title, meta[property='og:title'] usa strong/b
    for selector in ["strong", "b"]:
        el = soup.select_one(selector)
        if el:
            texto = _extraer_texto(el)
            if len(texto) > 4:
                return texto
    return "Beca"


# Alias en inglés para compatibilidad
# _build_driver = _construir_driver


def scrape_scholarship_pages(urls: List[str], headless: bool = True, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    """English entry point: scrape a list of scholarship pages and return dicts.

    Note: max_pages is currently unused but reserved for future pagination support.
    """
    driver = _construir_driver(headless=headless)
    wait = WebDriverWait(driver, 15)
    results: List[Dict[str, Any]] = []

    try:
        for url in urls:
            try:
                driver.get(url)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                time.sleep(1.2)
                html = driver.page_source
                soup = BeautifulSoup(html, "lxml")

                title = _mejor_titulo(soup)
                coverage = _buscar_por_pistas(soup, PISTAS_COBERTURA)
                location = _buscar_por_pistas(soup, PISTAS_UBICACION)
                scholarship_type = _buscar_por_pistas(soup, PISTAS_TIPO)
                amount = _adivinar_monto(soup.get_text(" ", strip=True))

                # canónica o og:url
                link_el = soup.select_one("link[rel='canonical'], meta[property='og:url']")
                detail_url = link_el.get("href") if link_el and hasattr(link_el, 'attrs') and 'href' in link_el.attrs else url
                if link_el and link_el.name == "meta":
                    detail_url = link_el.get("content", url)

                beca = Beca(
                    title=title,
                    location=location,
                    coverage=coverage,
                    amount=amount,
                    type=scholarship_type,
                    url=detail_url,
                    source_url=url,
                )
                results.append(asdict(beca))
            except Exception:
                continue
    finally:
        driver.quit()

    # --- Llamada e Integración del Scraper Especializado (DAAD) ---
    
    try:
        print("\n--- Integrando resultados del Scraper DAAD ---")
        # Llamar a la función encapsulada en wscraper_daad.py
        resultados_daad = scrape_daad_scholarships(headless=headless)
        
        # Fusión: Añadir los elementos de la segunda lista a la primera
        results.extend(resultados_daad)
        
    except Exception as e:
        # Captura errores que impidan la ejecución del scraper de DAAD
        print(f"❌ Error grave al integrar el scraper de DAAD: {e}. Los resultados genéricos se mantienen.")
        
    print(f"✅ Proceso completado. Total de becas recolectadas: {len(results)}")

    return results


# def raspar_paginas_becas(urls: List[str], headless: bool = True, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
#     return scrape_scholarship_pages(urls=urls, headless=headless, max_pages=max_pages)




# ==============================================================================
# 2. DATOS DE PRUEBA
# ==============================================================================
# URLs de ejemplo. Solo se necesitan para el scraper genérico.
# La lógica de DAAD iniciará su propio rastreo desde su URL fija.
URLS_DE_PRUEBA_GENERICAS = [
    "https://www.aauw.org/resources/programs/fellowships-grants/",  # URL de prueba 1
    "https://research.adobe.com/scholarship/",  # URL de prueba 2
]
# Nota: La URL de DAAD se llama internamente, por lo que no la incluimos aquí.

# ==============================================================================
# 3. EJECUCIÓN DE LA PRUEBA
# ==============================================================================

def run_test():
    """Ejecuta el scraper principal y verifica los resultados."""
    print("==================================================")
    print(" INICIANDO PRUEBA DEL SCRAPER INTEGRADO")
    print("==================================================")
    
    # Ejecuta el scraper, activando tanto la lógica genérica como la de DAAD
    try:
        # Usamos headless=False (opcional) para ver el navegador si hay fallos,
        # pero True es mejor para producción.
        resultados_finales: List[Dict[str, Any]] = scrape_scholarship_pages(
            urls=URLS_DE_PRUEBA_GENERICAS, 
            headless=True # Cambia a False si quieres ver el navegador (solo para debug)
        )
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO durante la ejecución de scrape_scholarship_pages: {e}")
        return

    # --- Verificación de Resultados ---
    print("\n==================================================")
    print(f"✅ VERIFICACIÓN DE RESULTADOS FINALES")
    print(f"Total de Becas Recolectadas: {len(resultados_finales)}")
    print("==================================================")

    if not resultados_finales:
        print("⚠️ Advertencia: No se pudo recolectar ninguna beca. Verifica tu conexión, el driver de Chrome y los selectores.")
        return

    # 1. Verificar el formato de las becas (la primera entrada)
    beca_ejemplo = resultados_finales[0]
    campos_esperados = ['title', 'location', 'coverage', 'amount', 'type', 'url', 'source_url']
    
    print("\n--- Verificando Formato (1ra Beca) ---")
    formato_ok = all(campo in beca_ejemplo for campo in campos_esperados)
    print(f"Formato de datos correcto (contiene {campos_esperados}): {'✅ SÍ' if formato_ok else '❌ NO'}")

    if not formato_ok:
        print(f"Campos encontrados: {list(beca_ejemplo.keys())}")

    # 2. Imprimir ejemplos para inspección
    print("\n--- Ejemplos de Salida ---")
    for i, res in enumerate(resultados_finales[:5]):
        print(f"[{i+1}] Título: {res.get('title', 'N/A')}")
        print(f"    URL: {res.get('url', 'N/A')}")
        print(f"    Monto: {res.get('amount', 'N/A')}")
        print(f"    Fuente: {res.get('source_url', 'N/A')}")
        print("-" * 30)

    # 3. Verificación Heurística de Integración (Opcional)
    # Busca un resultado que probablemente venga del scraper de DAAD
    daad_source = [r for r in resultados_finales if 'daad.de' in r.get('url', '').lower()]
    print(f"\n--- Verificando Integración DAAD ---")
    print(f"Resultados de DAAD encontrados: {'✅ SÍ' if daad_source else '❌ NO'}")
    if daad_source:
        print(f"Ejemplo de beca DAAD: {daad_source[0]['title']}")
        print(f"URL DAAD: {daad_source[0]['url']}")


if __name__ == '__main__':
    run_test()
