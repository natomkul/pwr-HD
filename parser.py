import re
import json
import unicodedata

def parsuj_plik_bib(sciezka_do_pliku):
    baza_wpisow = []
    
    try:
        with open(sciezka_do_pliku, 'r', encoding='utf-8') as plik:
            tresc = plik.read()
    except FileNotFoundError:
        print(f"Błąd: Nie znaleziono pliku {sciezka_do_pliku}")
        return []

    wzorzec_wpisu = r'@([a-zA-Z]+)\{([^,\s]+),\s*(.*?)\n\}'
    wpisy_raw = re.findall(wzorzec_wpisu, tresc, re.DOTALL)

    interesujace_pola = ['title', 'author', 'year', 'publisher', 'journal']

    for typ, klucz, blok in wpisy_raw:
        wpis = {
            "bib_type": typ.lower().strip(),
            "bib_key": klucz.strip(),
        }
        for pole in interesujace_pola:
            wpis[pole] = None
        
        blok_jednolinijkowy = re.sub(r'\s+', ' ', blok)

        for pole in interesujace_pola:
            szablon = rf'{pole}\s*=\s*[\{{\"]?(.*?)[\}}\"]?\s*(?:,|\s*$)'
            dopasowanie = re.search(szablon, blok_jednolinijkowy, re.IGNORECASE)
            
            if dopasowanie and dopasowanie.group(1):
                wartosc_raw = dopasowanie.group(1).strip()
                
                wartosc = wartosc_raw.rstrip(',').strip('}"')
                
                czysty_tekst = usun_znaki_specjalne(wartosc)
                czysty_tekst = re.sub(r'\s+', ' ', czysty_tekst).strip()
                
                if pole == 'author':
                    wpis[pole] = parsuj_autorow(czysty_tekst)
                else:
                    wpis[pole] = czysty_tekst
            else:
                wpis[pole] = None

        pola_tekstowe = [wpis[p] for p in interesujace_pola]

        if any(wpis.values()):
            baza_wpisow.append(wpis)
            
    return baza_wpisow

def usun_znaki_specjalne(tekst):
    """
    Zamienia litery z akcentami na zwykłe (np. ó->o, á->a, ł->l)
    oraz usuwa techniczne znaki LaTeX-a (\, ', {, }).
    """
    if not tekst:
        return tekst

    tekst = re.sub(r"\\[`'\^\"~]?", "", tekst)
    
    tekst = re.sub(r'[\{\}]', '', tekst)

    tekst = unicodedata.normalize('NFD', tekst)
    czysty_tekst = "".join(ch for ch in tekst if unicodedata.category(ch) != 'Mn')
    
    poprawki = {"ł": "l", "Ł": "L", "ß": "ss"}
    for stary, nowy in poprawki.items():
        czysty_tekst = czysty_tekst.replace(stary, nowy)
        
    return czysty_tekst


def zapisz_do_json(baza_wpisow, sciezka_wyjsciowa):
    try:
        with open(sciezka_wyjsciowa, 'w', encoding='utf-8') as plik:
            json.dump(baza_wpisow, plik, indent=4, ensure_ascii=False)
        
        print(f"Sukces: Dane zostały pomyślnie zapisane do pliku {sciezka_wyjsciowa}")
    
    except IOError as e:
        print(f"Błąd: Nie udało się zapisać pliku {sciezka_wyjsciowa}. Powód: {e}")


def parsuj_autorow(tekst_autorzy):
    """
    Rozbija ciąg znaków z autorami (rozdzielanymi przez 'and') 
    na listę słowników z rozbiciem na imię i nazwisko.
    """
    if not tekst_autorzy:
        return []

    lista_autorow = []
    
    # Rozdzielamy autorów po słowie "and" (niezależnie od wielkości liter)
    surowi_autorzy = re.split(r'\s+and\s+', tekst_autorzy, flags=re.IGNORECASE)

    for autor in surowi_autorzy:
        autor = autor.strip()
        if not autor:
            continue
            
        if ',' in autor:
            czesci = autor.split(',', 1)
            nazwisko = czesci[0].strip()
            imie = czesci[1].strip()
        
        else:
            czesci = autor.rsplit(' ', 1)
            if len(czesci) == 2:
                imie = czesci[0].strip()
                nazwisko = czesci[1].strip()
            else:
                imie = ""
                nazwisko = czesci[0].strip()

        lista_autorow.append({
            "first_name": imie,
            "last_name": nazwisko
        })

    return lista_autorow

#-----------------------------------------------------------------------------------

sciezka = 'AI.bib'
wyniki = parsuj_plik_bib(sciezka)

sciezka_json = 'wyniki_ai.json'
zapisz_do_json(wyniki, sciezka_json)

print(json.dumps(wyniki, indent=4, ensure_ascii=False))
