import time
import re
from typing import List, Dict, Union, Set, Tuple
from urllib.parse import urljoin, urlparse
from collections import defaultdict
import requests
from requests.exceptions import RequestException
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from bs4 import BeautifulSoup, Tag 

# --- Palabras clave para inferir el mapeo de H3 a variable ---
MAPPING_KEYWORDS = {
    'coverage_amount': ['value', 'amount', 'stipend', 'financ', 'benefit', 'sum', 'euro','eur', 'cover', 'fund', 'grant', 'scholarship', 'support', 'monthly'],
    'type_description': ['programme', 'target', 'group', 'field', 'study', 'who can apply'],
    'requirements': ['require', 'academic', 'application', 'docum'],
    'location_details': ['where', 'country', 'locat', 'city', 'place', 'university','state'],
}

class DAADScraper:
    """Clase para encapsular la lógica de rastreo, análisis estructural y extracción de DAAD."""

    def __init__(self, start_url: str, max_links: int = 120, wait_time: int = 10, sleep_time: float = 0.5):
        self.start_url = start_url
        self.max_links = max_links
        self.wait_time = wait_time
        self.sleep_time = sleep_time
        self.headers = {
            # User-Agent para simular un navegador
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.driver = None
        self.h3_frecuencias = defaultdict(int)
        self.h3_mappeo_dinamico = {}

    # --- Gestión del Driver ---

    def _init_driver(self):
        """Inicializa el driver de Selenium en modo headless."""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        try:
            # Puedes especificar la ruta al driver si no está en tu PATH, ej: executable_path='/ruta/a/chromedriver'
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
        except WebDriverException as e:
            print(f"❌ Error al iniciar el driver de Chrome. Asegúrate de tener 'chromedriver' en tu PATH: {e}")
            raise

    def _quit_driver(self):
        """Cierra el driver de Selenium si está inicializado."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    # --- Etapa 1: Rastreo de Enlaces (Selenium) ---

    def scrape_links(self) -> List[str]:
        """Rastrea todas las páginas y extrae enlaces hasta el límite o el final de la paginación."""
        try:
            self._init_driver()
            all_links: Set[str] = set()
            current_url: str = self.start_url

            while current_url and len(all_links) < self.max_links:
                #print(f"🔗 Navegando a: {current_url}")
                try:
                    self.driver.get(current_url)
                except TimeoutException:
                    print(f"⚠️ Advertencia: Timeout al cargar {current_url}.")
                except WebDriverException as e:
                    print(f"❌ Error al navegar a {current_url}: {e}. Deteniendo rastreo.")
                    break
                
                # Esperar a que el contenedor de entradas esté presente
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.entry'))
                    )
                except TimeoutException:
                    print(f"⚠️ No se encontraron elementos '.entry' en {current_url}. Deteniendo paginación.")
                    break
                
                # Extraer enlaces de la página actual
                entries = self.driver.find_elements(By.CSS_SELECTOR, '.entry a')
                for entry in entries:
                    link = entry.get_attribute('href')
                    # Convertir a URL absoluta y normalizar (quitar fragmentos)
                    absolute_link = urljoin(current_url, link) 
                    parsed_link = urlparse(absolute_link)._replace(fragment="").geturl()

                    if parsed_link and parsed_link not in all_links:
                        all_links.add(parsed_link)
                        if len(all_links) >= self.max_links:
                            break 
                
                if len(all_links) >= self.max_links:
                    break
                
                # Buscar el enlace de la siguiente página
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
                        else:
                            break # Enlace a la misma página
                    else:
                        break 
                except NoSuchElementException:
                    #print("✅ Paginación terminada: No se encontró el botón 'Next'.")
                    break
                except Exception:
                    break
        finally:
            self._quit_driver() # Asegura que el driver se cierra
            #print(f"✅ Rastreo completado. Enlaces encontrados: {len(all_links)}")

        return list(all_links)

    # --- Etapa 2: Descarga de Contenido (Requests) ---

    def fetch_body_content(self, links: List[str]) -> List[Dict[str, Union[str, int]]]:
        """Realiza peticiones GET, extrae el contenido del <body> y aplica pausas."""
        lista_de_bodys: List[Dict[str, Union[str, int]]] = []
        total_links = len(links)
        #print(f"\nIniciando descarga de contenido para {total_links} enlaces.")

        for i, link in enumerate(links):
            # Inicializamos resultado. source_url es igual a url en esta fase.
            resultado: Dict[str, Union[str, int]] = {'url': link, 'source_url': link} 
            
            try:
                response = requests.get(link, headers=self.headers, timeout=15)
                #print(f"⬇️ [{i+1}/{total_links}] Código {response.status_code} para {link}")

                if response.status_code == 200:
                    resultado['status_code'] = 200
                    text = response.text
                    
                    # Búsqueda robusta del body (case insensitive)
                    body_match = re.search(r'<body.*?>', text, re.IGNORECASE | re.DOTALL)
                    body_end_match = re.search(r'</body>', text, re.IGNORECASE | re.DOTALL)
                    
                    if body_match and body_end_match:
                        body_content = text[body_match.start():body_end_match.end()]
                        resultado['body_html'] = body_content
                    else:
                        resultado['body_html'] = text
                        
                else:
                    resultado['status_code'] = response.status_code
                    resultado['error'] = "Petición fallida: " + str(response.status_code)
                    
            except RequestException as e:
                resultado['error'] = str(e)
            
            lista_de_bodys.append(resultado)
            time.sleep(self.sleep_time)
            
        #print("\nDescarga completada.")
        return lista_de_bodys

    # --- Etapa 3: Análisis Estructural y Generación de Mapeo Dinámico ---
    
    def _analizar_estructura_y_h3_frecuencias(self, lista_de_bodys: List[Dict]):
        """Analiza los bodys para obtener la frecuencia de los H3."""
        #print("\nIniciando el análisis estructural para generar el mapeo de H3.")
        total_urls_analizadas = 0
        
        for item in lista_de_bodys:
            if item.get('status_code') != 200 or 'body_html' not in item:
                continue
                
            body_html = item['body_html']
            try:
                soup = BeautifulSoup(body_html, 'html.parser')
            except Exception:
                continue

            # El contenedor principal de la beca en DAAD
            contenedor_raiz = soup.find('div', class_='stipdb-detail')
            if not contenedor_raiz:
                continue
            
            total_urls_analizadas += 1
            
            # Recoger todos los títulos H3 que no sean de impresión
            h3_secciones = [
                h.text.strip() 
                for h in contenedor_raiz.find_all('h3') 
                if 'print-only' not in h.get('class', [])
            ]
            
            for h3_titulo in h3_secciones:
                clave = h3_titulo.lower().strip()
                self.h3_frecuencias[clave] += 1
        
        #print(f"Análisis estructural completado. URLs analizadas: {total_urls_analizadas}")
        return total_urls_analizadas
        
    def _generar_mapeo_dinamico(self, total_urls_analizadas: int):
        """Genera el diccionario de mapeo de H3 a variables de destino usando palabras clave."""
        if total_urls_analizadas == 0:
            print("❌ No se pudo analizar ninguna URL para generar el mapeo.")
            return
            
        # Umbral: solo se consideran títulos H3 que aparecen en más del 20% de las páginas
        umbral_minimo = total_urls_analizadas * 0.2
        self.h3_mappeo_dinamico = {}
        
        #print(f"Generando mapeo. Umbral de frecuencia: >{umbral_minimo:.0f} apariciones.")

        h3_comunes = sorted(self.h3_frecuencias.items(), key=lambda item: item[1], reverse=True)

        for h3_normalized, conteo in h3_comunes:
            if conteo < umbral_minimo:
                continue 

            # Intentar mapear el H3 a una variable usando las palabras clave
            for variable, keywords in MAPPING_KEYWORDS.items():
                if any(keyword in h3_normalized for keyword in keywords):
                    if h3_normalized not in self.h3_mappeo_dinamico:
                         self.h3_mappeo_dinamico[h3_normalized] = variable
                         print(f"  ✅ Mapeado: '{h3_normalized}' ({conteo} veces) -> '{variable}'")
                         break 
        
        if not self.h3_mappeo_dinamico:
            print("⚠️ Advertencia: El mapeo dinámico falló. Los resultados de extracción serán limitados.")

    # --- Etapa 4: Extracción Final de Variables ---

    def extraer_contenido_h3(self, h3_tag: Tag) -> str:
        """Extrae el contenido de texto de los elementos que siguen inmediatamente a un H3."""
        contenido = []
        for sibling in h3_tag.find_next_siblings():
            if sibling.name == 'h3':
                break
            if sibling.name in ['p', 'ul', 'ol', 'div']:
                if sibling.get('class') and any(cls in sibling['class'] for cls in ['footer', 'sidebar', 'nav']):
                    continue
                contenido.append(sibling.get_text(separator=' ', strip=True))
            if len(contenido) > 5:
                break
        return " ".join(contenido).strip()

    def extraer_variables_de_body(self, item: Dict) -> Dict:
        """Procesa un solo body HTML para extraer las variables finales usando el mapa dinámico."""
        url = item['url']
        extracted_data = {
            'title': 'N/A', 
            'location': 'Germany', 
            'coverage': 'N/A', 
            'amount': 'N/A', 
            'type': 'N/A', 
            'url': url, 
            'source_url': item.get('source_url', url), # Usa el valor de la lista_de_bodys
            'raw_h3_data': {} # Temporal
        }

        if item.get('status_code') != 200 or 'body_html' not in item:
            extracted_data['error'] = item.get('error', 'Contenido faltante/Error de red.')
            return extracted_data

        body_html = item['body_html']
        try:
            soup = BeautifulSoup(body_html, 'html.parser')
        except Exception as e:
            extracted_data['error'] = f"Error al parsear HTML: {e}"
            return extracted_data

        h2_title_tag = soup.find('h2', class_='title')
        if h2_title_tag:
            extracted_data['title'] = h2_title_tag.text.strip()
            
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

        # POST-PROCESAMIENTO: Asignar los datos raw a las variables finales
        raw_data = extracted_data['raw_h3_data']

        if 'coverage_amount' in raw_data:
            full_text = raw_data['coverage_amount']
            if re.search(r'[\d,\.]+\s*(?:€|\$|Euro|US\$|GBP)', full_text, re.IGNORECASE):
                extracted_data['amount'] = full_text
                extracted_data['coverage'] = full_text
            else:
                extracted_data['coverage'] = full_text

        if 'type_description' in raw_data:
            extracted_data['type'] = raw_data['type_description']
            
        # Limpieza
        del extracted_data['raw_h3_data']

        return extracted_data

    # --- Función principal de ejecución (Orquestación) ---

    def run_scraper(self):
        """Ejecuta el proceso completo de scraping, análisis y extracción."""
        
        # 1. Rastreo
        links = self.scrape_links()
        if not links:
            return []

        # 2. Descarga de contenido HTML
        lista_de_bodys = self.fetch_body_content(links)
        
        # 3. ANÁLISIS ESTRUCTURAL
        total_analizadas = self._analizar_estructura_y_h3_frecuencias(lista_de_bodys)
        
        # 4. GENERACIÓN DEL MAPEO DINÁMICO
        self._generar_mapeo_dinamico(total_analizadas)

        # 5. Extracción de variables
        resultados_extraccion: List[Dict] = []
        #print("\nIniciando la extracción final de variables.")
        for i, item in enumerate(lista_de_bodys):
            resultado = self.extraer_variables_de_body(item)
            resultados_extraccion.append(resultado)
            if resultado.get('error'):
                 print(f"❌ Extracción {i+1}: {resultado.get('url')} - ERROR")
            else:
                continue
                #print(f"✅ Extracción {i+1}: {resultado.get('title', 'N/A')}")
            
        #print("\nProceso de extracción completado.")
        return resultados_extraccion

# ==============================================================================
# --- Configuración y Ejecución Principal ---
# ==============================================================================

if __name__ == '__main__':
    # URL inicial
    STARTING_URL = "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"

    # Instanciar y ejecutar el scraper
    scraper = DAADScraper(start_url=STARTING_URL, max_links=120, sleep_time=0.5) 
    
    try:
        resultados_finales = scraper.run_scraper()
        
        # Imprimir un resumen
        """print("\n==================================================")
        print("RESULTADOS FINALES DEL SCRAPING:")
        print("==================================================")
        """
        for i, res in enumerate(resultados_finales):
            
            print(f"[{i+1}] Título: {res['title']}")
            print(f"    Ubicación: {res['location']}")
            print(f"    Monto: {res['amount']}")
            print(f"    Cobertura: {res['coverage'][:50]}...")
            print(f"    Tipo: {res['type'][:50]}...")
            print(f"    URL: {res['url']}")
            print(f"    Fuente: {res['source_url']}")
            
            if res.get('error'):
                print(f"    ❌ ERROR: {res['error']}")
            print("-" * 50)
            
        print(f"\nTotal de resultados procesados: {len(resultados_finales)}")

    except Exception as e:
        print(f"\nUn error fatal ocurrió durante la ejecución: {e}")