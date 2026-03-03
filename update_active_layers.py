# FILENAME: update_active_layers.py

'''
Добавляет параметр layer_value="36048" к каждому url в поле kadastrurl для каждого объекта из polygon.json
'''

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


def add_active_layers_param(url: str, layer_value: str = "36048") -> str:
    if not url:
        return url

    parsed = urlparse(url)
    query = parse_qs(parsed.query, keep_blank_values=True)

    # Обновляем/добавляем параметр
    query["active_layers"] = [layer_value]

    new_query = urlencode(query, doseq=True)
    new_parsed = parsed._replace(query=new_query)
    return urlunparse(new_parsed)


def main():
    polygon_path = Path("polygon.json")
    if not polygon_path.exists():
        print("Файл polygon.json не найден рядом со скриптом")
        return

    with polygon_path.open("r", encoding="utf-8") as f:
        poly = json.load(f)

    items = poly.get("data", [])
    for item in items:
        url = item.get("kadastrurl") or ""
        new_url = add_active_layers_param(url, "36048")
        item["kadastrurl"] = new_url

    with polygon_path.open("w", encoding="utf-8") as f:
        json.dump(poly, f, ensure_ascii=False, indent=2)

    print("Готово: параметр active_layers=36048 добавлен/обновлён во всех kadastrurl")


if __name__ == "__main__":
    main()
