# FILENAME: parser copy.py

import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

NSPD_URL = "https://nspd.gov.ru/map"


def start_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1600,900")
    options.add_argument("--ignore-certificate-errors")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    return driver


def open_map(driver):
    print("Открываю карту НСПД...")
    driver.get(NSPD_URL)

    WebDriverWait(driver, 60).until(
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

    time.sleep(8)

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
    Вводит кадастровый номер, кликает по найденному объекту и возвращает URL с selectedCard.
    sidebar_shadow должен быть актуальным для текущего состояния m-sidebar.
    """
    print("L3: ищу m-search-field внутри shadow_root m-sidebar...")
    search_host = WebDriverWait(sidebar_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-search-field"))
    )
    print("L3: m-search-field найден")

    search_shadow = search_host.shadow_root
    print("L4: shadow_root m-search-field получен")

    print("L5: ищу form > label.input-label > input внутри shadow_root m-search-field...")
    search_input = WebDriverWait(search_shadow, timeout).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "form > label.input-label > input")
        )
    )
    print("L5: input найден, ввожу кадастровый номер...")

    search_input.clear()
    search_input.send_keys(cad_num)
    search_input.send_keys(Keys.ENTER)

    print("L6: жду m-found-objects внутри shadow_root m-sidebar...")
    found_host = WebDriverWait(sidebar_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-found-objects"))
    )
    print("L6: m-found-objects найден")

    found_shadow = found_host.shadow_root
    print("L7: shadow_root m-found-objects получен")

    print("L8: ищу m-accordion внутри shadow_root m-found-objects...")
    accordion = WebDriverWait(found_shadow, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "m-accordion"))
    )
    accordion_shadow = accordion.shadow_root
    print("L8: m-accordion найден, shadow_root m-accordion получен")

    print("L9: ищу первый button span внутри shadow_root m-accordion и кликаю...")
    first_item_span = WebDriverWait(accordion_shadow, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button span"))
    )
    first_item_span.click()

    print("L10: клик по результату выполнен, жду selectedCard в URL...")
    WebDriverWait(driver, timeout).until(
        lambda d: "selectedCard=" in d.current_url
    )
    time.sleep(2)

    url = driver.current_url
    print(f"L11: current_url = {url}")
    return url


def click_back_js(driver) -> str:
    """
    Кликает по 'Назад в найденные объекты' через JS:
    берём ПЕРВЫЙ m-typography внутри edit-back-button.shadowRoot и жмём по нему.
    """
    print("JS-BACK: пробую кликнуть 'Назад' через execute_script...")
    script = """
      const sidebar = document.querySelector('m-sidebar');
      if (!sidebar || !sidebar.shadowRoot) return 'no-sidebar';

      const sr = sidebar.shadowRoot;
      const sideDiv = sr.querySelector('div.sidebar.hide');
      if (!sideDiv) return 'no-sidebar-div';

      const selectedPage = sideDiv.querySelector('m-selected-object-page');
      if (!selectedPage) return 'no-selected-page';

      const backHost = selectedPage.querySelector('edit-back-button');
      if (!backHost || !backHost.shadowRoot) return 'no-back-host';

      const backRoot = backHost.shadowRoot;

      const typo = backRoot.querySelector('m-typography');
      if (!typo) return 'no-typography';

      typo.click();
      return 'clicked';
    """
    result = driver.execute_script(script)
    print(f"JS-BACK result: {result}")
    return result


def read_cad_list(path: Path) -> list[str]:
    cad_numbers = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cad_numbers.append(line)
    return cad_numbers


def main():
    cad_file = Path("cad_list.txt")
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
        # 1) Открываем карту один раз
        open_map(driver)

        # 2) Берём sidebar_shadow один раз и дальше переиспользуем
        sidebar_shadow = get_sidebar_shadow(driver)

        first = True

        for cad in cad_numbers:
            print(f"=== Обрабатываю {cad} ===")

            if not first:
                # Возвращаемся со страницы объекта к списку найденных
                res = click_back_js(driver)
                print(f"Результат JS-BACK: {res}")
                # даём UI обновиться
                time.sleep(2)

            # На первом шаге мы уже в состоянии поиска, на последующих — после 'Назад'
            url = search_and_open_card(driver, sidebar_shadow, cad)
            print(f"  OK: {url}")
            results.append({"cad_num": cad, "url": url})

            first = False

        print("Обработка всех кадастровых номеров завершена.")

    finally:
        driver.quit()

    out_path = Path("result.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Готово, записано в {out_path}")


if __name__ == "__main__":
    main()
