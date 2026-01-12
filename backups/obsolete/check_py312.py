#!/usr/bin/env python3
"""
Verificador de compatibilidad Python 3.12
"""
import sys
import platform
import importlib.metadata as metadata

def check_python_version():
    """Verifica versión de Python"""
    version = sys.version_info
    print(f"🐍 Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major == 3 and version.minor == 12:
        return True
    else:
        print(f"⚠️  Se recomienda Python 3.12, tienes {version.major}.{version.minor}")
        return False

def check_dependencies():
    """Verifica dependencias críticas"""
    critical_deps = {
        'solana': '>=0.32.0',
        'solders': '>=0.20.0',
        'anchorpy': '>=0.19.0',
        'web3': '>=6.15.0',
        'aiogram': '>=3.0.0',
        'cryptography': '>=42.0.0',
        'aiohttp': '>=3.9.0',
        'pydantic': '>=2.5.0',
    }
    
    print("\n🔍 Verificando dependencias críticas:")
    all_ok = True
    
    for dep, required_version in critical_deps.items():
        try:
            # Intenta importar primero
            __import__(dep)
            
            # Obtiene versión instalada
            try:
                installed = metadata.version(dep)
                print(f"  ✅ {dep:20} v{installed}")
            except:
                print(f"  ⚠️  {dep:20} Instalado (versión no detectable)")
                
        except ImportError as e:
            print(f"  ❌ {dep:20} NO INSTALADO")
            print(f"     → pip install {dep}{required_version}")
            all_ok = False
    
    return all_ok

def check_orca():
    """Verifica orca-py específicamente"""
    print("\n🐋 Verificando orca-py:")
    try:
        # Intenta importar componentes clave de orca
        from orca.whirlpool.accounts import Whirlpool
        from orca.whirlpool.constants import ORCA_WHIRLPOOL_PROGRAM_ID
        
        print("  ✅ orca-py importado correctamente")
        print(f"  → Whirlpool program: {ORCA_WHIRLPOOL_PROGRAM_ID}")
        
        # Verifica versión si es posible
        try:
            import orca
            if hasattr(orca, '__version__'):
                print(f"  → Versión: {orca.__version__}")
        except:
            pass
            
        return True
    except ImportError as e:
        print(f"  ❌ Error importando orca-py: {e}")
        print("  → pip install git+https://github.com/orca-so/orca-py.git")
        return False
    except Exception as e:
        print(f"  ⚠️  Error en orca: {e}")
        return False

def check_async():
    """Verifica funcionalidades async"""
    print("\n⚡ Verificando async/await:")
    try:
        import asyncio
        import inspect
        
        # Verifica que podemos usar asyncio.run()
        async def test_coro():
            return "OK"
        
        result = asyncio.run(test_coro())
        print(f"  ✅ asyncio funcionando: {result}")
        
        # Verifica que aiogram sea async
        try:
            import aiogram
            if aiogram.__version__.startswith('3'):
                print(f"  ✅ aiogram v3+ (async nativo)")
            else:
                print(f"  ⚠️  aiogram {aiogram.__version__} (actualizar a v3+)")
        except:
            pass
            
        return True
    except Exception as e:
        print(f"  ❌ Error async: {e}")
        return False

def main():
    print("=" * 60)
    print("VERIFICADOR ORCA BOT - PYTHON 3.12")
    print("=" * 60)
    
    # Verificaciones
    py_ok = check_python_version()
    deps_ok = check_dependencies()
    orca_ok = check_orca()
    async_ok = check_async()
    
    print("\n" + "=" * 60)
    print("RESUMEN:")
    print(f"  Python 3.12: {'✅' if py_ok else '❌'}")
    print(f"  Dependencias: {'✅' if deps_ok else '❌'}")
    print(f"  Orca-py: {'✅' if orca_ok else '❌'}")
    print(f"  Async: {'✅' if async_ok else '❌'}")
    
    all_ok = py_ok and deps_ok and orca_ok and async_ok
    
    if all_ok:
        print("\n🎉 ¡Todo listo para desarrollar con Python 3.12!")
        print("   Ejecuta: python main.py")
    else:
        print("\n⚠️  Hay problemas que resolver:")
        if not py_ok:
            print("   - Actualiza a Python 3.12")
        if not deps_ok:
            print("   - Instala dependencias faltantes")
        if not orca_ok:
            print("   - Reinstala orca-py desde GitHub")
    
    print("=" * 60)

if __name__ == "__main__":
    main()