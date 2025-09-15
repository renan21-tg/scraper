import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
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

    print(f"\n[✓] Nome do fabricante encontrado: {manufacturer_name}")

    manufacturer_address = get_address_from_google(manufacturer_name)

    if not manufacturer_address:
        print(f"\n[!] Não foi possível encontrar um endereço para '{manufacturer_name}'.")
        return
        
    print(f"[✓] Endereço do fabricante encontrado: {manufacturer_address}")
    print("\n--- Processo Concluído ---")
    
    return {
        "part_number": part_number,
        "manufacturer_name": manufacturer_name,
        "manufacturer_address": manufacturer_address
    }

def get_manufacturer_with_selenium(part_number: str) -> str | None:
    """
    Usa o undetected_chromedriver para extrair dados da Arrow Electronics.
    """
    print(f"\n[ETAPA 1 - SELENIUM STEALTH] Buscando '{part_number}' na Arrow...")
    
    url = f"https://www.arrow.com/en/products/search?q={urllib.parse.quote(part_number)}"
    
    options = uc.ChromeOptions()
    # Mantenha a linha abaixo comentada para o teste
    # options.add_argument("--headless") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")

    driver = None
    try:
        # --- CÓDIGO SIMPLIFICADO ---
        # A biblioteca agora gerencia o driver automaticamente.
        driver = uc.Chrome(options=options)
        # --- FIM DA MUDANÇA ---
        
        print("(Navegador iniciado, acessando a URL da Arrow...)")
        driver.get(url)

        wait = WebDriverWait(driver, 20)
        
        print("(Aguardando o elemento do fabricante aparecer na página...)")
        manufacturer_element = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, 'Product-SimplifiedSummary-SubHeading-Manufacturer'))
        )
        
        print("(Elemento encontrado! Extraindo texto...)")
        manufacturer_name = manufacturer_element.get_attribute("textContent")

        if manufacturer_name:
            return manufacturer_name.strip()
        
        return None

    except Exception as e:
        print(f"[ERRO SELENIUM] Falha ao buscar dados na Arrow: {e}")
        if driver:
            screenshot_path = "arrow_error_screenshot.png"
            driver.save_screenshot(screenshot_path)
            print(f"[DEBUG] Screenshot do erro salvo como '{screenshot_path}'")
        return None
    finally:
        if driver:
            driver.quit()

# A função do Google permanece a mesma
def get_address_from_google(company_name: str) -> str | None:
    # ... (código sem alterações) ...
    print(f"\n[ETAPA 2] Buscando endereço para '{company_name}' no Google...")
    time.sleep(random.uniform(1, 3))
    query = f"{company_name} headquarters address"
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        address_span = soup.find("span", class_="LrzXr")
        if address_span: return address_span.get_text(strip=True)
        address_div = soup.find("div", class_="Z1hOCe")
        if address_div: return address_div.get_text(strip=True)
        return None
    except requests.exceptions.RequestException as e:
        print(f"[ERRO] Falha ao acessar o Google: {e}")
        return None

# Bloco principal permanece o mesmo
if __name__ == "__main__":
    part_number_exemplo = "CL10C330JB8NNNC"
    informacoes = find_manufacturer_info(part_number_exemplo)
    if informacoes:
        print("\n--- DADOS ESTRUTURADOS ---")
        print(f"Part Number: {informacoes['part_number']}")
        print(f"Fabricante: {informacoes['manufacturer_name']}")
        print(f"Endereço: {informacoes['manufacturer_address']}")