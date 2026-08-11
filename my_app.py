import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Data Collection - Examen",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
COLAB_DIR = BASE_DIR / "Colab"
WEB_SCRAPER_DIR = BASE_DIR / "Web_Scraper"
FORM_DIR = BASE_DIR / "Formulaire"

DB_PATH = BASE_DIR / "data_collection.db"


# ============================================================
# DATABASE SQL - SQLite
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def save_to_sql(df: pd.DataFrame, table_name: str):
    """Enregistre un DataFrame dans SQLite."""
    if df is None or df.empty:
        return

    with get_connection() as conn:
        df.to_sql(table_name, conn, if_exists="replace", index=False)


def get_sql_tables():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()
    return [row[0] for row in rows]


# ============================================================
# FICHIERS
# ============================================================

BOOKS_CSV = WEB_SCRAPER_DIR / "Source_1_Books_to_Scrape.csv"
GAARAAS_CSV = WEB_SCRAPER_DIR / "Source_2_Gaaraas).csv"

BOOKS_NOTEBOOK = COLAB_DIR / "books_to_scrape(Selenium).ipynb"
GAARAAS_NOTEBOOK = COLAB_DIR / "gaaraas(Selenium).ipynb"

GOOGLE_FORM_FILE = FORM_DIR / "formulaire_forms.xlsx"
KOBO_FORM_FILE = FORM_DIR / "formulaire_kobotoolbox.xlsx"


def read_csv(path: Path):
    """Lecture robuste des CSV finaux du dossier Web_Scraper."""
    if not path.exists():
        return None

    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(path, encoding=encoding, on_bad_lines="skip")
        except Exception:
            pass

    return None


# ============================================================
# FORMULAIRES
# ============================================================

def extract_urls_from_excel(path: Path):
    """
    Récupère les URLs présentes dans les fichiers Excel
    des formulaires, soit comme hyperliens Excel, soit
    comme texte.
    """
    if not path.exists():
        return []

    urls = []

    try:
        from openpyxl import load_workbook

        wb = load_workbook(path, data_only=False)

        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for cell in row:
                    if cell.hyperlink and cell.hyperlink.target:
                        url = cell.hyperlink.target.strip()
                        if url not in urls:
                            urls.append(url)

                    if isinstance(cell.value, str):
                        found = re.findall(
                            r"https?://[^\s<>'\"]+",
                            cell.value
                        )
                        for url in found:
                            url = url.rstrip(".,;)")
                            if url not in urls:
                                urls.append(url)

        wb.close()

    except Exception:
        return []

    return urls


def show_form_button(label, url, key):
    """Bouton qui ouvre directement le formulaire dans le navigateur."""
    st.link_button(label, url, use_container_width=True)


# ============================================================
# SELENIUM
# ============================================================

def create_driver():
    """Crée un Chrome/Chromium Selenium headless compatible Cloud."""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()

    # Utilise Chromium/Chrome disponible sur l'environnement.
    possible_binaries = [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]

    for binary in possible_binaries:
        if Path(binary).exists():
            options.binary_location = binary
            break

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--lang=fr-FR")

    return webdriver.Chrome(options=options)


# ============================================================
# SELENIUM - BOOKS TO SCRAPE
# ============================================================

def scrape_books(start_page=1, end_page=50):
    """
    Scraping Selenium de Books to Scrape.
    Parcourt les pages demandées puis visite chaque fiche produit.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = create_driver()
    records = []

    try:
        progress = st.progress(0)
        total = end_page - start_page + 1

        for position, page in enumerate(
            range(start_page, end_page + 1), start=1
        ):
            url = f"https://books.toscrape.com/catalogue/page-{page}.html"
            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "article.product_pod")
                    )
                )
            except Exception:
                pass

            products = driver.find_elements(
                By.CSS_SELECTOR, "article.product_pod"
            )

            links = []
            for product in products:
                try:
                    link = product.find_element(
                        By.CSS_SELECTOR, "h3 a"
                    ).get_attribute("href")
                    if link:
                        links.append(link)
                except Exception:
                    continue

            for product_url in links:
                try:
                    driver.get(product_url)

                    def text(css, default=""):
                        try:
                            return driver.find_element(
                                By.CSS_SELECTOR, css
                            ).text.strip()
                        except Exception:
                            return default

                    rating_class = ""
                    try:
                        rating_class = driver.find_element(
                            By.CSS_SELECTOR,
                            "div.product_main p.star-rating"
                        ).get_attribute("class")
                    except Exception:
                        pass

                    records.append({
                        "page": page,
                        "number_of_products": len(products),
                        "title": text("div.product_main h1"),
                        "price": text(
                            "div.product_main p.price_color"
                        ),
                        "availability": text(
                            "div.product_main p.instock.availability"
                        ),
                        "star_rating": rating_class,
                        "reviews": text(
                            "table.table-striped tr:nth-child(7) td"
                        ),
                        "description": text(
                            "#product_description + p"
                        ),
                        "product_type": text(
                            "ul.breadcrumb li:nth-child(3) a"
                        ),
                        "tax": text(
                            "table.table-striped tr:nth-child(5) td"
                        ),
                        "url": product_url,
                    })

                except Exception:
                    continue

            progress.progress(position / total)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)


# ============================================================
# SELENIUM - GAARAAS
# ============================================================

def scrape_gaaraas(start_page=1, end_page=13):
    """
    Scraping Selenium de Gaaraas.
    Parcourt les pages du vendeur Dakar Auto puis visite
    les annonces disponibles.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = create_driver()
    records = []

    try:
        progress = st.progress(0)
        total = end_page - start_page + 1

        for position, page in enumerate(
            range(start_page, end_page + 1), start=1
        ):
            url = (
                "https://www.gaaraas.com/fr/users/dakar-auto"
                f"?page={page}"
            )

            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "a.common-ad-card")
                    )
                )
            except Exception:
                pass

            cards = driver.find_elements(
                By.CSS_SELECTOR,
                "a.common-ad-card"
            )

            links = []
            for card in cards:
                try:
                    href = card.get_attribute("href")
                    if href and href not in links:
                        links.append(href)
                except Exception:
                    continue

            for ad_url in links:
                try:
                    driver.get(ad_url)

                    def text(css, default=""):
                        try:
                            return driver.find_element(
                                By.CSS_SELECTOR, css
                            ).text.strip()
                        except Exception:
                            return default

                    records.append({
                        "page": page,
                        "number_of_ads": len(cards),
                        "marque_modele": text(
                            ".ad-title-block h2"
                        ),
                        "annee": text(
                            "div.prop:nth-of-type(4) span:nth-of-type(2)"
                        ),
                        "prix": text(
                            ".back-wrapper .ad-price span.price-wrap"
                        ),
                        "kilometrage": text(
                            "div.prop:nth-of-type(3) span:nth-of-type(2)"
                        ),
                        "type_boite_de_vitesse": text(
                            "div.prop:nth-of-type(2) span:nth-of-type(2)"
                        ),
                        "region_de_vente": text(
                            ".ad-title a span"
                        ),
                        "url": ad_url,
                    })

                except Exception:
                    continue

            progress.progress(position / total)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)


# ============================================================
# NETTOYAGE
# ============================================================

def clean_books(df):
    df = df.copy()

    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    if "price" in df.columns:
        df["price_numeric"] = pd.to_numeric(
            df["price"].astype(str)
            .str.replace("£", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce",
        )

    if "star_rating" in df.columns:
        rating_map = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
        }

        df["rating"] = (
            df["star_rating"]
            .astype(str)
            .str.extract(
                r"(One|Two|Three|Four|Five)",
                expand=False
            )
            .map(rating_map)
        )

    if "reviews" in df.columns:
        df["reviews_numeric"] = pd.to_numeric(
            df["reviews"],
            errors="coerce"
        )

    return df.drop_duplicates().reset_index(drop=True)


def clean_gaaraas(df):
    df = df.copy()

    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    if "annee" in df.columns:
        df["annee_numeric"] = pd.to_numeric(
            df["annee"],
            errors="coerce"
        )

    if "prix" in df.columns:
        df["prix_numeric"] = pd.to_numeric(
            df["prix"].astype(str)
            .str.replace("CFA", "", regex=False)
            .str.replace("FCFA", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.strip(),
            errors="coerce",
        )

    if "kilometrage" in df.columns:
        df["kilometrage_numeric"] = pd.to_numeric(
            df["kilometrage"].astype(str)
            .str.replace("km", "", case=False, regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.strip(),
            errors="coerce",
        )

    return df.drop_duplicates().reset_index(drop=True)


# ============================================================
# SESSION STATE
# ============================================================

if "books_selenium" not in st.session_state:
    st.session_state.books_selenium = None

if "gaaraas_selenium" not in st.session_state:
    st.session_state.gaaraas_selenium = None


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("📊 Data Collection")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Accueil",
        "Scraping Selenium",
        "Données Web Scraper",
        "Dashboard",
        "Formulaires d'évaluation",
        "Base SQL",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Projet Examen Data Collection"
)


# ============================================================
# ACCUEIL
# ============================================================

if menu == "Accueil":

    st.title("📊 Application Data Collection")

    st.markdown(
        """
        ### Objectif

        Cette application regroupe les différentes étapes du projet :

        - 🕷️ collecte avec **Selenium** sur plusieurs pages ;
        - 📥 téléchargement des données brutes produites par
          **Web Scraper** ;
        - 🧹 nettoyage des données Selenium ;
        - 📊 visualisation sous forme de dashboard ;
        - 📝 accès direct aux deux formulaires d'évaluation ;
        - 🗄️ stockage des données dans une base SQL SQLite.

        Les fichiers **JSON du dossier `Web_Scraper` sont volontairement
        ignorés**. Seuls les deux fichiers CSV finaux sont utilisés.
        """
    )

    st.success("Application prête.")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "CSV Web Scraper",
            2 if BOOKS_CSV.exists() and GAARAAS_CSV.exists() else 0
        )

    with c2:
        st.metric(
            "Notebooks Selenium",
            2 if BOOKS_NOTEBOOK.exists() and GAARAAS_NOTEBOOK.exists() else 0
        )

    with c3:
        st.metric(
            "Formulaires",
            2 if GOOGLE_FORM_FILE.exists() and KOBO_FORM_FILE.exists() else 0
        )

    with c4:
        st.metric(
            "Tables SQL",
            len(get_sql_tables())
        )


# ============================================================
# SCRAPING SELENIUM
# ============================================================

elif menu == "Scraping Selenium":

    st.title("🕷️ Scraping Selenium")

    tab_books, tab_gaaraas = st.tabs(
        ["📚 Books to Scrape", "🚗 Gaaraas"]
    )

    # --------------------------------------------------------
    # BOOKS
    # --------------------------------------------------------

    with tab_books:

        st.subheader("Books to Scrape")

        st.write(
            "Le notebook `books_to_scrape(Selenium).ipynb` "
            "sert de référence pour cette collecte."
        )

        col1, col2 = st.columns(2)

        with col1:
            start = st.number_input(
                "Première page",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
                key="books_start"
            )

        with col2:
            end = st.number_input(
                "Dernière page",
                min_value=1,
                max_value=50,
                value=50,
                step=1,
                key="books_end"
            )

        if st.button(
            "🚀 Lancer le scraping Books to Scrape",
            type="primary",
            use_container_width=True,
        ):

            if start > end:
                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )
            else:
                try:
                    with st.spinner(
                        "Scraping Books to Scrape en cours..."
                    ):
                        raw = scrape_books(start, end)
                        cleaned = clean_books(raw)

                    st.session_state.books_selenium = cleaned
                    save_to_sql(cleaned, "selenium_books")

                    st.success(
                        f"{len(cleaned)} observations enregistrées."
                    )

                except Exception as exc:
                    st.error(
                        "Erreur Selenium : "
                        f"{exc}"
                    )

        if st.session_state.books_selenium is not None:

            df = st.session_state.books_selenium

            st.metric(
                "Livres collectés",
                len(df)
            )

            st.dataframe(
                df,
                use_container_width=True,
                height=450
            )

            st.download_button(
                "⬇️ Télécharger les données Books Selenium",
                df.to_csv(index=False).encode("utf-8"),
                "books_selenium_clean.csv",
                "text/csv",
                use_container_width=True,
            )

    # --------------------------------------------------------
    # GAARAAS
    # --------------------------------------------------------

    with tab_gaaraas:

        st.subheader("Gaaraas")

        st.write(
            "Le notebook `gaaraas(Selenium).ipynb` "
            "sert de référence pour cette collecte."
        )

        col1, col2 = st.columns(2)

        with col1:
            start = st.number_input(
                "Première page",
                min_value=1,
                max_value=13,
                value=1,
                step=1,
                key="gaaraas_start"
            )

        with col2:
            end = st.number_input(
                "Dernière page",
                min_value=1,
                max_value=13,
                value=13,
                step=1,
                key="gaaraas_end"
            )

        if st.button(
            "🚀 Lancer le scraping Gaaraas",
            type="primary",
            use_container_width=True,
        ):

            if start > end:
                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )
            else:
                try:
                    with st.spinner(
                        "Scraping Gaaraas en cours..."
                    ):
                        raw = scrape_gaaraas(start, end)
                        cleaned = clean_gaaraas(raw)

                    st.session_state.gaaraas_selenium = cleaned
                    save_to_sql(cleaned, "selenium_gaaraas")

                    st.success(
                        f"{len(cleaned)} observations enregistrées."
                    )

                except Exception as exc:
                    st.error(
                        "Erreur Selenium : "
                        f"{exc}"
                    )

        if st.session_state.gaaraas_selenium is not None:

            df = st.session_state.gaaraas_selenium

            st.metric(
                "Annonces collectées",
                len(df)
            )

            st.dataframe(
                df,
                use_container_width=True,
                height=450
            )

            st.download_button(
                "⬇️ Télécharger les données Gaaraas Selenium",
                df.to_csv(index=False).encode("utf-8"),
                "gaaraas_selenium_clean.csv",
                "text/csv",
                use_container_width=True,
            )


# ============================================================
# WEB SCRAPER - UNIQUEMENT LES DEUX CSV
# ============================================================

elif menu == "Données Web Scraper":

    st.title("📥 Données brutes Web Scraper")

    st.info(
        "Les fichiers JSON sont ignorés. "
        "Seuls les deux CSV finaux sont pris en compte."
    )

    csv_files = [
        BOOKS_CSV,
        GAARAAS_CSV,
    ]

    available = [path for path in csv_files if path.exists()]

    if not available:
        st.error(
            "Les deux fichiers CSV du dossier Web_Scraper "
            "sont introuvables."
        )

    for path in available:

        df = read_csv(path)

        if df is None:
            st.error(f"Impossible de lire {path.name}.")
            continue

        st.subheader(f"📄 {path.name}")

        c1, c2 = st.columns(2)

        with c1:
            st.metric("Lignes", df.shape[0])

        with c2:
            st.metric("Colonnes", df.shape[1])

        st.dataframe(
            df.head(100),
            use_container_width=True,
            height=350
        )

        st.download_button(
            f"⬇️ Télécharger {path.name}",
            df.to_csv(index=False).encode("utf-8"),
            path.name,
            "text/csv",
            key=f"download_{path.name}",
            use_container_width=True,
        )

        # Stockage des deux sources Web Scraper dans SQL.
        if path.name == BOOKS_CSV.name:
            save_to_sql(df, "webscraper_books")
        elif path.name == GAARAAS_CSV.name:
            save_to_sql(df, "webscraper_gaaraas")


# ============================================================
# DASHBOARD
# ============================================================

elif menu == "Dashboard":

    st.title("📊 Dashboard des données Selenium nettoyées")

    books = st.session_state.books_selenium
    gaaraas = st.session_state.gaaraas_selenium

    if books is None and gaaraas is None:
        st.warning(
            "Aucune donnée Selenium n'est encore disponible. "
            "Lancez les deux collectes dans la section "
            "'Scraping Selenium'."
        )

    # --------------------------------------------------------
    # BOOKS
    # --------------------------------------------------------

    if books is not None:

        st.header("📚 Books to Scrape")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Livres", len(books))

        with c2:
            value = (
                books["price_numeric"].mean()
                if "price_numeric" in books
                else None
            )
            st.metric(
                "Prix moyen",
                f"£{value:.2f}" if pd.notna(value) else "N/A"
            )

        with c3:
            value = (
                books["rating"].mean()
                if "rating" in books
                else None
            )
            st.metric(
                "Note moyenne",
                f"{value:.2f}/5" if pd.notna(value) else "N/A"
            )

        with c4:
            value = (
                books["product_type"].nunique()
                if "product_type" in books
                else 0
            )
            st.metric("Types de produits", value)

        left, right = st.columns(2)

        with left:
            if "product_type" in books:
                st.subheader("Top catégories")
                st.bar_chart(
                    books["product_type"]
                    .value_counts()
                    .head(10)
                )

        with right:
            if "rating" in books:
                st.subheader("Répartition des notes")
                st.bar_chart(
                    books["rating"]
                    .value_counts()
                    .sort_index()
                )

        with st.expander("Voir les données Books nettoyées"):
            st.dataframe(
                books,
                use_container_width=True
            )

    # --------------------------------------------------------
    # GAARAAS
    # --------------------------------------------------------

    if gaaraas is not None:

        st.divider()
        st.header("🚗 Gaaraas")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric("Annonces", len(gaaraas))

        with c2:
            value = (
                gaaraas["prix_numeric"].mean()
                if "prix_numeric" in gaaraas
                else None
            )
            st.metric(
                "Prix moyen",
                f"{value:,.0f} FCFA" if pd.notna(value) else "N/A"
            )

        with c3:
            value = (
                gaaraas["annee_numeric"].mean()
                if "annee_numeric" in gaaraas
                else None
            )
            st.metric(
                "Année moyenne",
                f"{value:.0f}" if pd.notna(value) else "N/A"
            )

        with c4:
            value = (
                gaaraas["kilometrage_numeric"].mean()
                if "kilometrage_numeric" in gaaraas
                else None
            )
            st.metric(
                "Kilométrage moyen",
                f"{value:,.0f} km"
                if pd.notna(value)
                else "N/A"
            )

        left, right = st.columns(2)

        with left:
            if "marque_modele" in gaaraas:
                st.subheader("Top marques / modèles")
                st.bar_chart(
                    gaaraas["marque_modele"]
                    .value_counts()
                    .head(10)
                )

        with right:
            if "annee_numeric" in gaaraas:
                st.subheader("Répartition par année")
                st.bar_chart(
                    gaaraas["annee_numeric"]
                    .value_counts()
                    .sort_index()
                )

        with st.expander("Voir les données Gaaraas nettoyées"):
            st.dataframe(
                gaaraas,
                use_container_width=True
            )


# ============================================================
# FORMULAIRES
# ============================================================

elif menu == "Formulaires d'évaluation":

    st.title("📝 Formulaires d'évaluation")

    st.write(
        "Les deux formulaires sont accessibles directement "
        "depuis cette page."
    )

    google_urls = extract_urls_from_excel(GOOGLE_FORM_FILE)
    kobo_urls = extract_urls_from_excel(KOBO_FORM_FILE)

    st.subheader("📋 Google Forms")

    if google_urls:
        for index, url in enumerate(google_urls, start=1):
            show_form_button(
                f"📝 Ouvrir Google Forms {index}",
                url,
                f"google_form_{index}",
            )
    else:
        st.warning(
            "Aucun lien détecté dans "
            "`formulaire_forms.xlsx`."
        )

    st.divider()

    st.subheader("📋 KoboToolbox")

    if kobo_urls:
        for index, url in enumerate(kobo_urls, start=1):
            show_form_button(
                f"📝 Ouvrir KoboToolbox {index}",
                url,
                f"kobo_form_{index}",
            )
    else:
        st.warning(
            "Aucun lien détecté dans "
            "`formulaire_kobotoolbox.xlsx`."
        )

    st.caption(
        "Les URLs sont lues automatiquement depuis les fichiers "
        "Excel du dossier Formulaire."
    )


# ============================================================
# BASE SQL
# ============================================================

elif menu == "Base SQL":

    st.title("🗄️ Base de données SQL")

    st.write(
        """
        L'application utilise SQLite pour stocker les données
        collectées. Une table distincte est utilisée pour chaque
        source de données.
        """
    )

    tables = get_sql_tables()

    if not tables:
        st.info(
            "La base SQL ne contient encore aucune table. "
            "Lancez un scraping ou consultez les données Web Scraper."
        )

    else:

        st.success(
            f"{len(tables)} table(s) SQL disponible(s)."
        )

        for table in tables:

            with st.expander(f"📁 {table}"):

                try:
                    with get_connection() as conn:
                        df = pd.read_sql_query(
                            f'SELECT * FROM "{table}"',
                            conn
                        )

                    st.write(
                        f"{len(df)} lignes × {len(df.columns)} colonnes"
                    )

                    st.dataframe(
                        df.head(100),
                        use_container_width=True
                    )

                    st.download_button(
                        "⬇️ Télécharger la table",
                        df.to_csv(index=False).encode("utf-8"),
                        f"{table}.csv",
                        "text/csv",
                        key=f"sql_{table}",
                    )

                except Exception as exc:
                    st.error(
                        f"Erreur de lecture SQL : {exc}"
                    )

    st.divider()

    st.subheader("Schéma SQL")

    schema = pd.DataFrame({
        "Source": [
            "Selenium Books to Scrape",
            "Selenium Gaaraas",
            "Web Scraper Books to Scrape",
            "Web Scraper Gaaraas",
        ],
        "Table": [
            "selenium_books",
            "selenium_gaaraas",
            "webscraper_books",
            "webscraper_gaaraas",
        ],
    })

    st.dataframe(
        schema,
        use_container_width=True,
        hide_index=True
    )
