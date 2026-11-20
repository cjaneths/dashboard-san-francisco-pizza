import os
from pathlib import Path
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='SF Crust Pizza | Inteligencia comercial', page_icon='🍕', layout='wide')
st.markdown('''<style>.block-container{padding-top:1.5rem}.stMetric{background:#f7f9fc;padding:16px;border-radius:12px;border:1px solid #e6eaf0}h1{color:#182a42}</style>''', unsafe_allow_html=True)
REQUIRED = {'ventas': ['VentaID','Fecha','Ciudad','Sucursal','ClienteID','ProductoID','Cantidad','VentaNeta','CostoTotal','UtilidadBruta'], 'clientes':['ClienteID','Segmento'], 'productos':['ProductoID','Producto','Categoria']}

@st.cache_data(show_spinner='Leyendo archivo Excel...')
def load_excel(raw):
    return pd.read_excel(BytesIO(raw) if isinstance(raw, bytes) else raw, engine='openpyxl')

def read_input(upload, key):
    if upload is not None:
        df = load_excel(upload.getvalue())
    else:
        candidates = sorted((Path(__file__).parent / 'data').glob('*.xlsx'))
        matches = [p for p in candidates if f'_{key.lower()}.xlsx' in p.name.lower()]
        if not matches:
            st.info(f'Para comenzar, carga el archivo original de {key} en el panel lateral.')
            st.stop()
        df = load_excel(matches[0].read_bytes())
    df.columns = df.columns.astype(str).str.strip()
    missing = set(REQUIRED[key]) - set(df.columns)
    if missing:
        st.error(f'El archivo de {key} no cumple el esquema. Faltan columnas: {", ".join(sorted(missing))}'); st.stop()
    return df

st.title('🍕 San Francisco Crust Pizza')
st.caption('Sistema inteligente de apoyo a decisiones · Cuadro de mando comercial')
with st.sidebar:
    st.header('📁 Actualizar bases')
    st.info('Datos exclusivamente de los Excel originales. Puedes sustituir cualquiera de las tres bases cargando un nuevo archivo.')
    st.caption('Cargar un archivo reemplaza los datos de esa tabla en esta sesión. Los demás permanecen sin cambios.')
    u_ventas = st.file_uploader('Ventas (.xlsx)',type=['xlsx'],key='v')
    u_clientes = st.file_uploader('Clientes (.xlsx)',type=['xlsx'],key='c')
    u_productos = st.file_uploader('Productos (.xlsx)',type=['xlsx'],key='p')

st.caption('Resultados calculados exclusivamente con las tres bases originales; no hay datos ficticios.')
ventas = read_input(u_ventas,'ventas')
clientes = read_input(u_clientes,'clientes')
productos = read_input(u_productos,'productos')
for col in ('ClienteID',):
    clientes[col] = clientes[col].astype(str).str.strip()
for col in ('ProductoID',):
    productos[col] = productos[col].astype(str).str.strip()
for col in ('ClienteID','ProductoID','VentaID'):
    ventas[col] = ventas[col].astype(str).str.strip()
if clientes.ClienteID.duplicated().any() or productos.ProductoID.duplicated().any():
    st.error('Hay identificadores duplicados en las tablas maestras de clientes o productos. Corrígelos antes de continuar.'); st.stop()
ventas['Fecha'] = pd.to_datetime(ventas['Fecha'],errors='coerce')
for col in ['VentaNeta','CostoTotal','UtilidadBruta','Cantidad']:
    ventas[col] = pd.to_numeric(ventas[col],errors='coerce')
invalid_rows = int(ventas[['Fecha','VentaNeta','CostoTotal','Cantidad']].isna().any(axis=1).sum())
if invalid_rows:
    st.error(f'Hay {invalid_rows:,} filas de ventas con fecha, importe, costo o cantidad inválidos. Corrige el archivo antes de continuar para evitar resultados incompletos.')
    st.stop()
# Recalcular la utilidad de las operaciones para asegurar consistencia contable.
ventas['UtilidadCalculada'] = ventas['VentaNeta'] - ventas['CostoTotal']
base = ventas.merge(clientes[['ClienteID','Segmento']],on='ClienteID',how='left',validate='many_to_one',indicator='_cliente_match')
base = base.merge(productos[['ProductoID','Producto','Categoria'] + (['Tamaño'] if 'Tamaño' in productos.columns else [])],on='ProductoID',how='left',validate='many_to_one',indicator='_producto_match')
base['Segmento'] = base['Segmento'].fillna('Sin clasificar (sin coincidencia en Clientes)')
base['Producto'] = base['Producto'].fillna('Sin identificar (sin coincidencia en Productos)')
base['ProductoDetalle'] = base['Producto'].astype(str) + ((' · '+base['Tamaño'].fillna('').astype(str)) if 'Tamaño' in base else '')
with st.sidebar:
    st.divider(); st.header('🎛️ Filtros')
    if base.empty:
        st.error('El archivo de ventas no contiene registros para analizar.'); st.stop()
    min_date,max_date = base.Fecha.min().date(),base.Fecha.max().date()
    date_range = st.date_input('Fecha (desde / hasta)',value=(min_date,max_date),min_value=min_date,max_value=max_date)
    ciudades = st.multiselect('Ciudad',sorted(base.Ciudad.dropna().unique()),placeholder='Todas')
    suc_options = sorted(base.loc[base.Ciudad.isin(ciudades),'Sucursal'].dropna().unique()) if ciudades else sorted(base.Sucursal.dropna().unique())
    sucursales = st.multiselect('Sucursal',suc_options,placeholder='Todas')
    segmentos = st.multiselect('Segmento de cliente',sorted(base.Segmento.dropna().unique()),placeholder='Todos')
    prods = st.multiselect('Producto',sorted(base.ProductoDetalle.dropna().unique()),placeholder='Todos')
    st.caption('Deja un filtro sin seleccionar para incluir todos sus valores.')

df=base.copy()
if isinstance(date_range,(tuple,list)) and len(date_range)==2:
    df=df[df.Fecha.dt.date.between(date_range[0],date_range[1])]
if ciudades:df=df[df.Ciudad.isin(ciudades)]
if sucursales:df=df[df.Sucursal.isin(sucursales)]
if segmentos:df=df[df.Segmento.isin(segmentos)]
if prods:df=df[df.ProductoDetalle.isin(prods)]
if df.empty:
    st.warning('No hay ventas con los filtros seleccionados.'); st.stop()

ventas_total = float(df.VentaNeta.sum())
utilidad = float(df.UtilidadCalculada.sum())
transacciones = int(df.VentaID.nunique())
clientes_unicos = int(df.ClienteID.nunique())
margen = utilidad/ventas_total*100 if ventas_total else 0
ticket = ventas_total/transacciones if transacciones else 0
