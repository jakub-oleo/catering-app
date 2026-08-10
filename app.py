import streamlit as st
import pandas as pd
from datetime import date
import gspread
import os

st.set_page_config(page_title="Catering Rating App", page_icon="🍱", layout="centered")

if 'dodano_opinie' in st.session_state and st.session_state['dodano_opinie']:
    st.success("Dziękujemy! Twoja opinia została pomyślnie zapisana. 🎈")
    st.session_state['dodano_opinie'] = False 

@st.cache_data(ttl=600) 
def load_data():
    if os.path.exists('google_credentials.json'):
        gc = gspread.service_account(filename='google_credentials.json')
    else:
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        
    sh = gc.open("Baza_Danych_Catering")
    
    # 1. Ładowanie i zabezpieczenie Katalogu
    katalog_rekordy = sh.worksheet("Katalog_Dan").get_all_records()
    katalog = pd.DataFrame(katalog_rekordy)
    if katalog.empty:
        katalog = pd.DataFrame(columns=['ID_Dania', 'Nazwa_Dania', 'Kategoria', 'Opis', 'Srednia'])
        
    # 2. Ładowanie i zabezpieczenie Menu Dnia
    menu_rekordy = sh.worksheet("Menu_Dnia").get_all_records()
    menu_dnia = pd.DataFrame(menu_rekordy)
    if menu_dnia.empty:
        menu_dnia = pd.DataFrame(columns=['Data', 'ID_Dania'])
    elif 'Nazwa_Dania' in menu_dnia.columns:
        menu_dnia = menu_dnia.drop(columns=['Nazwa_Dania'])
    
    # 3. Ładowanie i zabezpieczenie Opinii
    opinie_rekordy = sh.worksheet("Opinie").get_all_records()
    if not opinie_rekordy: 
        opinie = pd.DataFrame(columns=[
            'ID_Opinii', 'Data_Dodania', 'ID_Dania', 'Ocena_Smak', 'Ocena_Swiezosc', 
            'Ocena_Jakosc_Cena', 'Ocena_Wyglad', 'Ocena_Zgodnosc', 'Srednia', 'Komentarz', 'Autor'
        ])
    else:
        opinie = pd.DataFrame(opinie_rekordy)
    
    # 4. Ustalenie wyświetlanej daty
    dzisiejsza_data = date.today().strftime("%Y-%m-%d")
    
    if not menu_dnia[menu_dnia['Data'] == dzisiejsza_data].empty:
        wybrane_menu = menu_dnia[menu_dnia['Data'] == dzisiejsza_data]
        wyswietlana_data = dzisiejsza_data
    else:
        wyswietlana_data = str(menu_dnia['Data'].max()) if not menu_dnia.empty else dzisiejsza_data
        wybrane_menu = menu_dnia[menu_dnia['Data'] == wyswietlana_data] if not menu_dnia.empty else pd.DataFrame(columns=menu_dnia.columns)
    
    dzisiejsze = pd.merge(wybrane_menu, katalog, on="ID_Dania", how="left")
    return dzisiejsze, opinie, katalog, wyswietlana_data

def oblicz_srednia_wazona(row):
    try:
        s = float(row.get('Ocena_Smak', 0))
        sw = float(row.get('Ocena_Swiezosc', 0))
        jc = float(row.get('Ocena_Jakosc_Cena', 0))
        w = float(row.get('Ocena_Wyglad', 0))
        z_val = row.get('Ocena_Zgodnosc', 'Nie')
        z = 10.0 if z_val == 'Tak' else 2.0
        
        wynik = (s * 0.40) + (sw * 2 * 0.25) + (jc * 2 * 0.15) + (z * 0.10) + (w * 2 * 0.10)
        return round(wynik, 1)
    except:
        return 0.0

def wyswietl_dania(dania_df, wszystkie_opinie_df):
    for index, row in dania_df.iterrows():
        id_dania = row['ID_Dania']
        opinie_dania = wszystkie_opinie_df[wszystkie_opinie_df['ID_Dania'] == id_dania]
        
        if not opinie_dania.empty:
            srednia_ogolna = round(opinie_dania['Srednia_Obliczona'].mean(), 1)
            liczba_ocen = len(opinie_dania)
            srednia_wyswietl = f"{srednia_ogolna} ⭐ ({liczba_ocen} ocen)"
        else:
            srednia_wyswietl = "Brak ocen"

        with st.container(border=True):
            col_img, col_txt, col_ocena = st.columns([1, 3, 1])
            
            with col_img:
                if 'Zdjecie' in row and str(row['Zdjecie']).startswith('http'):
                    st.image(row['Zdjecie'], use_container_width=True)
                else:
                    st.markdown("<h1 style='text-align: center;'>🍽️</h1>", unsafe_allow_html=True)
                    
            with col_txt:
                cena_str = f" | {row['Cena']}" if 'Cena' in row and str(row['Cena']).strip() != "" else ""
                st.markdown(f"**{row['Nazwa_Dania']}{cena_str}**")
                
                if str(row['Opis']).strip() != "Brak opisu":
                    st.caption(f"🥗 *Skład:* {row['Opis']}")
                    
            with col_ocena:
                st.markdown(f"**{srednia_wyswietl}**")
                
            if not opinie_dania.empty:
                with st.expander("💬 Komentarze"):
                    for _, op in opinie_dania.iterrows():
                        autor = op['Autor'] if str(op['Autor']).strip() != "" else "Anonim"
                        komentarz = op['Komentarz'] if str(op['Komentarz']).strip() != "" else "*Brak komentarza*"
                        ocena_indywidualna = op['Srednia_Obliczona']
                        st.markdown(f"- **{autor}** ({ocena_indywidualna}⭐): {komentarz}")

# ==========================================
# GŁÓWNA LOGIKA APLIKACJI
# ==========================================
try:
    dzisiejsze_menu, opinie_df, pelny_katalog, aktualna_data = load_data()
    if not opinie_df.empty:
        opinie_df['Srednia_Obliczona'] = opinie_df.apply(oblicz_srednia_wazona, axis=1)
except Exception as e:
    st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
    st.stop()

# ==========================================
# NAGŁÓWEK I WYSZUKIWARKA
# ==========================================
col_title, col_search = st.columns([2, 1]) 

with col_title:
    st.title("🍽️ Panel Ocen")
    st.markdown(f"**Menu na:** {aktualna_data}")

with col_search:
    st.write("") # Odstęp, aby wyrównać z tytułem
    wyszukiwana_fraza = st.text_input("🔍 Szukaj produktu:", placeholder="Wpisz nazwę...")

st.divider()

# ==========================================
# WIDOK: WYSZUKIWANIE LUB ZAKŁADKI
# ==========================================
if wyszukiwana_fraza:
    # WIDOK WYSZUKIWANIA
    st.subheader(f"Wyniki wyszukiwania dla: '{wyszukiwana_fraza}'")
    wyniki = pelny_katalog[pelny_katalog['Nazwa_Dania'].str.contains(wyszukiwana_fraza, case=False, na=False)]
    
    if not wyniki.empty:
        wyswietl_dania(wyniki, opinie_df)
    else:
        st.warning("Nie znaleziono dań pasujących do wpisanej frazy. Spróbuj wpisać inną nazwę.")
        
else:
    # WIDOK ZAKŁADEK (gdy wyszukiwarka jest pusta)
    tab_menu, tab_katalog, tab_ocena, tab_statystyki = st.tabs(["📋 Menu Dnia", "📚 Pełny Katalog", "✍️ Dodaj Opinię", "📈 Statystyki"])

    with tab_menu:
        st.header("Co dzisiaj jemy?")
        wszystkie_kategorie = [k for k in pelny_katalog['Kategoria'].unique().tolist() if str(k).strip() != ""]
        
        if wszystkie_kategorie:
            wybrana_kategoria = st.radio("Wybierz kategorię produktów:", options=wszystkie_kategorie, horizontal=True, label_visibility="collapsed")
            st.divider()
            dania_z_kategorii = dzisiejsze_menu[dzisiejsze_menu['Kategoria'] == wybrana_kategoria]
            
            if not dania_z_kategorii.empty:
                wyswietl_dania(dania_z_kategorii, opinie_df)
            else:
                st.info(f"Brak pozycji w kategorii **{wybrana_kategoria}** w tym dniu.")
        else:
            st.info("Brak kategorii w bazie danych.")

    with tab_katalog:
        st.header("📚 Pełny Katalog Produktów")
        st.markdown("Poniżej znajdziesz wszystkie produkty zebrane w naszej bazie, podzielone na kategorie.")
        
        if wszystkie_kategorie:
            for kategoria in wszystkie_kategorie:
                st.subheader(f"🔹 {kategoria}")
                dania_w_kategorii = pelny_katalog[pelny_katalog['Kategoria'] == kategoria]
                
                if not dania_w_kategorii.empty:
                    wyswietl_dania(dania_w_kategorii, opinie_df)
                else:
                    st.info("Brak dań w tej kategorii.")
                    
                st.divider()
        else:
            st.info("Baza danych jest pusta.")

    with tab_ocena:
        st.header("✍️ Oceń swoje zamówienie")
        st.info("Wpisz nazwę dowolnego dania z naszego katalogu, aby je ocenić.")
        
        with st.form("formularz_oceny", clear_on_submit=True):
            lista_wszystkich_dan = sorted([d for d in pelny_katalog['Nazwa_Dania'].tolist() if str(d).strip() != ""])
            wybrane_danie_nazwa = st.selectbox("Wyszukaj danie do oceny:", options=lista_wszystkich_dan, index=None, placeholder="🔍 Wpisz fragment nazwy lub kliknij...")
            
            st.markdown("**Szczegółowa ocena (skala 1-10):**")
            ocena_smak = st.slider("Smak", min_value=1, max_value=10, value=7)
            
            st.markdown("**Kryteria dodatkowe (skala 1-5):**")
            colA, colB, colC = st.columns(3)
            with colA:
                ocena_swiezosc = st.slider("Świeżość", min_value=1, max_value=5, value=4)
            with colB:
                ocena_cena = st.slider("Jakość/Cena", min_value=1, max_value=5, value=4)
            with colC:
                ocena_wyglad = st.slider("Wygląd", min_value=1, max_value=5, value=4)
                
            ocena_zgodnosc = st.radio("Czy danie było zgodne z opisem?", options=["Tak", "Nie"], horizontal=True)
            
            komentarz = st.text_area("Opcjonalny komentarz (co poprawić?)", max_chars=200)
            autor = st.text_input("Twoje imię (opcjonalnie)")
            
            submitted = st.form_submit_button("Wyślij Ocenę 🚀", use_container_width=True)
            
            if submitted:
                if wybrane_danie_nazwa is None:
                    st.warning("⚠️ Proszę wybrać danie z listy przed wysłaniem opinii.")
                else:
                    try:
                        id_dania = pelny_katalog.loc[pelny_katalog['Nazwa_Dania'] == wybrane_danie_nazwa, 'ID_Dania'].values[0]
                        
                        if os.path.exists('google_credentials.json'):
                            gc = gspread.service_account(filename='google_credentials.json')
                        else:
                            gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
                            
                        sh = gc.open("Baza_Danych_Catering")
                        ws = sh.worksheet("Opinie")
                        
                        nowy_wiersz_numer = len(ws.get_all_values()) + 1
                        id_opinii = f"OP-{nowy_wiersz_numer}"
                        dzisiaj_zapis = date.today().strftime("%Y-%m-%d")
                        
                        formula_srednia = f'=ZAOKR((D{nowy_wiersz_numer}*0,4) + (E{nowy_wiersz_numer}*2*0,25) + (F{nowy_wiersz_numer}*2*0,15) + (G{nowy_wiersz_numer}*2*0,1) + (JEŻELI(H{nowy_wiersz_numer}="Tak"; 10; 2)*0,1); 1)'
                        
                        ws.append_row(
                            [id_opinii, dzisiaj_zapis, id_dania, ocena_smak, ocena_swiezosc, ocena_cena, ocena_wyglad, ocena_zgodnosc, formula_srednia, komentarz, autor if autor else "Anonim"],
                            value_input_option='USER_ENTERED'
                        )
                        
                        st.cache_data.clear()
                        st.session_state['dodano_opinie'] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Błąd zapisu do chmury: {e}")

    with tab_statystyki:
        st.header("📈 Statystyki i Nowości")
        col_stat1, col_stat2 = st.columns(2)
        
        with col_stat1:
            st.subheader("🏆 Top 5 Najlepszych")
            if opinie_df.empty:
                st.info("Brak ocen w systemie.")
            else:
                statystyki = opinie_df.groupby('ID_Dania').agg(Srednia=('Srednia_Obliczona', 'mean'), Liczba_Ocen=('ID_Opinii', 'count')).reset_index()
                ranking_df = pd.merge(statystyki, pelny_katalog, on="ID_Dania")
                top_5 = ranking_df.sort_values(by=['Srednia', 'Liczba_Ocen'], ascending=[False, False]).head(5)
                
                for i, row in enumerate(top_5.iterrows(), 1):
                    dane = row[1]
                    st.markdown(f"**{i}. {dane['Nazwa_Dania']}**")
                    st.caption(f"{dane['Srednia']:.1f} ⭐ ({dane['Liczba_Ocen']} opinii) | {dane['Kategoria']}")
                    
        with col_stat2:
            st.subheader("🌟 Nowości w menu")
            nowosci = pelny_katalog.tail(5)
            for i, row in enumerate(nowosci.iterrows(), 1):
                dane = row[1]
                st.markdown(f"**- {dane['Nazwa_Dania']}**")
                st.caption(f"Kategoria: {dane['Kategoria']}")
