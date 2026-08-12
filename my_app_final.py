import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# CONFIGURATION

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

# Fichiers finaux utilisés.
BOOKS_CSV = WEB_SCRAPER_DIR / "Source_1_Books_to_Scrape.csv"
GAARAAS_CSV = WEB_SCRAPER_DIR / "Source_2_Gaaraas).csv"

# Les JSON du dossier Web_Scraper sont volontairement ignorés.

# Liens directs des formulaires.
GOOGLE_FORM_URL = (
    "https://docs.google.com/forms/d/e/"
    "1FAIpQLSc7F8m3eBJkCqpOUa4pTQX0zyIov_4LWXRYOV3XKbmi0vJJoQ/"
    "viewform?usp=publish-editor"
)
KOBO_FORM_URL = "https://ee.kobotoolbox.org/i/1zbGqqaq"

# BASE SQL

def get_connection():
    return sqlite3.connect(DB_PATH)


def save_to_sql(df, table_name):
    if df is None or df.empty:
        return

    with get_connection() as conn:
        df.to_sql(
            table_name,
            conn,
            if_exists="replace",
            index=False
        )


def get_sql_tables():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()

    return [row[0] for row in rows]

# LECTURE CSV

def read_csv_file(path):
    if not path.exists():
        return None

    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read_csv(
                path,
                encoding=encoding,
                on_bad_lines="skip"
            )
        except Exception:
            continue

    return None

# SELENIUM

def create_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    options = Options()

    for binary in (
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ):
        if Path(binary).exists():
            options.binary_location = binary
            break

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")

    return webdriver.Chrome(options=options)

# SELENIUM - BOOKS TO SCRAPE

def scrape_books(start_page=1, end_page=50):

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = create_driver()
    records = []

    try:
        progress = st.progress(0)
        total_pages = end_page - start_page + 1

        for position, page in enumerate(
            range(start_page, end_page + 1),
            start=1
        ):
            url = (
                f"https://books.toscrape.com/"
                f"catalogue/page-{page}.html"
            )

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
                By.CSS_SELECTOR,
                "article.product_pod"
            )

            links = []

            for product in products:
                try:
                    href = product.find_element(
                        By.CSS_SELECTOR,
                        "h3 a"
                    ).get_attribute("href")

                    if href:
                        links.append(href)
                except Exception:
                    continue

            for product_url in links:

                try:
                    driver.get(product_url)

                    def text(css, default=""):
                        try:
                            return driver.find_element(
                                By.CSS_SELECTOR,
                                css
                            ).text.strip()
                        except Exception:
                            return default

                    try:
                        rating_class = driver.find_element(
                            By.CSS_SELECTOR,
                            "div.product_main p.star-rating"
                        ).get_attribute("class")
                    except Exception:
                        rating_class = ""

                    records.append({
                        "page": page,
                        "number_of_products": len(products),
                        "title": text(
                            "div.product_main h1"
                        ),
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

            progress.progress(position / total_pages)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)

# SELENIUM - GAARAAS

def scrape_gaaraas(start_page=1, end_page=13):

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    driver = create_driver()
    records = []

    try:
        progress = st.progress(0)
        total_pages = end_page - start_page + 1

        for position, page in enumerate(
            range(start_page, end_page + 1),
            start=1
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
                                By.CSS_SELECTOR,
                                css
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

            progress.progress(position / total_pages)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)

# NETTOYAGE

def clean_books(df):

    df = df.copy()

    for col in df.select_dtypes(
        include="object"
    ).columns:
        df[col] = df[col].astype(str).str.strip()

    if "price" in df.columns:
        df["price_numeric"] = pd.to_numeric(
            df["price"]
            .astype(str)
            .str.replace("£", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce"
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

    for col in df.select_dtypes(
        include="object"
    ).columns:
        df[col] = df[col].astype(str).str.strip()

    if "annee" in df.columns:
        df["annee_numeric"] = pd.to_numeric(
            df["annee"],
            errors="coerce"
        )

    if "prix" in df.columns:
        df["prix_numeric"] = pd.to_numeric(
            df["prix"]
            .astype(str)
            .str.replace("CFA", "", regex=False)
            .str.replace("FCFA", "", regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.strip(),
            errors="coerce"
        )

    if "kilometrage" in df.columns:
        df["kilometrage_numeric"] = pd.to_numeric(
            df["kilometrage"]
            .astype(str)
            .str.replace("km", "", case=False, regex=False)
            .str.replace("\u00a0", "", regex=False)
            .str.replace(" ", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.strip(),
            errors="coerce"
        )

    return df.drop_duplicates().reset_index(drop=True)


# ============================================================
# SESSION STATE
# ============================================================

if "books_selenium" not in st.session_state:
    st.session_state.books_selenium = None

if "gaaraas_selenium" not in st.session_state:
    st.session_state.gaaraas_selenium = None

# SIDEBAR

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
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("Projet Examen Data Collection")

# ACCUEIL

if menu == "Accueil":

    st.title("📊 Application Data Collection")

    st.markdown(
        """
        ### Objectif

        Cette application regroupe les différentes étapes du projet :

        - 🕷️ collecte avec **Selenium** sur plusieurs pages ;
        - 📥 téléchargement des données brutes **Web Scraper** ;
        - 🧹 nettoyage des données Selenium ;
        - 📊 dashboard des données nettoyées ;
        - 📝 accès aux formulaires d'évaluation ;
        - 🗄️ stockage SQL.

        **Les fichiers JSON sont volontairement ignorés.**
        """
    )

    st.success("Application prête.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "CSV Web Scraper",
            sum(
                path.exists()
                for path in [BOOKS_CSV, GAARAAS_CSV]
            )
        )

    with c2:
        st.metric(
            "Sources Selenium",
            2
        )

    with c3:
        st.metric(
            "Formulaires",
            2
        )

# SCRAPING SELENIUM

elif menu == "Scraping Selenium":

    st.title("🕷️ Scraping Selenium")

    tab_books, tab_gaaraas = st.tabs(
        [
            "📚 Books to Scrape",
            "🚗 Gaaraas"
        ]
    )

    # BOOKS

    with tab_books:

        st.subheader("📚 Books to Scrape")

        col1, col2 = st.columns(2)

        with col1:
            start_books = st.number_input(
                "Première page",
                min_value=1,
                max_value=50,
                value=1,
                step=1,
                key="start_books"
            )

        with col2:
            end_books = st.number_input(
                "Dernière page",
                min_value=1,
                max_value=50,
                value=50,
                step=1,
                key="end_books"
            )

        if st.button(
            "🚀 Lancer le scraping Books to Scrape",
            type="primary",
            use_container_width=True
        ):

            if start_books > end_books:

                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )

            else:

                try:

                    with st.spinner(
                        "Scraping Books to Scrape..."
                    ):

                        raw_books = scrape_books(
                            start_books,
                            end_books
                        )

                        books = clean_books(
                            raw_books
                        )

                    st.session_state.books_selenium = books

                    save_to_sql(
                        books,
                        "selenium_books"
                    )

                    st.success(
                        f"{len(books)} livres collectés."
                    )

                except Exception as exc:

                    st.error(
                        f"Erreur Selenium : {exc}"
                    )

        if st.session_state.books_selenium is not None:

            books = st.session_state.books_selenium

            st.metric(
                "Livres collectés",
                len(books)
            )

            st.dataframe(
                books,
                use_container_width=True,
                height=450
            )

            st.download_button(
                "⬇️ Télécharger les données nettoyées",
                books.to_csv(index=False).encode("utf-8"),
                "books_selenium_clean.csv",
                "text/csv",
                use_container_width=True
            )

    # GAARAAS

    with tab_gaaraas:

        st.subheader("🚗 Gaaraas")

        col1, col2 = st.columns(2)

        with col1:
            start_gaaraas = st.number_input(
                "Première page",
                min_value=1,
                max_value=13,
                value=1,
                step=1,
                key="start_gaaraas"
            )

        with col2:
            end_gaaraas = st.number_input(
                "Dernière page",
                min_value=1,
                max_value=13,
                value=13,
                step=1,
                key="end_gaaraas"
            )

        if st.button(
            "🚀 Lancer le scraping Gaaraas",
            type="primary",
            use_container_width=True
        ):

            if start_gaaraas > end_gaaraas:

                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )

            else:

                try:

                    with st.spinner(
                        "Scraping Gaaraas..."
                    ):

                        raw_gaaraas = scrape_gaaraas(
                            start_gaaraas,
                            end_gaaraas
                        )

                        gaaraas = clean_gaaraas(
                            raw_gaaraas
                        )

                    st.session_state.gaaraas_selenium = gaaraas

                    save_to_sql(
                        gaaraas,
                        "selenium_gaaraas"
                    )

                    st.success(
                        f"{len(gaaraas)} annonces collectées."
                    )

                except Exception as exc:

                    st.error(
                        f"Erreur Selenium : {exc}"
                    )

        if st.session_state.gaaraas_selenium is not None:

            gaaraas = st.session_state.gaaraas_selenium

            st.metric(
                "Annonces collectées",
                len(gaaraas)
            )

            st.dataframe(
                gaaraas,
                use_container_width=True,
                height=450
            )

            st.download_button(
                "⬇️ Télécharger les données nettoyées",
                gaaraas.to_csv(index=False).encode("utf-8"),
                "gaaraas_selenium_clean.csv",
                "text/csv",
                use_container_width=True
            )

# DONNEES WEB SCRAPER

elif menu == "Données Web Scraper":

    st.title("📥 Données brutes Web Scraper")

    files = [
        BOOKS_CSV,
        GAARAAS_CSV
    ]

    found_files = [
        path for path in files
        if path.exists()
    ]

    if not found_files:

        st.warning(
            "Aucun des deux fichiers CSV n'a été trouvé."
        )

    for path in found_files:

        st.subheader(
            f"📄 {path.name}"
        )

        df = read_csv_file(path)

        if df is None:

            st.error(
                f"Impossible de lire {path.name}."
            )

            continue

        c1, c2 = st.columns(2)

        with c1:
            st.metric(
                "Lignes",
                df.shape[0]
            )

        with c2:
            st.metric(
                "Colonnes",
                df.shape[1]
            )

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
            use_container_width=True
        )

        if path.name == BOOKS_CSV.name:

            save_to_sql(
                df,
                "webscraper_books"
            )

        elif path.name == GAARAAS_CSV.name:

            save_to_sql(
                df,
                "webscraper_gaaraas"
            )

# DASHBOARD

elif menu == "Dashboard":

    st.title(
        "📊 Dashboard des données Selenium nettoyées"
    )

    books = st.session_state.books_selenium
    gaaraas = st.session_state.gaaraas_selenium

    if books is None and gaaraas is None:

        st.warning(
            "Aucune donnée Selenium disponible. "
            "Lancez le scraping dans la section Selenium."
        )

    # BOOKS

    if books is not None:

        st.header("📚 Books to Scrape")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Livres",
                len(books)
            )

        with c2:

            if "price_numeric" in books:

                value = books[
                    "price_numeric"
                ].mean()

                st.metric(
                    "Prix moyen",
                    f"£{value:.2f}"
                    if pd.notna(value)
                    else "N/A"
                )

            else:

                st.metric(
                    "Prix moyen",
                    "N/A"
                )

        with c3:

            if "rating" in books:

                value = books[
                    "rating"
                ].mean()

                st.metric(
                    "Note moyenne",
                    f"{value:.2f}/5"
                    if pd.notna(value)
                    else "N/A"
                )

            else:

                st.metric(
                    "Note moyenne",
                    "N/A"
                )

        with c4:

            if "product_type" in books:

                st.metric(
                    "Types de produits",
                    books[
                        "product_type"
                    ].nunique()
                )

            else:

                st.metric(
                    "Types de produits",
                    0
                )

        left, right = st.columns(2)

        with left:

            if "product_type" in books:

                st.subheader(
                    "Top catégories"
                )

                st.bar_chart(
                    books[
                        "product_type"
                    ]
                    .value_counts()
                    .head(10)
                )

        with right:

            if "rating" in books:

                st.subheader(
                    "Répartition des notes"
                )

                st.bar_chart(
                    books[
                        "rating"
                    ]
                    .value_counts()
                    .sort_index()
                )

        with st.expander(
            "Voir les données Books nettoyées"
        ):

            st.dataframe(
                books,
                use_container_width=True
            )

    # GAARAAS

    if gaaraas is not None:

        st.divider()

        st.header("🚗 Gaaraas")

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Annonces",
                len(gaaraas)
            )

        with c2:

            if "prix_numeric" in gaaraas:

                value = gaaraas[
                    "prix_numeric"
                ].mean()

                st.metric(
                    "Prix moyen",
                    f"{value:,.0f} FCFA"
                    if pd.notna(value)
                    else "N/A"
                )

            else:

                st.metric(
                    "Prix moyen",
                    "N/A"
                )

        with c3:

            if "annee_numeric" in gaaraas:

                value = gaaraas[
                    "annee_numeric"
                ].mean()

                st.metric(
                    "Année moyenne",
                    f"{value:.0f}"
                    if pd.notna(value)
                    else "N/A"
                )

            else:

                st.metric(
                    "Année moyenne",
                    "N/A"
                )

        with c4:

            if "kilometrage_numeric" in gaaraas:

                value = gaaraas[
                    "kilometrage_numeric"
                ].mean()

                st.metric(
                    "Kilométrage moyen",
                    f"{value:,.0f} km"
                    if pd.notna(value)
                    else "N/A"
                )

            else:

                st.metric(
                    "Kilométrage moyen",
                    "N/A"
                )

        left, right = st.columns(2)

        with left:

            if "marque_modele" in gaaraas:

                st.subheader(
                    "Top marques / modèles"
                )

                st.bar_chart(
                    gaaraas[
                        "marque_modele"
                    ]
                    .value_counts()
                    .head(10)
                )

        with right:

            if "annee_numeric" in gaaraas:

                st.subheader(
                    "Répartition par année"
                )

                st.bar_chart(
                    gaaraas[
                        "annee_numeric"
                    ]
                    .value_counts()
                    .sort_index()
                )

        with st.expander(
            "Voir les données Gaaraas nettoyées"
        ):

            st.dataframe(
                gaaraas,
                use_container_width=True
            )

# FORMULAIRES D'EVALUATION

elif menu == "Formulaires d'évaluation":

    st.title("📝 Formulaires d'évaluation")

    st.subheader("📋 Google Forms")

    st.link_button(
        "📝 Ouvrir le formulaire Google Forms",
        GOOGLE_FORM_URL,
        use_container_width=True
    )

    st.divider()

    st.subheader("📋 KoboToolbox")

    st.link_button(
        "📝 Ouvrir le formulaire KoboToolbox",
        KOBO_FORM_URL,
        use_container_width=True
    )

# BASE SQL

elif menu == "Base SQL":

    st.title("🗄️ Base de données SQL")

    st.write(
        """
        Les données collectées sont stockées dans une base SQLite.

        Les tables utilisées sont :

        - `selenium_books`
        - `selenium_gaaraas`
        - `webscraper_books`
        - `webscraper_gaaraas`
        """
    )

    tables = get_sql_tables()

    if not tables:

        st.info(
            "La base SQL est actuellement vide. "
            "Lancez une collecte ou consultez les données "
            "Web Scraper pour l'alimenter."
        )

    else:

        st.success(
            f"{len(tables)} table(s) disponible(s)."
        )

        for table in tables:

            with st.expander(
                f"📁 {table}"
            ):

                try:

                    with get_connection() as conn:

                        df = pd.read_sql_query(
                            f'SELECT * FROM "{table}"',
                            conn
                        )

                    st.write(
                        f"{len(df)} lignes × "
                        f"{len(df.columns)} colonnes"
                    )

                    st.dataframe(
                        df.head(100),
                        use_container_width=True
                    )

                    st.download_button(
                        "⬇️ Télécharger la table",
                        df.to_csv(
                            index=False
                        ).encode("utf-8"),
                        f"{table}.csv",
                        "text/csv",
                        key=f"sql_{table}"
                    )

                except Exception as exc:

                    st.error(
                        f"Erreur SQL : {exc}"
                    )

    st.divider()

    st.subheader(
        "Structure des sources"
    )

    schema = pd.DataFrame({
        "Source": [
            "Selenium Books to Scrape",
            "Selenium Gaaraas",
            "Web Scraper Books to Scrape",
            "Web Scraper Gaaraas",
        ],
        "Table SQL": [
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
