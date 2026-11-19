# Ursus – inwestycje – instrukcja dla Vibe CLI

Dokument opisuje comiesięczne zadanie tworzenia podsumowania inwestycji dzielnicy Ursus (Warszawa) i zapisywania go jako dokument Google Drive. Zawiera oryginalny prompt użytkownika oraz sprawdzoną procedurę wykonania wraz z napotkanymi problemami i obejściami.

## 1. Cel i harmonogram

Zadanie uruchamiane jest 1. dnia każdego miesiąca. Podsumowanie dotyczy poprzedniego miesiąca: jeśli uruchamiamy je 1 grudnia, powstaje podsumowanie listopada, obejmujące newsy z całego listopada oraz wydarzenia z grudnia (czyli miesiąca następnego, żeby można było jeszcze na nie przyjść).

Wynik: dokument Google Drive o nazwie „Ursus - inwestycje - $miesiąc $rok” (np. „Ursus - inwestycje - listopad 2026”), w formacie możliwie wiernie odwzorowującym szablon zielonyursus.pl.

## 2. Oryginalny prompt użytkownika

Potrzebuję 1 dnia każdego miesiąca odpalać następujące zadanie.

Przygotowanie: Wejdź na stronę zielonyursus.pl i przeczytaj podsumowania inwestycji żeby wytworzyć sobie wzorzec.

Następnie odwiedź następujące strony na Facebooku: facebook.com/dzielnicaursus, facebook.com/zielonyursus, facebook.com/sowursusie, facebook.com/kdauksz. Sprawdź ich zawartość z ostatniego miesiąca. Wybierz tematy, które potencjalnie mogą pasować do profilu podsumowania inwestycji – rozstrzygnięte przetargi, budowy, podpisane umowy.

Następnie wejdź w wątek: skyscrapercity.com/threads/ursus-inwestycje.495227/ i zrób to samo.

Następnie wejdź na stronę: ursus.um.warszawa.pl/-/wykazy-za-rok-2026, pobierz pliki i zrób to samo.

Następnie wejdź na stronę: bip.warszawa.pl/web/ursus/interpelacje-zapytania-szukaj i wyszukaj interpelacje, zapytania i wnioski z ostatniego miesiąca. Podsumuj je zgodnie ze wzorem, sformatuj tekst w ten sposób, żeby tytuły interpelacji były jednocześnie linkami do poszczególnych stron w BIP.

Do działu Wydarzenia użyj tej strony: zielonyursus.pl/pchlitarg/ oraz ewentualnych wydarzeń ze strony urzędu dzielnicy Ursus – ale pamiętaj, wydarzenia muszą być na następny miesiąc, żeby można było jeszcze na nie przyjść. W podsumowaniu listopada robimy wydarzenia grudniowe.

Utwórz na moim drive plik – „Ursus - inwestycje - $miesiąc $rok”. Zamieść w nim krótkie streszczenie każdej z informacji którą znalazłeś wraz z linkiem do źródła. Postaraj się odwzorować szablon jak najwierniej umiesz. Jeżeli nie wiesz do którego obszaru (Skorosze/Szamoty itd) przynależy informacja, zamieść ją w ogólnych.

## 3. Wzorzec redakcyjny

Szablon zielonyursus.pl ma stałą strukturę. Odwzoruj ją dokładnie:

Nagłówek: „Ursus – inwestycje – $miesiąc $rok” (H1), pod nim krótkie zaproszenie do lektury (2–3 zdania).

Sekcje (H2), w tej kolejności: 🟢 CZECHOWICE 🟢, 🟢 SKOROSZE 🟢, 🟢 GOŁĄBKI 🟢, 🟢 NIEDŹWIADEK 🟢, 🟢 SZAMOTY 🟢, 🟢 WYDARZENIA 🟢, 🟢 OGÓLNE 🟢, 🟢 PRACA RADNYCH 🟢.

Wpis: pogrubiony tytuł poprzedzony strzałką „👉”, w nowej linii 2–5 zdań streszczenia, na końcu link(i) do źródła jako słowo „źródło” (lub „FB”, „źródło (13.11)”).

Odstęp między punktami. Każdy wpis to osobny akapit z odstępem dolnym (padding-bottom ok. 11 pt) — dokładnie tak, jak w dokumencie „Ursus - inwestycje - listopad 2026”. Bez tego tekst skleja się w jedną ścianę i nie da się go czytać.

Przypisanie do sekcji: jeśli nie wiesz, do którego obszaru należy informacja, wrzuć ją do OGÓLNE. Nie twórz nowych sekcji.

Wydarzenia: wyłącznie z następnego miesiąca, z datą i godziną w tytule wpisu.

Praca radnych — tylko klub Bezpieczny i Zielony Ursus (BiZU). Uwzględniamy wyłącznie radnych: Krzysztof Daukszewicz, Karol Bąkowski, Karolina Sowińska. Interpelacje, zapytania i wnioski radnych Koalicji Obywatelskiej, Stowarzyszenia Obywatelskiego w Ursusie i Prawa i Sprawiedliwości pomijamy — nawet jeśli są najnowsze i tematycznie pasują. Tytuł interpelacji jest jednocześnie linkiem do jej strony w BIP. Grupuj po radnym.

## 4. Procedura wykonania – krok po kroku

Krok 1. Wzorzec. Wejdź na zielonyursus.pl i przeczytaj 2–3 ostatnie podsumowania inwestycji. Zapisz sobie strukturę i styl (krótkie zdania, konkretne kwoty, nazwy wykonawców, terminy).

Krok 2. Facebook – tylko przez Apify. Facebook nie udostępnia publicznego API, a wyszukiwarki zwracają jedynie fragmenty. Używaj aktora apify/facebook-posts-scraper (NIE facebook-pages-scraper – zwraca tylko metadane strony; NIE web-scraper – wymaga zatwierdzenia pełnych uprawnień).

Input: {"startUrls":[{"url":"https://www.facebook.com/dzielnicaursus"}],"resultsLimit":40,"onlyPostsNewerThan":"RRRR-MM-01"}. Powtórz dla czterech profili: dzielnicaursus, zielonyursus, sowursusie, kdauksz. Token API i szczegóły w sekcji 6.

Krok 3. SkyscraperCity. Wątek skyscrapercity.com/threads/ursus-inwestycje.495227/ ma kilkaset stron – czytaj ostatnie 3–5 stron (numery stron w URL). Najlepiej przez aktora apify/website-content-crawler. Uwaga: część stron zwraca 429 lub challenge JS – wtedy ponów próbę lub poprzestań na stronach, które się pobrały, i zaznacz to w podsumowaniu.

Linkowanie forum. Wpis oparty na forum musi linkować do konkretnej strony wątku (…/ursus-inwestycje.495227/page-N), a nie do strony głównej ani do przypadkowego posta na FB. W przebiegu próbnym zdarzyło się, że wpisy z forum dostały linki do Facebooka — tak nie robimy.

Krok 4. Wykazy z urzędu dzielnicy. Strona ursus.um.warszawa.pl/-/wykazy-za-rok-2026 zawiera 8 plików XLSX hostowanych na cdn.um.warszawa.pl: rejestry decyzji WZ, PnB, LCP i ZRID oraz rejestry wniosków o WZ, wniosków o PnB, wniosków LCP i zgłoszeń robót budowlanych. Pobierz wszystkie osiem i przeszukaj pod kątem dat z opisywanego miesiąca. Pliki parsuj przez zipfile + XML (openpyxl/pandas mogą nie być dostępne).

Dwa formaty dat w jednym zestawie. W rejestrach decyzji (WZ, PnB, LCP, ZRID) data jest tekstem w kolumnie z numerem decyzji, np. „79/URS/WZ/2026/O z 21.10.2026” — wyciągaj ją regexem \d{2}\.\d{2}\.\d{4}. W rejestrach wniosków i zgłoszeń daty to numery seryjne Excela — konwertuj przez 1899-12-30 + liczba dni. Jeśli zastosujesz tylko jedną metodę, połowa plików wygląda na pustą.

Świeżość plików. Rejestry są odświeżane nieregularnie, mniej więcej raz w miesiącu. Datę publikacji znajdziesz w parametrze t= w adresie pliku (unix ms). Przykład z listopada 2026: pliki miały t= z 30.10.2026, a najnowszy wpis pochodził z 21.10.2026 — dane były opóźnione o blisko trzy tygodnie. Zanim napiszesz „brak danych”, sprawdź t= i podaj, na jaki dzień rejestr jest aktualny.

Profil treści. Decyzje WZ i PnB to w praktyce budownictwo jednorodzinne od osób fizycznych — do podsumowania inwestycji trafia rzadko. Najbardziej „inwestycyjne” są ZRID (drogi) i LCP (sieci i infrastruktura).

Krok 5. BIP – interpelacje. Strona bip.warszawa.pl/web/ursus/interpelacje-zapytania-szukaj wymaga nagłówka przeglądarki (User-Agent Chrome), inaczej zwraca pustą stronę. Lista pokazuje tylko 10 najnowszych pozycji – jeśli w miesiącu było ich więcej, filtruj po dacie publikacji. Zbierz: typ, numer, datę, temat, radnego, klub, treść odpowiedzi, URL.

Filtr klubu. Do podsumowania trafiają wyłącznie wystąpienia radnych BiZU (Daukszewicz, Bąkowski, Sowińska). Klub odczytaj z BIP albo z bazy interpelacji (pole „klub”); nie zgaduj po nazwisku.

Krok 6. Wydarzenia. Źródła: zielonyursus.pl/pchlitarg/ oraz aktualności urzędu dzielnicy (ursus.um.warszawa.pl). Filtruj wyłącznie wydarzenia z następnego miesiąca. Uważaj na daty z fragmentów wyszukiwarek – weryfikuj na stronie źródłowej.

Krok 7. Selekcja. Z całego zebranego materiału wybierz tematy pasujące do profilu podsumowania inwestycji: rozstrzygnięte przetargi, podpisane umowy, postępy budów, decyzje administracyjne, zmiany budżetowe, planowane inwestycje. Pomiń politykę, imprezy sportowe, konkursy, ciekawostki.

Krok 8. Redakcja. Napisz podsumowanie w HTML według wzorca z sekcji 3. Każdy wpis musi mieć działający link do źródła. Linki do postów FB buduj z pola url zwróconego przez Apify.

Krok 9. Zapis na Drive. Utwórz dokument Google (nie plik HTML – inaczej linki i nagłówki nie będą edytowalne):

1) create_file z content_mime_type: "application/vnd.google-apps.document" i tytułem „Ursus - inwestycje - $miesiąc $rok” (pusty dokument).
2) update_file z file_id z kroku 1, text_content = HTML podsumowania, content_mime_type: "text/html".
3) Zweryfikuj: download_file_content z export_mime_type: "text/html" (wynik jest base64) – sprawdź, że liczba href zgadza się z liczbą źródeł.

## 5. Środowisko i pułapki techniczne

PowerShell psuje polskie znaki i nie ma heredoców. Wszystkie skrypty parsujące pisz jako pliki .py przez write_file, wyniki zapisuj do plików JSON/TXT i czytaj przez read_file. Nie przekazuj polskiego tekstu przez argumenty linii poleceń.

Nie zgaduj dat. Wiele artykułów wraca w wynikach wyszukiwania mimo że pochodzi z wcześniejszych miesięcy. Zawsze sprawdź datę publikacji na stronie źródłowej. Przykład z przebiegu próbnego: artykuły o przetargu na prace przedprojektowe metra M2 do Ursusa pochodziły z czerwca 2026, nie z listopada – zostały pominięte.

Brak danych to też informacja. Jeśli w danym źródle nie ma wpisów z opisywanego miesiąca, napisz to wprost w odpowiedniej sekcji (np. „W okresie 1–19 listopada nie opublikowano nowych interpelacji. Ostatnie wpisy:”) i podaj najnowsze dostępne pozycje z linkami.

## 6. Konfiguracja Apify

Konto: temperate_velveteen (plan FREE). Token API: wyłącznie ze zmiennej środowiskowej APIFY_TOKEN — nigdy nie zapisuj tokena w tej instrukcji, w promptach ani w plikach (stary token z obiegu został unieważniony; nowy wygeneruj w konsoli Apify i ustaw jako APIFY_TOKEN dla procesu Vibe). Jeśli APIFY_TOKEN jest niedostępny: pomiń źródło Facebook-Apify, użyj czytnika r.jina.ai (odstęp min. 20 s między zapytaniami, ponawiaj przy 429/ścianie logowania) i wyraźnie zaznacz to ograniczenie w dokumencie.

Wywołanie: POST https://api.apify.com/v2/acts/apify~facebook-posts-scraper/run-sync-get-dataset-items?token=$APIFY_TOKEN z ciałem JSON opisanym w kroku 2. Zwracane pola: time, pageName, text, url.

## 7. Checklist przed publikacją

☐ Wszystkie 8 sekcji obecnych, w właściwej kolejności.
☐ Każdy wpis ma link do źródła; linki działają.
☐ Każdy wpis jest osobnym akapitem z odstępem dolnym — nic się nie skleja.
☐ Wydarzenia wyłącznie z następnego miesiąca, z datą i godziną.
☐ Interpelacje: tylko radni BiZU, tytuł = link do BIP, pogrupowane po radnym.
☐ Wpisy z forum linkują do konkretnej strony wątku na SkyscraperCity.
☐ Sprawdzono parametr t= w adresach plików XLSX — wiadomo, na jaki dzień rejestry są aktualne.
☐ Informacje o niepewnej lokalizacji w sekcji OGÓLNE.
☐ Nazwa pliku: „Ursus - inwestycje - $miesiąc $rok” (miesiąc małą literą, po polsku).
☐ Dokument na Drive jest typu Google Doc, nie HTML.
☐ Liczba linków w dokumencie zgadza się z liczbą źródeł w materiale.

## 8. Uwagi z przebiegu próbnego (listopad 2026)

Przebieg próbny objął okres 1–19 listopada 2026 (nie cały miesiąc) i wydarzenia grudniowe. Napotkane sytuacje:

• Facebook: 72 posty z czterech profili (dzielnicaursus 40, zielonyursus 14, kdauksz 10, sowursusie 8). Actor facebook-pages-scraper zwrócił tylko metadane – bezużyteczny.
• SkyscraperCity: strony 427–428 nie pobrały się (challenge JS), strona 429 pobrała się poprawnie. Treść to głównie dyskusje — do podsumowania trafiły wątki o Giserskiej/Hennela, skwerze przy Apartamentowej, szkole Ronson i ul. Meyera. W pierwszej wersji dokumentu żaden z tych wpisów nie linkował do forum (0 z 36 linków); poprawiono ręcznie, dodając 3 linki do strony 429.
• BIP: brak interpelacji z listopada; 10 najnowszych wpisów (nr 630–634, zapytania 230–234) pochodzi z 29–30 października i zostało opublikowanych 4 listopada. W dokumencie listopadowym znaleźli się też radni spoza BiZU (Dratkiewicz – PiS) – w kolejnych edycjach odpada.
• Wykazy XLSX: 8 plików, od 3 pozycji (ZRID) do 94 (decyzje PnB). Najnowszy wpis 21.10.2026 — WZ 79/URS/WZ/2026/O, Kompanii AK „Kordian”, decyzja odmowna. Pliki opublikowane 30.10.2026, więc zero wpisów listopadowych. Rejestry decyzji trzymają daty jako tekst, rejestry wniosków i zgłoszeń jako numery seryjne Excela.
• Jarmark Świąteczny: potwierdzony na 5–6 grudnia, 12:00–19:00, Park Czechowicki. Wcześniejszy fragment z wyszukiwarki podawał błędnie 12–14 grudnia – dlatego weryfikacja u źródła jest obowiązkowa.
• Komisje dzielnicy: protokoły z zielonyursus.pl (np. komisja gospodarki przestrzennej i oświaty 16 listopada) są najlepszym źródłem szczegółów budżetowych i projektowych – warto je czytać w całości.
