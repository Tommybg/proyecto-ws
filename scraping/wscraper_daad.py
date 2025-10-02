import time
import re
from typing import List, Dict, Union, Set, Tuple, Any
from urllib.parse import urljoin, urlparse
from collections import defaultdict
from dataclasses import dataclass, asdict

import requests
from requests.exceptions import RequestException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup, Tag 

# ==============================================================================
# 1. DEFINICIONES DE CLASE Y CONSTANTES
# ==============================================================================

@dataclass
class Beca:
    """Clase que representa una beca (estructura de datos de salida)."""
    title: str       # Título de la beca
    location: str    # Ubicación/país
    coverage: str    # Qué cubre la beca
    amount: str      # Monto
    type: str        # Tipo de beca
    url: str         # URL de detalles
    source_url: str  # URL origen

# Palabras clave para inferir el mapeo de H3 a variable (para el mapeo dinámico)
MAPPING_KEYWORDS = {
    'coverage_amount': ['value', 'amount', 'stipend', 'financ', 'benefit', 'sum'],
    'type_description': ['programme', 'target', 'group', 'field', 'study', 'who can apply'],
    'requirements': ['require', 'academic', 'application', 'docum'],
    'location_details': ['where', 'country', 'locat', 'city']
}

DAAD_STARTING_URL = "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"


# ==============================================================================
# 2. CLASE DE RASTREO ESPECIALIZADA (LÓGICA OPTIMIZADA)
# ==============================================================================

class DAADScraper:
    """Clase especializada para rastreo y extracción de DAAD con mapeo dinámico."""

    def __init__(self, start_url: str, max_links: int, wait_time: int, sleep_time: float, headless: bool):
        self.start_url = start_url
        self.max_links = max_links
        self.wait_time = wait_time
        self.sleep_time = sleep_time
        self.headless = headless
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.driver = None
        self.h3_frecuencias = defaultdict(int)
        self.h3_mappeo_dinamico = {}

    def _init_driver(self):
        """Inicializa el driver de Selenium."""
        options = webdriver.ChromeOptions()
        if self.headless: options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
        except WebDriverException as e:
            # Re-lanza la excepción para que el llamador pueda manejar la falta del driver
            raise WebDriverException(f"Error al iniciar el driver de Chrome: {e}. Asegúrate del driver.")

    def _quit_driver(self):
        """Cierra el driver de Selenium si está inicializado."""
        if self.driver: self.driver.quit(); self.driver = None

    # --- Etapa 1: Rastreo de Enlaces (Selenium) ---
    def scrape_links(self) -> List[str]:
        """Rastrea todas las páginas y extrae enlaces."""
        all_links: Set[str] = set()
        current_url: str = self.start_url
        try:
            self._init_driver()
            while current_url and len(all_links) < self.max_links:
                self.driver.get(current_url)
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.entry'))
                    )
                except TimeoutException: break
                
                entries = self.driver.find_elements(By.CSS_SELECTOR, '.entry a')
                for entry in entries:
                    link = entry.get_attribute('href')
                    absolute_link = urljoin(current_url, link) 
                    parsed_link = urlparse(absolute_link)._replace(fragment="").geturl()
                    if parsed_link and parsed_link not in all_links:
                        all_links.add(parsed_link)
                        if len(all_links) >= self.max_links: break 
                if len(all_links) >= self.max_links: break
                
                try:
                    next_button = self.driver.find_element(
                        By.XPATH, 
                        "//a[contains(text(), 'Next') or contains(text(), '»') or contains(@class, 'next')]"
                    )
                    next_page_link = next_button.get_attribute('href')
                    if next_page_link:
                        next_page_link = urljoin(current_url, next_page_link)
                        next_page_link_normalized = urlparse(next_page_link)._replace(fragment="").geturl()
                        if next_page_link_normalized != urlparse(current_url)._replace(fragment="").geturl():
                            current_url = next_page_link_normalized
                        else: break
                    else: break 
                except NoSuchElementException: break
                except Exception: break
        finally:
            self._quit_driver()
        return list(all_links)

    # --- Etapa 2: Descarga de Contenido (Requests) ---
    def fetch_body_content(self, links: List[str]) -> List[Dict[str, Union[str, int]]]:
        """Realiza peticiones GET y extrae el contenido del <body>."""
        lista_de_bodys: List[Dict[str, Union[str, int]]] = []
        for link in links:
            resultado: Dict[str, Union[str, int]] = {'url': link, 'source_url': link} 
            try:
                response = requests.get(link, headers=self.headers, timeout=15)
                if response.status_code == 200:
                    resultado['status_code'] = 200
                    text = response.text
                    body_match = re.search(r'<body.*?>', text, re.IGNORECASE | re.DOTALL)
                    body_end_match = re.search(r'</body>', text, re.IGNORECASE | re.DOTALL)
                    if body_match and body_end_match:
                        resultado['body_html'] = text[body_match.start():body_end_match.end()]
                    else:
                        resultado['body_html'] = text
                else: resultado['status_code'] = response.status_code
            except RequestException: pass
            lista_de_bodys.append(resultado)
            time.sleep(self.sleep_time)
        return lista_de_bodys

    # --- Etapa 3: Análisis Estructural y Generación de Mapeo Dinámico ---
    def _analizar_estructura_y_h3_frecuencias(self, lista_de_bodys: List[Dict]) -> int:
        total_urls_analizadas = 0
        for item in lista_de_bodys:
            if item.get('status_code') != 200 or 'body_html' not in item: continue
            try:
                soup = BeautifulSoup(item['body_html'], 'html.parser')
                contenedor_raiz = soup.find('div', class_='stipdb-detail')
                if not contenedor_raiz: continue
                total_urls_analizadas += 1
                h3_secciones = [
                    h.text.strip() for h in contenedor_raiz.find_all('h3') 
                    if 'print-only' not in h.get('class', [])
                ]
                for h3_titulo in h3_secciones:
                    self.h3_frecuencias[h3_titulo.lower().strip()] += 1
            except Exception: pass
        return total_urls_analizadas
        
    def _generar_mapeo_dinamico(self, total_urls_analizadas: int):
        if total_urls_analizadas == 0: return
        umbral_minimo = total_urls_analizadas * 0.2
        self.h3_mappeo_dinamico = {}
        h3_comunes = sorted(self.h3_frecuencias.items(), key=lambda item: item[1], reverse=True)
        for h3_normalized, conteo in h3_comunes:
            if conteo < umbral_minimo: continue 
            for variable, keywords in MAPPING_KEYWORDS.items():
                if any(keyword in h3_normalized for keyword in keywords):
                    if h3_normalized not in self.h3_mappeo_dinamico:
                         self.h3_mappeo_dinamico[h3_normalized] = variable
                         break 

    # --- Etapa 4: Extracción Final de Variables ---
    def extraer_contenido_h3(self, h3_tag: Tag) -> str:
        contenido = []
        for sibling in h3_tag.find_next_siblings():
            if sibling.name == 'h3': break
            if sibling.name in ['p', 'ul', 'ol', 'div']:
                if sibling.get('class') and any(cls in sibling['class'] for cls in ['footer', 'sidebar', 'nav']): continue
                contenido.append(sibling.get_text(separator=' ', strip=True))
            if len(contenido) > 5: break
        return " ".join(contenido).strip()

    def extraer_variables_de_body(self, item: Dict) -> Dict:
        url = item['url']
        extracted_data = {
            'title': 'N/A', 'location': 'Germany', 'coverage': 'N/A', 'amount': 'N/A', 
            'type': 'N/A', 'url': url, 'source_url': item.get('source_url', url), 
            'raw_h3_data': {} 
        }

        if item.get('status_code') != 200 or 'body_html' not in item:
            extracted_data['error'] = item.get('error', 'Contenido faltante/Error de red.')
            return extracted_data

        try:
            soup = BeautifulSoup(item['body_html'], 'html.parser')
            h2_title_tag = soup.find('h2', class_='title')
            if h2_title_tag: extracted_data['title'] = h2_title_tag.text.strip()
            
            contenedor_raiz = soup.find('div', class_='stipdb-detail')
            if not contenedor_raiz:
                extracted_data['error'] = 'Contenedor stipdb-detail no encontrado.'
                return extracted_data
            
            h3_tags = [h for h in contenedor_raiz.find_all('h3') if 'print-only' not in h.get('class', [])]
            for h3 in h3_tags:
                h3_normalized = h3.text.strip().lower()
                if h3_normalized in self.h3_mappeo_dinamico:
                    campo_destino = self.h3_mappeo_dinamico[h3_normalized]
                    contenido = self.extraer_contenido_h3(h3)
                    if contenido:
                        current_data = extracted_data['raw_h3_data'].setdefault(campo_destino, "")
                        extracted_data['raw_h3_data'][campo_destino] = (current_data + " " + contenido).strip()

            raw_data = extracted_data['raw_h3_data']
            if 'coverage_amount' in raw_data:
                full_text = raw_data['coverage_amount']
                if re.search(r'[\d,\.]+\s*(?:€|\$|Euro|US\$|GBP)', full_text, re.IGNORECASE):
                    extracted_data['amount'] = full_text
                    extracted_data['coverage'] = full_text
                else: extracted_data['coverage'] = full_text
            if 'type_description' in raw_data:
                extracted_data['type'] = raw_data['type_description']
                
            del extracted_data['raw_h3_data']
            return extracted_data
        except Exception as e:
            extracted_data['error'] = f"Error en la extracción: {e}"
            return extracted_data

# ==============================================================================
# 3. FUNCIÓN DE UTILIDAD PARA INTEGRACIÓN (PUNTO DE ENTRADA EXTERNO)
# ==============================================================================

def scrape_daad_scholarships(headless: bool = True) -> List[Dict[str, Any]]:
    """
    Ejecuta el proceso completo de DAADScraper (rastreo, análisis, extracción) 
    y retorna los resultados como una lista de diccionarios Beca.
    """
    
    max_links = 120 
    sleep_time = 0.5 

    scraper = DAADScraper(
        start_url=DAAD_STARTING_URL, 
        max_links=max_links, 
        wait_time=10, 
        sleep_time=sleep_time, 
        headless=headless
    )
    
    print("\n[DAAD] Iniciando rastreo y extracción especializada.")
    
    try:
        links = scraper.scrape_links()
        if not links: return []

        lista_de_bodys = scraper.fetch_body_content(links)
        
        total_analizadas = scraper._analizar_estructura_y_h3_frecuencias(lista_de_bodys)
        scraper._generar_mapeo_dinamico(total_analizadas)

        resultados_extraccion: List[Dict[str, Any]] = []
        for item in lista_de_bodys:
            data = scraper.extraer_variables_de_body(item)
            
            if 'error' not in data:
                # Mapear los datos extraídos a la clase Beca y luego a dict
                beca = Beca(
                    title=data['title'],
                    location=data['location'],
                    coverage=data['coverage'],
                    amount=data['amount'],
                    type=data['type'],
                    url=data['url'],
                    source_url=data['source_url'],
                )
                resultados_extraccion.append(asdict(beca))
        
        print(f"[DAAD] Proceso especializado finalizado. Becas extraídas: {len(resultados_extraccion)}")
        return resultados_extraccion
        
    except WebDriverException as e:
        print(f"[DAAD] ❌ Error de Selenium (Driver no encontrado/fallo): {e}")
        return []
    except Exception as e:
        print(f"[DAAD] ❌ Error grave en el scraper de DAAD: {e}")
        return []

# ==============================================================================
# EJECUCIÓN DE PRUEBA (OPCIONAL)
# ==============================================================================
"""if __name__ == '__main__':
    print("--- PRUEBA DEL MÓDULO WSCRAPER_DAAD.PY ---")
    resultados_daad = scrape_daad_scholarships(headless=True)
    if resultados_daad:
        print(f"Total: {len(resultados_daad)}. Ejemplo: {resultados_daad}")"""