import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title='Analiza Sprzedaży',layout='wide')

@st.cache_data
def load_data():
    df=pd.read_excel('Raport_sprzedazy.xlsx',sheet_name='Dane',engine='openpyxl')
    df['Calendar day']=pd.to_datetime(df['Calendar day'],dayfirst=True,errors='coerce')
    return df

df=load_data()

st.title('📊 Analiza Sprzedaży AL-KO')

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
    rank=f.groupby('RKS',as_index=False)['Net Value'].sum().sort_values('Net Value',ascending=False)
    st.dataframe(rank)
    comp=f.pivot_table(index='RKS',columns='Calendar year',values='Net Value',aggfunc='sum').fillna(0)
    st.dataframe(comp)
    if 2025 in comp.columns and 2024 in comp.columns:
      comp['YoY % 25/24']=(comp[2025]-comp[2024])/comp[2024].replace(0,pd.NA)*100
    if 2026 in comp.columns and 2025 in comp.columns:
      comp['YoY % 26/25']=(comp[2026]-comp[2025])/comp[2025].replace(0,pd.NA)*100
    st.dataframe(comp)

elif page=='Klienci':
    top=f.groupby('Payer name',as_index=False)['Net Value'].sum().nlargest(20,'Net Value')
    st.plotly_chart(px.bar(top,x='Payer name',y='Net Value'),use_container_width=True)
    top['Udział %']=top['Net Value']/sales*100 if sales else 0
    st.dataframe(top)
    trend=f.groupby(['Calendar day','Payer name'],as_index=False)['Net Value'].sum()
    st.plotly_chart(px.line(trend,x='Calendar day',y='Net Value',color='Payer name'),use_container_width=True)

elif page=='Produkty':
    st.plotly_chart(px.bar(f.groupby('Material name',as_index=False)['Net Value'].sum().nlargest(20,'Net Value'),x='Material name',y='Net Value'),use_container_width=True)
    st.plotly_chart(px.bar(f.groupby('Material name',as_index=False)['sales - credit (quantity)'].sum().nlargest(20,'sales - credit (quantity)'),x='Material name',y='sales - credit (quantity)'),use_container_width=True)
    st.plotly_chart(px.treemap(f.groupby('Category',as_index=False)['Net Value'].sum(),path=['Category'],values='Net Value'),use_container_width=True)

buf=BytesIO();
with pd.ExcelWriter(buf,engine='openpyxl') as writer: f.to_excel(writer,index=False)
st.download_button('Export Excel',buf.getvalue(),'sprzedaz.xlsx')

pdf=BytesIO(); doc=SimpleDocTemplate(pdf); styles=getSampleStyleSheet();
doc.build([Paragraph('Raport sprzedaży',styles['Title']),Spacer(1,12),Paragraph(f'Sprzedaż: {sales:,.0f}',styles['BodyText'])])
st.download_button('Export PDF',pdf.getvalue(),'raport.pdf')
