import time
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


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

SCHOLARSHIP_AMERICA_URL = "https://scholarshipamerica.org/students/browse-scholarships/"


# 2. CLASE DE RASTREO ESPECIALIZADA SCHOLARSHIP AMERICA 


class ScholarshipAmericaScraper:
    """Scraper simple y robusto para Scholarship America basado en la estructura DOM real."""
    
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
            while current_page <= self.max_pages:
                print(f"[ScholarshipAmerica] Scraping page {current_page}")
                
                self.driver.get(self.start_url)
                
                # Esperar a que cargue el contenido
                try:
                    WebDriverWait(self.driver, self.wait_time).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "mgpb-listing-item__content"))
                    )
                    time.sleep(2)  # Espera extra para contenido dinámico
                except TimeoutException:
                    print(f"[ScholarshipAmerica] Timeout waiting for content on page {current_page}")
                    break
                
                # Obtener HTML de la página
                html = self.driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extraer becas
                scholarships = self._extract_scholarships_from_page(soup)
                if not scholarships:
                    print(f"[ScholarshipAmerica] No scholarships found on page {current_page}")
                    break
                
                results.extend(scholarships)
                print(f"[ScholarshipAmerica] Found {len(scholarships)} scholarships on page {current_page}")
                
                # Intentar navegar a la siguiente página
                if current_page < self.max_pages:
                    next_page_num = current_page + 1
                    try:
                        # Encontrar y hacer clic en el botón de siguiente página
                        next_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, f'a.facetwp-page[data-page="{next_page_num}"]'))
                        )
                        next_button.click()
                        time.sleep(self.sleep_time)
                        current_page += 1
                    except:
                        print(f"[ScholarshipAmerica] No more pages available")
                        break
                else:
                    break
                
        except Exception as e:
            print(f"[ScholarshipAmerica] Error during scraping: {e}")
        finally:
            self._quit_driver()
        
        return results

    def _extract_scholarships_from_page(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extraer becas de la página usando la estructura DOM real."""
        scholarships: List[Dict[str, Any]] = []
        
        # Encontrar todos los elementos de becas usando la clase real del DOM
        items = soup.find_all('div', class_='mgpb-listing-item__content')
        
        print(f"[ScholarshipAmerica] Found {len(items)} scholarship items in HTML")
        
        for item in items:
            try:
                scholarship_data = self._extract_scholarship_data(item)
                if scholarship_data and scholarship_data.get('title'):
                    scholarships.append(scholarship_data)
            except Exception as e:
                print(f"[ScholarshipAmerica] Error extracting scholarship: {e}")
                continue
        
        return scholarships

    def _extract_scholarship_data(self, item) -> Dict[str, Any]:
        """Extraer datos de un elemento individual de beca basado en la estructura DOM real."""
        data = {
            'title': 'N/A',
            'location': 'United States',
            'coverage': '',
            'amount': 'N/A',
            'type': 'N/A',
            'url': '',
            'source_url': self.start_url
        }
        
        # Extraer título del encabezado
        title_elem = item.find('a', class_='mgpb-listing-item__heading')
        if title_elem:
            data['title'] = title_elem.get_text(strip=True)
            # Extraer URL del mismo elemento
            href = title_elem.get('href')
            if href:
                data['url'] = href if href.startswith('http') else f"https://scholarshipamerica.org{href}"
        
        # Encontrar la lista de detalles
        details_list = item.find('ul', class_='mgpb-listing-item__scholarship-details')
        if details_list:
            list_items = details_list.find_all('li')
            
            for li in list_items:
                li_text = li.get_text(strip=True)
                
                # Extraer Monto del Premio
                if 'Award Amount' in li_text:
                    amount_span = li.find_all('span')
                    if len(amount_span) >= 2:
                        amount = amount_span[-1].get_text(strip=True)
                        data['amount'] = amount
                        data['coverage'] = amount
                
                # Extraer Fecha Límite y agregar a cobertura
                elif 'Deadline' in li_text:
                    deadline_span = li.find_all('span')
                    if len(deadline_span) >= 2:
                        deadline = deadline_span[-1].get_text(strip=True)
                        if data['coverage']:
                            data['coverage'] += f" | Deadline: {deadline}"
                        else:
                            data['coverage'] = f"Deadline: {deadline}"
                
                # Extraer Instituciones (tipo)
                elif 'Institutions' in li_text:
                    inst_span = li.find_all('span')
                    if len(inst_span) >= 2:
                        data['type'] = inst_span[-1].get_text(strip=True)
                
                # Extraer Estado/Territorio (ubicación)
                elif 'State/Territory' in li_text:
                    state_span = li.find_all('span')
                    if len(state_span) >= 2:
                        state = state_span[-1].get_text(strip=True)
                        if state.lower() != 'national':
                            data['location'] = f"United States ({state})"
                        else:
                            data['location'] = "United States (National)"
        
        # Extraer extracto/descripción y agregar a cobertura si está disponible
        excerpt = item.find('div', class_='mgpb-listing-item__excerpt')
        if excerpt:
            excerpt_text = excerpt.get_text(strip=True)
            if excerpt_text and len(excerpt_text) > 10:
                if data['coverage']:
                    data['coverage'] += f" | {excerpt_text[:150]}..."
                else:
                    data['coverage'] = excerpt_text[:150] + "..."
        
        return data


# 3. FUNCIÓN DE UTILIDAD PARA INTEGRACIÓN (PUNTO DE ENTRADA EXTERNO)


def scrape_scholarship_america_scholarships(headless: bool = True, max_pages: int = 3) -> List[Dict[str, Any]]:
    """Ejecuta el proceso completo de scraping de Scholarship America y retorna resultados como diccionarios Beca.
    
    Args:
        headless: Si ejecutar el navegador en modo headless
        max_pages: Máximo número de páginas a extraer
        
    Returns:
        Lista de diccionarios de becas
    """
    
    scraper = ScholarshipAmericaScraper(
        start_url=SCHOLARSHIP_AMERICA_URL,
        max_pages=max_pages,
        wait_time=10,
        sleep_time=0.5,
        headless=headless
    )
    
    print(f"[ScholarshipAmerica] Starting scraping with max_pages={max_pages}")
    
    try:
        results = scraper.scrape_scholarships()
        
        # Convertir al formato Beca
        beca_results: List[Dict[str, Any]] = []
        for data in results:
            beca = Beca(
                title=data.get('title', 'N/A'),
                location=data.get('location', 'United States'),
                coverage=data.get('coverage', 'N/A'),
                amount=data.get('amount', 'N/A'),
                type=data.get('type', 'N/A'),
                url=data.get('url', ''),
                source_url=data.get('source_url', SCHOLARSHIP_AMERICA_URL)
            )
            beca_results.append(asdict(beca))
        
        print(f"[ScholarshipAmerica] Scraping completed. Found {len(beca_results)} scholarships")
        return beca_results
        
    except Exception as e:
        print(f"[ScholarshipAmerica] Error in scraping: {e}")
        return []