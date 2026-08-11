```python
import streamlit as st
import pandas as pd
import numpy as np
import os
import io
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Data Collection Dashboard",
    page_icon="💜",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# STYLE VIOLET
# ============================================================

st.markdown("""
<style>

    /* ==============================
       GENERAL
       ============================== */

    .stApp {
        background: #faf8ff;
    }

    .main {
        background: #faf8ff;
    }

    h1, h2, h3 {
        color: #5b21b6;
    }

    p {
        color: #374151;
    }

    /* ==============================
       SIDEBAR
       ============================== */

    section[data-testid="stSidebar"] {
        background: linear-gradient(
            180deg,
            #4c1d95 0%,
            #6d28d9 45%,
            #7c3aed 100%
        );
    }

    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* ==============================
       TITRE
       ============================== */

    .main-title {
        font-size: 42px;
        font-weight: 800;
        color: #5b21b6;
        margin-bottom: 5px;
    }

    .subtitle {
        font-size: 17px;
        color: #6b7280;
        margin-bottom: 30px;
    }

    /* ==============================
       CARDS
       ============================== */

    .metric-card {
        background: white;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid #e9d5ff;
        box-shadow: 0px 5px 20px rgba(91, 33, 182, 0.08);
        text-align: center;
        margin-bottom: 15px;
    }

    .metric-title {
        color: #6b7280;
        font-size: 14px;
        font-weight: 600;
    }

    .metric-value {
        color: #5b21b6;
        font-size: 30px;
        font-weight: 800;
        margin-top: 5px;
    }

    /* ==============================
       INFO BOX
       ============================== */

    .info-box {
        background: #f3e8ff;
        border-left: 5px solid #7c3aed;
        padding: 18px;
        border-radius: 12px;
        margin: 15px 0;
    }

    /* ==============================
       DATASET CARD
       ============================== */

    .dataset-card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e9d5ff;
        box-shadow: 0px 4px 15px rgba(91, 33, 182, 0.06);
        margin-bottom: 15px;
    }

    /* ==============================
       BUTTONS
       ============================== */

    .stButton > button {
        background: #7c3aed;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background: #5b21b6;
        color: white;
    }

    /* ==============================
       DOWNLOAD BUTTON
       ============================== */

    .stDownloadButton > button {
        background: #6d28d9;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
    }

    .stDownloadButton > button:hover {
        background: #4c1d95;
        color: white;
    }

    /* ==============================
       TABS
       ============================== */

    button[data-baseweb="tab"] {
        color: #5b21b6 !important;
        font-weight: 600;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #7c3aed !important;
    }

    /* ==============================
       LINKS
       ============================== */

    a {
        color: #7c3aed !important;
        font-weight: 600;
    }

</style>
""", unsafe_allow_html=True)


# ============================================================
# CHEMINS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

COLAB_DIR = BASE_DIR / "Colab"
WEB_SCRAPER_DIR = BASE_DIR / "Web_Scraper"
FORMULAIRE_DIR = BASE_DIR / "Formulaire"


# ============================================================
# FONCTIONS UTILITAIRES
# ============================================================

def clean_dataframe(df):
    """
    Nettoyage générique des données.
    Les colonnes numériques utilisent la médiane.
    Les colonnes booléennes utilisent False.
    Les autres colonnes utilisent 'Non renseigné'.
    """

    df = df.copy()

    for col in df.columns:

        if pd.api.types.is_numeric_dtype(df[col]):

            median_value = df[col].median()

            if pd.isna(median_value):
                median_value = 0

            df[col] = df[col].fillna(median_value)

        elif pd.api.types.is_bool_dtype(df[col]):

            df[col] = df[col].fillna(False)

        else:

            df[col] = df[col].fillna("Non renseigné")

    return df


def load_csv_files():

    """
    Charge uniquement les fichiers CSV du dossier Web_Scraper.
    Les fichiers JSON sont volontairement ignorés.
    """

    datasets = {}

    if not WEB_SCRAPER_DIR.exists():
        return datasets

    for file in WEB_SCRAPER_DIR.glob("*.csv"):

        try:

            df = pd.read_csv(file)

            datasets[file.name] = df

        except Exception as e:

            st.warning(
                f"Impossible de lire {file.name}: {e}"
            )

    return datasets


def create_driver():

    """
    Création d'un navigateur Chrome/Chromium
    compatible avec un environnement Streamlit Cloud.
    """

    options = Options()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")

    options.add_argument(
        "--user-agent=Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)

    return driver


# ============================================================
# SCRAPING BOOKS TO SCRAPE
# ============================================================

@st.cache_data(show_spinner=False)
def scrape_books(max_pages):

    url_base = "https://books.toscrape.com/catalogue/page-{}.html"

    data = []

    driver = None

    try:

        driver = create_driver()

        for page in range(1, max_pages + 1):

            url = url_base.format(page)

            driver.get(url)

            try:

                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "article.product_pod")
                    )
                )

            except Exception:

                continue

            products = driver.find_elements(
                By.CSS_SELECTOR,
                "article.product_pod"
            )

            for product in products:

                try:

                    title = product.find_element(
                        By.CSS_SELECTOR,
                        "h3 a"
                    ).get_attribute("title")

                except Exception:

                    title = "Non renseigné"

                try:

                    price = product.find_element(
                        By.CSS_SELECTOR,
                        ".price_color"
                    ).text

                except Exception:

                    price = "Non renseigné"

                try:

                    availability = product.find_element(
                        By.CSS_SELECTOR,
                        ".availability"
                    ).text.strip()

                except Exception:

                    availability = "Non renseigné"

                try:

                    rating_element = product.find_element(
                        By.CSS_SELECTOR,
                        "p.star-rating"
                    )

                    rating = rating_element.get_attribute(
                        "class"
                    ).replace("star-rating", "").strip()

                except Exception:

                    rating = "Non renseigné"

                try:

                    product_url = product.find_element(
                        By.CSS_SELECTOR,
                        "h3 a"
                    ).get_attribute("href")

                except Exception:

                    product_url = "Non renseigné"

                data.append({
                    "Titre": title,
                    "Prix": price,
                    "Disponibilité": availability,
                    "Évaluation": rating,
                    "URL": product_url,
                    "Page": page
                })

    except Exception as e:

        return pd.DataFrame(), str(e)

    finally:

        if driver:

            driver.quit()

    return pd.DataFrame(data), None


# ============================================================
# SCRAPING GAARAAS
# ============================================================

@st.cache_data(show_spinner=False)
def scrape_gaaraas(max_pages):

    """
    Scraping multi-pages du site Gaaraas.

    Les sélecteurs sont volontairement robustes afin de
    fonctionner avec différentes structures de cartes.
    """

    url_base = "https://gaaraas.com/vehicles?page={}"

    data = []

    driver = None

    try:

        driver = create_driver()

        for page in range(1, max_pages + 1):

            url = url_base.format(page)

            driver.get(url)

            time.sleep(2)

            cards = driver.find_elements(
                By.CSS_SELECTOR,
                "a"
            )

            for card in cards:

                try:

                    text = card.text.strip()

                    if not text:
                        continue

                    href = card.get_attribute("href")

                    if not href:
                        continue

                    if "gaaraas" not in href.lower():
                        continue

                    data.append({
                        "Informations": text,
                        "URL": href,
                        "Page": page
                    })

                except Exception:

                    continue

    except Exception as e:

        return pd.DataFrame(), str(e)

    finally:

        if driver:

            driver.quit()

    df = pd.DataFrame(data)

    if not df.empty:

        df = df.drop_duplicates(
            subset=["URL"]
        )

    return df, None


# ============================================================
# EXPORT CSV
# ============================================================

def dataframe_to_csv(df):

    return df.to_csv(
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">💜 Data Collection</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Plateforme de collecte, exploration et visualisation '
    'des données issues du Web Scraping'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.markdown(
    "## 💜 DATA COLLECTION"
)

st.sidebar.markdown(
    "### Navigation"
)

page = st.sidebar.radio(
    "",
    [
        "🏠 Accueil",
        "🕷️ Scraping Selenium",
        "📁 Données brutes",
        "📊 Dashboard",
        "📝 Évaluation"
    ]
)

st.sidebar.markdown("---")

st.sidebar.markdown(
    """
    **Projet Data Collection**

    Cette application permet de :

    • scraper plusieurs pages  
    • télécharger les données brutes  
    • analyser les données nettoyées  
    • visualiser un dashboard  
    • évaluer l'application
    """
)


# ============================================================
# ACCUEIL
# ============================================================

if page == "🏠 Accueil":

    st.markdown("## Bienvenue 👋")

    st.markdown(
        """
        <div class="info-box">

        Cette application centralise les différentes étapes
        de notre projet de <strong>Data Collection</strong>.

        Elle permet de collecter des données avec Selenium,
        consulter les données brutes produites par Web Scraper,
        explorer les données nettoyées et accéder aux formulaires
        d'évaluation.

        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-title">Sources</div>
                <div class="metric-value">2</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-title">Méthode</div>
                <div class="metric-value">Selenium</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-title">Données</div>
                <div class="metric-value">CSV</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col4:

        st.markdown(
            """
            <div class="metric-card">
                <div class="metric-title">Dashboard</div>
                <div class="metric-value">✓</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    st.subheader("🚀 Fonctionnalités")

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            """
            ### 🕷️ Scraping Selenium

            Scrapez automatiquement plusieurs pages
            depuis les différentes sources du projet.

            Les données peuvent ensuite être téléchargées
            directement au format CSV.
            """
        )

    with col2:

        st.markdown(
            """
            ### 📊 Dashboard

            Explorez les données nettoyées avec :

            - indicateurs statistiques
            - tableaux
            - graphiques
            - filtres
            - analyses descriptives
            """
        )


# ============================================================
# SCRAPING SELENIUM
# ============================================================

elif page == "🕷️ Scraping Selenium":

    st.header("🕷️ Scraping multi-pages avec Selenium")

    st.markdown(
        """
        Cette section permet de lancer les deux scrapers
        utilisés dans le projet.
        """
    )

    tab1, tab2 = st.tabs(
        [
            "📚 Books to Scrape",
            "🚗 Gaaraas"
        ]
    )

    # --------------------------------------------------------
    # BOOKS
    # --------------------------------------------------------

    with tab1:

        st.subheader("📚 Books to Scrape")

        pages_books = st.slider(
            "Nombre de pages à scraper",
            min_value=1,
            max_value=50,
            value=5,
            key="books_pages"
        )

        st.info(
            f"Vous allez scraper {pages_books} page(s)."
        )

        if st.button(
            "🚀 Lancer le scraping Books",
            key="scrape_books_button"
        ):

            with st.spinner(
                "Scraping des livres en cours..."
            ):

                df_books, error = scrape_books(
                    pages_books
                )

            if error:

                st.error(
                    f"Erreur pendant le scraping : {error}"
                )

            elif df_books.empty:

                st.warning(
                    "Aucune donnée n'a été récupérée."
                )

            else:

                st.success(
                    f"{len(df_books)} livres récupérés."
                )

                st.dataframe(
                    df_books,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    label="⬇️ Télécharger les données Books",
                    data=dataframe_to_csv(df_books),
                    file_name="books_selenium.csv",
                    mime="text/csv"
                )

    # --------------------------------------------------------
    # GAARAAS
    # --------------------------------------------------------

    with tab2:

        st.subheader("🚗 Gaaraas")

        pages_gaaraas = st.slider(
            "Nombre de pages à scraper",
            min_value=1,
            max_value=13,
            value=5,
            key="gaaraas_pages"
        )

        st.info(
            f"Vous allez scraper {pages_gaaraas} page(s)."
        )

        if st.button(
            "🚀 Lancer le scraping Gaaraas",
            key="scrape_gaaraas_button"
        ):

            with st.spinner(
                "Scraping des véhicules en cours..."
            ):

                df_gaaraas, error = scrape_gaaraas(
                    pages_gaaraas
                )

            if error:

                st.error(
                    f"Erreur pendant le scraping : {error}"
                )

            elif df_gaaraas.empty:

                st.warning(
                    "Aucune donnée n'a été récupérée."
                )

            else:

                st.success(
                    f"{len(df_gaaraas)} annonces récupérées."
                )

                st.dataframe(
                    df_gaaraas,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    label="⬇️ Télécharger les données Gaaraas",
                    data=dataframe_to_csv(df_gaaraas),
                    file_name="gaaraas_selenium.csv",
                    mime="text/csv"
                )


# ============================================================
# DONNÉES BRUTES
# ============================================================

elif page == "📁 Données brutes":

    st.header("📁 Données brutes — Web Scraper")

    st.markdown(
        """
        Les fichiers présentés ici proviennent du dossier
        <strong>Web_Scraper</strong>.

        Seuls les fichiers <strong>CSV</strong> sont utilisés.
        Les fichiers JSON sont volontairement ignorés.
        """,
        unsafe_allow_html=True
    )

    datasets = load_csv_files()

    if not datasets:

        st.warning(
            "Aucun fichier CSV trouvé dans Web_Scraper."
        )

    else:

        st.success(
            f"{len(datasets)} fichier(s) CSV trouvé(s)."
        )

        for filename, df in datasets.items():

            with st.expander(
                f"📄 {filename}"
            ):

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.metric(
                        "Lignes",
                        len(df)
                    )

                with col2:

                    st.metric(
                        "Colonnes",
                        len(df.columns)
                    )

                with col3:

                    st.metric(
                        "Valeurs manquantes",
                        int(df.isna().sum().sum())
                    )

                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                st.download_button(
                    label=f"⬇️ Télécharger {filename}",
                    data=dataframe_to_csv(df),
                    file_name=filename,
                    mime="text/csv",
                    key=f"download_{filename}"
                )


# ============================================================
# DASHBOARD
# ============================================================

elif page == "📊 Dashboard":

    st.header("📊 Dashboard des données nettoyées")

    datasets = load_csv_files()

    if not datasets:

        st.warning(
            "Aucune donnée CSV disponible pour construire le dashboard."
        )

    else:

        dataset_name = st.selectbox(
            "Choisir le jeu de données",
            list(datasets.keys())
        )

        df_raw = datasets[dataset_name]

        df = clean_dataframe(df_raw)

        st.markdown(
            f"### 📌 Analyse de : `{dataset_name}`"
        )

        # ----------------------------------------------------
        # INDICATEURS
        # ----------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Observations</div>
                    <div class="metric-value">
                        {len(df):,}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Variables</div>
                    <div class="metric-value">
                        {len(df.columns)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col3:

            numeric_columns = df.select_dtypes(
                include=np.number
            ).columns

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        Variables numériques
                    </div>
                    <div class="metric-value">
                        {len(numeric_columns)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col4:

            missing = int(
                df_raw.isna().sum().sum()
            )

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">
                        Valeurs manquantes initiales
                    </div>
                    <div class="metric-value">
                        {missing}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("---")

        # ----------------------------------------------------
        # ONGLETS
        # ----------------------------------------------------

        tab_data, tab_stats, tab_graphs, tab_missing = st.tabs(
            [
                "📋 Données",
                "📈 Statistiques",
                "📊 Visualisations",
                "🧹 Nettoyage"
            ]
        )

        # ----------------------------------------------------
        # DONNEES
        # ----------------------------------------------------

        with tab_data:

            st.subheader("📋 Données nettoyées")

            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                label="⬇️ Télécharger les données nettoyées",
                data=dataframe_to_csv(df),
                file_name=f"cleaned_{dataset_name}",
                mime="text/csv"
            )

        # ----------------------------------------------------
        # STATISTIQUES
        # ----------------------------------------------------

        with tab_stats:

            st.subheader(
                "📈 Statistiques descriptives"
            )

            numeric_df = df.select_dtypes(
                include=np.number
            )

            if numeric_df.empty:

                st.info(
                    "Aucune variable numérique disponible."
                )

            else:

                st.dataframe(
                    numeric_df.describe().T,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # GRAPHIQUES
        # ----------------------------------------------------

        with tab_graphs:

            st.subheader(
                "📊 Visualisation des données"
            )

            numeric_columns = df.select_dtypes(
                include=np.number
            ).columns.tolist()

            if numeric_columns:

                selected_column = st.selectbox(
                    "Variable numérique",
                    numeric_columns
                )

                chart_data = df[
                    [selected_column]
                ].copy()

                chart_data = chart_data.reset_index(
                    drop=True
                )

                st.line_chart(
                    chart_data,
                    use_container_width=True
                )

                st.bar_chart(
                    chart_data,
                    use_container_width=True
                )

            else:

                st.info(
                    "Aucune variable numérique disponible "
                    "pour les graphiques."
                )

            # Variables catégorielles

            categorical_columns = df.select_dtypes(
                include=["object", "category"]
            ).columns.tolist()

            if categorical_columns:

                st.markdown("---")

                st.subheader(
                    "📊 Répartition d'une variable catégorielle"
                )

                category = st.selectbox(
                    "Choisir une variable",
                    categorical_columns
                )

                counts = (
                    df[category]
                    .value_counts()
                    .head(10)
                )

                st.bar_chart(
                    counts,
                    use_container_width=True
                )

        # ----------------------------------------------------
        # VALEURS MANQUANTES
        # ----------------------------------------------------

        with tab_missing:

            st.subheader(
                "🧹 Gestion des valeurs manquantes"
            )

            missing_before = df_raw.isna().sum()

            missing_after = df.isna().sum()

            missing_table = pd.DataFrame({
                "Avant nettoyage": missing_before,
                "Après nettoyage": missing_after
            })

            st.dataframe(
                missing_table,
                use_container_width=True
            )

            if missing_after.sum() == 0:

                st.success(
                    "✓ Il ne reste aucune valeur manquante."
                )

            else:

                st.warning(
                    "Certaines valeurs manquantes subsistent."
                )


# ============================================================
# EVALUATION
# ============================================================

elif page == "📝 Évaluation":

    st.header("📝 Évaluation de l'application")

    st.markdown(
        """
        Votre avis nous permet d'améliorer l'application,
        l'expérience utilisateur et la qualité de la collecte
        de données.
        """
    )

    st.markdown("---")

    col1, col2 = st.columns(2)

    # --------------------------------------------------------
    # KOBO
    # --------------------------------------------------------

    with col1:

        st.markdown(
            """
            <div class="dataset-card">

            ## 📱 KoboToolbox

            Évaluez l'application à travers le formulaire
            KoboToolbox.

            </div>
            """,
            unsafe_allow_html=True
        )

        # Remplacer cette URL par l'URL exacte du formulaire Kobo
        kobo_url = st.text_input(
            "URL du formulaire Kobo",
            value="",
            key="kobo_url"
        )

        if kobo_url:

            st.link_button(
                "📱 Ouvrir le formulaire Kobo",
                kobo_url
            )

    # --------------------------------------------------------
    # GOOGLE FORMS
    # --------------------------------------------------------

    with col2:

        st.markdown(
            """
            <div class="dataset-card">

            ## 📝 Google Forms

            Évaluez également l'application via
            Google Forms.

            </div>
            """,
            unsafe_allow_html=True
        )

        # Remplacer cette URL par l'URL exacte du formulaire Google
        google_url = st.text_input(
            "URL du formulaire Google Forms",
            value="",
            key="google_url"
        )

        if google_url:

            st.link_button(
                "📝 Ouvrir Google Forms",
                google_url
            )

    st.markdown("---")

    st.info(
        "Les fichiers d'évaluation présents dans le dossier "
        "Formulaire peuvent également être conservés dans le "
        "dépôt pour consultation."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.markdown(
    """
    <div style="text-align:center; color:#6b7280; padding:20px;">

    💜 <strong>Data Collection Dashboard</strong><br>

    Selenium • Web Scraper • Pandas • Streamlit

    </div>
    """,
    unsafe_allow_html=True
)
```





 


