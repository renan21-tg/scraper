import re
from ddgs import DDGS
from collections import Counter

def carregar_fabricantes_com_variacoes(caminho_txt: str) -> dict[str, list[str]]:
    fabricantes_map = {}
    with open(caminho_txt, "r", encoding="utf-8") as f:
        for linha in f:
            nome_completo = linha.strip()
            if not nome_completo:
                continue
            
            nome_principal = nome_completo.split('/')[0].strip()
            
            if nome_principal not in fabricantes_map:
                fabricantes_map[nome_principal] = []
            
            fabricantes_map[nome_principal].append(nome_completo)
            
    return fabricantes_map

def buscar_fabricante_com_pontuacao(part_number: str, fabricantes_map: dict[str, list[str]]) -> str | None:
    print(f"\nBuscando fabricante para '{part_number}'...")
    query = f'"{part_number}" manufacturer datasheet'
    
    ocorrencias = Counter()

    try:
        with DDGS() as ddgs:
            resultados = ddgs.text(query, max_results=10)
            
            if not resultados:
                print("(DDGS não retornou resultados para a busca de fabricante.)")
                return None

            texto_completo_busca = " ".join([r.get("title", "") + " " + r.get("body", "") for r in resultados])

            for nome_principal, variacoes in fabricantes_map.items():
                for variacao in variacoes:
                    padrao = r"\b" + re.escape(variacao) + r"\b"
                    if re.search(padrao, texto_completo_busca, re.IGNORECASE):
                        ocorrencias[nome_principal] += 1
    
    except Exception as e:
        print(f"Falha ao buscar fabricante: {e}")
        return None

    if not ocorrencias:
        print("(Nenhum fabricante conhecido foi encontrado nos resultados.)")
        return None

    fabricante_mais_comum = ocorrencias.most_common(1)[0][0]
    print(f"(Fabricante mais provável encontrado: '{fabricante_mais_comum}' com {ocorrencias[fabricante_mais_comum]} menções)")
    return fabricante_mais_comum

def get_address_with_ddg(company_name: str) -> str | None:
    print(f"\nBuscando endereço para '{company_name}'...")
    query = f"{company_name} headquarters address"
    address_keywords = ['Street', 'St', 'Road', 'Rd', 'Ave', 'Avenue', 'Tokyo', 'Japan', 'Osaka', 'San Jose', 'CA']
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return None
            for result in results:
                snippet = result.get('body', '')
                has_number = any(char.isdigit() for char in snippet)
                has_keyword = any(keyword.lower() in snippet.lower() for keyword in address_keywords)
                if has_number and has_keyword:
                    print(f"(Snippet de endereço encontrado: '{snippet}')")
                    return snippet
            print("(Nenhum snippet de endereço encontrado, retornando o primeiro resultado como fallback.)")
            return results[0].get('body', '')
    except Exception as e:
        print(f"[ERRO DDGS] Falha ao buscar endereço: {e}")
        return None

def extrair_cidade_pais(texto_endereco: str) -> str | None:
    if not texto_endereco:
        return None
        
    padrao = r"([A-Z][a-zA-Z\s-]+,\s*[A-Z][a-zA-Z\s]+)"
    matches = re.findall(padrao, texto_endereco)
    
    if matches:
        return matches[-1].strip()
        
    return None

def find_all_info(part_number: str):
    print(f"--- Iniciando busca APENAS COM DDGS para o Part Number: {part_number} ---")
    
    fabricantes_map = carregar_fabricantes_com_variacoes("fabricantes.txt")
    fabricante = buscar_fabricante_com_pontuacao(part_number, fabricantes_map)

    if fabricante:
        print(f"\n[✓] Nome do fabricante encontrado: {fabricante}")
        endereco_completo = get_address_with_ddg(fabricante)
        
        if endereco_completo:
            print(f"[✓] Snippet de endereço encontrado: {endereco_completo}")
            cidade_pais = extrair_cidade_pais(endereco_completo)
            
            print("\n--- Processo Concluído ---")
            print("\n--- DADOS ESTRUTURADOS ---")
            print(f"Part Number: {part_number}")
            print(f"Fabricante: {fabricante}")
            print(f"Cidade/País: {cidade_pais if cidade_pais else 'Não encontrado'}")
        else:
            print(f"\n[!] Não foi possível encontrar um endereço para '{fabricante}'.")
    else:
        print(f"\n[!] Não foi possível identificar um fabricante para '{part_number}'")

if __name__ == "__main__":
    part_number_exemplo = "CL10C330JB8NNNC"
    
    find_all_info(part_number_exemplo)