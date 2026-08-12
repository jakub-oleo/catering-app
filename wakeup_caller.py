from playwright.sync_api import sync_playwright

def wybudz_aplikacje(url):
    print(f"⏰ Odwiedzam stronę: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # MASKOWANIE BOTA
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            page.goto(url)
            print("⏳ Strona załadowana. Sprawdzam, czy aplikacja śpi...")
            
            # Czeka inteligentnie DO 15 sekund na przycisk z odpowiednim data-testid
            selekktor_przycisku = '[data-testid*="wakeup-button"]'
            
            try:
                przycisk = page.wait_for_selector(selekktor_przycisku, timeout=15000)
                print("💤 Znalazłem przycisk wybudzania! Klikam...")
                przycisk.click()
                
                print("☕ Kliknięto. Czekam, aż serwer wstanie...")
                page.wait_for_selector(selekktor_przycisku, state="hidden", timeout=30000)
                print("✅ Aplikacja pomyślnie wybudzona!")
                
            except Exception:
                print("✅ Przycisk wybudzania nie pojawił się. Aplikacja prawdopodobnie już działa!")
                
        except Exception as e:
            print(f"⚠️ Wystąpił błąd nawigacji lub połączenia: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    adres_aplikacji = "https://oleo-szop.streamlit.app/" 
    wybudz_aplikacje(adres_aplikacji)
