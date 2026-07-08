# 🍔 Mr. Beast Burger — Dashboard de Delivery

Dashboard interactivo en **Streamlit** conectado a **Google Sheets**, con la identidad visual de la marca (fondo `#121212`, azul `#00BFFF`, rosa `#FF007F`, fuentes Anybody / Be Vietnam Pro).

## Qué incluye

- **Resumen en tarjetas**: venta total, transacciones, ticket promedio, cancelaciones (en órdenes y en Bs).
- **Heatmap 12:00–23:00** por día de semana con 3 tonalidades — **Bajo / Medio / Rush** — mostrando pedidos promedio y venta promedio por hora.
- **Análisis de ticket**: cuántas transacciones están cerca/dentro de la media (banda ajustable ±%) y cuántas están en el promedio o por encima.
- **Filtros**: rango de fechas y sucursal (Equipetrol, Centro, Norte).
- Tablas por sucursal y método de pago, y venta por día.
- Si Google Sheets falla, permite subir el `.xlsx/.csv` manualmente.

> Nota de negocio: el 100% de la venta se recibe en línea. «Pago en efectivo» = lo que el cliente paga al repartidor; el rider no entrega dinero al negocio.

## Paso 1 — Subir la base a Google Sheets

1. Entra a [sheets.google.com](https://sheets.google.com) → hoja nueva.
2. **Archivo → Importar → Subir** el `.xlsx` que descarga la app de delivery → "Reemplazar hoja".
3. No cambies los encabezados (el app los reconoce tal como vienen del reporte).
4. **Compartir → "Cualquier persona con el enlace" → Lector** y copia la URL.
   (Si prefieres mantenerla privada, usa la Opción B del archivo `.streamlit/secrets.toml.example` con Service Account.)

Cuando descargues un reporte nuevo, solo pega/importa las filas nuevas en la misma hoja: el dashboard se actualiza solo (caché de 5 min).

## Paso 2 — Subir el código a GitHub

1. Crea un repositorio en [github.com](https://github.com/new) (ej. `mrbeast-dashboard`, puede ser privado).
2. Sube estos archivos:

```
mrbeast-dashboard/
├── app.py
├── requirements.txt
├── .gitignore
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

O por terminal:

```bash
git init
git add .
git commit -m "Dashboard Mr. Beast Burger"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/mrbeast-dashboard.git
git push -u origin main
```

⚠️ Nunca subas `secrets.toml` real (el `.gitignore` ya lo bloquea).

## Paso 3 — Desplegar en Streamlit Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) con tu cuenta de GitHub.
2. **New app** → elige tu repo → branch `main` → archivo `app.py` → Deploy.
3. En **App → Settings → Secrets**, pega:

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA/edit"
worksheet = "0"
```

4. Guarda y reinicia la app. Listo: tendrás una URL pública tipo `https://tu-app.streamlit.app`.

## Ejecutar en local (opcional)

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # edita la URL
streamlit run app.py
```

## Cómo se calcula el heatmap

Para cada combinación día-de-semana × hora se calcula el **promedio de pedidos por día** (total de pedidos ÷ nº de fechas de ese día en el rango filtrado). Los umbrales Bajo/Medio/Rush son los terciles de esos promedios, así que se recalibran automáticamente con cada filtro.
