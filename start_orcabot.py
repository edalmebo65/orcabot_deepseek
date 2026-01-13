#!/usr/bin/env python3
"""
Punto de entrada principal para OrcaBot - Usa config.py
"""
import sys
import logging
from pathlib import Path

def setup_from_config_py():
    """Configura todo desde config.py"""
    print("🚀 ORCABOT - Iniciando desde config.py")
    print("="*50)
    
    # 1. Verificar que config.py existe
    if not Path("config.py").exists():
        print("❌ ERROR: config.py no encontrado")
        print("\n📝 Crea config.py con:")
        print("   1. Ejecuta: python config_py_validator.py")
        print("   2. Selecciona opción 2 para crear template")
        print("   3. Configura tus datos en config.py")
        return False
    
    # 2. Validar config.py
    try:
        from config_py_validator import validate_config_py_structure
        if not validate_config_py_structure():
            print("\n❌ Corrige config.py antes de continuar")
            return False
    except Exception as e:
        print(f"❌ Error validando config.py: {e}")
        return False
    
    # 3. Configurar logging desde config.py
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", "config.py")
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        
        log_level = getattr(config_module.CONFIG, 'LOG_LEVEL', 'INFO')
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(getattr(config_module.CONFIG, 'LOGS_DIR', Path.cwd() / 'logs') / 'orcboot.log'),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger("OrcaBot")
        logger.info("✅ Logging configurado desde config.py")
        
    except Exception as e:
        print(f"❌ Error configurando logging: {e}")
        return False
    
    # 4. Verificar directorios
    try:
        config_module.CONFIG.setup_directories()
        print("✅ Directorios creados/verificados")
    except Exception as e:
        print(f"⚠️  Error con directorios: {e}")
    
    print("\n" + "="*50)
    print("✅ Configuración desde config.py COMPLETADA")
    print("="*50)
    
    return True

def main():
    """Función principal"""
    # Configurar desde config.py
    if not setup_from_config_py():
        sys.exit(1)
    
    # Mostrar información de configuración
    try:
        from config_manager_integrated import config_integrator
        print("\n📋 RESUMEN DE CONFIGURACIÓN:")
        print(config_integrator.generate_config_report())
    except Exception as e:
        print(f"⚠️  Error mostrando resumen: {e}")
    
    # Opciones
    print("\n🎯 OPCIONES:")
    print("1. Iniciar OrcaBot Optimizado")
    print("2. Verificar saldos")
    print("3. Probar conexión RPC")
    print("4. Salir")
    
    try:
        option = input("\nSelecciona opción (1-4): ").strip()
        
        if option == "1":
            print("\n🚀 Iniciando OrcaBot Optimizado...")
            import asyncio
            from main_integrated import main_optimized
            asyncio.run(main_optimized())
        
        elif option == "2":
            print("\n💰 Verificando saldos...")
            # Aquí iría la lógica para verificar saldos
        
        elif option == "3":
            print("\n🌐 Probando conexión RPC...")
            # Aquí iría la lógica para probar RPC
        
        elif option == "4":
            print("\n👋 ¡Hasta luego!")
        
        else:
            print("\n❌ Opción inválida")
    
    except KeyboardInterrupt:
        print("\n\n👋 Operación cancelada")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()