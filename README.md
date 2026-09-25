# Cuillas — Punto de Venta

Sistema de Punto de Venta de escritorio para **Cuillas** (bebidas, crepas y waffles), hecho con Python y CustomTkinter.

## Funcionalidades

- **Login con roles** (administrador / vendedor), cada uno con su propia vista.
- **Inventario**: ingredientes, boba/perlas explosivas, bebidas y desechables, con bitácora de movimientos de stock (entradas, ajustes y consumo por venta). El vendedor puede registrar entradas de mercancía; solo el administrador puede crear, editar o desactivar artículos.
- **Punto de venta**: catálogo de Crepas/Waffles (armado a la medida con ingredientes) y Bebidas (con extras de boba/perlas) en una sola pantalla, carrito de cobro con descuentos, promociones y atribución de qué empleado cobró.
- **Impresión**: ticket para el cliente y comanda de preparación (sin precios) en una impresora térmica Epson ESC/POS por USB.
- **Cobro con tarjeta**: integración con Mercado Pago Point (con un simulador de terminal mientras no haya credenciales configuradas).
- **Dashboard y reportes**: ventas, productos más vendidos, ventas y descuentos por empleado, gastos del negocio, y exportación de todo a PDF.
- **Recetas**: cada producto tiene una imagen de paso a paso (ampliable a pantalla completa) junto con ingredientes y pasos detallados.

## Requisitos

- Python 3.11 o superior (evita el Python que trae macOS por defecto — instala uno desde [python.org](https://www.python.org/downloads/) o con Homebrew).
- Para imprimir tickets: la librería de sistema `libusb` (`brew install libusb` en Mac).

## Instalación

```bash
git clone <url-del-repositorio>
cd puntodeventa
python3 -m venv venv
source venv/bin/activate   # en Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 main.py
```

La primera vez que se corre, se crea automáticamente la base de datos (`data/pos.db`) con datos de ejemplo, incluyendo dos usuarios para entrar:

| Usuario    | Contraseña   | Rol           |
|------------|--------------|---------------|
| `admin`    | `admin123`   | Administrador |
| `vendedor` | `vendedor123`| Vendedor      |

### Probar en Windows con Git + VS Code

Windows es el sistema operativo con el que se va a usar en Cuillas, así que antes de armar un instalador conviene probar así, corriendo el código directo desde Git — cada `git pull` trae los cambios en segundos, sin tener que generar un instalador nuevo cada vez.

1. **Instalar Python** desde [python.org/downloads](https://www.python.org/downloads/) (no el que ofrece la Microsoft Store). En el instalador, en la primera pantalla, marca la casilla **"Add python.exe to PATH"** antes de darle a Install — si no la marcas, Windows no va a reconocer el comando `python`.
2. **Instalar Git para Windows** desde [git-scm.com/download/win](https://git-scm.com/download/win). Se puede dejar todo con las opciones por default del instalador.
3. **Instalar VS Code** desde [code.visualstudio.com](https://code.visualstudio.com/) y, ya adentro, instalar la extensión oficial **"Python"** (de Microsoft) desde la pestaña de extensiones.
4. Abrir una carpeta donde quieras guardar el proyecto, clic derecho → **"Abrir en Terminal"** (o abrir VS Code y usar su terminal integrada con `` Ctrl+` ``), y correr:

   ```powershell
   git clone <url-del-repositorio>
   cd puntodeventa
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

   Nota: en Windows el comando es `python`, no `python3`.

5. Si al activar el entorno virtual (`venv\Scripts\activate`) PowerShell dice algo como *"no se puede cargar porque la ejecución de scripts está deshabilitada"*, es una restricción de seguridad normal en Windows. Se resuelve corriendo una sola vez, en esa misma ventana de PowerShell:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

   y luego repitiendo `venv\Scripts\activate`.

6. Para abrir el proyecto directamente en VS Code después de clonarlo: `code .` desde la misma carpeta (o Archivo → Abrir carpeta). Con `Ctrl+Shift+P` → **"Python: Select Interpreter"** puedes elegir el intérprete de `venv` para que VS Code use ese entorno.

Cada vez que haya cambios nuevos para probar, basta con `git pull` dentro de la carpeta del proyecto y volver a correr `python main.py` (solo se necesita repetir `pip install -r requirements.txt` si `requirements.txt` cambió).

> Nota aparte: para imprimir con la impresora térmica por USB en Windows normalmente hace falta instalar un driver adicional (con una herramienta llamada Zadig) para que Windows la reconozca como dispositivo USB genérico. Eso lo vemos cuando lleguemos a probar la impresión real, no bloquea nada de lo anterior.

## Configuración opcional (`.env`)

Copia `.env.example` a `.env` para configurar Mercado Pago Point (`MP_ACCESS_TOKEN` y `MP_TERMINAL_ID`). Mientras no esté configurado, el cobro con tarjeta usa un simulador para poder probar el flujo completo sin cuenta ni terminal real. El archivo `.env` nunca debe subirse al repositorio (ya está en `.gitignore`).

## Estructura del proyecto

```
db/         esquema de la base de datos, migraciones y datos de ejemplo
models/     acceso a datos (una clase + funciones CRUD por tabla)
services/   lógica de negocio (validaciones, reportes, impresión, Mercado Pago)
ui/         interfaz en CustomTkinter (admin/, ventas/, recetas/, components/)
assets/     logo e imágenes usadas en la app
```

## Notas

- Cada quien crea su propio entorno virtual (`venv`) local; no se sube al repositorio.
- La base de datos (`data/pos.db`) tampoco se sube — es la información real del negocio, distinta en cada instalación.
