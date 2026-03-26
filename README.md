# DHM Pro

Aplicación de escritorio para gestión de clientes, dominios, hosting, tickets, cotizaciones, facturación y auditoría para un reseller o pequeña operación de servicios digitales.

> Estado actual: **prototipo funcional / MVP**. El código muestra una base sólida de funcionalidades, pero necesita ajustes de estructura, dependencias y endurecimiento antes de publicarse como proyecto listo para producción.

## Qué hace

- Dashboard con métricas de servicios, tickets, vencimientos próximos y actividad reciente.
- Gestión de clientes.
- Gestión de servicios/inventario (dominios, hosting, SSL, etc.).
- CRM con tickets, cotizaciones, tareas y plantillas de mensajes.
- Facturación manual y automática por renovación.
- Reportes CSV/PDF.
- Bitácora de auditoría.
- Backups y restauración de base SQLite.
- Recordatorios automáticos por vencimiento.
- Integración básica con WhatsApp (`wa.me`) y email (`mailto:`).

## Stack técnico

- **Python 3.10+**
- **PySide6** para la interfaz gráfica
- **Peewee** como ORM
- **SQLite** como base local
- **FPDF** para PDFs
- **Pandas** para exportación CSV
- **Cryptography / Fernet** para cifrado simple de credenciales
- **PyInstaller** para empaquetado en Windows

## Estructura recomendada del repositorio

La app fue escrita esperando una estructura por paquetes. Para que funcione como está importada en el código, el repositorio debería quedar así:

```text
.
├── main.py
├── seed.py
├── build_exe.py
├── README.md
└── app/
    ├── __init__.py
    ├── models/
    │   ├── __init__.py
    │   └── database.py
    ├── services/
    │   ├── __init__.py
    │   └── logic.py
    └── utils/
        ├── __init__.py
        └── security.py
```

## Instalación

### 1) Crear entorno virtual

```bash
python -m venv .venv
```

### 2) Activarlo

**Windows (PowerShell)**

```bash
.venv\Scripts\Activate.ps1
```

**Linux/macOS**

```bash
source .venv/bin/activate
```

### 3) Instalar dependencias

```bash
pip install PySide6 peewee pandas fpdf cryptography pyinstaller
```

## Puesta en marcha

### Inicializar base de datos

```bash
python seed.py
```

Esto crea `dhm_local.db` y carga datos demo.

### Ejecutar la app

```bash
python main.py
```

### Credenciales por defecto

```text
usuario: admin
contraseña: admin
```

## Empaquetado a EXE

```bash
python build_exe.py
```

El script genera un ejecutable de Windows con PyInstaller.

## Base de datos y archivos locales

La aplicación guarda archivos locales en el directorio de trabajo:

- `dhm_local.db`: base SQLite
- `secret.key`: clave Fernet para cifrado local
- backups `dhm_backup_YYYYMMDD_HHMMSS.db`

## Módulos principales

### `main.py`
Contiene toda la interfaz PySide6:

- login
- navegación lateral
- dashboard
- clientes
- inventario
- CRM
- finanzas
- reportes
- configuración
- bitácora

### `database.py`
Define los modelos principales:

- `Provider`
- `Client`
- `Contact`
- `Service`
- `Ticket`
- `Offer`
- `Task`
- `MessageTemplate`
- `Invoice`
- `InvoiceItem`
- `Payment`
- `Note`
- `Reminder`
- `AuditLog`

### `logic.py`
Contiene la lógica de negocio:

- cálculo de estados de servicios
- renovaciones
- facturación masiva
- exportaciones
- pagos
- reportes
- plantillas y mensajería
- recordatorios

### `security.py`
Incluye:

- generación/carga de clave Fernet
- cifrado / descifrado de payloads
- backup y restore de SQLite

### `seed.py`
Carga datos de ejemplo para pruebas manuales.

## Flujo funcional esperado

1. Inicializar BD.
2. Iniciar sesión local.
3. Registrar clientes.
4. Registrar servicios con fecha de vencimiento.
5. Visualizar alertas y renovaciones.
6. Generar facturas manuales o automáticas.
7. Registrar pagos.
8. Exportar reportes y comprobantes.

## Limitaciones y mejoras pendientes

Antes de publicar o usar en operación real, conviene resolver lo siguiente:

1. **Estructura del proyecto**
   - Los imports apuntan a `app.models`, `app.services` y `app.utils`.
   - Si los archivos están planos en la raíz, la app no arranca sin reorganizar el repo.

2. **Seguridad**
   - Login fijo `admin/admin`.
   - No hay gestión real de usuarios, hashing ni roles.
   - `secret.key` se genera localmente pero no hay estrategia de rotación ni manejo seguro para despliegue.

3. **Calidad de datos**
   - Faltan validaciones más estrictas para emails, teléfonos, montos y duplicados funcionales.
   - Conviene normalizar catálogos y estados.

4. **Arquitectura**
   - `main.py` concentra demasiada lógica de UI en un solo archivo grande.
   - Recomendable separar vistas, diálogos, servicios y utilidades.

5. **Manejo de errores**
   - Hay operaciones que hoy dependen de supuestos frágiles y pueden romperse en tiempo de ejecución.

6. **Packaging**
   - Antes de distribuir un EXE, validar recursos, rutas relativas, base inicial y estructura final de paquetes.

## Roadmap sugerido

- [ ] Reorganizar el proyecto en paquetes reales (`app/models`, `app/services`, `app/utils`)
- [ ] Crear `requirements.txt`
- [ ] Agregar `.gitignore`
- [ ] Separar la UI por módulos
- [ ] Reemplazar login hardcoded por autenticación real
- [ ] Agregar pruebas unitarias para la lógica de negocio
- [ ] Corregir consultas y backrefs inconsistentes
- [ ] Añadir migraciones de base de datos
- [ ] Preparar build reproducible para Windows

## `.gitignore` recomendado

```gitignore
__pycache__/
*.pyc
.venv/
build/
dist/
*.spec
*.db
*.pre_restore
secret.key
*.log
```

## Licencia

Define aquí la licencia que quieras usar, por ejemplo MIT.

---

Si vas a subir este proyecto a GitHub, lo recomendable es hacerlo como **desktop business app / internal tool** y no venderlo todavía como release estable hasta corregir la estructura y los bugs detectados.
