# Dietify - Sistema Experto por Consola (CLI)

Este es el sistema experto **Dietify**, diseñado para recomendar menús (diarios o semanales) basados en el inventario actual de tu cocina (alacenas, heladera) y tu tipo de dieta (deportes, peso, médica, propia/custom).

El sistema se ejecuta completamente por consola (interfaz CLI) y utiliza la biblioteca **experta** de Python, un motor de reglas basado en CLIPS adaptado para Python, y una base de datos local **SQLite3**.

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
├── dietify.py        # Script unificado (motor experta + SQLite3 + interfaz CLI)
├── test_cli.py       # Script de pruebas automatizadas del CLI
├── requirements.txt  # Dependencias del proyecto (solo experta)
└── README.md         # Documentación de uso
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

Para iniciar la interfaz interactiva por consola:
```bash
python dietify.py
```

### Opciones del Menú Principal:
1. **Recomendar menú para el día o la semana:** Permite elegir tu dieta, ingresar ingredientes manualmente o cargarlos de la base de datos, y generar tu menú con las recetas que mejor coincidan con lo que tienes.
2. **Gestionar alimentos en la alacena / heladera:** Permite ver, agregar, actualizar o eliminar ingredientes guardados en tu cocina virtual.
3. **Ver catálogo de recetas en el sistema:** Muestra todas las recetas configuradas con sus instrucciones e ingredientes.
4. **Registrar una nueva receta en el catálogo:** Registra recetas nuevas y las guarda de forma permanente en el sistema SQLite.

---

## Ejecutar Pruebas Automatizadas

Hemos provisto un script de pruebas integrado para validar el correcto funcionamiento del motor de reglas del CLI y la lógica de recomendación:
```bash
python test_cli.py
```
