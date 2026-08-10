# --- START APLIKACJI ---
try:
    dzisiejsze_menu, opinie_df, pelny_katalog, aktualna_data = load_data()
    if not opinie_df.empty:
        opinie_df['Srednia_Obliczona'] = opinie_df.apply(oblicz_srednia_wazona, axis=1)
except Exception as e:
    st.error(f"❌ Błąd połączenia z Google Sheets: {e}")
    st.stop()

# ==========================================
# NAGŁÓWEK I WYSZUKIWARKA (GÓRNY PRAWY RÓG)
# ==========================================
col_title, col_search = st.columns([2, 1]) # Proporcje 2:1 (tytuł szerszy, wyszukiwarka węższa)

with col_title:
    st.title("🍽️ Panel Ocen")
    st.markdown(f"**Menu na:** {aktualna_data}")

with col_search:
    st.write("") # Pusty odstęp, żeby wyrównać pole wyszukiwania w pionie
    wyszukiwana_fraza = st.text_input("🔍 Szukaj produktu:", placeholder="Wpisz nazwę...")

st.divider()

# ==========================================
# LOGIKA WYSZUKIWANIA VS ZAKŁADKI
# ==========================================
if wyszukiwana_fraza:
    # Użytkownik coś wpisał -> pokazujemy WYNIKI WYSZUKIWANIA
    st.subheader(f"Wyniki wyszukiwania dla: '{wyszukiwana_fraza}'")
    
    # Filtrowanie po nazwie (nie zważając na wielkość liter)
    wyniki = pelny_katalog[pelny_katalog['Nazwa_Dania'].str.contains(wyszukiwana_fraza, case=False, na=False)]
    
    if not wyniki.empty:
        wyswietl_dania(wyniki, opinie_df)
    else:
        st.warning("Nie znaleziono dań pasujących do wpisanej frazy. Spróbuj wpisać inną nazwę.")

else:
    # Wyszukiwarka jest pusta -> pokazujemy NORMALNE ZAKŁADKI
    tab_menu, tab_katalog, tab_ocena, tab_statystyki = st.tabs(["📋 Menu Dnia", "📚 Pełny Katalog", "✍️ Dodaj Opinię", "📈 Statystyki"])

    # ==========================================
    # ZAKŁADKA 1: MENU DNIA
    # ==========================================
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

    # ==========================================
    # ZAKŁADKA 2: PEŁNY KATALOG
    # ==========================================
    with tab_katalog:
        st.header("📚 Pełny Katalog Produktów")
        st.markdown("Poniżej znajdziesz wszystkie produkty zebrane w naszej bazie, podzielone na kategorie.")
        
        wszystkie_kategorie = [k for k in pelny_katalog['Kategoria'].unique().tolist() if str(k).strip() != ""]
        
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

    # ==========================================
    # ZAKŁADKA 3: DODAJ OPINIĘ
    # ==========================================
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

    # ==========================================
    # ZAKŁADKA 4: STATYSTYKI & NOWOŚCI
    # ==========================================
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
