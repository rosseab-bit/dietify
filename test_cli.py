import subprocess
import os
import sys

def test_cli():
    print("=== INICIANDO PRUEBAS DEL SCRIPT DIETIFY CLI ===")
    
    # Define inputs to send to the CLI:
    # 1: Option 1 (Recomendar menú)
    # 1: Sports diet
    # 1: Daily period
    # 2: Manual ingredients
    # huevo, tomate, aceite: Ingredients
    # \n: Press Enter to return to main menu
    # 5: Option 5 (Salir)
    input_data = "1\n1\n1\n2\nhuevo, tomate, aceite\n\n5\n"
    
    # Run the CLI script
    process = subprocess.Popen(
        [sys.executable, "dietify.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    
    stdout, stderr = process.communicate(input=input_data, timeout=10)
    
    print("\n--- SALIDA DEL CLI ---")
    print(stdout)
    
    if stderr:
        print("\n--- ERRORES DEL CLI ---")
        print(stderr)
        
    print("\n--- VERIFICANDO RESULTADOS ---")
    # Verify the exit code is 0
    assert process.returncode == 0, f"El proceso termino con codigo {process.returncode}"
    
    # Verify the recommendation output contains 'Huevos revueltos con tomate'
    assert "Huevos revueltos con tomate" in stdout, "No se recomendo 'Huevos revueltos con tomate'"
    assert "✓ EXACTO" in stdout, "El estado del desayuno no es EXACTO"
    
    print("✓ La recomendación exacta funciona correctamente.")
    print("=== PRUEBAS COMPLETADAS CON ÉXITO ===")

if __name__ == "__main__":
    test_cli()
