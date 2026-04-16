# 🌿 Farmacia Inclusiva

Sistema web de gestión para farmacias desarrollado con **Django 5** y **PostgreSQL**, orientado a facilitar el control de inventario, ventas, clientes y proveedores.

> Proyecto desarrollado en el **Instituto Tecnológico de Colima**  
> Autores: Ayala Reynoso · Morán Aréchiga · Rodríguez García

---

## 📋 Tabla de contenidos

- [Descripción](#descripción)
- [Características principales](#características-principales)
- [Tecnologías](#tecnologías)
- [Modelo de datos](#modelo-de-datos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación y configuración](#instalación-y-configuración)
- [Variables de entorno](#variables-de-entorno)
- [Comandos útiles](#comandos-útiles)
- [Módulos del sistema](#módulos-del-sistema)

---

## Descripción

Farmacia Inclusiva es una aplicación web para la gestión integral de una farmacia. Permite registrar y controlar el inventario de medicamentos por lotes, administrar las relaciones con proveedores y clientes, gestionar las cuentas de los usuarios del sistema y procesar ventas con su detalle de productos.

El sistema incluye un esquema de **colorimetría de inventario** que clasifica cada medicamento según su nivel de stock (verde, amarillo, rojo o sin stock), además de la generación y gestión de **códigos QR** por medicamento.

---

## Características principales

- **Gestión de inventario** con control por lote: número de lote, fechas de fabricación/caducidad/ingreso, precios de compra y venta, stock actual y estado de activación.
- **Colorimetría de stock**: cada medicamento tiene un estado visual (🟢 verde, 🟡 amarillo, 🔴 rojo, ⚫ sin stock) para identificar rápidamente el nivel de inventario.
- **Control de medicamentos**: nombre, presentación, concentración, indicador de receta y fecha de registro.
- **Códigos QR**: generación, regeneración, seguimiento de escaneos y estado activo/inactivo por medicamento.
- **Proveedores**: directorio con nombre, teléfono, correo y dirección; vista de todos los lotes suministrados.
- **Clientes**: registro de nombre, apellidos, teléfono y fecha de alta; historial de compras por cliente.
- **Usuarios**: gestión de cuentas con roles (administrador, cajero, almacén), datos personales y registro de última conexión.
- **Ventas**: punto de venta con carrito dinámico, selección de cajero, método de pago y cliente opcional; detalle de productos por venta con ticket imprimible.
- **Dashboard**: resumen de alertas de inventario, ventas recientes del día y accesos rápidos a las acciones más frecuentes.
- Interfaz web responsive construida con Django Templates.
- Contenerización completa con **Docker Compose** (Django + PostgreSQL).

---

## Tecnologías

| Componente | Tecnología |
|---|---|
| Backend | Django 5.0.2 (Python 3.11) |
| Base de datos | PostgreSQL 15 |
| ORM | Django ORM |
| Frontend | Django Templates + CSS personalizado |
| Imágenes | Pillow 10.2.0 |
| Contenerización | Docker & Docker Compose |

---

## Modelo de datos

El sistema está compuesto por las siguientes entidades principales y sus relaciones:

```
Proveedor ──────────────────┐
                            ↓
                          Lote ──────────────┐
                                             ↓
                                      Medicamento ←─── CodigoQR
                                             ↑
                                             │
Usuario ──────────────┐                     │
                      ↓                     │
Cliente ──────────► Venta ──────► DetalleVenta
                      ↑
                MetodoPago
```

### Entidades

**`proveedor`** — Directorio de proveedores de medicamentos.

| Campo | Tipo | Descripción |
|---|---|---|
| id_prov | Serial PK | Identificador único |
| nombre | VARCHAR(100) | Nombre del proveedor |
| telefono | VARCHAR(15) | Teléfono de contacto |
| correo | VARCHAR(100) | Correo electrónico |
| direccion | VARCHAR(200) | Dirección física |

**`lote`** — Entradas de mercancía agrupadas por número de lote.

| Campo | Tipo | Descripción |
|---|---|---|
| id_lote | Serial PK | Identificador único |
| id_prov | FK → proveedor | Proveedor que lo suministró |
| numero_lote | VARCHAR(60) | Clave del lote |
| fecha_fabricacion | DATE | Fecha de fabricación |
| fecha_caducidad | DATE | Fecha de vencimiento |
| fecha_ingreso | DATE | Fecha de entrada al almacén |
| fecha_compra | DATE | Fecha de compra al proveedor |
| stock_actual | INTEGER | Unidades disponibles |
| activo | BOOLEAN | Si el lote sigue activo |
| precio_compra | NUMERIC(10,2) | Precio pagado al proveedor |
| precio_venta | NUMERIC(10,2) | Precio de venta al público |

**`medicamento`** — Catálogo de productos de la farmacia.

| Campo | Tipo | Descripción |
|---|---|---|
| id_med | Serial PK | Identificador único |
| id_lote | FK → lote | Lote al que pertenece |
| nombre | VARCHAR(120) | Nombre del medicamento |
| presentacion | VARCHAR(80) | Tabletas, jarabe, cápsulas, etc. |
| concentracion | VARCHAR(60) | Ej: 500mg, 250mg/5ml |
| requiere_receta | BOOLEAN | Si necesita prescripción |
| fecha_registro | DATE | Fecha de alta en el sistema |
| estado_colorimetria | VARCHAR(20) | `verde`, `amarillo`, `rojo`, `sin_stock` |

**`codigos_qr`** — Códigos QR vinculados a medicamentos.

| Campo | Tipo | Descripción |
|---|---|---|
| id_qr | Serial PK | Identificador único |
| id_medicamento | FK → medicamento | Medicamento al que pertenece |
| token | VARCHAR(64) UNIQUE | Token único del QR |
| url_qr | VARCHAR(255) | URL que codifica el QR |
| fecha_generacion | DATE | Cuándo fue generado |
| fecha_regeneracion | DATE | Última regeneración |
| contador_escaneos | INTEGER | Número de veces escaneado |
| activo | BOOLEAN | Si el QR está vigente |

**`usuario`** — Cuentas de acceso al sistema.

| Campo | Tipo | Descripción |
|---|---|---|
| id_usuario | Serial PK | Identificador único |
| usuario | VARCHAR(60) UNIQUE | Nombre de usuario |
| rol | VARCHAR(30) | `admin`, `cajero`, `almacen` |
| nombre | VARCHAR(80) | Nombre(s) |
| ap_pat | VARCHAR(60) | Apellido paterno |
| ap_mat | VARCHAR(60) | Apellido materno |
| telefono | VARCHAR(15) | Teléfono |
| fecha_creacion | DATE | Fecha de alta |
| ultima_conexion | TIMESTAMP | Último acceso registrado |

**`cliente`** — Registro de clientes de la farmacia.

| Campo | Tipo | Descripción |
|---|---|---|
| id_cliente | Serial PK | Identificador único |
| nombre | VARCHAR(80) | Nombre(s) |
| ap_pat | VARCHAR(60) | Apellido paterno |
| ap_mat | VARCHAR(60) | Apellido materno |
| telefono | VARCHAR(15) | Teléfono |
| fecha_registro | DATE | Fecha de alta |

**`metodo_pago`** — Catálogo de formas de pago aceptadas.

| Campo | Tipo | Descripción |
|---|---|---|
| id_metPag | Serial PK | Identificador único |
| nombre_metodo | VARCHAR(50) | Nombre del método |
| descripcion | VARCHAR(150) | Descripción opcional |

**`ventas`** — Registro de transacciones.

| Campo | Tipo | Descripción |
|---|---|---|
| id_ventas | Serial PK | Folio de la venta |
| id_usuario | FK → usuario | Cajero que la registró |
| id_metPag | FK → metodo_pago | Forma de pago utilizada |
| id_cliente | FK → cliente (nullable) | Cliente (puede ser público en general) |
| fecha_venta | TIMESTAMP | Fecha y hora de la transacción |
| total_venta | NUMERIC(10,2) | Total cobrado |

**`detalle_ventas_medicamento`** — Líneas de producto por venta.

| Campo | Tipo | Descripción |
|---|---|---|
| id_detalle | Serial PK | Identificador único |
| id_ventas | FK → ventas | Venta a la que pertenece |
| id_medicamento | FK → medicamento | Producto vendido |
| cantidad | INTEGER | Unidades vendidas |
| precio_unitario | NUMERIC(10,2) | Precio al momento de la venta |
| subtotal | NUMERIC(10,2) | cantidad × precio_unitario |

---

## Estructura del proyecto

```
farmacia_inclusiva/
│
├── docker-compose.yml          # Orquestación de servicios
├── Dockerfile                  # Imagen de la aplicación Django
├── .env                        # Variables de entorno (no subir a Git)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── requirements.txt            # Dependencias Python
├── manage.py
│
├── farmacia/                   # Configuración principal del proyecto
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── medicamentos/           # Gestión de medicamentos, lotes y QR
│   │   ├── models.py           # Lote, Medicamento, CodigoQR
│   │   ├── views.py
│   │   ├── admin.py
│   │   └── migrations/
│   │
│   ├── proveedores/            # Directorio de proveedores
│   │   ├── models.py           # Proveedor
│   │   ├── views.py
│   │   └── migrations/
│   │
│   ├── clientes/               # Registro de clientes
│   │   ├── models.py           # Cliente
│   │   ├── views.py
│   │   └── migrations/
│   │
│   ├── usuarios/               # Cuentas de acceso al sistema
│   │   ├── models.py           # Usuario
│   │   ├── views.py
│   │   └── migrations/
│   │
│   └── ventas/                 # Punto de venta y facturación
│       ├── models.py           # MetodoPago, Venta, DetalleVenta
│       ├── views.py
│       └── migrations/
│
├── templates/                  # Plantillas HTML
│   ├── base.html               # Layout global
│   ├── dashboard.html          # Página de inicio
│   ├── components/
│   │   ├── navbar.html
│   │   └── footer.html
│   ├── medicamentos/
│   ├── proveedores/
│   ├── clientes/
│   ├── usuarios/
│   └── ventas/
│
├── static/                     # Archivos estáticos
│
└── BaseDeDatos/
    └── farmacia_inclusiva.sql  # Script SQL de creación de tablas
```

---

## Instalación y configuración

### Prerrequisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop) instalado y corriendo
- Git

### Pasos

**1. Clonar el repositorio**

```bash
git clone <url-del-repositorio>
cd farmacia_inclusiva
```

**2. Crear el archivo de variables de entorno**

```bash
cp .env.example .env
```

Edita `.env` con tus valores (ver sección [Variables de entorno](#variables-de-entorno)).

**3. Construir e iniciar los contenedores**

```bash
docker compose up --build -d
```

**4. Aplicar las migraciones**

```bash
docker compose exec web python manage.py migrate
```

**5. Crear un superusuario para el panel de administración**

```bash
docker compose exec web python manage.py createsuperuser
```

**6. Abrir la aplicación**

- Aplicación: [http://localhost:8000](http://localhost:8000)
- Panel de administración: [http://localhost:8000/admin](http://localhost:8000/admin)

---

## Variables de entorno

Copia `.env.example` como `.env` y ajusta los valores. **Nunca subas `.env` a Git.**

```env
# Django
DJANGO_SECRET_KEY=django-insecure-change-this-in-production
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# PostgreSQL
POSTGRES_DB=farmacia_inclusiva
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Configuración regional
TIME_ZONE=America/Mexico_City
LANGUAGE_CODE=es-mx
```

> En producción establece `DJANGO_DEBUG=False` y usa una `DJANGO_SECRET_KEY` única y segura generada con:
> ```bash
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> ```

---

## Comandos útiles

```bash
# Iniciar servicios en segundo plano
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f web

# Detener servicios
docker compose down

# Crear migraciones después de modificar modelos
docker compose exec web python manage.py makemigrations

# Aplicar migraciones
docker compose exec web python manage.py migrate

# Abrir shell de Django (para pruebas de ORM)
docker compose exec web python manage.py shell

# Conectarse directamente a PostgreSQL
docker compose exec db psql -U postgres -d farmacia_inclusiva

# Recolectar archivos estáticos (producción)
docker compose exec web python manage.py collectstatic --noinput

# Eliminar contenedores y volúmenes (⚠️ borra la base de datos)
docker compose down -v
```

---

## Módulos del sistema

### 💊 Medicamentos y lotes

Permite registrar los medicamentos del catálogo de la farmacia, asociándolos a un lote de proveedor. Cada lote lleva control de fechas de fabricación, caducidad, precios y stock. El sistema asigna automáticamente un estado de colorimetría para alertas visuales de inventario.

### 📱 Códigos QR

Generación y gestión de códigos QR vinculados a medicamentos. Incluye contador de escaneos, regeneración de token y activación/desactivación de QR.

### 🏭 Proveedores

Directorio de los proveedores que surten a la farmacia. Desde el perfil de cada proveedor se puede ver el historial completo de lotes suministrados.

### 👤 Clientes

Registro de clientes con datos de contacto. El detalle de cada cliente muestra su historial de compras, lo que facilita el seguimiento y la atención personalizada.

### 👥 Usuarios

Gestión de las cuentas de acceso al sistema. Los roles disponibles son administrador, cajero y almacén, permitiendo diferenciar los niveles de acceso según las responsabilidades de cada persona.

### 🛒 Ventas

Punto de venta con selección dinámica de productos, cálculo automático de subtotales y total, método de pago y asociación opcional a un cliente registrado. Cada venta genera un detalle consultable e imprimible como ticket.

---

## Administración Django

El panel de administración en `/admin` permite gestionar todos los modelos directamente. Accede con el superusuario creado durante la instalación.

Modelos registrados:

- `Lote`, `Medicamento`, `CodigoQR` (app medicamentos)
- `Proveedor` (app proveedores)
- `Cliente` (app clientes)
- `Usuario` (app usuarios)
- `MetodoPago`, `Venta`, `DetalleVenta` (app ventas)

---

## Notas de desarrollo

- El proyecto usa `DJANGO_SETTINGS_MODULE = 'farmacia.settings'`
- La configuración de base de datos lee las credenciales desde variables de entorno, con valores por defecto para desarrollo local
- `ALLOWED_HOSTS = ['*']` está activado en el `settings.py` actual; en producción debe restringirse al dominio real
- Los archivos estáticos están configurados bajo `STATICFILES_DIRS = [BASE_DIR / 'static']`

---

*Instituto Tecnológico de Colima — Taller de Desarrollo Web*
