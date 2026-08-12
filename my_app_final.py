import re
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

\# CONFIGURATION

st.set\_page\_config(
    page\_title="Data Collection - Examen",
    page\_icon="📊",
    layout="wide",
)

BASE\_DIR = Path(\_\_file\_\_).resolve().parent
COLAB\_DIR = BASE\_DIR / "Colab"
WEB\_SCRAPER\_DIR = BASE\_DIR / "Web\_Scraper"
FORM\_DIR = BASE\_DIR / "Formulaire"

DB\_PATH = BASE\_DIR / "data\_collection.db"

\# Fichiers finaux utilisés.
BOOKS\_CSV = WEB\_SCRAPER\_DIR / "Source\_1\_Books\_to\_Scrape.csv"
GAARAAS\_CSV = WEB\_SCRAPER\_DIR / "Source\_2\_Gaaraas).csv"

\# Les JSON du dossier Web\_Scraper sont volontairement ignorés.

\# Liens directs des formulaires.
GOOGLE\_FORM\_URL = (
    "[https://docs.google.com/forms/d/e/](https://docs.google.com/forms/d/e/)"
    "1FAIpQLSc7F8m3eBJkCqpOUa4pTQX0zyIov\_4LWXRYOV3XKbmi0vJJoQ/"
    "viewform?usp=publish-editor"
)
KOBO\_FORM\_URL = "[https://ee.kobotoolbox.org/i/1zbGqqaq](https://ee.kobotoolbox.org/i/1zbGqqaq)"

\# BASE SQL

def get\_connection():
    return sqlite3.connect(DB\_PATH)


def save\_to\_sql(df, table\_name):
    if df is None or df.empty:
        return

    with get\_connection() as conn:
        df.to\_sql(
            table\_name,
            conn,
            if\_exists="replace",
            index=False
        )


def get\_sql\_tables():
    with get\_connection() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite\_master "
            "WHERE type='table' ORDER BY name"
        ).fetchall()

    return [row[0] for row in rows]

\# LECTURE CSV

def read\_csv\_file(path):
    if not path.exists():
        return None

    for encoding in ("utf-8-sig", "utf-8", "latin1"):
        try:
            return pd.read\_csv(
                path,
                encoding=encoding,
                on\_bad\_lines="skip"
            )
        except Exception:
            continue

    return None

\# SELENIUM

def create\_driver():
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
            options.binary\_location = binary
            break

    options.add\_argument("--headless=new")
    options.add\_argument("--no-sandbox")
    options.add\_argument("--disable-dev-shm-usage")
    options.add\_argument("--disable-gpu")
    options.add\_argument("--window-size=1920,1080")
    options.add\_argument("--disable-notifications")

    return webdriver.Chrome(options=options)

\# SELENIUM - BOOKS TO SCRAPE

def scrape\_books(start\_page=1, end\_page=50):

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected\_conditions as EC

    driver = create\_driver()
    records = []

    try:
        progress = st.progress(0)
        total\_pages = end\_page - start\_page + 1

        for position, page in enumerate(
            range(start\_page, end\_page + 1),
            start=1
        ):
            url = (
                f"[https://books.toscrape.com/](https://books.toscrape.com/)"
                f"catalogue/page-{page}.html"
            )

            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence\_of\_all\_elements\_located(
                        (By.CSS\_SELECTOR, "article.product\_pod")
                    )
                )
            except Exception:
                pass

            products = driver.find\_elements(
                By.CSS\_SELECTOR,
                "article.product\_pod"
            )

            links = []

            for product in products:
                try:
                    href = product.find\_element(
                        By.CSS\_SELECTOR,
                        "h3 a"
                    ).get\_attribute("href")

                    if href:
                        links.append(href)
                except Exception:
                    continue

            for product\_url in links:

                try:
                    driver.get(product\_url)

                    def text(css, default=""):
                        try:
                            return driver.find\_element(
                                By.CSS\_SELECTOR,
                                css
                            ).text.strip()
                        except Exception:
                            return default

                    try:
                        rating\_class = driver.find\_element(
                            By.CSS\_SELECTOR,
                            "div.product\_main p.star-rating"
                        ).get\_attribute("class")
                    except Exception:
                        rating\_class = ""

                    records.append({
                        "page": page,
                        "number\_of\_products": len(products),
                        "title": text(
                            "div.product\_main h1"
                        ),
                        "price": text(
                            "div.product\_main p.price\_color"
                        ),
                        "availability": text(
                            "div.product\_main p.instock.availability"
                        ),
                        "star\_rating": rating\_class,
                        "reviews": text(
                            "table.table-striped tr\:nth-child(7) td"
                        ),
                        "description": text(
                            "#product\_description + p"
                        ),
                        "product\_type": text(
                            "ul.breadcrumb li\:nth-child(3) a"
                        ),
                        "tax": text(
                            "table.table-striped tr\:nth-child(5) td"
                        ),
                        "url": product\_url,
                    })

                except Exception:
                    continue

            progress.progress(position / total\_pages)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)

\# SELENIUM - GAARAAS

def scrape\_gaaraas(start\_page=1, end\_page=13):

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected\_conditions as EC

    driver = create\_driver()
    records = []

    try:
        progress = st.progress(0)
        total\_pages = end\_page - start\_page + 1

        for position, page in enumerate(
            range(start\_page, end\_page + 1),
            start=1
        ):
            url = (
                "[https://www.gaaraas.com/fr/users/dakar-auto](https://www.gaaraas.com/fr/users/dakar-auto)"
                f"?page={page}"
            )

            driver.get(url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence\_of\_all\_elements\_located(
                        (By.CSS\_SELECTOR, "a.common-ad-card")
                    )
                )
            except Exception:
                pass

            cards = driver.find\_elements(
                By.CSS\_SELECTOR,
                "a.common-ad-card"
            )

            links = []

            for card in cards:
                try:
                    href = card.get\_attribute("href")

                    if href and href not in links:
                        links.append(href)
                except Exception:
                    continue

            for ad\_url in links:

                try:
                    driver.get(ad\_url)

                    def text(css, default=""):
                        try:
                            return driver.find\_element(
                                By.CSS\_SELECTOR,
                                css
                            ).text.strip()
                        except Exception:
                            return default

                    records.append({
                        "page": page,
                        "number\_of\_ads": len(cards),
                        "marque\_modele": text(
                            ".ad-title-block h2"
                        ),
                        "annee": text(
                            "div.prop\:nth-of-type(4) span\:nth-of-type(2)"
                        ),
                        "prix": text(
                            ".back-wrapper .ad-price span.price-wrap"
                        ),
                        "kilometrage": text(
                            "div.prop\:nth-of-type(3) span\:nth-of-type(2)"
                        ),
                        "type\_boite\_de\_vitesse": text(
                            "div.prop\:nth-of-type(2) span\:nth-of-type(2)"
                        ),
                        "region\_de\_vente": text(
                            ".ad-title a span"
                        ),
                        "url": ad\_url,
                    })

                except Exception:
                    continue

            progress.progress(position / total\_pages)

        progress.empty()

    finally:
        driver.quit()

    return pd.DataFrame(records)

\# NETTOYAGE

def clean\_books(df):

    df = df.copy()

    for col in df.select\_dtypes(
        include="object"
    ).columns:
        df[col] = df[col].astype(str).str.strip()

    if "price" in df.columns:
        df["price\_numeric"] = pd.to\_numeric(
            df["price"]
            .astype(str)
            .str.replace("£", "", regex=False)
            .str.replace(",", "", regex=False)
            .str.strip(),
            errors="coerce"
        )

    if "star\_rating" in df.columns:

        rating\_map = {
            "One": 1,
            "Two": 2,
            "Three": 3,
            "Four": 4,
            "Five": 5,
        }

        df["rating"] = (
            df["star\_rating"]
            .astype(str)
            .str.extract(
                r"(One|Two|Three|Four|Five)",
                expand=False
            )
            .map(rating\_map)
        )

    if "reviews" in df.columns:
        df["reviews\_numeric"] = pd.to\_numeric(
            df["reviews"],
            errors="coerce"
        )

    return df.drop\_duplicates().reset\_index(drop=True)


def clean\_gaaraas(df):

    df = df.copy()

    for col in df.select\_dtypes(
        include="object"
    ).columns:
        df[col] = df[col].astype(str).str.strip()

    if "annee" in df.columns:
        df["annee\_numeric"] = pd.to\_numeric(
            df["annee"],
            errors="coerce"
        )

    if "prix" in df.columns:
        df["prix\_numeric"] = pd.to\_numeric(
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
        df["kilometrage\_numeric"] = pd.to\_numeric(
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

    return df.drop\_duplicates().reset\_index(drop=True)


\# ============================================================
\# SESSION STATE
\# ============================================================

if "books\_selenium" not in st.session\_state:
    st.session\_state.books\_selenium = None

if "gaaraas\_selenium" not in st.session\_state:
    st.session\_state.gaaraas\_selenium = None

\# SIDEBAR

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

\# ACCUEIL

if menu == "Accueil":

    st.title("📊 Application Data Collection")

    st.markdown(
        """
        \### Objectif

        Cette application regroupe les différentes étapes du projet :

        \- 🕷️ collecte avec \*\*Selenium\*\* sur plusieurs pages ;
        \- 📥 téléchargement des données brutes \*\*Web Scraper\*\* ;
        \- 🧹 nettoyage des données Selenium ;
        \- 📊 dashboard des données nettoyées ;
        \- 📝 accès aux formulaires d'évaluation ;
        \- 🗄️ stockage SQL.
        
        """
    )

    st.success("Application prête.")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "CSV Web Scraper",
            sum(
                path.exists()
                for path in [BOOKS\_CSV, GAARAAS\_CSV]
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

\# SCRAPING SELENIUM

elif menu == "Scraping Selenium":

    st.title("🕷️ Scraping Selenium")

    tab\_books, tab\_gaaraas = st.tabs(
        [
            "📚 Books to Scrape",
            "🚗 Gaaraas"
        ]
    )

    \# BOOKS

    with tab\_books:

        st.subheader("📚 Books to Scrape")

        col1, col2 = st.columns(2)

        with col1:
            start\_books = st.number\_input(
                "Première page",
                min\_value=1,
                max\_value=50,
                value=1,
                step=1,
                key="start\_books"
            )

        with col2:
            end\_books = st.number\_input(
                "Dernière page",
                min\_value=1,
                max\_value=50,
                value=50,
                step=1,
                key="end\_books"
            )

        if st.button(
            "🚀 Lancer le scraping Books to Scrape",
            type="primary",
            use\_container\_width=True
        ):

            if start\_books > end\_books:

                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )

            else:

                try:

                    with st.spinner(
                        "Scraping Books to Scrape..."
                    ):

                        raw\_books = scrape\_books(
                            start\_books,
                            end\_books
                        )

                        books = clean\_books(
                            raw\_books
                        )

                    st.session\_state.books\_selenium = books

                    save\_to\_sql(
                        books,
                        "selenium\_books"
                    )

                    st.success(
                        f"{len(books)} livres collectés."
                    )

                except Exception as exc:

                    st.error(
                        f"Erreur Selenium : {exc}"
                    )

        if st.session\_state.books\_selenium is not None:

            books = st.session\_state.books\_selenium

            st.metric(
                "Livres collectés",
                len(books)
            )

            st.dataframe(
                books,
                use\_container\_width=True,
                height=450
            )

            st.download\_button(
                "⬇️ Télécharger les données nettoyées",
                books.to\_csv(index=False).encode("utf-8"),
                "books\_selenium\_clean.csv",
                "text/csv",
                use\_container\_width=True
            )

    \# GAARAAS

    with tab\_gaaraas:

        st.subheader("🚗 Gaaraas")

        col1, col2 = st.columns(2)

        with col1:
            start\_gaaraas = st.number\_input(
                "Première page",
                min\_value=1,
                max\_value=13,
                value=1,
                step=1,
                key="start\_gaaraas"
            )

        with col2:
            end\_gaaraas = st.number\_input(
                "Dernière page",
                min\_value=1,
                max\_value=13,
                value=13,
                step=1,
                key="end\_gaaraas"
            )

        if st.button(
            "🚀 Lancer le scraping Gaaraas",
            type="primary",
            use\_container\_width=True
        ):

            if start\_gaaraas > end\_gaaraas:

                st.error(
                    "La première page doit être inférieure "
                    "ou égale à la dernière."
                )

            else:

                try:

                    with st.spinner(
                        "Scraping Gaaraas..."
                    ):

                        raw\_gaaraas = scrape\_gaaraas(
                            start\_gaaraas,
                            end\_gaaraas
                        )

                        gaaraas = clean\_gaaraas(
                            raw\_gaaraas
                        )

                    st.session\_state.gaaraas\_selenium = gaaraas

                    save\_to\_sql(
                        gaaraas,
                        "selenium\_gaaraas"
                    )

                    st.success(
                        f"{len(gaaraas)} annonces collectées."
                    )

                except Exception as exc:

                    st.error(
                        f"Erreur Selenium : {exc}"
                    )

        if st.session\_state.gaaraas\_selenium is not None:

            gaaraas = st.session\_state.gaaraas\_selenium

            st.metric(
                "Annonces collectées",
                len(gaaraas)
            )

            st.dataframe(
                gaaraas,
                use\_container\_width=True,
                height=450
            )

            st.download\_button(
                "⬇️ Télécharger les données nettoyées",
                gaaraas.to\_csv(index=False).encode("utf-8"),
                "gaaraas\_selenium\_clean.csv",
                "text/csv",
                use\_container\_width=True
            )

\# DONNEES WEB SCRAPER

elif menu == "Données Web Scraper":

    st.title("📥 Données brutes Web Scraper")

    files = [
        BOOKS\_CSV,
        GAARAAS\_CSV
    ]

    found\_files = [
        path for path in files
        if path.exists()
    ]

    if not found\_files:

        st.warning(
            "Aucun des deux fichiers CSV n'a été trouvé."
        )

    for path in found\_files:

        st.subheader(
            f"📄 {path.name}"
        )

        df = read\_csv\_file(path)

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
            use\_container\_width=True,
            height=350
        )

        st.download\_button(
            f"⬇️ Télécharger {path.name}",
            df.to\_csv(index=False).encode("utf-8"),
            path.name,
            "text/csv",
            key=f"download\_{path.name}",
            use\_container\_width=True
        )

        if path.name == BOOKS\_CSV.name:

            save\_to\_sql(
                df,
                "webscraper\_books"
            )

        elif path.name == GAARAAS\_CSV.name:

            save\_to\_sql(
                df,
                "webscraper\_gaaraas"
            )

\# DASHBOARD

elif menu == "Dashboard":

    st.title(
        "📊 Dashboard des données Selenium nettoyées"
    )

    books = st.session\_state.books\_selenium
    gaaraas = st.session\_state.gaaraas\_selenium

    if books is None and gaaraas is None:

        st.warning(
            "Aucune donnée Selenium disponible. "
            "Lancez le scraping dans la section Selenium."
        )

    \# BOOKS

    if books is not None:

        st.header("📚 Books to Scrape")

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            st.metric(
                "Livres",
                len(books)
            )

        with c2:

            if "price\_numeric" in books:

                value = books[
                    "price\_numeric"
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

            if "product\_type" in books:

                st.metric(
                    "Types de produits",
                    books[
                        "product\_type"
                    ].nunique()
                )

            else:

                st.metric(
                    "Types de produits",
                    0
                )

        left, right = st.columns(2)

        with left:

            if "product\_type" in books:

                st.subheader(
                    "Top catégories"
                )

                st.bar\_chart(
                    books[
                        "product\_type"
                    ]
                    .value\_counts()
                    .head(10)
                )

        with right:

            if "rating" in books:

                st.subheader(
                    "Répartition des notes"
                )

                st.bar\_chart(
                    books[
                        "rating"
                    ]
                    .value\_counts()
                    .sort\_index()
                )

        with st.expander(
            "Voir les données Books nettoyées"
        ):

            st.dataframe(
                books,
                use\_container\_width=True
            )

    \# GAARAAS

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

            if "prix\_numeric" in gaaraas:

                value = gaaraas[
                    "prix\_numeric"
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

            if "annee\_numeric" in gaaraas:

                value = gaaraas[
                    "annee\_numeric"
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

            if "kilometrage\_numeric" in gaaraas:

                value = gaaraas[
                    "kilometrage\_numeric"
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

            if "marque\_modele" in gaaraas:

                st.subheader(
                    "Top marques / modèles"
                )

                st.bar\_chart(
                    gaaraas[
                        "marque\_modele"
                    ]
                    .value\_counts()
                    .head(10)
                )

        with right:

            if "annee\_numeric" in gaaraas:

                st.subheader(
                    "Répartition par année"
                )

                st.bar\_chart(
                    gaaraas[
                        "annee\_numeric"
                    ]
                    .value\_counts()
                    .sort\_index()
                )

        with st.expander(
            "Voir les données Gaaraas nettoyées"
        ):

            st.dataframe(
                gaaraas,
                use\_container\_width=True
            )

\# FORMULAIRES D'EVALUATION

elif menu == "Formulaires d'évaluation":

    st.title("📝 Formulaires d'évaluation")

    st.subheader("📋 Google Forms")

    st.link\_button(
        "📝 Ouvrir le formulaire Google Forms",
        GOOGLE\_FORM\_URL,
        use\_container\_width=True
    )

    st.divider()

    st.subheader("📋 KoboToolbox")

    st.link\_button(
        "📝 Ouvrir le formulaire KoboToolbox",
        KOBO\_FORM\_URL,
        use\_container\_width=True
    )

\# BASE SQL

elif menu == "Base SQL":

    st.title("🗄️ Base de données SQL")

    st.write(
        """
        Les données collectées sont stockées dans une base SQLite.

        Les tables utilisées sont :

        \- \`selenium\_books\`
        \- \`selenium\_gaaraas\`
        \- \`webscraper\_books\`
        \- \`webscraper\_gaaraas\`
        """
    )

    tables = get\_sql\_tables()

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

                    with get\_connection() as conn:

                        df = pd.read\_sql\_query(
                            f'SELECT \* FROM "{table}"',
                            conn
                        )

                    st.write(
                        f"{len(df)} lignes × "
                        f"{len(df.columns)} colonnes"
                    )

                    st.dataframe(
                        df.head(100),
                        use\_container\_width=True
                    )

                    st.download\_button(
                        "⬇️ Télécharger la table",
                        df.to\_csv(
                            index=False
                        ).encode("utf-8"),
                        f"{table}.csv",
                        "text/csv",
                        key=f"sql\_{table}"
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
            "selenium\_books",
            "selenium\_gaaraas",
            "webscraper\_books",
            "webscraper\_gaaraas",
        ],
    })

    st.dataframe(
        schema,
        use\_container\_width=True,
        hide\_index=True
    ) supprime les emojis
