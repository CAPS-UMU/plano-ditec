#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import sys

API_URL = (
    'https://telematica.um.es/fichas/api/query/users/'
    '?UNIDADES=a002b031&FILIACION=a004|a007&limit=200'
)

DESPACHO_REGEX = re.compile(r'B1\.3\.\d+')

def fetch_personnel():
    """Recupera la lista de personal desde la API JSON."""
    r = requests.get(API_URL)
    r.raise_for_status()
    return r.json().get('data', [])

def extract_despacho(html):
    """
    Busca el código de despacho en el HTML:
      - Primero intenta la fila 'Despacho: ... >B1.3.XXX<'
      - Si falla, busca cualquier patrón B1.3.xxx
      - Si no hay nada, devuelve 'B1.3.XXX'
    """
    m = re.search(r'Despacho:.*?>(B1\.3\.\d+)<', html, re.S)
    if m:
        return m.group(1)
    m = DESPACHO_REGEX.search(html)
    return m.group(0) if m else 'B1.3.XXX'

def main(output_prefix='despachos'):
    people = fetch_personnel()
    records = []

    for p in people:
        name = p.get('cn','').strip()
        mails = p.get('mail') or []
        if not name or not mails:
            continue  # saltamos si falta nombre o mail

        email = mails[0]
        url = (
            'https://www.um.es/atica/directorio/'
            '?usuario=&lang=0&vista=unidades&search=$' + email
        )

        try:
            resp = requests.get(url)
            resp.raise_for_status()
            despacho = extract_despacho(resp.text)
        except Exception as e:
            print(f"[!] Error al descargar {url}: {e}", file=sys.stderr)
            despacho = 'B1.3.XXX'

        records.append((name, despacho))

    # ordenar por nombre (insensible a mayúsculas)
    records.sort(key=lambda x: x[0].lower())

    # 1) Tab-separated text
    txt_path = f'{output_prefix}.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        for name, despacho in records:
            f.write(f"{name}\t{despacho}\n")

    # 2) Markdown
    md_path = f'{output_prefix}.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('| Nombre | Despacho |\n')
        f.write('|--------|----------|\n')
        for name, despacho in records:
            f.write(f'| {name} | {despacho} |\n')

    # 3) CSV
    csv_path = f'{output_prefix}.csv'
    with open(csv_path, 'w', encoding='utf-8') as f:
        f.write('Nombre,Despacho\n')
        for name, despacho in records:
            safe_name = name.replace('"','""')
            f.write(f'"{safe_name}",{despacho}\n')

    print(f"Generados:\n - {txt_path}\n - {md_path}\n - {csv_path}")

if __name__ == '__main__':
    main()
