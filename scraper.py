from playwright.sync_api import sync_playwright
from datetime import date, timedelta
import gspread
import uuid

def pobierz_dania_z_dnia(page):
    dania = []
    page.wait_for_timeout(2000)
    
    for _ in range(15):
        page.mouse.wheel(0, 800)
        page.wait_for_timeout(300)
        
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)
    
    wyniki = page.evaluate('''() => {
        let zebrane = [];
        let aktualnaKategoria = "Inne";
        
        let elementy = document.querySelectorAll('h2.text-title-large, .v-card');
        
        for (let el of elementy) {
            if (el.tagName.toLowerCase() === 'h2') {
                aktualnaKategoria = el.innerText.trim();
            } else if (el.classList.contains('v-card')) {
                let nameEl = el.querySelector('.guest-menu-product-card__name');
                if (!nameEl) continue; // Pomijamy puste/inne karty systemu
                
                let nazwa = nameEl.innerText.trim();
                
                let cenaEl = el.querySelector('.guest-menu-product-card__actions p');
                let cena = cenaEl ? cenaEl.innerText.trim() : "";
                
                let imgEl = el.querySelector('img.v-img__img');
                let zdjecieUrl = imgEl ? imgEl.getAttribute('src') : "";
                
                zebrane.push({
                    "Nazwa_Dania": nazwa,
                    "Opis": "Brak opisu",
                    "Kategoria": aktualnaKategoria,
                    "Cena": cena,
                    "Zdjecie": zdjecieUrl
                });
            }
        }
        return zebrane;
    }''')
    
    return wyniki

def pobierz_pelne_menu(url):
    print(f"🌐 Otwieram przeglądarkę i łączę z: {url}...")
    dni_tygodnia = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    
    menu_tygodniowe = {dzien: [] for dzien in dni_tygodnia}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url)
            page.wait_for_timeout(3000)
            
            for dzien in dni_tygodnia:
                print(f"\n📅 Pobieram menu na: {dzien}")
                try:
                    page.locator(f"button:has-text('{dzien}')").first.click(timeout=3000)
                    page.wait_for_timeout(1500)
                except:
                    print(f"⚠️ Nie mogłem kliknąć w {dzien}.")
                    continue
                
                zebrane = pobierz_dania_z_dnia(page)
                if zebrane:
                    print(f"   ✔️ Znaleziono łącznie {len(zebrane)} pozycji w menu na {dzien}")
                    menu_tygodniowe[dzien].extend(zebrane)
                    
        except Exception as e:
            print(f"❌ Błąd nawigacji: {e}")
        finally:
            browser.close()
            
    return menu_tygodniowe

def aktualizuj_baze_danych(menu_tygodniowe):
    dzisiaj = date.today()
    dzisiaj_index = dzisiaj.weekday() 
    
    if dzisiaj_index >= 4:
        index_jutra = 0
        jutro_data = dzisiaj + timedelta(days=(7 - dzisiaj_index))
    else:
        index_jutra = dzisiaj_index + 1
        jutro_data = dzisiaj + timedelta(days=1)
        
    dni_nazwy = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek"]
    nazwa_dnia_jutro = dni_nazwy[index_jutra]
    jutro_str = jutro_data.strftime("%Y-%m-%d")
    
    print(f"\n📝 Zapis do chmury... Menu jutra to: {nazwa_dnia_jutro} ({jutro_str})")
    
    wszystkie_dania = []
    for dania in menu_tygodniowe.values():
        wszystkie_dania.extend(dania)
        
    unikalny_katalog_dict = {}
    for danie in wszystkie_dania:
        if danie['Nazwa_Dania'] not in unikalny_katalog_dict:
            unikalny_katalog_dict[danie['Nazwa_Dania']] = danie
    unikalny_katalog = list(unikalny_katalog_dict.values())
    
    menu_jutro_surowe = menu_tygodniowe[nazwa_dnia_jutro]
    menu_jutro_dict = {}
    for danie in menu_jutro_surowe:
        if danie['Nazwa_Dania'] not in menu_jutro_dict:
            menu_jutro_dict[danie['Nazwa_Dania']] = danie
    menu_jutro = list(menu_jutro_dict.values())
    
    try:
        print("🔗 Łączenie z Google Sheets...")
        gc = gspread.service_account(filename='google_credentials.json')
        sh = gc.open("Baza_Danych_Catering")
        
        ws_katalog = sh.worksheet("Katalog_Dan")
        ws_menu = sh.worksheet("Menu_Dnia")
        
        katalog_dane = ws_katalog.get_all_records()
        znane_nazwy = [row['Nazwa_Dania'] for row in katalog_dane]
        id_map = {row['Nazwa_Dania']: row['ID_Dania'] for row in katalog_dane}
        znane_id = list(id_map.values()) 
        
        nowe_do_katalogu = []
        dodano_nowe = 0
        dzisiaj_zapis = date.today().strftime("%Y-%m-%d")
        
        for danie in unikalny_katalog:
            nazwa = danie["Nazwa_Dania"]
            if nazwa not in znane_nazwy:
                while True:
                    nowe_id = f"D-{str(uuid.uuid4())[:6]}"
                    if nowe_id not in znane_id:
                        znane_id.append(nowe_id)
                        break
                        
                formula = f'=JEŻELI.BŁĄD(ZAOKR(ŚREDNIA.JEŻELI(Opinie!C:C; "{nowe_id}"; Opinie!I:I); 1); 0)'
                
                nowe_do_katalogu.append([
                    nowe_id, 
                    nazwa, 
                    danie["Kategoria"], 
                    danie["Opis"], 
                    formula, 
                    danie.get("Cena", ""), 
                    danie.get("Zdjecie", ""),
                    dzisiaj_zapis 
                ])
                znane_nazwy.append(nazwa)
                id_map[nazwa] = nowe_id
                dodano_nowe += 1
                
        if nowe_do_katalogu:
            ws_katalog.append_rows(nowe_do_katalogu, value_input_option='USER_ENTERED')
        print(f"➕ Dodano {dodano_nowe} nowości do głównego katalogu.")

        print("🧹 Czyszczenie starego menu dnia...")
        ws_menu.clear()
        ws_menu.append_row(['Data', 'ID_Dania', 'Nazwa_Dania'])

        nowe_do_menu = []
        zapisane_menu = 0
        aktualny_wiersz_menu = 1 
        
        for danie in menu_jutro:
            nazwa = danie["Nazwa_Dania"]
            id_dania = id_map.get(nazwa)
            
            if id_dania:
                aktualny_wiersz_menu += 1
                formula_vlookup = f'=WYSZUKAJ.PIONOWO(B{aktualny_wiersz_menu}; Katalog_Dan!A:E; 2; FAŁSZ)'
                nowe_do_menu.append([jutro_str, id_dania, formula_vlookup])
                zapisane_menu += 1
                
        if nowe_do_menu:
            ws_menu.append_rows(nowe_do_menu, value_input_option='USER_ENTERED')
        print(f"✅ Zapisano {zapisane_menu} unikalnych pozycji do NOWEGO Menu Dnia na {jutro_str}.")
        
    except Exception as e:
        print(f"❌ BŁĄD POŁĄCZENIA Z GOOGLE SHEETS: {e}")

if __name__ == "__main__":
    adres = "https://kanapkaman.pl/sandwiczSzop"
    menu_tygodnia = pobierz_pelne_menu(adres)
    
    czy_puste = all(len(dania) == 0 for dania in menu_tygodnia.values())
    if not czy_puste:
        aktualizuj_baze_danych(menu_tygodnia)
    else:
        print("Nie pobrano żadnych danych ze strony.")
