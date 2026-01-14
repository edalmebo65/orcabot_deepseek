# check_balances_simple_final.py
"""
Check balances SIN necesidad de spl-token
Usando métodos nativos de Solana
"""
import asyncio
import sys
import os
import base64
import time

sys.path.insert(0, os.path.dirname(__file__))

# Importar configuración
try:
    import config
    print("✅ config.py cargado")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

async def main():
    """Función principal simplificada"""
    print("\n" + "="*60)
    print("💰 VERIFICACIÓN DE BALANCES - SIN DEPENDENCIAS EXTRA")
    print("="*60)
    
    # Verificar configuración
    if not hasattr(config, 'PHANTOM_PRIVATE_KEY_BYTES') or not config.PHANTOM_PRIVATE_KEY_BYTES:
        print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
        return
    
    # Decodificar clave
    try:
        private_key_bytes = base64.b64decode(config.PHANTOM_PRIVATE_KEY_BYTES.strip())
        print(f"🔑 Clave decodificada: {len(private_key_bytes)} bytes")
    except:
        print("❌ Error decodificando clave")
        return
    
    # Importar solo lo esencial
    try:
        from solders.keypair import Keypair
        from solana.rpc.async_api import AsyncClient
        from solana.rpc.commitment import Confirmed
        print("✅ Dependencias básicas cargadas")
    except ImportError as e:
        print(f"❌ Faltan dependencias básicas: {e}")
        print("\n💡 Instala mínimo: pip install solders solana")
        return
    
    # Configurar RPC
    rpc_url = getattr(config, 'HELIUS_BASE_URL', 'https://api.mainnet-beta.solana.com')
    if hasattr(config, 'HELIUS_VOICEINDIGO_API_KEY') and config.HELIUS_VOICEINDIGO_API_KEY:
        if "helius" in rpc_url.lower():
            rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
    
    print(f"\n🌐 Conectando a: {rpc_url[:50]}...")
    
    client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
    
    try:
        # Crear keypair
        keypair = Keypair.from_bytes(private_key_bytes)
        wallet_address = str(keypair.pubkey())
        print(f"✅ Wallet: {wallet_address}")
        
        # 1. VERIFICAR CONEXIÓN
        print("\n🔍 Verificando conexión...")
        try:
            block_height = await client.get_block_height()
            print(f"   ✅ Conectado - Block height: {block_height}")
        except Exception as e:
            print(f"   ❌ Error de conexión: {e}")
            return
        
        # 2. BALANCE DE SOL
        print("\n1️⃣ BALANCE DE SOL:")
        try:
            start_time = time.time()
            sol_balance = await client.get_balance(keypair.pubkey())
            elapsed = time.time() - start_time
            
            if sol_balance.value:
                sol_amount = sol_balance.value / 1_000_000_000
                print(f"   💰 Balance: {sol_amount:.6f} SOL")
                print(f"   ⏱️  Tiempo: {elapsed:.2f}s")
                
                min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
                if sol_amount >= min_sol:
                    print(f"   ✅ Suficiente para fees (mínimo: {min_sol} SOL)")
                else:
                    print(f"   ❌ Insuficiente para fees")
                    print(f"   💡 Necesitas {min_sol - sol_amount:.6f} SOL más")
                    print(f"   📋 Envía SOL a: {wallet_address}")
            else:
                print("   ❌ Sin balance de SOL")
                print(f"   💡 Envía SOL a: {wallet_address}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 3. VERIFICAR CUENTA (sin USDC por ahora)
        print("\n2️⃣ INFORMACIÓN DE CUENTA:")
        try:
            account_info = await client.get_account_info(keypair.pubkey())
            
            if account_info.value:
                print(f"   ✅ Cuenta activa en blockchain")
                print(f"   💾 Espacio usado: {account_info.value.data_len} bytes")
                print(f"   💰 Lamports: {account_info.value.lamports}")
                print(f"   🏦 Balance: {account_info.value.lamports / 1_000_000_000:.6f} SOL")
            else:
                print(f"   ⚠️  Cuenta no encontrada en blockchain")
                print(f"   💡 Es una wallet nueva sin transacciones")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. VERIFICAR RECIENTES (opcional)
        print("\n3️⃣ ACTIVIDAD RECIENTE:")
        try:
            # Obtener transacciones recientes
            signatures = await client.get_signatures_for_address(keypair.pubkey(), limit=3)
            
            if signatures.value:
                print(f"   ✅ {len(signatures.value)} transacciones encontradas")
                for i, sig in enumerate(signatures.value[:2], 1):
                    print(f"   {i}. {sig.signature[:16]}... ({sig.slot})")
            else:
                print(f"   📭 Sin transacciones recientes")
                
        except Exception as e:
            print(f"   ℹ️  Sin actividad reciente")
        
        # 5. RESUMEN
        print("\n" + "="*60)
        print("📊 RESUMEN PARA DEPÓSITO")
        print("="*60)
        
        print(f"\n👛 TU DIRECCIÓN PARA DEPOSITAR:")
        print(f"   {wallet_address}")
        
        print(f"\n💰 FONDOS NECESARIOS:")
        print(f"   1. SOL: mínimo 0.05 SOL (recomendado 0.1 SOL)")
        print(f"   2. USDC: mínimo 5 USDC (recomendado 10 USDC)")
        
        if 'sol_amount' in locals():
            print(f"\n📈 BALANCE ACTUAL:")
            print(f"   SOL: {sol_amount:.6f}")
            
            if sol_amount < 0.05:
                needed = 0.05 - sol_amount
                print(f"\n⚠️  DEPÓSITO REQUERIDO:")
                print(f"   Envía al menos {needed:.6f} SOL a tu dirección")
        
        print(f"\n🔧 PARA DEPOSITAR USDC:")
        print(f"   1. En exchange: selecciona red Solana (SPL)")
        print(f"   2. En wallet: envía USDC (SPL token)")
        print(f"   3. Dirección: la misma {wallet_address}")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()
        print("\n✅ Conexión cerrada")

if __name__ == "__main__":
    # Configurar Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    asyncio.run(main())
    input("\nPresiona Enter para salir...")