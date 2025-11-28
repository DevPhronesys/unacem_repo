# unacem_repo

Dashboard interactivo para órdenes de entrega con filtrado por mes, cliente y sede, matriz de distancias y mapa con puntos de sede y entrega.

## Requisitos
Instala dependencias con:

```bash
pip install -r requirements.txt
```

## Datos esperados
El API debe devolver un JSON con las órdenes que incluya:

- `fecha_creacion` o `fecha_creacion_copia` (se usa para el filtro por mes)
- `organizacion` (cliente)
- `local` (sede/pedido)
- `lat_sede`, `lng_sede` (coordenadas de la sede)
- `latitud_entrega`, `longitud_entrega` (coordenadas de entrega)
- `order_id`, `no_orden` (identificadores usados en el detalle)

## Ejecución
Por defecto la app apunta al API público `https://retoolapi.dev/dle9do/data`. Puedes cambiar el endpoint en la barra lateral.

Ejecútalo con:

```bash
streamlit run dashboard.py --server.port 8501
```

Luego ingresa o confirma la URL del API en la barra lateral para cargar y explorar las órdenes. El dashboard mostrará:

- Filtros por mes, cliente y sede.
- Matriz mensual de órdenes por rangos de distancia (0-1 km, 1-2 km, …, >10 km) con totales y porcentajes.
- Detalle de órdenes con distancia calculada (haversine) redondeada a 2 decimales.
- Mapa pydeck con color diferenciado para sedes y entregas.
