


import urllib.parse
import time
import random

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from ddgs import DDGS

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
]

def find_manufacturer_info(part_number: str):
    """
    Função principal que orquestra a busca de informações do fabricante.
    """
    print(f"--- Iniciando busca para o Part Number: {part_number} ---")
    
    manufacturer_name = get_manufacturer_with_selenium(part_number)
    
    if not manufacturer_name or not manufacturer_name.strip():
        print(f"\n[!] Não foi possível encontrar o nome do fabricante para '{part_number}'. Encerrando.")
        return

    clean_manufacturer_name = manufacturer_name.replace("Co., Ltd.", "").strip()
    print(f"\n[✓] Nome do fabricante encontrado: {clean_manufacturer_name}")

    manufacturer_address = get_address_with_ddg(clean_manufacturer_name)

    if not manufacturer_address:
        print(f"\n[!] Não foi possível encontrar um endereço para '{clean_manufacturer_name}'.")
        return
        
    print(f"[✓] Endereço do fabricante encontrado: {manufacturer_address}")
    print("\n--- Processo Concluído ---")
    
    return {
        "part_number": part_number,
        "manufacturer_name": clean_manufacturer_name,
        "manufacturer_address": manufacturer_address
    }

def get_manufacturer_with_selenium(part_number: str) -> str | None:
    """
    Usa o undetected_chromedriver para extrair o nome do fabricante da Arrow Electronics.
    Com lógica para lidar com páginas de lista de resultados.
    """
    print(f"\n[ETAPA 1 - SELENIUM STEALTH] Buscando '{part_number}' na Arrow...")
    url = f"https://www.arrow.com/en/products/search?q={urllib.parse.quote(part_number)}"
    options = uc.ChromeOptions()
    # Mantenha comentado para assistir o robô clicar!
    # options.add_argument("--headless")
    
    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get(url)
        
        try:
            print("(Tentativa 1: Procurando fabricante na página de produto...)")
            wait = WebDriverWait(driver, 5)
            manufacturer_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'Product-SimplifiedSummary-SubHeading-Manufacturer'))
            )
        except TimeoutException:
            print("(Página de produto não encontrada, tratando como lista de resultados...)")
            wait = WebDriverWait(driver, 10)
            
            # --- ESTRATÉGIA FINAL: BUSCAR PELO LINK (href) ---
            # Converte o part number para minúsculas para corresponder ao formato da URL
            part_number_lower = part_number.lower()
            product_link_selector = f"a[href*='{part_number_lower}']"
            print(f"(Procurando pelo link cujo href contém '{part_number_lower}'...)")

            product_link = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, product_link_selector))
            )
            # --- FIM DA ESTRATÉGIA ---

            print("(Link encontrado, clicando...)")
            product_link.click()
            
            print("(Aguardando página do produto carregar após o clique...)")
            wait = WebDriverWait(driver, 10)
            manufacturer_element = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, 'Product-SimplifiedSummary-SubHeading-Manufacturer'))
            )

        print("(Elemento do fabricante encontrado! Extraindo texto...)")
        manufacturer_name = manufacturer_element.get_attribute("textContent")
        return manufacturer_name.strip() if manufacturer_name else None

    except Exception as e:
        print(f"[ERRO SELENIUM] Falha ao buscar dados na Arrow: {e}")
        if driver:
            driver.save_screenshot("arrow_error_screenshot.png")
        return None
    finally:
        if driver:
            driver.quit()

def get_address_with_ddg(company_name: str) -> str | None:
    """
    Usa a busca de texto do DDGS e uma lógica inteligente para encontrar o endereço.
    """
    print(f"\n[ETAPA 2 - DDGS TEXT-SEARCH] Buscando endereço para '{company_name}'...")
    query = f"{company_name} headquarters address"
    address_keywords = ['Street', 'St', 'Road', 'Rd', 'Ave', 'Avenue', 'Suwon', 'Maetan-ro', 'Jose', 'CA']
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                print("(DDGS não retornou resultados.)")
                return None
            for result in results:
                snippet = result.get('body', '')
                has_number = any(char.isdigit() for char in snippet)
                has_keyword = any(keyword.lower() in snippet.lower() for keyword in address_keywords)
                if has_number and has_keyword:
                    print(f"(Snippet de endereço encontrado: '{snippet}')")
                    return snippet
            print("(Nenhum snippet nos resultados pareceu ser um endereço. Retornando o primeiro resultado como fallback.)")
            return results[0].get('body', '')
    except Exception as e:
        print(f"[ERRO DDGS] Falha ao buscar: {e}")
        return None

if __name__ == "__main__":
    part_number_exemplo = "ERJ-2RKF2201X"
    
    informacoes = find_manufacturer_info(part_number_exemplo)
    
    if informacoes:
        print("\n--- DADOS ESTRUTURADOS ---")
        print(f"Part Number: {informacoes['part_number']}")
        print(f"Fabricante: {informacoes['manufacturer_name']}")
        print(f"Endereço: {informacoes['manufacturer_address']}")