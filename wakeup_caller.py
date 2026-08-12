from playwright.sync_api import sync_playwright

def wybudz_aplikacje(url):
    print(f"⏰ Odwiedzam stronę: {url}")
    with sync_playwright() as p:
        # Uruchamiamy w tle
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto(url)
            # Czekamy chwilę na załadowanie ewentualnego ekranu uśpienia
            page.wait_for_timeout(5000)
            
            # Szukamy niebieskiego przycisku z obrazka
            przycisk = page.locator('[data-testid="wakeup-button-owner"]')
            
            if przycisk.count() > 0 and przycisk.first.is_visible():
                print("💤 Aplikacja śpi. Klikam przycisk wybudzania...")
                przycisk.first.click()
                
                # Dajemy jej czas na "wstanie" z łóżka
                page.wait_for_timeout(10000) 
                print("✅ Aplikacja pomyślnie wybudzona!")
            else:
                print("✅ Aplikacja nie śpi, wszystko działa prawidłowo!")
                
        except Exception as e:
            print(f"⚠️ Wystąpił błąd: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    # PODMIEŃ NA ADRES SWOJEJ APKI
    adres_aplikacji = "https://oleo-szop.streamlit.app/" 
    wybudz_aplikacje(adres_aplikacji)
