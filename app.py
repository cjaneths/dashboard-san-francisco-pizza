import os
from pathlib import Path
from io import BytesIO
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title='SF Crust Pizza | Inteligencia comercial', page_icon='🍕', layout='wide', initial_sidebar_state='collapsed')
st.markdown('''<style>.block-container{padding-top:1.5rem}.stMetric{background:#f7f9fc;padding:16px;border-radius:12px;border:1px solid #e6eaf0}h1{color:#182a42}</style>''', unsafe_allow_html=True)
REQUIRED = {'ventas': ['VentaID','Fecha','Ciudad','Sucursal','ClienteID','ProductoID','Cantidad','VentaNeta','CostoTotal','UtilidadBruta'], 'clientes':['ClienteID','Segmento'], 'productos':['ProductoID','Producto','Categoria']}

@st.cache_data(show_spinner='Leyendo archivo Excel...')
def load_excel(raw):
    return pd.read_excel(BytesIO(raw) if isinstance(raw, bytes) else raw, engine='openpyxl')

def read_input(upload, key):
    if upload is not None:
        df = load_excel(upload.getvalue())
    else:
        candidates = sorted((Path(__file__).parent / 'data').glob('*.xlsx')) + sorted(Path(__file__).parent.glob('*.xlsx'))
        matches = [p for p in candidates if f'_{key.lower()}.xlsx' in p.name.lower()]
        if not matches:
            st.info(f'Para comenzar, carga el archivo original de {key} en la sección superior «Actualizar bases Excel».')
            st.stop()
        df = load_excel(matches[0].read_bytes())
    df.columns = df.columns.astype(str).str.strip()
    missing = set(REQUIRED[key]) - set(df.columns)
    if missing:
        st.error(f'El archivo de {key} no cumple el esquema. Faltan columnas: {", ".join(sorted(missing))}'); st.stop()
    return df

st.title('🍕 San Francisco Crust Pizza')
st.caption('Sistema inteligente de apoyo a decisiones · Cuadro de mando comercial')
with st.expander('📁 Actualizar bases Excel (cargar o reemplazar archivos)', expanded=True):
    st.info('Utiliza exclusivamente tus tres Excel originales. Puedes reemplazar cada archivo sin modificar el código.')
    c1, c2, c3 = st.columns(3)
    with c1:
        u_ventas = st.file_uploader('Ventas (.xlsx)', type=['xlsx'], key='v')
    with c2:
        u_clientes = st.file_uploader('Clientes (.xlsx)', type=['xlsx'], key='c')
    with c3:
        u_productos = st.file_uploader('Productos (.xlsx)', type=['xlsx'], key='p')

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
    st.warning(f'Se detectaron {invalid_rows:,} filas con datos esenciales inválidos. Se excluyen únicamente esas filas de los cálculos; el archivo original no se modifica.')
    st.download_button('Descargar filas para revisión', data=ventas.loc[ventas[['Fecha','VentaNeta','CostoTotal','Cantidad']].isna().any(axis=1)].to_csv(index=False).encode('utf-8-sig'), file_name='filas_para_revision.csv', mime='text/csv')
    ventas = ventas.loc[~ventas[['Fecha','VentaNeta','CostoTotal','Cantidad']].isna().any(axis=1)].copy()
# Recalcular la utilidad de las operaciones para asegurar consistencia contable.
ventas['UtilidadCalculada'] = ventas['VentaNeta'] - ventas['CostoTotal']
base = ventas.merge(clientes[['ClienteID','Segmento']],on='ClienteID',how='left',validate='many_to_one',indicator='_cliente_match')
base = base.merge(productos[['ProductoID','Producto','Categoria'] + (['Tamaño'] if 'Tamaño' in productos.columns else [])],on='ProductoID',how='left',validate='many_to_one',indicator='_producto_match')
base['Segmento'] = base['Segmento'].fillna('Sin clasificar (sin coincidencia en Clientes)')
base['Producto'] = base['Producto'].fillna('Sin identificar (sin coincidencia en Productos)')
base['ProductoDetalle'] = base['Producto'].astype(str) + ((' · '+base['Tamaño'].fillna('').astype(str)) if 'Tamaño' in base else '')
st.divider()
st.subheader('🎛️ Mandos de control y filtros')
if base.empty:
    st.error('El archivo de ventas no contiene registros para analizar.')
    st.stop()
min_date, max_date = base.Fecha.min().date(), base.Fecha.max().date()
col_fecha, col_ciudad, col_sucursal, col_segmento, col_producto = st.columns([1.35, 1, 1, 1.1, 1.35])
with col_fecha:
    date_range = st.date_input('Fecha (desde / hasta)', value=(min_date, max_date), min_value=min_date, max_value=max_date)
with col_ciudad:
    ciudades = st.multiselect('Ciudad', sorted(base.Ciudad.dropna().unique()), placeholder='Todas')
with col_sucursal:
    suc_options = sorted(base.loc[base.Ciudad.isin(ciudades), 'Sucursal'].dropna().unique()) if ciudades else sorted(base.Sucursal.dropna().unique())
    sucursales = st.multiselect('Sucursal', suc_options, placeholder='Todas')
with col_segmento:
    segmentos = st.multiselect('Segmento de cliente', sorted(base.Segmento.dropna().unique()), placeholder='Todos')
with col_producto:
    prods = st.multiselect('Producto', sorted(base.ProductoDetalle.dropna().unique()), placeholder='Todos')
st.caption('Los controles están en la parte superior. Si dejas un filtro vacío, se incluyen todos sus valores.')
st.divider()

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
usd=lambda x:f'${x:,.2f}'

st.subheader('Indicadores ejecutivos')
cols=st.columns(3)
for c,label,value in zip(cols,['Ventas totales','Utilidad bruta','Margen bruto'],[usd(ventas_total),usd(utilidad),f'{margen:,.2f}%']):c.metric(label,value)
cols=st.columns(3)
for c,label,value in zip(cols,['Ticket promedio','Clientes únicos','Transacciones'],[usd(ticket),f'{clientes_unicos:,}',f'{transacciones:,}']):c.metric(label,value)
st.caption('Utilidad bruta = venta neta − costo total; margen = utilidad / venta neta; ticket = venta neta / VentaID únicos. Los clientes se cuentan por ClienteID distinto.')

# Paleta diversa, sobria y legible para un tablero ejecutivo.
PALETA = ['#147D8C', '#E8A04B', '#6D63A8', '#D56F79', '#6C9C65', '#3981C6', '#B98748', '#8A6A9B']
PLOT_TEMPLATE = 'plotly_white'

def mostrar_grafico(fig, altura=370):
    fig.update_layout(
        template=PLOT_TEMPLATE, height=altura,
        margin=dict(l=18, r=18, t=65, b=25),
        font=dict(family='Arial', size=13, color='#24354A'),
        title_font=dict(size=17, color='#24354A'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0),
        paper_bgcolor='white', plot_bgcolor='white',
    )
    fig.update_xaxes(showgrid=True, gridcolor='#EAEFF4', zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#EAEFF4', zeroline=False)
    st.plotly_chart(fig, use_container_width=True)

st.subheader('📈 Evolución y rentabilidad')
by_month = df.assign(Mes=df.Fecha.dt.to_period('M').dt.to_timestamp()).groupby('Mes', as_index=False).agg(
    Ventas=('VentaNeta', 'sum'), Utilidad=('UtilidadCalculada', 'sum'))
by_month['Margen (%)'] = by_month.Utilidad / by_month.Ventas.replace(0, float('nan')) * 100
left, right = st.columns([1.65, 1])
with left:
    # Serie temporal: líneas con dos colores para comparar ventas y utilidad.
    fig = px.line(by_month, x='Mes', y=['Ventas', 'Utilidad'], markers=True,
                  color_discrete_sequence=[PALETA[0], PALETA[1]],
                  title='Tendencia mensual · ventas y utilidad',
                  labels={'value': 'USD', 'variable': 'Indicador', 'Mes': 'Mes'})
    fig.update_traces(line=dict(width=3), marker=dict(size=7))
    mostrar_grafico(fig)
with right:
    # Área para comunicar la evolución del margen, distinta de las líneas anteriores.
    fig = px.area(by_month, x='Mes', y='Margen (%)',
                  color_discrete_sequence=[PALETA[2]],
                  title='Evolución del margen bruto',
                  labels={'Mes': 'Mes', 'Margen (%)': 'Margen (%)'})
    fig.update_traces(line=dict(width=2))
    mostrar_grafico(fig)

st.subheader('🌎 Desempeño geográfico y comercial')
left, right = st.columns(2)
with left:
    city = df.groupby('Ciudad', as_index=False).VentaNeta.sum().sort_values('VentaNeta', ascending=False)
    # Barras verticales con colores distintos por ciudad.
    fig = px.bar(city, x='Ciudad', y='VentaNeta', color='Ciudad',
                 color_discrete_sequence=PALETA, title='Facturación por ciudad',
                 labels={'VentaNeta': 'Ventas (USD)', 'Ciudad': 'Ciudad'})
    fig.update_layout(showlegend=False)
    mostrar_grafico(fig)
with right:
    branch = df.groupby('Sucursal', as_index=False).VentaNeta.sum().sort_values('VentaNeta', ascending=False).head(12)
    # Barras horizontales para que los nombres de sucursal sean legibles.
    fig = px.bar(branch.sort_values('VentaNeta'), x='VentaNeta', y='Sucursal',
                 orientation='h', color='VentaNeta', color_continuous_scale='Tealgrn',
                 title='Sucursales con mayores ventas · Top 12',
                 labels={'VentaNeta': 'Ventas (USD)', 'Sucursal': 'Sucursal'})
    fig.update_layout(coloraxis_showscale=False)
    mostrar_grafico(fig, 440)

left, right = st.columns(2)
with left:
    seg = df.groupby('Segmento', as_index=False).VentaNeta.sum().sort_values('VentaNeta', ascending=False)
    # Donut para participación por segmento; evitar demasiadas categorías.
    if len(seg) <= 7:
        fig = px.pie(seg, names='Segmento', values='VentaNeta', hole=0.58,
                     color_discrete_sequence=PALETA, title='Participación de ventas por segmento')
        fig.update_traces(textposition='inside', textinfo='percent',
                          hovertemplate='%{label}<br>Ventas: $%{value:,.2f}<br>Participación: %{percent}<extra></extra>')
    else:
        fig = px.bar(seg, x='Segmento', y='VentaNeta', color='Segmento',
                     color_discrete_sequence=PALETA, title='Ventas por segmento',
                     labels={'VentaNeta': 'Ventas (USD)'})
        fig.update_layout(showlegend=False)
    mostrar_grafico(fig)
with right:
    top = df.groupby('ProductoDetalle', as_index=False).agg(
        Unidades=('Cantidad', 'sum'), Ventas=('VentaNeta', 'sum'),
        Utilidad=('UtilidadCalculada', 'sum')).sort_values('Unidades', ascending=False).head(10)
    # Barras horizontales con gradiente por volumen.
    fig = px.bar(top.sort_values('Unidades'), x='Unidades', y='ProductoDetalle',
                 orientation='h', color='Unidades', color_continuous_scale='Sunset',
                 title='Los 10 productos más vendidos · unidades',
                 labels={'Unidades': 'Unidades vendidas', 'ProductoDetalle': 'Producto'})
    fig.update_layout(coloraxis_showscale=False)
    mostrar_grafico(fig, 440)

st.subheader('🍕 Composición de ventas y rentabilidad')
left, right = st.columns(2)
with left:
    category = df.groupby('Categoria', dropna=False, as_index=False).VentaNeta.sum().sort_values('VentaNeta', ascending=False)
    category['Categoria'] = category['Categoria'].fillna('Sin categoría')
    # Treemap: superficie proporcional a la venta por categoría.
    fig = px.treemap(category, path=['Categoria'], values='VentaNeta',
                     color='VentaNeta', color_continuous_scale='Teal',
                     title='Distribución de ventas por categoría')
    fig.update_layout(coloraxis_showscale=False)
    mostrar_grafico(fig)
with right:
    # Ranking horizontal: compara márgenes por producto sin mezclar USD y porcentajes en los ejes.
    rentabilidad = df.groupby('ProductoDetalle', as_index=False).agg(
        Ventas=('VentaNeta', 'sum'), Utilidad=('UtilidadCalculada', 'sum'),
        Unidades=('Cantidad', 'sum'))
    rentabilidad = rentabilidad[rentabilidad['Ventas'] > 0].copy()
    rentabilidad['Margen (%)'] = rentabilidad['Utilidad'] / rentabilidad['Ventas'] * 100
    rentabilidad = rentabilidad.dropna(subset=['Margen (%)'])
    # Se muestran los 12 productos con mayor facturación, ordenados por rentabilidad.
    ranking = rentabilidad.nlargest(12, 'Ventas').sort_values('Margen (%)')
    if ranking.empty:
        st.info('No hay productos con ventas positivas para calcular el margen bruto.')
    else:
        fig = px.bar(
            ranking, x='Margen (%)', y='ProductoDetalle', orientation='h',
            color='Margen (%)', color_continuous_scale='Tealgrn',
            text='Margen (%)', custom_data=['Ventas', 'Utilidad', 'Unidades'],
            title='Margen bruto (%) · 12 productos de mayor venta',
            labels={'Margen (%)': 'Margen bruto (%)', 'ProductoDetalle': 'Producto'}
        )
        fig.update_traces(
            texttemplate='%{text:.1f}%', textposition='outside',
            hovertemplate='<b>%{y}</b><br>Margen: %{x:.1f}%<br>Ventas: $%{customdata[0]:,.2f}<br>Utilidad: $%{customdata[1]:,.2f}<br>Unidades: %{customdata[2]:,.0f}<extra></extra>'
        )
        fig.update_layout(coloraxis_showscale=False, margin=dict(l=12, r=65, t=60, b=25))
        mostrar_grafico(fig, 440)
    st.caption('El ranking considera los 12 productos de mayor venta; el margen se calcula como utilidad bruta / ventas netas. Pasa el cursor para ver ventas y utilidad.')

with st.expander('📊 Tabla de detalle y descarga'):
    detail=df[['VentaID','Fecha','Ciudad','Sucursal','ClienteID','Segmento','ProductoDetalle','Cantidad','VentaNeta','CostoTotal','UtilidadCalculada']].copy()
    st.dataframe(detail,use_container_width=True,hide_index=True)
    st.download_button('Descargar ventas filtradas (CSV)',detail.to_csv(index=False).encode('utf-8-sig'),'ventas_filtradas.csv','text/csv')
with st.expander('🔎 Calidad de datos'):
    st.write(f'Registros de ventas válidos: **{len(ventas):,}**. Registros tras filtros: **{len(df):,}**.')
    st.write(f'Ventas sin cliente relacionado: **{int((base._cliente_match=="left_only").sum()):,}**; sin producto relacionado: **{int((base._producto_match=="left_only").sum()):,}**.')
    dif=(ventas.UtilidadBruta-ventas.UtilidadCalculada).abs()
    st.write(f'Filas con discrepancia de utilidad superior a USD 0,02: **{int((dif>0.02).sum()):,}**. Se usa la utilidad recalculada.')
    st.info('Se asume que VentaID identifica una transacción. Si una transacción puede contener múltiples líneas, la suma de ventas sigue siendo por línea y el ticket se divide por identificadores únicos.')

st.subheader('🤖 Asistente de recomendaciones comerciales')
st.caption('El análisis utiliza exclusivamente los datos filtrados. Las propuestas son hipótesis que deben revisarse antes de tomar decisiones.')
prod_stats=df.groupby('ProductoDetalle').agg(Ventas=('VentaNeta','sum'),Unidades=('Cantidad','sum'),Utilidad=('UtilidadCalculada','sum')).sort_values('Ventas',ascending=False)
branch_stats=df.groupby('Sucursal').agg(Ventas=('VentaNeta','sum'),Utilidad=('UtilidadCalculada','sum')).sort_values('Ventas',ascending=False)
seg_stats=df.groupby('Segmento').VentaNeta.sum().sort_values(ascending=False)
context={'ventas':round(ventas_total,2),'utilidad':round(utilidad,2),'margen_pct':round(margen,2),'ticket':round(ticket,2),'clientes':clientes_unicos,'transacciones':transacciones,'top_productos':prod_stats.head(8).round(2).reset_index().to_dict('records'),'sucursales':branch_stats.head(15).round(2).reset_index().to_dict('records'),'segmentos':seg_stats.round(2).to_dict(),'serie_mensual':by_month.tail(18).round(2).assign(Mes=lambda d:d.Mes.dt.strftime('%Y-%m')).to_dict('records')}
if st.button('Generar diagnóstico y recomendaciones',type='primary'):
    low_branch=branch_stats.assign(Margen=lambda d:d.Utilidad/d.Ventas.replace(0,float('nan'))*100).sort_values('Margen').head(1)
    st.markdown('**Diagnóstico automático basado en reglas (sin servicio externo):**')
    st.write(f'1. El margen bruto del período es **{margen:.1f}%**. Revisar descuentos, costos y mezcla de productos antes de fijar una meta de mejora.')
    if not top.empty:st.write(f'2. **{top.iloc[0].ProductoDetalle}** lidera las unidades vendidas ({top.iloc[0].Unidades:,.0f}); verificar su disponibilidad y rentabilidad antes de ampliar promociones.')
    if not low_branch.empty:st.write(f'3. **{low_branch.index[0]}** presenta el margen más bajo entre las sucursales del filtro ({low_branch.iloc[0].Margen:.1f}%); investigar composición de ventas, descuentos y costos.')
    if len(by_month)>1:st.write(f'4. Las ventas del último mes registrado fueron **{usd(by_month.iloc[-1].Ventas)}** frente a **{usd(by_month.iloc[-2].Ventas)}** del anterior. Comprobar si ambos meses tienen cobertura completa antes de interpretar la variación.')
    st.warning('Validación humana obligatoria: contrastar estacionalidad, cobertura temporal, stock, competencia y causalidad; no ejecutar decisiones automáticamente.')

st.markdown('**Consulta a un modelo de IA (opcional)**')
api_key=st.text_input('Clave API de OpenAI (solo para esta sesión)',type='password',help='La clave no se almacena en el proyecto. También puedes usar la variable de entorno OPENAI_API_KEY.')
question=st.text_area('Pregunta comercial','¿Qué oportunidades de mejora comercial muestran los datos y cómo las priorizarías?')
if st.button('Consultar IA'):
    key=api_key or os.getenv('OPENAI_API_KEY')
    if not key:st.info('Introduce una clave API para activar el modelo de IA. El diagnóstico automático anterior funciona sin clave.')
    else:
        try:
            from openai import OpenAI
            import json
            client=OpenAI(api_key=key)
            answer=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),instructions='Eres analista comercial. Responde en español. Usa solo los datos agregados entregados, no inventes cifras. Separa observaciones, recomendaciones, supuestos y riesgos. Señala que las recomendaciones requieren validación humana.',input=f'Datos agregados: {json.dumps(context,ensure_ascii=False,default=str)}\nPregunta: {question}')
            st.markdown(answer.output_text)
            st.warning('La IA puede equivocarse. El equipo debe verificar cálculos, supuestos y viabilidad antes de incorporar las recomendaciones.')
        except Exception as e:st.error(f'No fue posible consultar el modelo: {e}')
