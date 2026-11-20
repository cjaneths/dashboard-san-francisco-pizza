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
usd=lambda x:f'${x:,.2f}'

st.subheader('Indicadores ejecutivos')
cols=st.columns(3)
for c,label,value in zip(cols,['Ventas totales','Utilidad bruta','Margen bruto'],[usd(ventas_total),usd(utilidad),f'{margen:,.2f}%']):c.metric(label,value)
cols=st.columns(3)
for c,label,value in zip(cols,['Ticket promedio','Clientes únicos','Transacciones'],[usd(ticket),f'{clientes_unicos:,}',f'{transacciones:,}']):c.metric(label,value)
st.caption('Utilidad bruta = venta neta − costo total; margen = utilidad / venta neta; ticket = venta neta / VentaID únicos. Los clientes se cuentan por ClienteID distinto.')

st.subheader('Evolución y rentabilidad')
by_month=df.assign(Mes=df.Fecha.dt.to_period('M').dt.to_timestamp()).groupby('Mes',as_index=False).agg(Ventas=('VentaNeta','sum'),Utilidad=('UtilidadCalculada','sum'))
by_month['Margen (%)']=by_month.Utilidad/by_month.Ventas.replace(0,float('nan'))*100
left,right=st.columns([2,1])
with left:st.plotly_chart(px.line(by_month,x='Mes',y=['Ventas','Utilidad'],markers=True,title='Ventas y utilidad por mes',labels={'value':'USD','variable':'Indicador'}),use_container_width=True)
with right:st.plotly_chart(px.line(by_month,x='Mes',y='Margen (%)',markers=True,title='Margen bruto mensual'),use_container_width=True)

st.subheader('Desempeño comercial')
left,right=st.columns(2)
with left:
    city=df.groupby('Ciudad',as_index=False).VentaNeta.sum().sort_values('VentaNeta',ascending=False)
    st.plotly_chart(px.bar(city,x='VentaNeta',y='Ciudad',orientation='h',title='Ventas por ciudad',labels={'VentaNeta':'Ventas (USD)'}),use_container_width=True)
with right:
    branch=df.groupby('Sucursal',as_index=False).VentaNeta.sum().sort_values('VentaNeta',ascending=False).head(15)
    st.plotly_chart(px.bar(branch,x='VentaNeta',y='Sucursal',orientation='h',title='Ventas por sucursal · Top 15',labels={'VentaNeta':'Ventas (USD)'}),use_container_width=True)
left,right=st.columns(2)
with left:
    seg=df.groupby('Segmento',as_index=False).VentaNeta.sum().sort_values('VentaNeta',ascending=False)
    st.plotly_chart(px.bar(seg,x='Segmento',y='VentaNeta',title='Ventas por segmento',labels={'VentaNeta':'Ventas (USD)'}),use_container_width=True)
with right:
    top=df.groupby('ProductoDetalle',as_index=False).agg(Unidades=('Cantidad','sum'),Ventas=('VentaNeta','sum'),Utilidad=('UtilidadCalculada','sum')).sort_values('Unidades',ascending=False).head(10)
    st.plotly_chart(px.bar(top.sort_values('Unidades'),x='Unidades',y='ProductoDetalle',orientation='h',title='Top 10 productos por unidades'),use_container_width=True)

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
