# Polish Shipment Tracking

English version: [README_EN.md](README_EN.md)

![Shipment Tracking card](images/screenshot.png)


[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

Integracja dla Home Assistant do śledzenia przesyłek u popularnych przewoźników w Polsce. Tworzy encje sensor dla aktywnych przesyłek oraz zawiera kartę Lovelace z listą przesyłek.

## Funkcje

- Obsługa wielu przewoźników w jednej integracji (Config Flow)
- Encje sensor dla aktywnych przesyłek
- Normalizacja statusów na wspólny zestaw stanów
- Automatyczne wykrywanie nowych przesyłek oraz sprzątanie starych encji
- Wbudowana karta Lovelace:
  - serwowana przez integrację
  - automatyczna rejestracja zasobu w dashboardach w trybie storage

> [!TIP]
> Możesz dodać wiele kont / numerów dla tego samego przewoźnika (np. dla dwóch osób) – dotyczy to wszystkich przewoźników, szczegóły w sekcji [Wiele kont u jednego przewoźnika](#wiele-kont-u-jednego-przewoźnika).

## Wspierani przewoźnicy

| Przewoźnik | Logowanie | Wiele kont | Konto rozróżniane po |
|---|---|:---:|---|
| InPost | numer telefonu + kod SMS | ✅ | numerze telefonu |
| DPD | numer telefonu + kod SMS | ✅ | numerze telefonu |
| DHL | numer telefonu + kod SMS | ✅ | numerze telefonu |
| Pocztex (Poczta Polska) | e-mail + hasło | ✅ | adresie e-mail |
| GLS | numer telefonu + hasło do konta myGLS | ✅ | numerze telefonu |
| Allegro | ciasteczko sesji `QXLSESSID` + kontekst konta (prywatne / firmowe) | ✅ | ciasteczku i kontekście (opcjonalna własna etykieta) |
| UPS | wklejone „Copy as cURL” żądania `GetIncomingShipments` z pulpitu ups.com | ✅ | wklejonej sesji |

### Wiele kont u jednego przewoźnika

Każdy przewoźnik obsługuje wiele kont – dodaj integrację ponownie i wybierz tego samego przewoźnika z innymi danymi logowania (np. numery telefonów dwóch osób). Każde konto to osobny wpis z własnymi encjami; atrybut `account_contact` sensora mówi, do którego konta należy przesyłka.

| Przewoźnik | Jak działa wiele kont |
|---|---|
| InPost | Przesyłka udostępniona między Twoimi własnymi kontami pojawia się tylko raz (u właściciela). Przesyłki udostępnione przez osoby spoza integracji są nadal widoczne. |
| DPD, Pocztex | Konta są niezależne – każde ma własny token. |
| DHL, GLS | Każde konto ma własną, odizolowaną sesję, więc ciasteczka kont nie mieszają się ze sobą. |
| Allegro | Jeden wpis na ciasteczko i kontekst. To samo logowanie możesz dodać dwa razy: jako konto prywatne i jako Allegro Biznes. |
| UPS | Jeden wpis na wklejoną sesję przeglądarki. |

Uwagi:

- **Allegro** zwraca tylko aktywne przesyłki. Przesyłka śledzona już przez konto właściwego przewoźnika (np. InPost lub DHL) nie jest dublowana. Po wygaśnięciu ciasteczka wpis trzeba dodać ponownie.
- **UPS** nie ma logowania w integracji – sesja jest przejmowana z przeglądarki i podtrzymywana przez cykliczne odpytywanie.

> [!WARNING]
> Integracja korzysta z nieoficjalnych API aplikacji/serwisów przewoźników. Te API mogą ulec zmianie bez uprzedzenia.

> [!CAUTION]
> Nie ponoszę odpowiedzialności za ewentualne blokady lub ograniczenia konta przez przewoźnika.


## Wymagania

- Home Assistant: 2024.6 lub nowszy
- (Opcjonalnie) HACS: 1.30 lub nowszy

## Instalacja

### Instalacja przez HACS (zalecane)

1. Otwórz HACS -> Integrations.
2. Dodaj repo jako Custom repository:
   - Repository: https://github.com/radzio/polish_shipment_tracking
   - Category: Integration
3. Zainstaluj integrację.
4. Zrestartuj Home Assistant.

### Instalacja ręczna

1. Skopiuj katalog `custom_components/polish_shipment_tracking` do:
   `<config>/custom_components/polish_shipment_tracking`
2. Zrestartuj Home Assistant.

## Konfiguracja

1. Ustawienia -> Urządzenia i usługi -> Dodaj integrację
2. Wyszukaj "Polish Shipment Tracking"
3. Wybierz przewoźnika i uzupełnij wymagane dane logowania
4. Zapisz

Po pierwszym odświeżeniu powinny pojawić się encje `sensor` dla przesyłek.

## Encje

Integracja tworzy encję `sensor` dla każdej aktywnej (niedostarczonej) przesyłki.

- atrybut `delivery_type`: dokąd trafia przesyłka – `home` (pod adres), `parcel_locker` (automat paczkowy), `pickup_point` (punkt odbioru) albo `unknown`; te same wartości dla każdego przewoźnika
- unique_id: `<courier>_<shipment_id>`
- stan sensora: status znormalizowany (np. in_transport)
- atrybuty: zależnie od przewoźnika, przykładowo:
  - numer przesyłki
  - status surowy
  - historia zdarzeń
  - daty zdarzeń
  - informacje o punkcie odbioru




## Ignorowanie przesyłek

Przesyłkę, która nigdy nie dotrze (np. nadawca wygenerował nową etykietę, a stara została w systemie przewoźnika), można ukryć. Działa to dla wszystkich przewoźników.

- **Z karty:** otwórz szczegóły przesyłki i kliknij ikonę przekreślonego oka w nagłówku, a następnie kliknij ją ponownie, aby potwierdzić.
- **Akcją:** `polish_shipment_tracking.ignore_shipment` z polem `tracking_number`.

Zignorowana przesyłka znika ze wszystkich kont (także jej kopia z Allegro) i nie wraca po restarcie. Lista zignorowanych przesyłek jest w atrybucie `ignored_shipments` sensora „Aktywne przesyłki”.

Aby przywrócić przesyłkę, wywołaj `polish_shipment_tracking.unignore_shipment` z tym samym `tracking_number`. Wpis znika z listy sam: gdy konto, które zwracało przesyłkę, przestaje ją zwracać, wpis jest usuwany po 24 godzinach (zwłoka chroni przed chwilowo pustą odpowiedzią przewoźnika).

## Zdarzenia (custom events)

Integracja publikuje zdarzenia na magistrali `hass.bus`:

- `polish_shipment_tracking_new_shipment` - nowa przesyłka
- `polish_shipment_tracking_shipment_status_changed` - przesyłka zmieniła stan

Przykładowy payload:

```json
{
  "courier": "inpost",
  "shipment_id": "1234567890",
  "entity_id": "sensor.inpost_paczka_1234567890",
  "status_raw": "in_transit",
  "status_key": "in_transport"
}
```

Dla `polish_shipment_tracking_shipment_status_changed` dodatkowo występują pola:

- `old_status_raw`
- `old_status_key`
- `new_status_raw`
- `new_status_key`

## Statusy (normalizacja)

Różne nazwy statusów przewoźników są mapowane do wspólnego zestawu. Przykładowo:
- created
- in_transport
- waiting_for_pickup
- delivered
- exception
- cancelled
- returned
- unknown

> [!NOTE]
> Mapowanie statusów nie jest jeszcze kompletne; PR-y z nowymi mapowaniami są mile widziane.

Dokładne mapowania są w kodzie integracji (sensor.py).

## Karta Lovelace


Integracja zawiera kartę Lovelace (JavaScript module) i automatycznie dodaje ją jako zasób w dashboardach.

## Debugowanie

Możesz włączyć debug logi dla integracji:

```yaml
logger:
  default: info
  logs:
    custom_components.polish_shipment_tracking: debug
```

## Znane problemy

* Zmiany po stronie przewoźników (API, autoryzacja, limity) mogą powodować błędy logowania lub pobierania przesyłek.

## Zgłoszenia błędów i wsparcie

* Issues: [https://github.com/radzio/polish_shipment_tracking/issues](https://github.com/radzio/polish_shipment_tracking/issues)
* Pull requests: mile widziane

W zgłoszeniu błędu dołącz:

* wersję Home Assistant
* logi (z włączonym debug dla integracji)
* wybranego przewoźnika
* opis kroków odtworzenia

## Licencja

GNU General Public License v3.0. Zobacz plik LICENSE.
