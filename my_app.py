import streamlit as st
import pandas as pd
import sqlite3
import re
from pathlib import Path
from io import StringIO
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


# =====================================================
# CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="Data Collection",
    page_icon="💜",
    layout="wide"
)

BASE = Path(__file__).parent
WEB = BASE / "Web_Scraper"
DB = BASE / "data.db"


# =====================================================
# STYLE
# =====================================================

st.markdown("""
<style>

.stApp {
    background: #f8f7fc;
    color: #27223b;
}

h1 {
    color: #4c1d95 !important;
    font-weight: 800;
}

h2, h3 {
    color: #5b21b6 !important;
}

[data-testid="stSidebar"] {
    background: #3b176d;
}

[data-testid="stSidebar"] * {
    color: white !important;
}

.card {
    background: white;
    border: 1px solid #e5d8f7;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 3px 12px rgba(76,29,149,.08);
    text-align: center;
}

.card h2 {
    color: #6d28d9 !important;
    margin: 5px;
}

.card p {
    color: #6b7280;
    margin: 0;
}

.stButton > button {
    background: #6d28d9;
    color: white;
    border: none;
    border-radius: 8px;
}

.stButton > button:hover {
    background: #4c1d95;
    color: white;
}

.stDownloadButton > button {
    background: #ede9fe;
    color: #5b21b6;
    border: 1px solid #c4b5fd;
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# LECTURE DES CSV
# =====================================================

def load_csv(path):

    text = path.read_text(
        encoding="utf-8-sig"
    )

    lines = text.splitlines()

    if not lines:
        return pd.DataFrame()

    # En-tête normal
    header = lines[0].strip()

    # Correction du format particulier produit
    # par les fichiers Web Scraper
    cleaned = [header]

    for line in lines[1:]:

        line = line.strip()

        if not line:
            continue

        # Retire les guillemets externes
        if line.startswith('"'):
            line = line[1:]

        # Retire les séparateurs ; inutiles à la fin
        line = re.sub(r';+$', '', line)

        if line.endswith('"'):
            line = line[:-1]

        # Corrige le double niveau de guillemets
        line = line.replace('""', '"')

        cleaned.append(line)

    data = "\n".join(cleaned)

    return pd.read_csv(
        StringIO(data),
        sep=",",
        quotechar='"',
        engine="python"
    )


books_file = WEB / "Source_1_Books_to_Scrape.csv"
gaaraas_file = WEB / "Source_2_Gaaraas).csv"


@st.cache_data
def get_data():

    books = load_csv(books_file)
    gaaraas = load_csv(gaaraas_file)

    return books, gaaraas


books, gaaraas = get_data()


# =====================================================
# NETTOYAGE / VARIABLES NUMERIQUES
# =====================================================

def prepare_books(df):

    df = df.copy()

    df["prix_num"] = (
        df["price"]
        .astype(str)
        .str.replace("£", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    df["rating_num"] = (
        df["star_rating"]
        .astype(str)
        .str.extract(r"(One|Two|Three|Four|Five)", expand=False)
        .map({
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5
        })
    )

    return df


def prepare_gaaraas(df):

    df = df.copy()

    df["prix_num"] = (
        df["prix"]
        .astype(str)
        .str.replace("CFA", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    df["annee_num"] = pd.to_numeric(
        df["annee"],
        errors="coerce"
    )

    df["kilometrage_num"] = (
        df["kilometrage"]
        .astype(str)
        .str.replace("km", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace("nan", None)
    )

    df["kilometrage_num"] = pd.to_numeric(
        df["kilometrage_num"],
        errors="coerce"
    )

    return df


books_clean = prepare_books(books)
gaaraas_clean = prepare_gaaraas(gaaraas)


# =====================================================
# BASE SQL
# =====================================================

def save_sql(df, table):

    con = sqlite3.connect(DB)

    df.to_sql(
        table,
        con,
        if_exists="replace",
        index=False
    )

    con.close()


def read_sql(table):

    con = sqlite3.connect(DB)

    try:
        df = pd.read_sql(
            f"SELECT * FROM {table}",
            con
        )
    except:
        df = pd.DataFrame()

    con.close()

    return df


# Création de la base
if not DB.exists():

    save_sql(
        books_clean,
        "books"
    )

    save_sql(
        gaaraas_clean,
        "gaaraas"
    )


# =====================================================
# SELENIUM
# =====================================================

def get_driver():

    options = webdriver.ChromeOptions()

    options.add_argument(
        "--headless=new"
    )

    options.add_argument(
        "--no-sandbox"
    )

    options.add_argument(
        "--disable-dev-shm-usage"
    )

    options.add_argument(
        "--window-size=1920,1080"
    )

    return webdriver.Chrome(
        options=options
    )


def scrape_books(pages):

    driver = get_driver()

    data = []

    for page in range(1, pages + 1):

        driver.get(
            f"https://books.toscrape.com/catalogue/page-{page}.html"
        )

        time.sleep(1)

        products = driver.find_elements(
            By.CSS_SELECTOR,
            "article.product_pod"
        )

        for product in products:

            try:

                data.append({

                    "page": page,

                    "title": product.find_element(
                        By.CSS_SELECTOR,
                        "h3 a"
                    ).get_attribute("title"),

                    "price": product.find_element(
                        By.CSS_SELECTOR,
                        ".price_color"
                    ).text,

                    "availability": product.find_element(
                        By.CSS_SELECTOR,
                        ".availability"
                    ).text.strip(),

                    "star_rating": product.find_element(
                        By.CSS_SELECTOR,
                        "p.star-rating"
                    ).get_attribute("class")

                })

            except:
                continue

    driver.quit()

    return pd.DataFrame(data)


def scrape_gaaraas(pages):

    driver = get_driver()

    data = []

    for page in range(1, pages + 1):

        driver.get(
            f"https://www.gaaraas.com/fr/users/dakar-auto?page={page}"
        )

        time.sleep(2)

        cards = driver.find_elements(
            By.CSS_SELECTOR,
            "a.common-ad-card"
        )

        for card in cards:

            try:

                data.append({

                    "page": page,

                    "url": card.get_attribute(
                        "href"
                    ),

                    "annonce": card.text

                })

            except:
                continue

    driver.quit()

    return pd.DataFrame(data)


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.markdown(
    "# 💜 Data Collection"
)

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


# =====================================================
# ACCUEIL
# =====================================================

if menu == "🏠 Accueil":

    st.title(
        "💜 Data Collection Dashboard"
    )

    st.write(
        "Collecte, traitement, stockage et "
        "visualisation des données Web."
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.markdown(
        f"""
        <div class="card">
        <p>Livres</p>
        <h2>{len(books):,}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c2.markdown(
        f"""
        <div class="card">
        <p>Véhicules</p>
        <h2>{len(gaaraas):,}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c3.markdown(
        f"""
        <div class="card">
        <p>Colonnes Books</p>
        <h2>{len(books.columns)}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c4.markdown(
        f"""
        <div class="card">
        <p>Colonnes Gaaraas</p>
        <h2>{len(gaaraas.columns)}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader(
        "📌 Sources de données"
    )

    a, b = st.columns(2)

    with a:

        st.info(
            "**📚 Books to Scrape**\n\n"
            "Données bibliographiques : titre, prix, "
            "disponibilité, évaluation, description, "
            "type de produit et taxe."
        )

    with b:

        st.info(
            "**🚗 Gaaraas**\n\n"
            "Données automobiles : marque/modèle, année, "
            "prix, kilométrage, boîte de vitesse et région."
        )


# =====================================================
# SCRAPING
# =====================================================

elif menu == "🕷️ Scraping":

    st.title(
        "🕷️ Scraping Selenium"
    )

    source = st.selectbox(
        "Source",
        [
            "Books to Scrape",
            "Gaaraas"
        ]
    )

    maximum = (
        50
        if source == "Books to Scrape"
        else 13
    )

    pages = st.slider(
        "Nombre de pages",
        1,
        maximum,
        min(5, maximum)
    )

    if st.button(
        "🚀 Lancer le scraping"
    ):

        with st.spinner(
            "Collecte des données..."
        ):

            if source == "Books to Scrape":

                df = scrape_books(pages)
                table = "books"

            else:

                df = scrape_gaaraas(pages)
                table = "gaaraas"

        if df.empty:

            st.error(
                "Aucune donnée récupérée."
            )

        else:

            save_sql(
                df,
                table
            )

            st.success(
                f"{len(df)} lignes collectées."
            )

            st.dataframe(
                df,
                use_container_width=True
            )

            st.download_button(
                "⬇️ Télécharger les données",
                df.to_csv(
                    index=False
                ).encode("utf-8"),
                f"{table}_selenium.csv",
                "text/csv"
            )


# =====================================================
# DONNEES BRUTES
# =====================================================

elif menu == "📁 Données brutes":

    st.title(
        "📁 Données brutes"
    )

    st.caption(
        "Données issues du scraping Web Scraper — "
        "les fichiers JSON sont volontairement ignorés."
    )

    source = st.selectbox(
        "Choisir la source",
        [
            "Books to Scrape",
            "Gaaraas"
        ]
    )

    df = (
        books
        if source == "Books to Scrape"
        else gaaraas
    )

    st.metric(
        "Nombre de lignes",
        len(df)
    )

    st.metric(
        "Nombre de colonnes",
        len(df.columns)
    )

    st.subheader(
        "Colonnes disponibles"
    )

    st.write(
        list(df.columns)
    )

    st.subheader(
        "Aperçu des données"
    )

    st.dataframe(
        df,
        use_container_width=True,
        height=500
    )

    st.download_button(
        "⬇️ Télécharger le CSV",
        df.to_csv(
            index=False
        ).encode("utf-8"),
        f"{source}.csv",
        "text/csv"
    )


# =====================================================
# DASHBOARD
# =====================================================

elif menu == "📊 Dashboard":

    st.title(
        "📊 Dashboard"
    )

    source = st.selectbox(
        "Source",
        [
            "📚 Books to Scrape",
            "🚗 Gaaraas"
        ]
    )

    if source == "📚 Books to Scrape":

        df = books_clean

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Livres",
            len(df)
        )

        c2.metric(
            "Prix moyen",
            f"£{df.prix_num.mean():.2f}"
        )

        c3.metric(
            "Prix minimum",
            f"£{df.prix_num.min():.2f}"
        )

        c4.metric(
            "Prix maximum",
            f"£{df.prix_num.max():.2f}"
        )

        st.divider()

        a, b = st.columns(2)

        with a:

            st.subheader(
                "📚 Livres par catégorie"
            )

            categories = (
                df["product_type"]
                .value_counts()
                .head(10)
            )

            st.bar_chart(
                categories
            )

        with b:

            st.subheader(
                "💰 Distribution des prix"
            )

            st.bar_chart(
                df["prix_num"]
                .head(30)
            )

        st.subheader(
            "📋 Données"
        )

        st.dataframe(
            df,
            use_container_width=True
        )

    else:

        df = gaaraas_clean

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Véhicules",
            len(df)
        )

        c2.metric(
            "Prix moyen",
            f"{df.prix_num.mean():,.0f} CFA"
        )

        c3.metric(
            "Prix minimum",
            f"{df.prix_num.min():,.0f} CFA"
        )

        c4.metric(
            "Prix maximum",
            f"{df.prix_num.max():,.0f} CFA"
        )

        st.divider()

        a, b = st.columns(2)

        with a:

            st.subheader(
                "🚗 Marques / modèles"
            )

            models = (
                df["marque_modele"]
                .value_counts()
                .head(10)
            )

            st.bar_chart(
                models
            )

        with b:

            st.subheader(
                "⚙️ Boîte de vitesse"
            )

            gearbox = (
                df["type_boite_de_vitesse"]
                .value_counts()
            )

            st.bar_chart(
                gearbox
            )

        st.subheader(
            "📋 Données automobiles"
        )

        st.dataframe(
            df,
            use_container_width=True
        )


# =====================================================
# SQL
# =====================================================

elif menu == "🗄️ Base SQL":

    st.title(
        "🗄️ Base de données SQL"
    )

    st.write(
        "La base SQLite contient une table par source."
    )

    for table in [
        "books",
        "gaaraas"
    ]:

        df = read_sql(table)

        st.subheader(
            f"Table : {table}"
        )

        st.metric(
            "Enregistrements",
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


# =====================================================
# EVALUATION
# =====================================================

elif menu == "📝 Évaluation":

    st.title(
        "📝 Évaluation de l'application"
    )

    st.write(
        "Votre avis nous aide à améliorer "
        "l'application."
    )

    c1, c2 = st.columns(2)

    with c1:

        st.subheader(
            "📱 KoboToolbox"
        )

        st.link_button(
            "Ouvrir le formulaire Kobo",
            "https://ee.kobotoolbox.org/"
        )

    with c2:

        st.subheader(
            "📝 Google Forms"
        )

        st.link_button(
            "Ouvrir Google Forms",
            "https://forms.google.com/"
        )



 


