import json
import re
import time
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# Domínios que costumamos ignorar (distribuidores, vídeo, marketplaces)
BLACKLIST_HOSTS = {
    "youtube.com", "youtu.be", "digikey.com", "mouser.com", "arrow.com",
    "rs-online.com", "aliexpress.com", "amazon.com", "ebay.com",
    "wikipedia.org"
}

# Palavras que indicam páginas de distribuidor (evitar como fabricante)
BLACKLIST_TOKENS = {"digi-key", "digikey", "mouser", "arrow", "rs components", "rs-online", "distributor"}

# Padrão simples para detectar nomes óbvios de PN no título (para remover)
def remove_part_from_title(title: str, pn: str) -> str:
    return title.replace(pn, "").strip()

def host_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""

def looks_like_distributor(host: str, title: str) -> bool:
    host = host.lower()
    if any(b in host for b in BLACKLIST_HOSTS):
        return True
    title_low = title.lower()
    if any(tok in title_low for tok in BLACKLIST_TOKENS):
        return True
    return False

def extract_jsonld_from_html(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    scripts = soup.find_all("script", type="application/ld+json")
    objs = []
    for s in scripts:
        text = s.string
        if not text:
            continue
        # Alguns sites colocam vários JSONs na mesma tag -> tentar carregar safe
        try:
            data = json.loads(text)
            objs.append(data)
        except Exception:
            # tentar "multidoc" separado por '}{'
            try:
                parts = re.split(r'\}\s*\{', text)
                for i, p in enumerate(parts):
                    if i == 0:
                        p2 = p + "}"
                    elif i == len(parts) - 1:
                        p2 = "{" + p
                    else:
                        p2 = "{" + p + "}"
                    objs.append(json.loads(p2))
            except Exception:
                continue
    return objs

def parse_manufacturer_and_address_from_jsonld(objs: list) -> tuple[Optional[str], Optional[str]]:
    # procura por Product.manufacturer ou Organization
    for obj in objs:
        # Normaliza lista / dict
        candidates = [obj] if isinstance(obj, dict) else list(obj)
        for c in candidates:
            if not isinstance(c, dict):
                continue
            t = c.get("@type") or c.get("type")
            if isinstance(t, list):
                t = t[0]
            if not t:
                # examina keys for nested product
                pass
            if t and t.lower() in ("product", "productinformation"):
                manufacturer = c.get("manufacturer") or c.get("brand")
                if isinstance(manufacturer, dict):
                    name = manufacturer.get("name")
                    # try address in same doc
                    addr = manufacturer.get("address") or c.get("manufacturer", {}).get("address")
                    addr_str = None
                    if isinstance(addr, dict):
                        # montar string simples
                        addr_str = ", ".join(filter(None, [
                            addr.get("streetAddress"),
                            addr.get("addressLocality"),
                            addr.get("addressRegion"),
                            addr.get("postalCode"),
                            addr.get("addressCountry")
                        ]))
                    return (name, addr_str)
            if t and t.lower() in ("organization", "company"):
                name = c.get("name")
                addr = c.get("address")
                addr_str = None
                if isinstance(addr, dict):
                    addr_str = ", ".join(filter(None, [
                        addr.get("streetAddress"),
                        addr.get("addressLocality"),
                        addr.get("addressRegion"),
                        addr.get("postalCode"),
                        addr.get("addressCountry")
                    ]))
                elif isinstance(addr, str):
                    addr_str = addr
                return (name, addr_str)
    return (None, None)

def fetch_page(url: str, timeout=8) -> Optional[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def find_manufacturer_with_ddgs_and_html(part_number: str, max_results=8):
    print(f"[START] Buscando candidatos DDG para PN={part_number}")
    query = f'"{part_number}"'
    candidates = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            title = r.get("title", "")
            url = r.get("url") or r.get("link") or ""
            host = host_from_url(url).lower()
            if not url:
                continue
            if looks_like_distributor(host, title):
                # skip distributors as first pass
                print(f"  - Pulando (distribuidor/social): {host} | {title}")
                continue
            candidates.append((title, url, host))

    # fallback: if nenhum candidato filtrado, usar os top results (até max_results) ignorando blacklist
    if not candidates:
        print("  - Nenhum candidato limpo encontrado. Fazendo fallback com top results (ignorar blacklist).")
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "")
                url = r.get("url") or r.get("link") or ""
                host = host_from_url(url).lower()
                if url:
                    candidates.append((title, url, host))

    # iterar candidatos e buscar JSON-LD / meta
    for title, url, host in candidates:
        print(f"  - Testando {host} -> {url}")
        html = fetch_page(url)
        if not html:
            print("    (falha ao baixar a página)")
            continue
        objs = extract_jsonld_from_html(html)
        name, address = parse_manufacturer_and_address_from_jsonld(objs)
        # heurística: se name vazio, tentar extrair via meta tags ou título
        if not name:
            soup = BeautifulSoup(html, "html.parser")
            # procurar meta property or og
            name = soup.find("meta", property="og:site_name") or soup.find("meta", property="og:brand")
            if name and name.get("content"):
                name = name.get("content")
            else:
                name = soup.find("meta", attrs={"name": "publisher"})
                name = name.get("content") if name and name.get("content") else None
        # Se ainda nada, tentar extrair do título (pior caso)
        if not name:
            cleaned_title = remove_part_from_title(title or "", part_number)
            # pegar primeiro chunk antes de "|" ou "-" ou "by"
            cleaned_title = re.split(r'\||\-|by', cleaned_title, flags=re.I)[0].strip()
            # evitar retornar palavras genéricas
            if cleaned_title and cleaned_title.lower() not in BLACKLIST_TOKENS:
                name = cleaned_title
        if name:
            # validar nome (evitar strings curtas/so 'home')
            if len(name) < 2:
                continue
            # retorne ao primeiro que tenha plausibilidade
            return {"part_number": part_number, "manufacturer_name": name.strip(), "manufacturer_address": address}
        # pequeno delay para não parecer bot
        time.sleep(0.5)
    return None

# Exemplo de uso
if __name__ == "__main__":
    pn = "CL10C330JB8NNNC"
    info = find_manufacturer_with_ddgs_and_html(pn)
    print("RESULT:", info)