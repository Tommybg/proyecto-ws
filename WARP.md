# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Development Commands

### Running the Application
```bash
streamlit run app.py
```

### Environment Setup
```bash
python -m venv proy_env
source proy_env/bin/activate  # Windows: proy_env\Scripts\activate
pip install -r requirements.txt
```

### Chrome/Brave Browser Path Configuration (macOS)
```bash
export CHROME_PATH="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
```

### Testing Individual Scrapers
```bash
# Run specific scraper modules directly
python -m scraping.scraping_esp.wscraper_daad
python -m scraping.scraping_esp.wscraper_scholarship_america
```

## Code Architecture

### Main Application Flow
The application follows a three-layer architecture:

1. **Presentation Layer (`app.py`)**
   - Streamlit-based web interface
   - User input handling for scholarship sources (DAAD, Scholarship America, or both)
   - Headless browser configuration
   - OpenAI model selection and result display

2. **Scraping Orchestration (`scraping/scraper.py`)**
   - Main entry point: `scrape_scholarship_pages()`
   - Source routing based on user selection
   - Result deduplication by URL
   - Integration with specialized scrapers

3. **Specialized Scrapers (`scraping/scraping_esp/`)**
   - **DAAD Scraper**: Multi-stage architecture with dynamic H3 mapping
     - Stage 1: Selenium-based link discovery with pagination
     - Stage 2: Requests-based content fetching
     - Stage 3: Dynamic field mapping based on H3 frequency analysis
     - Stage 4: Structured data extraction
   - **Scholarship America Scraper**: Card-based extraction with fallback selectors

### Data Processing Pipeline
1. **URL Collection**: Specialized scrapers collect scholarship detail URLs
2. **Content Extraction**: Each scraper extracts structured data into standardized format:
   ```python
   {
       'title': str,
       'location': str, 
       'coverage': str,
       'amount': str,
       'type': str,
       'url': str,
       'source_url': str
   }
   ```
3. **Deduplication**: Results merged by URL with data completion
4. **AI Processing**: OpenAI client generates formatted Markdown reports

### Key Design Patterns

#### Dynamic Field Mapping (DAAD)
- Frequency analysis of H3 headers across multiple pages
- Keyword-based classification into data categories
- Threshold-based mapping (20% minimum appearance rate)

#### Fallback Selector Strategy (Scholarship America) 
- Multiple CSS selector attempts for robustness
- Regex-based content extraction when selectors fail
- Graceful degradation for missing data

#### Driver Management
- Shared Chrome driver initialization pattern
- Headless/headed mode configuration
- Automatic cleanup with try/finally blocks

## Environment Configuration

### Required Environment Variables
- `OPENAI_API_KEY`: OpenAI API key for report generation (required)

### Browser Configuration
- Chrome is default and recommended
- Brave browser supported with `CHROME_PATH` environment variable
- Automatic ChromeDriver management via webdriver-manager

### OpenAI Models
- Default: `gpt-4.1-2025-04-14`
- Alternative: `gpt-4.1-mini-2025-04-14`

## Scraper-Specific Notes

### DAAD Scraper Limitations
- Fixed internal page limit (not configurable via UI)
- Requires stable H3 section structure
- German scholarship focus with "Germany" as default location

### Scholarship America Scraper
- Configurable page limits (default: 3 pages)
- Card-based UI extraction
- US-focused scholarships

## Development Guidelines

### Adding New Scrapers
1. Create new scraper class in `scraping/scraping_esp/`
2. Implement standardized data format output
3. Add integration to `scraping/scraper.py` source mapping
4. Update UI options in `app.py` if needed

### Modifying OpenAI Processing
- System prompt located in `utils/openai_client.py`
- Prompt optimized for Spanish language output
- Structured for regional organization and competitiveness analysis

### Streamlit Theming
- Custom dark theme configured in `.streamlit/config.toml`
- Primary color: `#4F46E5` (indigo)
- Background colors optimized for dark mode