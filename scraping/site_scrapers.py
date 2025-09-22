"""
Scrapers simples para sitios populares de becas.
"""

import re
import time
from typing import List, Dict, Any

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .scraper import Beca


class SimpleScraper:
    """Scraper simple y unificado"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
    
    def raspar(self, url: str) -> List[Dict[str, Any]]:
        """Raspa cualquier sitio de becas extrayendo: título, monto, ubicación"""
        try:
            # Cargar página
            self.driver.get(url)
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(3)  # Tiempo para cargar contenido dinámico
            
            soup = BeautifulSoup(self.driver.page_source, "lxml")
            texto_completo = soup.get_text()
            
            # Extraer los 3 datos clave
            titulo = self._obtener_titulo(soup)
            monto = self._buscar_monto(texto_completo)
            ubicacion = self._buscar_ubicacion(texto_completo)
            
            # Crear beca con datos extraídos
            beca = Beca(
                title=titulo,
                location=ubicacion,
                coverage=f"Título: {titulo}\nMonto: {monto}\nUbicación: {ubicacion}\nURL: {url}",
                amount=monto,
                type="Beca",
                url=url,
                source_url=url
            )
            
            return [beca.__dict__]
            
        except Exception as e:
            print(f"Error scrapeando {url}: {e}")
            return []
    
    def _obtener_titulo(self, soup: BeautifulSoup) -> str:
        """Obtiene el título de la página"""
        # Buscar en múltiples lugares comunes
        for selector in ["h1", "title", "h2", ".title", ".heading"]:
            elemento = soup.select_one(selector)
            if elemento:
                texto = elemento.get_text(strip=True)
                if texto and len(texto) > 5 and len(texto) < 200:
                    return texto
        
        return "Oportunidad de Beca"
    
    def _buscar_monto(self, texto: str) -> str:
        """Busca montos en formato de dinero"""
        # Patrones mejorados para encontrar dinero
        patrones = [
            r"\$[\d,]+(?:\.\d{2})?",
            r"USD\s*[\d,]+",
            r"[\d,]+\s*dollars?",
            r"premio.*\$[\d,]+",
            r"worth.*\$[\d,]+",
            r"up to.*\$[\d,]+",
            r"hasta.*\$[\d,]+"
        ]
        
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return "Monto no especificado"
    
    def _buscar_ubicacion(self, texto: str) -> str:
        """Busca ubicación/país en el texto"""
        # Patrones para encontrar ubicaciones
        patrones_paises = [
            r"\b(United States|USA|US|Estados Unidos|America)\b",
            r"\b(Canada|Canadá)\b",
            r"\b(Mexico|México)\b",
            r"\b(Spain|España)\b",
            r"\b(United Kingdom|UK|Reino Unido)\b",
            r"\b(Germany|Alemania)\b",
            r"\b(France|Francia)\b",
            r"\b(International|Internacional)\b"
        ]
        
        # Palabras clave que indican ubicación
        palabras_ubicacion = [
            r"residents of\s+([A-Za-z\s]+)",
            r"citizens of\s+([A-Za-z\s]+)",
            r"located in\s+([A-Za-z\s]+)",
            r"available in\s+([A-Za-z\s]+)",
            r"for students in\s+([A-Za-z\s]+)"
        ]
        
        # Buscar países específicos
        for patron in patrones_paises:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Buscar con palabras clave
        for patron in palabras_ubicacion:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Ubicación no especificada"


def obtener_scraper_para_url(url: str, driver: webdriver.Chrome) -> SimpleScraper:
    """Devuelve el scraper simple para cualquier URL"""
    return SimpleScraper(driver)


# Sitios populares de becas para acceso rápido
SITIOS_POPULARES_BECAS = {
    "Scholarship America": "https://scholarshipamerica.org/students/browse-scholarships/",
    "Fastweb": "https://www.fastweb.com/scholarships", 
    "College Board": "https://bigfuture.collegeboard.org/scholarship-search",
}
