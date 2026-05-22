@echo off
echo =======================================
echo Iniciando Dietify (Sistema Experto)
echo =======================================

:: Comprobar si existe el entorno virtual, si no, lo crea
if not exist venv\ (
    echo [1/3] Creando entorno virtual, esto puede tardar unos segundos...
    python -m venv venv
)

:: Activar el entorno virtual e instalar dependencias
echo [2/3] Activando entorno e instalando dependencias...
call venv\Scripts\activate
pip install -r requirements.txt -q

:: Lanzar la aplicacion
echo [3/3] Abriendo la aplicacion en tu navegador...
streamlit run app.py

pause
