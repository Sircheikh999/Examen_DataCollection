import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
import time


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
# STYLE
# =========================

st.markdown("""
<style>
.stApp {
    background: #faf7ff;
}

h1, h2, h3 {
    color: #6d28d9;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#4c1d95,#7c3aed);
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

.stButton button,
.stDownloadButton button {
    background: #7c3aed;
    color: white;
    border: none;
    border-radius: 10px;
}

.card {
    background: white;
    padding: 20px;
    border-radius: 15px;
    border: 1px solid #e9d5ff;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)


# =========================
# LECTURE CSV
# =========================

def load_csv(file):
    try:
        return pd.read_csv(
            file,
            sep=None,
            engine="python",
            encoding="utf-8",
            on_bad_lines="skip"
        )
    except UnicodeDecodeError:
        return pd.read_csv(
            file,
            sep=None,
            engine="python",
            encoding="latin1",
            on_bad_lines="skip"
        )


books_file = WEB / "Source_1_Books_to_Scrape.csv"
gaaraas_file = WEB / "Source_2_Gaaraas).csv"


# =========================
# BASE SQL
# =========================

def connect():
    return sqlite3.connect(DB)


def save_sql(df, table):
    con = connect()
    df.to_sql(table, con, if_exists="replace", index=False)
    con.close()


def read_sql(table):
    con = connect()

    try:
        df = pd.read_sql(
            f"SELECT * FROM {table}",
            con
        )
    except:
        df = pd.DataFrame()

    con.close()
    return df


# =========================
# DONNÉES INITIALES
# =========================

books = load_csv(books_file)
gaaraas = load_csv(gaaraas_file)

if not DB.exists():
    save_sql(books, "books")
    save_sql(gaaraas, "gaaraas")


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

                    "rating": product.find_element(
                        By.CSS_SELECTOR,
                        "p.star-rating"
                    ).get_attribute("class")
                })

            except:
                pass

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
                    "url": card.get_attribute("href"),
                    "annonce": card.text
                })

            except:
                pass

    driver.quit()

    return pd.DataFrame(data)


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
        "Application de collecte, nettoyage, stockage "
        "et visualisation des données."
    )

    c1, c2, c3 = st.columns(3)

    c1.markdown(
        f"""
        <div class="card">
        <h3>📚 Books</h3>
        <h2>{len(books)}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c2.markdown(
        f"""
        <div class="card">
        <h3>🚗 Gaaraas</h3>
        <h2>{len(gaaraas)}</h2>
        </div>
        """,
        unsafe_allow_html=True
    )

    c3.markdown(
        """
        <div class="card">
        <h3>🗄️ Base SQL</h3>
        <h2>SQLite</h2>
        </div>
        """,
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

            save_sql(df, table)

            st.success(
                f"{len(df)} lignes enregistrées dans la table {table}."
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

    st.title("📁 Données brutes")

    st.info(
        "Seuls les fichiers CSV du dossier Web_Scraper "
        "sont utilisés. Les fichiers JSON sont ignorés."
    )

    for file in [books_file, gaaraas_file]:

        df = load_csv(file)

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
        "Choisir la source",
        ["Books to Scrape", "Gaaraas"]
    )

    table = (
        "books"
        if source == "Books to Scrape"
        else "gaaraas"
    )

    df = read_sql(table)

    if df.empty:

        st.warning(
            "Aucune donnée disponible."
        )

    else:

        # Nettoyage
        for col in df.columns:

            if pd.api.types.is_numeric_dtype(df[col]):

                df[col] = df[col].fillna(
                    df[col].median()
                )

            else:

                df[col] = df[col].fillna(
                    "Non renseigné"
                )

        c1, c2 = st.columns(2)

        c1.metric(
            "Observations",
            len(df)
        )

        c2.metric(
            "Variables",
            len(df.columns)
        )

        st.subheader("📋 Données nettoyées")

        st.dataframe(
            df,
            use_container_width=True
        )

        numeric = df.select_dtypes(
            include="number"
        )

        if not numeric.empty:

            st.subheader("📈 Visualisation")

            column = st.selectbox(
                "Choisir une variable",
                numeric.columns
            )

            st.bar_chart(
                df[column]
            )


# =========================
# BASE SQL
# =========================

elif menu == "🗄️ Base SQL":

    st.title("🗄️ Base de données SQL")

    st.write(
        "La base SQLite contient une table pour "
        "chaque source de données."
    )

    for table in ["books", "gaaraas"]:

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
            "⬇️ Télécharger data.db",
            DB.read_bytes(),
            "data.db",
            "application/x-sqlite3"
        )


# =========================
# ÉVALUATION
# =========================

elif menu == "📝 Évaluation":

    st.title("📝 Évaluation")

    st.write(
        "Merci de donner votre avis sur l'application."
    )

    st.link_button(
        "📱 KoboToolbox",
        "https://ee.kobotoolbox.org/"
    )

    st.link_button(
        "📝 Google Forms",
        "https://forms.google.com/"
    )



 


