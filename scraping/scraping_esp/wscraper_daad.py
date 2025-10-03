import time
import re
from typing import List, Dict, Any
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# 1. DEFINICIONES DE CLASE Y CONSTANTES

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

DAAD_STARTING_URL = "https://www2.daad.de/deutschland/stipendium/datenbank/en/21148-scholarship-database/"



# 2. CLASE DE RASTREO ESPECIALIZADA DAAD

class DAADScraper:
    """Scraper simple y robusto para becas DAAD."""

    def __init__(self, start_url: str, max_pages: int, wait_time: int, sleep_time: float, headless: bool):
        self.start_url = start_url
        self.max_pages = max_pages
        self.wait_time = wait_time
        self.sleep_time = sleep_time
        self.headless = headless
        self.driver = None

    def _init_driver(self):
        """Inicializa el driver de Chrome."""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
        except WebDriverException as e:
            raise WebDriverException(f"Error al iniciar el driver de Chrome: {e}")

    def _quit_driver(self):
        """Cierra el driver si está inicializado."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def scrape_scholarships(self) -> List[Dict[str, Any]]:
        """Método principal de scraping con paginación."""
        results: List[Dict[str, Any]] = []
        
        try:
            self._init_driver()
            
            current_page = 1
            current_url = self.start_url
            
            while current_page <= self.max_pages and current_url:
                print(f"[DAAD] Scraping page {current_page}")
                
                self.driver.get(current_url)
                
                # Esperar a que cargue el contenido (buscar lista de resultados)
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'ul.resultlist'))
                    )
                    time.sleep(2)  # Espera extra para contenido dinámico
                except TimeoutException:
                    print(f"[DAAD] Timeout waiting for content on page {current_page}")
                    break
                
                # Obtener HTML de la página
                html = self.driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraer enlaces de becas de la página actual
                scholarship_links = self._extract_scholarship_links(soup)
                if not scholarship_links:
                    print(f"[DAAD] No scholarship links found on page {current_page}")
                    break
                
                print(f"[DAAD] Found {len(scholarship_links)} scholarship links on page {current_page}")
                
                # Visitar cada página de detalle de beca
                for link in scholarship_links:
                    scholarship_data = self._scrape_scholarship_detail(link)
                    if scholarship_data and scholarship_data.get('title'):
                        results.append(scholarship_data)
                    time.sleep(self.sleep_time)
                
                print(f"[DAAD] Extracted {len([r for r in results if r.get('title')])} valid scholarships from page {current_page}")
                
                # Intentar navegar a la siguiente página
                if current_page < self.max_pages:
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
                                current_page += 1
                            else:
                                print(f"[DAAD] Next page link is same as current, stopping")
                                break
                        else:
                            print(f"[DAAD] No next page link found")
                            break
                    except NoSuchElementException:
                        print(f"[DAAD] No more pages available")
                        break
                    except Exception as e:
                        print(f"[DAAD] Error navigating to next page: {e}")
                        break
                else:
                    break
                    
        except Exception as e:
            print(f"[DAAD] Error during scraping: {e}")
        finally:
            self._quit_driver()
        
        return results

    def _extract_scholarship_links(self, soup: BeautifulSoup) -> List[str]:
        """Extraer enlaces de detalle de becas de la página actual."""
        links = []
        # Buscar la lista de resultados
        result_list = soup.find('ul', class_='resultlist')
        
        if not result_list:
            print("[DAAD] No se encontró ul.resultlist")
            return links
        
        # Buscar todos los elementos li con clase 'entry'
        entries = result_list.find_all('li', class_='entry')
        print(f"[DAAD] Found {len(entries)} li.entry elements")
        
        for entry in entries:
            # El enlace está dentro del h2 > a
            h2 = entry.find('h2')
            if h2:
                link_element = h2.find('a')
                if link_element:
                    href = link_element.get('href')
                    if href:
                        absolute_link = urljoin(self.start_url, href)
                        parsed_link = urlparse(absolute_link)._replace(fragment="").geturl()
                        if parsed_link:
                            links.append(parsed_link)
        
        return links

    def _scrape_scholarship_detail(self, url: str) -> Dict[str, Any]:
        """Extraer datos de una página individual de detalle de beca."""
        data = {
            'title': 'N/A',
            'location': 'Germany',
            'coverage': '',
            'amount': 'N/A',
            'type': 'N/A',
            'url': url,
            'source_url': self.start_url
        }
        
        try:
            self.driver.get(url)
            
            # Esperar a que cargue el contenido
            try:
                WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'stipdb-detail'))
                )
            except TimeoutException:
                print(f"[DAAD] Timeout loading detail page: {url}")
                return data
            
            # Obtener HTML de la página
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extraer datos de la beca
            return self._extract_scholarship_data(soup, data)
            
        except Exception as e:
            print(f"[DAAD] Error scraping detail page {url}: {e}")
            return data

    def _extract_scholarship_data(self, soup: BeautifulSoup, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extraer datos de beca de la página de detalle usando selectores simples."""
        
        # Extraer título
        title_elem = soup.find('h2', class_='title')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
        
        # Encontrar el contenedor principal de contenido
        detail_container = soup.find('div', class_='stipdb-detail')
        if not detail_container:
            return data
        
        # Extraer información de las secciones H3 usando coincidencia simple de palabras clave
        h3_elements = detail_container.find_all('h3')
        
        coverage_parts = []
        
        for h3 in h3_elements:
            if 'print-only' in h3.get('class', []):
                continue
                
            h3_text = h3.get_text(strip=True).lower()
            
            # Obtener contenido después de este H3 hasta el siguiente H3
            content = self._get_content_after_h3(h3)
            
            if content:
                # Buscar información de monto/financiera
                if any(keyword in h3_text for keyword in ['value', 'amount', 'stipend', 'benefit', 'sum', 'financial']):
                    # Buscar valores monetarios
                    money_match = re.search(r'[\d,\.]+\s*(?:€|\$|Euro|US\$|GBP|EUR)', content, re.IGNORECASE)
                    if money_match:
                        data['amount'] = money_match.group(0)
                    coverage_parts.append(f"Amount: {content[:100]}")
                
                # Buscar información de programa/tipo
                elif any(keyword in h3_text for keyword in ['programme', 'target', 'field', 'study', 'who can apply']):
                    data['type'] = content[:150]
                
                # Buscar requisitos
                elif any(keyword in h3_text for keyword in ['require', 'academic', 'application']):
                    coverage_parts.append(f"Requirements: {content[:100]}")
                
                # Buscar detalles de ubicación (aunque por defecto es Alemania)
                elif any(keyword in h3_text for keyword in ['where', 'country', 'location']):
                    if 'germany' not in content.lower():
                        data['location'] = content[:50]
                
                # Agregar otra información relevante a cobertura
                elif len(content) > 20:
                    coverage_parts.append(f"{h3_text.title()}: {content[:100]}")
        
        # Combinar información de cobertura
        if coverage_parts:
            data['coverage'] = ' | '.join(coverage_parts[:3])  # Limitar a las primeras 3 partes
        elif data['amount'] != 'N/A':
            data['coverage'] = data['amount']
        
        return data
    
    def _get_content_after_h3(self, h3_element) -> str:
        """Obtener contenido de texto después del elemento H3 hasta el siguiente H3."""
        content_parts = []
        
        for sibling in h3_element.find_next_siblings():
            if sibling.name == 'h3':
                break
            if sibling.name in ['p', 'ul', 'ol', 'div']:
                # Omitir elementos de navegación y pie de página
                if sibling.get('class') and any(cls in sibling.get('class', []) for cls in ['footer', 'sidebar', 'nav']):
                    continue
                text = sibling.get_text(separator=' ', strip=True)
                if text:
                    content_parts.append(text)
            if len(content_parts) >= 3:  # Limitar extracción de contenido
                break
        
        return ' '.join(content_parts).strip()


# 3. FUNCIÓN DE UTILIDAD PARA INTEGRACIÓN 


def scrape_daad_scholarships(headless: bool = True, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Ejecuta el proceso completo de scraping DAAD y retorna resultados como diccionarios Beca.
    
    Args:
        headless: Si ejecutar el navegador en modo headless
        max_pages: Máximo número de páginas a extraer
        
    Returns:
        Lista de diccionarios de becas
    """
    
    scraper = DAADScraper(
        start_url=DAAD_STARTING_URL,
        max_pages=max_pages,
        wait_time=10,
        sleep_time=0.5,
        headless=headless
    )
    
    print(f"[DAAD] Starting scraping with max_pages={max_pages}")
    
    try:
        results = scraper.scrape_scholarships()
        
        # Convertir al formato Beca
        beca_results: List[Dict[str, Any]] = []
        for data in results:
            beca = Beca(
                title=data.get('title', 'N/A'),
                location=data.get('location', 'Germany'),
                coverage=data.get('coverage', 'N/A'),
                amount=data.get('amount', 'N/A'),
                type=data.get('type', 'N/A'),
                url=data.get('url', ''),
                source_url=data.get('source_url', DAAD_STARTING_URL)
            )
            beca_results.append(asdict(beca))
        
        print(f"[DAAD] Scraping completed. Found {len(beca_results)} scholarships")
        return beca_results
        
    except Exception as e:
        print(f"[DAAD] Error in scraping: {e}")
        return []

