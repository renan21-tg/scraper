import re
from ddgs import DDGS

def get_manufacturer_from_title(title: str, part_number: str) -> str | None:
    """
    Tenta extrair o nome de um fabricante do título de um resultado de busca.
    Ex: "ERJ-2RKF2201X by Panasonic Industry | Arrow.com" -> "Panasonic Industry"
    """
    # Remove o part number do título para evitar confusão
    title_without_pn = title.replace(part_number, "").strip()
    
    # Procura por padrões comuns, como "by Fabricante" ou "Fabricante |"
    # Esta é uma expressão regular que busca por uma ou mais palavras capitalizadas
    # que aparecem no início do título ou depois de "by".
    match = re.search(r"^(?:by\s)?([A-Z][a-zA-Z\s.&-]+)", title_without_pn)
    
    if match:
        # Pega o nome encontrado e remove lixo comum como " |"
        manufacturer = match.group(1).replace("|", "").strip()
        # Evita retornar nomes de distribuidores como fabricantes
        if manufacturer.lower() not in ["arrow", "mouser", "digi-key"]:
            return manufacturer
            
    return None

def find_info_with_ddg(part_number: str):
    """
    Função principal que usa apenas o DDGS para encontrar fabricante e endereço.
    """
    print(f"--- Iniciando busca APENAS COM DDGS para o Part Number: {part_number} ---")
    
    manufacturer_name = None
    
    # --- ETAPA 1: Encontrar o nome do fabricante ---
    print(f"\n[ETAPA 1 - DDGS] Buscando fabricante para '{part_number}'...")
    manufacturer_query = f'"{part_number}" manufacturer'
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(manufacturer_query, max_results=5))
            
            if not results:
                print("(DDGS não retornou resultados para a busca de fabricante.)")
            else:
                # Itera nos títulos dos resultados para encontrar o nome do fabricante
                for result in results:
                    title = result.get('title', '')
                    found_name = get_manufacturer_from_title(title, part_number)
                    if found_name:
                        manufacturer_name = found_name
                        print(f"(Fabricante encontrado no título: '{title}')")
                        break # Para no primeiro que encontrar

    except Exception as e:
        print(f"[ERRO DDGS] Falha ao buscar fabricante: {e}")

    if not manufacturer_name:
        print(f"\n[!] Não foi possível encontrar o nome do fabricante para '{part_number}'. Encerrando.")
        return

    print(f"\n[✓] Nome do fabricante encontrado: {manufacturer_name}")

    # --- ETAPA 2: Encontrar o endereço do fabricante ---
    print(f"\n[ETAPA 2 - DDGS] Buscando endereço para '{manufacturer_name}'...")
    address_query = f"{manufacturer_name} headquarters address"
    address_keywords = ['Street', 'St', 'Road', 'Rd', 'Ave', 'Avenue', 'Tokyo', 'Japan', 'Osaka']
    manufacturer_address = None

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(address_query, max_results=5))
            if not results:
                print("(DDGS não retornou resultados para a busca de endereço.)")
            else:
                for result in results:
                    snippet = result.get('body', '')
                    has_number = any(char.isdigit() for char in snippet)
                    has_keyword = any(keyword.lower() in snippet.lower() for keyword in address_keywords)
                    
                    if has_number and has_keyword:
                        manufacturer_address = snippet
                        print(f"(Snippet de endereço encontrado: '{snippet}')")
                        break

    except Exception as e:
        print(f"[ERRO DDGS] Falha ao buscar endereço: {e}")

    if not manufacturer_address:
        print(f"\n[!] Não foi possível encontrar o endereço para '{manufacturer_name}'.")
        return
        
    print(f"[✓] Endereço do fabricante encontrado: {manufacturer_address}")
    print("\n--- Processo Concluído ---")

    # Retorna os dados estruturados
    return {
        "part_number": part_number,
        "manufacturer_name": manufacturer_name,
        "manufacturer_address": manufacturer_address
    }


if __name__ == "__main__":
    # Teste com o Part Number que já sabemos que funciona
    part_number_exemplo = "CL10C330JB8NNNC"
    
    informacoes = find_info_with_ddg(part_number_exemplo)
    
    if informacoes:
        print("\n--- DADOS ESTRUTURADOS ---")
        print(f"Part Number: {informacoes['part_number']}")
        print(f"Fabricante: {informacoes['manufacturer_name']}")
        print(f"Endereço: {informacoes['manufacturer_address']}")