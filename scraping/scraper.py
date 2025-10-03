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

#import de scrapers especificos
from scraping.scraping_esp.wscraper_daad import scrape_daad_scholarships
from scraping.scraping_esp.wscraper_scholarship_america import scrape_scholarship_america_scholarships



def scrape_scholarship_pages(urls: List[str], headless: bool = True, max_pages: Optional[int] = None, source: str = "Ambos") -> List[Dict[str, Any]]:
    """Main scraping function that calls specialized scrapers based on source."""
    results: List[Dict[str, Any]] = []
    
    def _merge(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(existing)
        for k in ["title", "location", "coverage", "amount", "type", "url", "source_url"]:
            if not merged.get(k) and new.get(k):
                merged[k] = new[k]
        return merged

    # Map UI source names to internal logic
    source_map = {
        "Ambos": ["daad", "scholarship_america"],
        "DAAD (Alemania)": ["daad"],
        "Scholarship America (USA)": ["scholarship_america"],
        "Genérico": []  # Disabled for now
    }
    
    sources_to_run = source_map.get(source, ["daad", "scholarship_america"])

    # --- Llamada e Integración del Scraper Especializado (DAAD) ---
    if "daad" in sources_to_run:
        try:
            print("\n--- Integrando resultados del Scraper DAAD ---")
            resultados_daad = scrape_daad_scholarships(headless=headless)
            results.extend(resultados_daad)
        except Exception as e:
            print(f"❌ Error al integrar el scraper de DAAD: {e}")

    # --- Llamada e Integración del Scraper Especializado (Scholarship America) ---
    if "scholarship_america" in sources_to_run:
        try:
            print("\n--- Integrando resultados del Scraper Scholarship America ---")
            paginas_limite = 3 if (max_pages is None or max_pages == 0) else max_pages
            resultados_sa = scrape_scholarship_america_scholarships(headless=headless, max_pages=paginas_limite)
            results.extend(resultados_sa)
        except Exception as e:
            print(f"❌ Error al integrar el scraper de Scholarship America: {e}")

    print(f"✅ Proceso completado. Total de becas recolectadas: {len(results)}")

    # Deduplicación final por URL
    dedup: Dict[str, Dict[str, Any]] = {}
    for r in results:
        key = r.get("url") or r.get("source_url")
        if not key:
            continue
        if key in dedup:
            dedup[key] = _merge(dedup[key], r)
        else:
            dedup[key] = r

    return list(dedup.values())

