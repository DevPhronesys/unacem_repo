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
Puedes explorar el dashboard con los datos de ejemplo pre-cargados o apuntarlo a tu API.

Para iniciar la app:

```bash
streamlit run dashboard.py --server.port 8501
```

### Fuentes de datos
- **API en vivo (por defecto)**: el campo "API URL" viene precargado con `https://retoolapi.dev/dle9do/data` y la app descarga esa información al arrancar.
- **API personalizada**: si reemplazas la URL por otro endpoint compatible, se procesan los datos de ese servicio.

El dashboard mostrará:

- Filtros por mes, cliente y sede.
- Los meses se presentan en español (julio a diciembre) y el listado de sedes se acota al cliente seleccionado.
- Matriz de órdenes por rangos de distancia (0-1 km, 1-2 km, …, >10 km) con totales.
- Detalle de órdenes con distancia calculada (haversine) redondeada a 2 decimales.
- Mapa pydeck con color diferenciado para sedes y entregas.
