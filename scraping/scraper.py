from __future__ import annotations

import re
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


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
    # Alternativa: primer strong/bold
    for selector in ["strong", "b"]:
        el = soup.select_one(selector)
        if el:
            texto = _extraer_texto(el)
            if len(texto) > 4:
                return texto
    return "Beca"


# Alias en inglés para compatibilidad
_build_driver = _construir_driver
