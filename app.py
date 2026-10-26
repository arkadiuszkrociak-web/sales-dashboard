import streamlit as st
import pandas as pd
from PIL import Image
import plotly.express as px
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
def check_password():

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:

        password = st.text_input(
            "🔒 Podaj hasło",
            type="password"
        )

        if password == "ALKO2026!":
            st.session_state.authenticated = True
            st.rerun()

        elif password:
            st.error("Nieprawidłowe hasło")

        st.stop()

check_password()
st.set_page_config(page_title='Analiza Sprzedaży',layout='wide')

@st.cache_data
def load_data():

    usecols = [
        'Payer',
        'Payer name',
        'Material',
        'Material name',
        'Category',
        'RKS',
        'Calendar year',
        'Calendar month',
        'Calendar day',
        'sales - credit (quantity)',
        'Net Value'
    ]

    df = pd.read_parquet(
    'Raport_sprzedazy.parquet'
)
    st.write(df.columns.tolist())

    if 'Calendar day' in df.columns:
        df['Calendar day'] = pd.to_datetime(
            df['Calendar day'],
            dayfirst=True,
            errors='coerce'
    )

    for col in [
        'Payer name',
        'Category',
        'RKS',
        'Material name'
    ]:
        if col in df.columns:
            df[col] = df[col].astype('category')

    return df

df=load_data()
logo = Image.open("logo.png")

col1, col2 = st.columns([1,5])

with col1:
    st.image(logo, width=120)

with col2:
    st.title("📊 Analiza Sprzedaży AL-KO")

with st.sidebar:
    rok=st.multiselect('Rok',sorted(df['Calendar year'].dropna().unique()),default=sorted(df['Calendar year'].dropna().unique()))
    mies=st.multiselect('Miesiąc',sorted(df['Calendar month'].dropna().unique()),default=sorted(df['Calendar month'].dropna().unique()))
    rks=st.multiselect('Handlowiec',sorted(df['RKS'].dropna().unique()))
    klient=st.multiselect('Klient',sorted(df['Payer name'].dropna().unique()))
    kat=st.multiselect('Kategoria',sorted(df['Category'].dropna().unique()))
    prod=st.multiselect('Produkt',sorted(df['Material name'].dropna().unique()))

f=df[df['Calendar year'].isin(rok) & df['Calendar month'].isin(mies)]
for col,val in [('RKS',rks),('Payer name',klient),('Category',kat),('Material name',prod)]:
    if val: f=f[f[col].isin(val)]

page=st.sidebar.radio('Strona',['Dashboard','Handlowcy','Klienci','Produkty'])

sales=f['Net Value'].sum()
clients=f['Payer'].nunique()
products=f['Material'].nunique()
orders=max(len(f),1)
avg=sales/orders

top10=f.groupby('Payer name')['Net Value'].sum().nlargest(10).sum()
top10_share=(top10/sales*100) if sales else 0

if page=='Dashboard':
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric('Sprzedaż całkowita',f'{sales:,.0f}')
    c2.metric('Liczba klientów',clients)
    c3.metric('Liczba produktów',products)
    c4.metric('Śr. wartość zamówienia',f'{avg:,.0f}')
    c5.metric('TOP10 klientów %',f'{top10_share:.1f}%')

    st.plotly_chart(px.bar(f.groupby('RKS',as_index=False)['Net Value'].sum().sort_values('Net Value'),x='RKS',y='Net Value',title='Sprzedaż wg handlowców'),use_container_width=True)
    st.plotly_chart(px.bar(f.groupby('Payer name',as_index=False)['Net Value'].sum().nlargest(20,'Net Value'),x='Payer name',y='Net Value',title='TOP Klienci'),use_container_width=True)
    st.plotly_chart(px.treemap(f.groupby('Category',as_index=False)['Net Value'].sum(),path=['Category'],values='Net Value',title='Kategorie'),use_container_width=True)
    monthly=f.groupby(['Calendar year','Calendar month'],as_index=False)['Net Value'].sum()
    st.plotly_chart(px.line(monthly,x='Calendar month',y='Net Value',color='Calendar year',title='Trend YoY'),use_container_width=True)

elif page=='Handlowcy':

    rank = (
        f.groupby('RKS', as_index=False)['Net Value']
        .sum()
        .sort_values('Net Value', ascending=False)
        .reset_index(drop=True)
    )

    medale = []

    for i in range(len(rank)):
        if i == 0:
            medale.append("🥇")
        elif i == 1:
            medale.append("🥈")
        elif i == 2:
            medale.append("🥉")
        else:
            medale.append(str(i + 1))

    rank.insert(0, "Pozycja", medale)

    st.subheader("🏆 Ranking Handlowców")

    if len(rank) > 0:
        st.metric(
            "Lider sprzedaży",
            rank.iloc[0]["RKS"],
            f"{rank.iloc[0]['Net Value']:,.0f} zł"
        )

    rank_display = rank.copy()

    rank_display["Net Value"] = rank_display["Net Value"].map(
        lambda x: f"{x:,.0f} zł".replace(",", " ")
    )

    st.dataframe(
        rank_display,
        hide_index=True,
        use_container_width=True
    )

    st.subheader("📈 Dynamika sprzedaży")

    comp = (
    df.pivot_table(
        index='RKS',
        columns='Calendar year',
        values='Net Value',
        aggfunc='sum'
    )
    .fillna(0)
    )

    if 2025 in comp.columns and 2026 in comp.columns:

        yoy_df = pd.DataFrame()

        yoy_df["Handlowiec"] = comp.index

        yoy_df["2025"] = comp[2025].values

        yoy_df["2026"] = comp[2026].values

        yoy_df["Dynamika %"] = (
        (
            yoy_df["2026"] - yoy_df["2025"]
        )
        / yoy_df["2025"].replace(0, pd.NA)
        * 100
    ).round(1)

    yoy_df = yoy_df.sort_values(
        "Dynamika %",
        ascending=False
    )

    yoy_df["Trend"] = yoy_df["Dynamika %"].apply(
    lambda x: "🟢" if x > 0 else ("⚪" if x == 0 else "🔴")
    )
    yoy_df["2025"] = yoy_df["2025"].map(
    lambda x: f"{x:,.0f} zł".replace(",", " ")
    )

    yoy_df["2026"] = yoy_df["2026"].map(
    lambda x: f"{x:,.0f} zł".replace(",", " ")
    )

    st.dataframe(
        yoy_df[
        [
            "Trend",
            "Handlowiec",
            "2025",
            "2026",
            "Dynamika %"
        ]
    ],
    hide_index=True,
    use_container_width=True
    )


elif page=='Klienci':
    top=f.groupby('Payer name',as_index=False)['Net Value'].sum().nlargest(20,'Net Value')
    st.plotly_chart(px.bar(top,x='Payer name',y='Net Value'),use_container_width=True)
    st.subheader("🚀 TOP 10 klientów - wzrost sprzedaży")

    client_comp = (
        df.pivot_table(
            index='Payer name',
            columns='Calendar year',
            values='Net Value',
            aggfunc='sum'
    )
    .fillna(0)
    )

    if 2025 in client_comp.columns and 2026 in client_comp.columns:
       
        growth = pd.DataFrame()

        growth["Klient"] = client_comp.index

        growth["2025"] = client_comp[2025].values

        growth["2026"] = client_comp[2026].values

        growth["2025"] = pd.to_numeric(
            growth["2025"],
            errors="coerce"
        )

        growth["2026"] = pd.to_numeric(
            growth["2026"],
            errors="coerce"
        )
        growth = growth[
            growth["2025"] >= 50000
        ]

        growth["Dynamika %"] = (
            (
            growth["2026"] - growth["2025"]
            )
            / growth["2025"].replace(0, pd.NA)
            * 100
        )

        growth["Dynamika %"] = pd.to_numeric(
            growth["Dynamika %"],
            errors="coerce"
        ).round(1)
        
        growth = growth.dropna(subset=["Dynamika %"])
        
        growth = growth.dropna()

        growth_growth = growth.sort_values(
        "Dynamika %",
        ascending=False
        ).head(10)

        growth_decline = growth.sort_values(
        "Dynamika %",
        ascending=True
        ).head(10)

        col1, col2 = st.columns(2)

    with col1:

        st.subheader("🚀 Największe wzrosty")

        st.dataframe(
            growth_growth,
            hide_index=True,
            use_container_width=True
        )

    with col2:

        st.subheader("📉 Największe spadki")

        st.dataframe(
            growth_decline,
            hide_index=True,
            use_container_width=True
        )
    

elif page=='Produkty':
    st.plotly_chart(px.bar(f.groupby('Material name',as_index=False)['Net Value'].sum().nlargest(20,'Net Value'),x='Material name',y='Net Value'),use_container_width=True)
    st.plotly_chart(px.bar(f.groupby('Material name',as_index=False)['sales - credit (quantity)'].sum().nlargest(20,'sales - credit (quantity)'),x='Material name',y='sales - credit (quantity)'),use_container_width=True)
    st.plotly_chart(px.treemap(f.groupby('Category',as_index=False)['Net Value'].sum(),path=['Category'],values='Net Value'),use_container_width=True)

if st.button("📥 Przygotuj eksport Excel"):

    buf = BytesIO()

    with pd.ExcelWriter(
        buf,
        engine='openpyxl'
    ) as writer:
        f.to_excel(
            writer,
            index=False
        )

    st.download_button(
        'Pobierz Excel',
        buf.getvalue(),
        'sprzedaz.xlsx'
    )

