# Dietify - Sistema Experto Nutricional (Web UI)

Este es el sistema experto **Dietify**, diseñado para recomendar menús (diarios o semanales) basados en el inventario actual de tu cocina (alacenas, heladera) y tu tipo de dieta (deportes, peso, médica, propia/custom).

El sistema cuenta con una interfaz web interactiva desarrollada en **Streamlit** y utiliza la biblioteca **experta** de Python, un motor de reglas basado en CLIPS adaptado para Python, junto con una base de datos local **SQLite3**.

---

## Características
* **Sistema Experto:** Evalúa dinámicamente las recetas en la base de datos contra los ingredientes disponibles para determinar cuáles se pueden cocinar de inmediato (estado `✓ EXACTO`) o cuáles requieren comprar solo 1 o 2 ingredientes (estado `✗ CASI COMPLETO`).
* **Soporte para Planes de Dieta:**
  * **Deportes:** Prioriza comidas de alto valor proteico y carbohidratos (etiquetas `sports`, `high-protein`, `high-carb`).
  * **Control de Peso:** Prioriza comidas bajas en calorías o ricas en fibra (etiquetas `weight`, `low-calorie`, `low-carb`, `high-fiber`).
  * **Médica:** Prioriza comidas saludables y aplica filtros restrictivos (ej: excluye alimentos con miel/azúcar en perfiles de diabetes, o alimentos altos en sodio/grasas en hipertensión).
  * **Propia / General:** Ofrece recomendaciones generales sin restricciones estrictas.
* **Persistencia en SQLite3:** Guarda el inventario de la cocina y el catálogo de recetas de forma permanente en un archivo local `dietify.db`.
* **Inicialización Automática:** El sistema viene precargado con 18 recetas saludables y variadas. Si la base de datos no existe, se crea y siembra automáticamente en la primera ejecución.

---

## Estructura del Proyecto

```text
dietify/
├── dietify.db           (Tu base de datos SQLite)
├── dietify.py           (Punto de entrada CLI)
├── app.py               (Punto de entrada Web / HTTP)
├── core/
│   ├── __init__.py
│   ├── db.py            (Lógica de base de datos)
│   └── engine.py        (Motor de inferencia y reglas)
└── ui/
    ├── __init__.py
    ├── sidebar.py       (Componente del panel lateral)
    └── views.py         (Componentes de pestañas y renderizado)
```

---

## Instalación y Configuración

### 1. Prerrequisitos
Tener instalado Python 3.10 o superior (el sistema incluye un parche dinámico para compatibilidad de `experta` con Python 3.12+).

### 2. Crear Entorno Virtual e Instalar Dependencias
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar el entorno virtual
source venv/bin/activate  # En Linux/macOS
# o venv\Scripts\activate en Windows

# Instalar dependencias
pip install -r requirements.txt
```

---

## Ejecución del Programa

### Opción 1: Ejecución Rápida (Recomendado en Windows)
Si no quieres usar la terminal, simplemente ve a la carpeta del proyecto y haz **doble clic** en el archivo `iniciar.bat`. 
Este script se encargará de crear el entorno virtual, instalar lo que falte y abrir automáticamente la aplicación en tu navegador.

### Opción 2: Ejecución Manual (Windows / Mac / Linux)
Para iniciar la interfaz web de forma manual, asegúrate de estar en el entorno virtual activo y ejecuta el siguiente comando en la terminal:

```bash
streamlit run app.py
```

Esto abrirá automáticamente una pestaña en tu navegador web con la interfaz gráfica de Dietify, donde podrás:
1. **Generar Recomendación:** Elegir tu dieta, ingresar ingredientes y generar tu menú con las recetas que mejor coincidan con lo que tienes.
2. **Mi Alacena / Inventario:** Gestionar los alimentos guardados en tu cocina virtual.
3. **Catálogo de Recetas:** Ver todas las recetas y registrar opciones nuevas de forma permanente.

