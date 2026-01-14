# check_balances_simple.py
"""
Verificar balances SIN dependencias de config viejo
"""
import asyncio
import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# Importar NUESTRO config.py (no el viejo)
try:
    import config
    print("✅ config.py cargado")
except ImportError as e:
    print(f"❌ Error cargando config.py: {e}")
    print("💡 Asegúrate de que config.py esté en la carpeta principal")
    sys.exit(1)

async def main():
    """Función principal"""
    print("\n" + "="*60)
    print("💰 VERIFICACIÓN DE BALANCES SIMPLIFICADA")
    print("="*60)
    
    # Verificar configuración básica
    if not config.validate_config():
        print("❌ Configuración incompleta")
        return
    
    print(f"\n👛 Wallet: {config.PHANTOM_WALLET[:8]}...")
    
    # Intentar importar dependencias
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        from solana.rpc.async_api import AsyncClient
        from solana.rpc.commitment import Confirmed
        print("✅ Dependencias cargadas")
    except ImportError as e:
        print(f"❌ Faltan dependencias: {e}")
        print("\n💡 Instala las dependencias:")
        print("   pip install solders solana")
        return
    
    # Configurar RPC
    rpc_url = config.HELIUS_BASE_URL
    if config.HELIUS_VOICEINDIGO_API_KEY and "helius" in rpc_url.lower():
        rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
    
    print(f"\n🌐 Conectando a: {rpc_url[:50]}...")
    
    client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
    
    try:
        # Cargar wallet
        private_key_bytes = config.get_private_key()
        if not private_key_bytes:
            print("❌ No se pudo decodificar la clave privada")
            return
        
        keypair = Keypair.from_bytes(private_key_bytes)
        wallet_address = str(keypair.pubkey())
        
        print(f"✅ Wallet cargada: {wallet_address[:8]}...")
        
        # Probar conexión
        print("\n🔍 Probando conexión RPC...")
        try:
            health = await client.get_health()
            if health.value == "ok":
                print("✅ RPC conectado y saludable")
            else:
                print(f"⚠️ RPC: {health.value}")
        except Exception as e:
            print(f"❌ Error conectando a RPC: {e}")
            return
        
        # 1. BALANCE DE SOL
        print("\n1️⃣ BALANCE DE SOL:")
        try:
            sol_balance = await client.get_balance(keypair.pubkey())
            if sol_balance.value:
                sol_amount = sol_balance.value / 1_000_000_000
                print(f"   💰 Balance: {sol_amount:.6f} SOL")
                
                # Verificar mínimo
                if sol_amount >= config.MIN_SOL_FEES:
                    print(f"   ✅ Suficiente para fees (necesitas {config.MIN_SOL_FEES} SOL)")
                else:
                    print(f"   ❌ Insuficiente para fees")
                    print(f"   💡 Necesitas {config.MIN_SOL_FEES - sol_amount:.6f} SOL más")
            else:
                print("   ❌ No se pudo obtener balance de SOL")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. BALANCE DE USDC
        print("\n2️⃣ BALANCE DE USDC:")
        try:
            from spl.token.associated import get_associated_token_address
            
            usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            ata = get_associated_token_address(keypair.pubkey(), usdc_mint)
            
            balance_info = await client.get_token_account_balance(ata)
            
            if balance_info.value:
                usdc_amount = float(balance_info.value.ui_amount_string)
                print(f"   💰 Balance: {usdc_amount:.2f} USDC")
                
                # Verificar para swap de prueba
                if usdc_amount >= 5.0:
                    print(f"   ✅ Suficiente para swap de prueba (5 USDC)")
                else:
                    print(f"   ❌ Insuficiente para swap de prueba")
                    print(f"   💡 Necesitas {5.0 - usdc_amount:.2f} USDC más")
                
                # Verificar para trading
                if usdc_amount >= config.MIN_USDC_BALANCE:
                    print(f"   ✅ Suficiente para trading ({config.MIN_USDC_BALANCE} USDC)")
                else:
                    print(f"   ⚠️ Insuficiente para trading mínimo")
                    print(f"   💡 Para trading necesitas {config.MIN_USDC_BALANCE} USDC")
            else:
                print("   ❌ No se encontró cuenta de USDC")
                print("   💡 Necesitas tener USDC en tu wallet")
                
        except Exception as e:
            print(f"   ❌ Error obteniendo USDC: {e}")
            print("   💡 Es posible que no tengas USDC aún")
        
        # 3. RESUMEN
        print("\n" + "="*60)
        print("📊 RESUMEN FINAL")
        print("="*60)
        
        print(f"\n👛 Wallet: {wallet_address[:8]}...")
        print(f"💰 SOL: {sol_amount if 'sol_amount' in locals() else 0:.6f}")
        print(f"💵 USDC: {usdc_amount if 'usdc_amount' in locals() else 0:.2f}")
        
        # Verificar si está listo para swap
        sol_ok = 'sol_amount' in locals() and sol_amount >= config.MIN_SOL_FEES
        usdc_ok = 'usdc_amount' in locals() and usdc_amount >= 5.0
        
        if sol_ok and usdc_ok:
            print("\n🎉 ¡LISTO PARA SWAP DE PRUEBA!")
            print("💡 Ejecuta: python swap_test_simple.py")
        else:
            print("\n⚠️  FALTAN FONDOS:")
            if not sol_ok:
                print(f"   - Necesitas al menos {config.MIN_SOL_FEES} SOL para fees")
            if not usdc_ok:
                print(f"   - Necesitas al menos 5 USDC para el swap de prueba")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()
        print("\n✅ Conexión cerrada")

if __name__ == "__main__":
    # Configurar para Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    asyncio.run(main())
    input("\nPresiona Enter para salir...")