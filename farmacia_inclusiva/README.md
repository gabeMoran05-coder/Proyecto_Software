# 🏥 Farmacia Inclusiva – Sistema de Gestión

Django + PostgreSQL + PostgREST + Docker  
Proyecto académico – Instituto Tecnológico de Colima

---

## 📁 Estructura del proyecto

```
PROYECTO_SOFTWARE-MASTER/
├── apps/
│   ├── usuarios/        ← Autenticación y roles (admin/cajero)
│   ├── medicamentos/    ← Inventario, lotes, códigos QR, colorimetría
│   ├── ventas/          ← Punto de venta, historial, reportes
│   ├── clientes/        ← Registro de clientes
│   ├── proveedores/     ← Catálogo de proveedores
│   └── notificaciones/  ← Envío WhatsApp automático
├── config/              ← settings.py, urls.py, wsgi.py
├── templates/           ← HTML de todas las vistas
├── static/              ← CSS / JS
├── scripts/             ← setup_inicial.py, init_postgrest_role.sql
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## 🚀 Cómo levantar el proyecto (primera vez)

### 1. Requisitos previos
- Docker Desktop instalado y corriendo
- VS Code con extensión Docker (opcional)

### 2. Clonar / copiar el proyecto
Asegúrate de estar en la carpeta `PROYECTO_SOFTWARE-MASTER`

### 3. Crear archivo .env
Copia el archivo `.env` que ya viene incluido.  
Puedes cambiar las contraseñas si quieres.

### 4. Levantar los contenedores
```bash
docker compose up --build
```
Espera a que aparezca: `Starting development server at http://0.0.0.0:8000/`

### 5. Setup inicial (solo la primera vez)
En una terminal nueva:
```bash
docker compose exec web python scripts/setup_inicial.py
```
Esto crea:
- Usuario **admin** / contraseña: `Admin123!`
- Usuario **cajero1** / contraseña: `Cajero123!`
- Métodos de pago (Efectivo, Tarjeta, Transferencia)

### 6. Acceder al sistema
| Servicio | URL |
|---|---|
| Sistema web | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| API PostgREST | http://localhost:3000 |
| Swagger UI (API docs) | http://localhost:8080 |

---

## 🛑 Comandos útiles

```bash
# Parar contenedores
docker compose down

# Ver logs
docker compose logs web
docker compose logs db

# Crear migraciones después de cambiar modelos
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Crear superusuario manual
docker compose exec web python manage.py createsuperuser

# Ver logs de un contenedor específico
docker compose logs -f web
```

---

## 🎨 Funcionalidades principales

| Módulo | Descripción |
|---|---|
| **Colorimetría** | Semáforo Verde/Amarillo/Rojo automático por fecha de caducidad |
| **Códigos QR** | Generación de QR por medicamento, sticker imprimible |
| **Página pública QR** | El cliente escanea y ve el estado del medicamento + **audio descriptivo** |
| **Punto de venta** | Caja rápida con búsqueda AJAX y descuento automático de stock |
| **WhatsApp** | Genera enlace wa.me con info del medicamento al completar venta |
| **PostgREST** | API REST automática sobre PostgreSQL en puerto 3000 |

---

## 👥 Roles de usuario

| Rol | Permisos |
|---|---|
| **Administrador** | Todo: CRUD medicamentos, lotes, usuarios, proveedores, reportes |
| **Cajero** | Punto de venta, consultar medicamentos, sus propias ventas |
