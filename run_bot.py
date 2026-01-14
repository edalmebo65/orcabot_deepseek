# run_bot.py
"""
SCRIPT PRINCIPAL SIMPLIFICADO - SIN DEPENDENCIAS DE ARCHIVOS .env
"""
import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# Verificar que config.py esté presente
try:
    import config
    print("✅ config.py cargado correctamente")
except ImportError as e:
    print(f"❌ Error importando config.py: {e}")
    print("💡 Asegúrate de que config.py esté en el mismo directorio")
    sys.exit(1)

# Importar módulos principales
try:
    print("🔧 Cargando módulos...")
    
    # Solo importar lo esencial por ahora
    from ml_trainer import MLEnsemble, initialize_ml_system
    from token_selector_enhanced import VolatileTokenSelector
    from security_enhancer import SecurityManager
    
    print("✅ Módulos cargados")
    
except ImportError as e:
    print(f"⚠️ Algunos módulos no disponibles: {e}")
    print("💡 Instala las dependencias: pip install -r requirements_fixed_v2.txt")

def main():
    """Función principal simplificada"""
    print("\n" + "="*60)
    print("🚀 ORCABOT DEEPSEEK - MODO SIMPLIFICADO")
    print("="*60)
    
    # Mostrar configuración actual
    print(f"\n📋 CONFIGURACIÓN ACTUAL:")
    print(f"   👛 Wallet: {config.PHANTOM_WALLET[:8]}...")
    print(f"   🌐 RPC: {'Helius' if config.HELIUS_VOICEINDIGO_API_KEY else 'Público'}")
    print(f"   🤖 Telegram: {'Sí' if config.TELEGRAM_ENABLED else 'No'}")
    print(f"   💰 Capital: ${config.INITIAL_CAPITAL_USD}")
    
    # Opciones del menú
    print(f"\n🎯 OPCIONES:")
    print("   1. Probar selector de tokens")
    print("   2. Probar sistema ML")
    print("   3. Probar seguridad")
    print("   4. Verificar conexión RPC")
    print("   5. Salir")
    
    try:
        opcion = input("\nSelecciona una opción (1-5): ")
        
        if opcion == '1':
            test_token_selector()
        elif opcion == '2':
            test_ml_system()
        elif opcion == '3':
            test_security()
        elif opcion == '4':
            test_rpc_connection()
        elif opcion == '5':
            print("👋 Saliendo...")
            return
        else:
            print("❌ Opción no válida")
            
    except KeyboardInterrupt:
        print("\n\n👋 Interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")

async def test_token_selector():
    """Probar selector de tokens"""
    print("\n🎯 PROBANDO SELECTOR DE TOKENS...")
    
    try:
        selector = VolatileTokenSelector()
        await selector.initialize()
        
        tokens = await selector.select_top_tokens(5)  # Solo 5 para prueba
        print(f"✅ Encontrados {len(tokens)} tokens")
        
        for token in tokens[:3]:  # Mostrar primeros 3
            print(f"   📊 {token.symbol}: ${token.price:.4f} (Vol: ${token.volume_24h:,.0f})")
            
        await selector.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_ml_system():
    """Probar sistema ML"""
    print("\n🧠 PROBANDO SISTEMA ML...")
    
    try:
        # Inicializar sistema ML
        ml_manager = await initialize_ml_system()
        print("✅ Sistema ML inicializado")
        
        # Aquí iría la prueba de predicción
        print("💡 Sistema ML listo para entrenamiento")
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_security():
    """Probar sistema de seguridad"""
    print("\n🛡️ PROBANDO SISTEMA DE SEGURIDAD...")
    
    try:
        security = SecurityManager()
        await security.initialize()
        print("✅ Sistema de seguridad inicializado")
        
        # Probar encriptación
        test_data = "datos_de_prueba"
        encrypted = security.encrypt_data(test_data)
        decrypted = security.decrypt_data(encrypted)
        
        if test_data == decrypted:
            print("✅ Encriptación/desencriptación funcionando")
        else:
            print("❌ Error en encriptación")
            
        await security.shutdown()
        
    except Exception as e:
        print(f"❌ Error: {e}")

async def test_rpc_connection():
    """Probar conexión RPC"""
    print("\n🌐 PROBANDO CONEXIÓN RPC...")
    
    try:
        import aiohttp
        
        if config.HELIUS_VOICEINDIGO_API_KEY:
            url = f"{config.HELIUS_BASE_URL}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
        else:
            url = config.HELIUS_BASE_URL
            
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getHealth"
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'result' in data:
                        print("✅ Conexión RPC exitosa")
                    else:
                        print("⚠️ RPC respondió pero con error")
                else:
                    print(f"❌ Error HTTP: {response.status}")
                    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")

if __name__ == "__main__":
    # Para Windows, necesitamos configurar el event loop
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar función principal
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"\n❌ Error no manejado: {e}")