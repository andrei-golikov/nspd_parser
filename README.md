# FILENAME: README.md

# NSPD Parser

Скрипт `parser.py` автоматизирует получение URL карточек объектов недвижимости на карте НСПД (https://nspd.gov.ru/map) по списку кадастровых номеров.  
Результат — либо JSON‑файл соответствий `кадастровый номер → URL`, либо обновлённый `polygon.json` с заполненными полями `kadastrurl`.

## Возможности

- Открывает карту НСПД в Chrome через Selenium.
- Обходит проблему с сертификатом (страница «Подключение не защищено»).
- Работает в двух режимах входных данных:
  - при наличии `polygon.json` — берёт КН из него и **перезаписывает** поля `kadastrurl`;
  - при отсутствии `polygon.json` — берёт КН из `cad_list.txt` и пишет `result.json`.
- Для каждого кадастрового номера:
  - открывает карту и ждёт появления компонента `m-sidebar` вместо фиксированного таймаута;
  - находит поле «Поиск объектов недвижимости» внутри nested Shadow DOM;
  - вводит номер и запускает поиск;
  - выбирает первый (и единственный) результат в списке найденных объектов;
  - дожидается появления `selectedCard` в URL;
  - нажимает кнопку «Поделиться» в правой панели и получает чистую share‑ссылку из popup;
  - сохраняет итоговый URL.

## Требования

- Python 3.10+ (рекомендуется 3.11).
- Google Chrome (актуальная стабильная версия).
- Установленные пакеты:
  - `selenium`
  - `webdriver-manager`

Установка зависимостей в виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -U pip
pip install selenium webdriver-manager
Входные данные
Вариант 1: polygon.json (приоритетный)
Если в корне проекта есть файл polygon.json, скрипт работает с ним.

Ожидаемая структура (упрощённо):

json
{
  "inc": 256,
  "data": [
    {
      "id": 1,
      "adres": "ул. Предпринимателей, дом 4",
      "idtur": "00424",
      "kadastr": "16:20:050902:424",
      "kadastrurl": "",
      "priority": "1",
      "status": "sale",
      "coordinates": [ ... ]
    },
    {
      "id": 2,
      "adres": "ул. Сююмбике, дом 9",
      "idtur": "00436",
      "kadastr": "16:20:050902:436",
      "kadastrurl": "",
      "priority": "1",
      "status": "sale",
      "coordinates": [ ... ]
    }
  ]
}
Поведение:

Скрипт читает polygon.json.

Собирает список кадастровых номеров из поля kadastr для всех объектов в data, у которых kadastr непустой.

Обрабатывает каждый КН, получая share‑ссылку.

В конце прохода перезаписывает поле kadastrurl для соответствующих объектов и сохраняет обновлённый polygon.json.

Вариант 2: cad_list.txt (fallback)
Если polygon.json отсутствует или в нём нет ни одного непустого kadastr, скрипт работает как раньше — читает cad_list.txt.

Файл cad_list.txt в корне проекта, каждая строка — один кадастровый номер, без лишних пробелов и разделителей, например:

text
58:24:0381401:620
58:24:0381401:342
Пустые строки игнорируются.

Выходные данные
Если используется polygon.json
Обновляется существующий polygon.json.

Для каждого объекта в data, чей kadastr был успешно обработан, поле kadastrurl получает итоговую share‑ссылку, например:

json
{
  "id": 1,
  "kadastr": "16:20:050902:424",
  "kadastrurl": "https://nspd.gov.ru/map?zoom=...&coordinate_x=...&coordinate_y=...&baseLayerId=...&theme_id=1&is_copy_url=true&selectedCard=...",
  ...
}
Если используется cad_list.txt
После завершения работы создаётся файл result.json следующего вида:

json
[
  {
    "cad_num": "58:24:0381401:620",
    "url": "https://nspd.gov.ru/map?...&selectedCard=..."
  },
  {
    "cad_num": "58:24:0381401:342",
    "url": "https://nspd.gov.ru/map?...&selectedCard=..."
  }
]
При ошибке для конкретного номера (элемент не найден, таймаут и т.п.) в result.json для него может быть записан "url": null (если вы добавите такую обработку).

Как работает скрипт
1. Запуск браузера
Функция start_driver():

поднимает Chrome через webdriver-manager;

настраивает окно (--window-size=1600,900);

выключает GPU и sandbox;

добавляет флаг --ignore-certificate-errors для игнорирования проблем с сертификатом на НСПД;

задаёт page_load_timeout(60).

2. Открытие карты НСПД
Функция open_map(driver):

переходит по адресу https://nspd.gov.ru/map;

ждёт появления тега <body>;

если браузер показал страницу с ошибкой сертификата, автоматически нажимает «Дополнительно» → «Перейти»;

вместо жёсткого time.sleep(8) ждёт появления компонента <m-sidebar> в DOM через WebDriverWait;

для диагностики выводит в консоль количество найденных элементов <m-sidebar>, <m-search-field> и <input>.

open_map(driver) вызывается перед каждым кадастровым номером — карта заново загружается для каждого объекта. Это гарантирует стабильное состояние интерфейса, но замедляет работу.

3. Поиск и выбор участка + share‑ссылка
Функция search_and_open_card(driver, sidebar_shadow, cad_num, timeout=90) делает основную работу:

получает shadow_root m-sidebar;

внутри shadow_root m-sidebar находит m-search-field и его shadow_root;

в shadow_root m-search-field ищет form > label.input-label > input — поле «Поиск объектов недвижимости»;

очищает поле, вводит кадастровый номер и нажимает Enter;

в shadow_root m-sidebar ждёт появления m-found-objects и берёт его shadow_root;

внутри shadow_root m-found-objects находит m-accordion и его shadow_root;

в shadow_root m-accordion выбирает первый button span (единственный результат) и кликает по нему;

ждёт, пока в driver.current_url появится параметр selectedCard=...;

после загрузки карточки:

находит компонент copy-url-control в основном DOM;

заходит в его shadow_root;

через цепочку m-tooltip → m-button.copy-url → shadow_root → button нажимает кнопку «Поделиться»;

ждёт появления copy-url-popup, заходит в его shadow_root;

находит input.input с готовой ссылкой;

находит m-button.popup-button → shadow_root → button и нажимает «Скопировать ссылку»;

читает итоговый URL из input.value и возвращает его.

Работа с Shadow DOM выполняется через свойство element.shadow_root (Selenium 4).

4. Основной цикл
Функция main():

