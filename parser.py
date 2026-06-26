# FILENAME: parser.py

import json
import sys
import time
from pathlib import Path
from typing import Any, cast

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

NSPD_URL = "https://nspd.gov.ru/map"
sys.dont_write_bytecode = True


def wait_in(context: Any, timeout: int) -> WebDriverWait:
    return WebDriverWait(cast(Any, context), timeout)


def start_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1600,900")
    options.add_argument("--ignore-certificate-errors")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(120)
    return driver


def open_map(driver):
    print("Открываю карту НСПД...")
    driver.get(NSPD_URL)

    # Ждём базовую загрузку документа
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    page_source = driver.page_source
    if "ERR_CERT" in page_source or "Подключение не защищено" in page_source:
        try:
            details = driver.find_element(By.ID, "details-button")
            details.click()
            time.sleep(1)
            proceed = driver.find_element(By.ID, "proceed-link")
            proceed.click()
        except Exception:
            pass

    # Вместо жёсткого time.sleep(8) — ждём появления m-sidebar
    WebDriverWait(driver, 120).until(
        EC.presence_of_element_located((By.TAG_NAME, "m-sidebar"))
    )

    print("DOM после загрузки:")
    for tag in ["m-sidebar", "m-search-field", "input"]:
        elems = driver.find_elements(By.TAG_NAME, tag)
        print(f"  <{tag}> count = {len(elems)}")

    print("Карта (скорее всего) открыта.")

    print("DOM после загрузки:")
    for tag in ["m-sidebar", "m-search-field", "input"]:
        elems = driver.find_elements(By.TAG_NAME, tag)
        print(f"  <{tag}> count = {len(elems)}")

    print("Карта (скорее всего) открыта.")


def get_sidebar_shadow(driver, timeout: int = 90):
    print("S1: ищу хост m-sidebar в DOM...")
    sidebar_host = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "m-sidebar"))
    )
    print("S1: m-sidebar найден")

    sidebar_shadow = sidebar_host.shadow_root
    print("S2: shadow_root m-sidebar получен")
    return sidebar_shadow


def search_and_open_card(driver, sidebar_shadow, cad_num: str, timeout: int = 90) -> str:
    """
    Стабильный сценарий:
    - вводим КН;
    - кликаем по результату;
    - ждём selectedCard;
    - кликаем по 'Поделиться' через copy-url-control.shadow_root -> m-tooltip -> m-button.shadow_root
      и берём ссылку из popup (input.value).
    """
    print("L3: ищу m-search-field внутри shadow_root m-sidebar...")
    search_host = wait_in(sidebar_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-search-field"))
    )
    print("L3: m-search-field найден")

    search_shadow = search_host.shadow_root
    print("L4: shadow_root m-search-field получен")

    print("L5: ищу form > label.input-label > input внутри shadow_root m-search-field...")
    search_input = wait_in(search_shadow, timeout).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form > label.input-label > input")
        )
    )
    print("L5: input найден, очищаю и ввожу кадастровый номер...")

    search_input.clear()
    search_input.send_keys(cad_num)
    search_input.send_keys(Keys.ENTER)

    print("L6: жду m-found-objects внутри shadow_root m-sidebar...")
    found_host = wait_in(sidebar_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-found-objects"))
    )
    print("L6: m-found-objects найден")

    found_shadow = found_host.shadow_root
    print("L7: shadow_root m-found-objects получен")

    print("L8: ищу m-accordion внутри shadow_root m-found-objects...")
    accordion = wait_in(found_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-accordion"))
    )
    accordion_shadow = accordion.shadow_root
    print("L8: m-accordion найден, shadow_root m-accordion получен")

    print("L9: ищу первый button span внутри shadow_root m-accordion и кликаю...")
    first_item_span = wait_in(accordion_shadow, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button span"))
    )
    first_item_span.click()

    print("L10: клик по результату выполнен, жду selectedCard в URL...")
    WebDriverWait(driver, timeout).until(
        lambda d: "selectedCard=" in d.current_url
    )
    time.sleep(1)

    # ====== БЛОК 'ПОДЕЛИТЬСЯ' (share-ссылка через copy-url-control) ======

    print("L11: ищу host copy-url-control...")
    copy_ctrl_host = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "copy-url-control"))
    )
    print("L11: copy-url-control найден")

    copy_ctrl_shadow = copy_ctrl_host.shadow_root
    print("L11a: shadow_root(copy-url-control) получен")

    # 1) внутри shadow-root: m-tooltip -> m-button.copy-url -> shadow_root -> button (кнопка 'Поделиться')
    tooltip_host = wait_in(copy_ctrl_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-tooltip"))
    )
    print("L11b: m-tooltip найден")

    mbutton_host = WebDriverWait(tooltip_host, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-button.copy-url"))
    )
    print("L11c: m-button.copy-url найден")

    mbutton_shadow = mbutton_host.shadow_root
    print("L11d: shadow_root(m-button.copy-url) получен")

    share_button = wait_in(mbutton_shadow, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.outlined-icon"))
    )
    print("L11e: кнопка 'Поделиться' найдена, кликаю...")
    share_button.click()

    # 2) Ждём появления copy-url-popup внутри того же shadow_root copy-url-control
    print("L12: жду появления copy-url-popup...")
    popup_host = wait_in(copy_ctrl_shadow, timeout).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "copy-url-popup"))
    )
    print("L12a: copy-url-popup найден и видим")

    popup_shadow = popup_host.shadow_root
    print("L12b: shadow_root(copy-url-popup) получен")

    # 3) Внутри popup: input.input с ссылкой
    print("L12c: ищу input.input со ссылкой внутри popup...")
    share_input = wait_in(popup_shadow, timeout).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "div.copy-url-popup label > input.input")
        )
    )
    print("L12d: input.input найден")

    # 4) Кнопка 'Скопировать ссылку' (m-button.popup-button -> shadow_root -> button)
    print("L12e: ищу m-button.popup-button внутри popup...")
    popup_button_host = wait_in(popup_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-button.popup-button"))
    )
    popup_button_shadow = popup_button_host.shadow_root
    print("L12f: shadow_root(m-button.popup-button) получен")

    copy_btn = wait_in(popup_button_shadow, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button.filled"))
    )
    print("L12g: кнопка 'Скопировать ссылку' найдена, кликаю...")
    copy_btn.click()

    # 5) Берём итоговый URL из input.value
    time.sleep(0.2)
    share_url = share_input.get_attribute("value") or ""
    print(f"L13: share_url (из popup input) = {share_url}")

    if not share_url:
        print("L14: share_url пустой, fallback на current_url")
        share_url = driver.current_url

    return share_url


def read_cad_list(path: Path) -> list[str]:
    cad_numbers = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cad_numbers.append(line)
    return cad_numbers


def load_polygon_json(path: Path):
    """
    Читает polygon.json и возвращает (data, cad_numbers),
    где data — полный объект, а cad_numbers — список кадастровых номеров
    в порядке следования в data[]. Если kadastr пустой, такой объект пропускаем.
    """
    with path.open("r", encoding="utf-8") as f:
        poly = json.load(f)

    items = poly.get("data", [])
    cad_numbers = []
    for item in items:
        cad = (item.get("kadastr") or "").strip()
        if cad:
            cad_numbers.append(cad)

    return poly, cad_numbers


def save_polygon_json(path: Path, poly_obj):
    with path.open("w", encoding="utf-8") as f:
        json.dump(poly_obj, f, ensure_ascii=False, indent=2)


def main():
    polygon_path = Path("polygon.json")
    cad_file = Path("cad_list.txt")

    use_polygon = polygon_path.exists()
    cad_numbers: list[str] = []
    poly_obj = None

    if use_polygon:
        print("Найден polygon.json — беру кадастровые номера из него с приоритетом.")
        poly_obj, cad_numbers = load_polygon_json(polygon_path)
        if not cad_numbers:
            print("В polygon.json нет ни одного непустого kadastr — fallback на cad_list.txt.")
            use_polygon = False
    if not use_polygon:
        if not cad_file.exists():
            print("Файл cad_list.txt не найден в корне проекта")
            return
        cad_numbers = read_cad_list(cad_file)
        if not cad_numbers:
            print("Файл cad_list.txt пустой")
            return

    driver = start_driver()
    results = []

    try:
        for cad in cad_numbers:
            print(f"=== Обрабатываю {cad} ===")

            # Стабильная схема: под каждый КН полная перезагрузка карты
            open_map(driver)
            sidebar_shadow = get_sidebar_shadow(driver)

            url = search_and_open_card(driver, sidebar_shadow, cad)
            print(f"  OK (share): {url}")
            results.append({"cad_num": cad, "url": url})

    finally:
        driver.quit()

    if use_polygon:
        # Перезаписываем kadastrurl в polygon.json по совпадению kadastr
        print("Обновляю kadastrurl в polygon.json...")
        url_by_cad = {item["cad_num"]: item["url"] for item in results}
        if poly_obj is None:
            print("polygon.json не был загружен")
            return
        for item in poly_obj.get("data", []):
            cad = (item.get("kadastr") or "").strip()
            if cad and cad in url_by_cad:
                item["kadastrurl"] = url_by_cad[cad]
        save_polygon_json(polygon_path, poly_obj)
        print(f"Готово, обновлён {polygon_path}")
    else:
        out_path = Path("result.json")
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Готово, записано в {out_path}")


if __name__ == "__main__":
    main()
