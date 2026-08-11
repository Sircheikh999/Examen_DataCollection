import streamlit as st
import pandas as pd
import sqlite3
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By


# =========================
# CONFIGURATION
# =========================

st.set_page_config(
    page_title="Data Collection",
    page_icon="💜",
    layout="wide"
)

BASE = Path(__file__).parent
WEB = BASE / "Web_Scraper"
DB = BASE / "data.db"


# =========================
# STYLE VIOLET
# =========================

st.markdown("""
<style>
.stApp {background:#faf7ff;}
h1,h2,h3 {color:#6d28d9;}

section[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#4c1d95,#7c3aed);
}

section[data-testid="stSidebar"] * {
    color:white !important;
}

.stButton>button,
.stDownloadButton>button {
    background:#7c3aed;
    color:white;
    border:0;
    border-radius:10px;
}

.card {
    background:white;
    padding:20px;
    border-radius:15px;
    border:1px solid #e9d5ff;
    text-align:center;
}
</style>
""", unsafe_allow_html=True)


# =========================
# SQL
# =========================

def connect():
    return sqlite3.connect(DB)


def save(df, table):
    con = connect()
    df.to_sql(table, con, if_exists="replace", index=False)
    con.close()


def read(table):
    con = connect()
    try:
        df = pd.read_sql(f"SELECT * FROM {table}", con)
    except:
        df = pd.DataFrame()
    con.close()
    return df


# =========================
# CSV BRUTS
# JSON IGNORÉS
# =========================

books_csv = WEB / "Source_1_Books_to_Scrape.csv"
gaaraas_csv = WEB / "Source_2_Gaaraas).csv"

books = pd.read_csv(books_csv)
gaaraas = pd.read_csv(gaaraas_csv)

# Initialisation de la base
if not DB.exists():
    save(books, "books")
    save(gaaraas, "gaaraas")


# =========================
# SELENIUM
# =========================

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    return webdriver.Chrome(options=options)


def scrape_books(pages):
    driver = get_driver()
    result = []

    for i in range(1, pages + 1):
        driver.get(
            f"https://books.toscrape.com/catalogue/page-{i}.html"
        )
        time.sleep(1)

        links = driver.find_elements(
            By.CSS_SELECTOR,
            "article.product_pod h3 a"
        )

        urls = [
            x.get_attribute("href")
            for x in links
        ]

        for url in urls:
            try:
                driver.get(url)

                result.append({
                    "page": i,
                    "number_of_products": len(links),
                    "title": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.product_main h1"
                    ).text,
                    "price": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.product_main p.price_color"
                    ).text,
                    "availability": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.product_main p.instock.availability"
                    ).text,
                    "star_rating": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.product_main p.star-rating"
                    ).get_attribute("class"),
                    "reviews": driver.find_element(
                        By.CSS_SELECTOR,
                        "table.table-striped tr:nth-child(7) td"
                    ).text,
                    "description": driver.find_element(
                        By.CSS_SELECTOR,
                        "#product_description + p"
                    ).text,
                    "product_type": driver.find_element(
                        By.CSS_SELECTOR,
                        "ul.breadcrumb li:nth-child(3) a"
                    ).text,
                    "tax": driver.find_element(
                        By.CSS_SELECTOR,
                        "table.table-striped tr:nth-child(5) td"
                    ).text
                })

            except:
                pass

    driver.quit()
    return pd.DataFrame(result)


def scrape_gaaraas(pages):
    driver = get_driver()
    result = []

    for i in range(1, pages + 1):

        driver.get(
            f"https://www.gaaraas.com/fr/users/dakar-auto?page={i}"
        )
        time.sleep(2)

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "a.common-ad-card"
        )

        urls = [
            card.get_attribute("href")
            for card in cards
        ]

        for url in urls:
            try:
                driver.get(url)

                result.append({
                    "page": i,
                    "number_of_ads": len(cards),
                    "marque_modele": driver.find_element(
                        By.CSS_SELECTOR,
                        ".ad-title-block h2"
                    ).text,
                    "annee": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.prop:nth-of-type(4) span:nth-of-type(2)"
                    ).text,
                    "prix": driver.find_element(
                        By.CSS_SELECTOR,
                        ".back-wrapper .ad-price span.price-wrap"
                    ).text,
                    "kilometrage": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.prop:nth-of-type(3) span:nth-of-type(2)"
                    ).text,
                    "type_boite_de_vitesse": driver.find_element(
                        By.CSS_SELECTOR,
                        "div.prop:nth-of-type(2) span:nth-of-type(2)"
                    ).text,
                    "region_de_vente": driver.find_element(
                        By.CSS_SELECTOR,
                        ".ad-title a span"
                    ).text,
                    "url": url
                })

            except:
                pass

    driver.quit()
    return pd.DataFrame(result)


# =========================
# MENU
# =========================

st.sidebar.title("💜 Data Collection")

menu = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Accueil",
        "🕷️ Scraping",
        "📁 Données brutes",
        "📊 Dashboard",
        "🗄️ Base SQL",
        "📝 Évaluation"
    ]
)


# =========================
# ACCUEIL
# =========================

if menu == "🏠 Accueil":

    st.title("💜 Data Collection")

    st.write(
        "Application de collecte, stockage et visualisation "
        "des données issues du Web Scraping."
    )

    c1, c2, c3 = st.columns(3)

    c1.markdown(
        f'<div class="card"><h3>📚 Books</h3>'
        f'<h2>{len(books)}</h2></div>',
        unsafe_allow_html=True
    )

    c2.markdown(
        f'<div class="card"><h3>🚗 Gaaraas</h3>'
        f'<h2>{len(gaaraas)}</h2></div>',
        unsafe_allow_html=True
    )

    c3.markdown(
        '<div class="card"><h3>🗄️ SQL</h3>'
        '<h2>SQLite</h2></div>',
        unsafe_allow_html=True
    )


# =========================
# SCRAPING
# =========================

elif menu == "🕷️ Scraping":

    st.title("🕷️ Scraping Selenium")

    source = st.selectbox(
        "Choisir la source",
        ["Books to Scrape", "Gaaraas"]
    )

    max_pages = 50 if source == "Books to Scrape" else 13

    pages = st.slider(
        "Nombre de pages",
        1,
        max_pages,
        min(5, max_pages)
    )

    if st.button("🚀 Lancer le scraping"):

        with st.spinner("Scraping en cours..."):

            if source == "Books to Scrape":
                df = scrape_books(pages)
                table = "books"
            else:
                df = scrape_gaaraas(pages)
                table = "gaaraas"

        if df.empty:
            st.error("Aucune donnée récupérée.")
        else:
            save(df, table)

            st.success(
                f"{len(df)} données enregistrées dans SQL."
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            st.download_button(
                "⬇️ Télécharger CSV",
                df.to_csv(index=False).encode("utf-8"),
                f"{table}_selenium.csv",
                "text/csv"
            )


# =========================
# DONNÉES BRUTES
# =========================

elif menu == "📁 Données brutes":

    st.title("📁 Données brutes Web Scraper")

    for file in [books_csv, gaaraas_csv]:

        df = pd.read_csv(file)

        with st.expander(f"📄 {file.name}"):

            st.write(
                f"{len(df)} lignes × {len(df.columns)} colonnes"
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            st.download_button(
                "⬇️ Télécharger",
                df.to_csv(index=False).encode("utf-8"),
                file.name,
                "text/csv"
            )


# =========================
# DASHBOARD
# =========================

elif menu == "📊 Dashboard":

    st.title("📊 Dashboard")

    source = st.selectbox(
        "Source",
        ["Books to Scrape", "Gaaraas"]
    )

    table = "books" if source == "Books to Scrape" else "gaaraas"
    df = read(table)

    if df.empty:
        st.warning("Aucune donnée dans la base SQL.")
    else:

        c1, c2 = st.columns(2)

        c1.metric("Observations", len(df))
        c2.metric("Variables", len(df.columns))

        st.subheader("Données nettoyées")

        df = df.fillna("Non renseigné")

        st.dataframe(
            df,
            use_container_width=True
        )

        numeric = df.select_dtypes("number")

        if not numeric.empty:

            column = st.selectbox(
                "Variable numérique",
                numeric.columns
            )

            st.subheader("📈 Visualisation")

            st.bar_chart(
                df[column],
                use_container_width=True
            )


# =========================
# BASE SQL
# =========================

elif menu == "🗄️ Base SQL":

    st.title("🗄️ Base de données SQL")

    st.write(
        "La base SQLite contient une table par source."
    )

    for table in ["books", "gaaraas"]:

        df = read(table)

        st.subheader(f"Table : {table}")

        st.metric(
            "Nombre d'enregistrements",
            len(df)
        )

        st.dataframe(
            df.head(20),
            use_container_width=True
        )

    if DB.exists():

        st.download_button(
            "⬇️ Télécharger la base SQLite",
            DB.read_bytes(),
            "data.db",
            "application/x-sqlite3"
        )


# =========================
# ÉVALUATION
# =========================

elif menu == "📝 Évaluation":

    st.title("📝 Évaluation de l'application")

    st.write(
        "Merci de prendre quelques minutes pour évaluer "
        "notre application."
    )

    st.link_button(
        "📱 Ouvrir KoboToolbox",
        "https://ee.kobotoolbox.org/"
    )

    st.link_button(
        "📝 Ouvrir Google Forms",
        "https://forms.google.com/"
    )

    st.info(
        "Les résultats des formulaires sont conservés "
        "dans le dossier Formulaire."
    )




 


