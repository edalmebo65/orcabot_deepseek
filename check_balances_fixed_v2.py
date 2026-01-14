# check_balances_fixed_v2.py
"""
Check balances con métodos actualizados para solana-py
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

def decode_private_key(key_str: str) -> bytes:
    """Decodificar clave privada"""
    if not key_str:
        return None
    
    clean_key = key_str.strip()
    
    try:
        decoded = base64.b64decode(clean_key, validate=True)
        print(f"🔑 Clave decodificada: {len(decoded)} bytes")
        return decoded
    except:
        print("❌ No se pudo decodificar Base64")
        return None

async def check_rpc_health(client) -> bool:
    """Verificar salud del RPC (método actualizado)"""
    try:
        # Método 1: get_version (siempre funciona)
        version = await client.get_version()
        if version:
            print(f"✅ RPC conectado - Solana {version.value.get('solana-core', '?')}")
            return True
        
    except Exception as e:
        print(f"⚠️ Error get_version: {e}")
    
    try:
        # Método 2: get_block_height
        height = await client.get_block_height()
        if height:
            print(f"✅ RPC conectado - Block height: {height}")
            return True
            
    except Exception as e:
        print(f"⚠️ Error get_block_height: {e}")
    
    try:
        # Método 3: is_connected (más simple)
        connected = await client.is_connected()
        if connected:
            print(f"✅ RPC conectado")
            return True
            
    except Exception as e:
        print(f"⚠️ Error is_connected: {e}")
    
    return False

async def main():
    """Función principal"""
    print("\n" + "="*60)
    print("💰 VERIFICACIÓN DE BALANCES - VERSIÓN 2.0")
    print("="*60)
    
    # Verificar configuración
    if not hasattr(config, 'PHANTOM_PRIVATE_KEY_BYTES') or not config.PHANTOM_PRIVATE_KEY_BYTES:
        print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
        return
    
    wallet_preview = getattr(config, 'PHANTOM_WALLET', 'No configurada')[:8] + "..."
    print(f"\n👛 Wallet: {wallet_preview}")
    
    # Decodificar clave
    private_key_bytes = decode_private_key(config.PHANTOM_PRIVATE_KEY_BYTES)
    
    if not private_key_bytes:
        print("❌ Error con clave privada")
        return
    
    # Importar dependencias
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        from solana.rpc.async_api import AsyncClient
        from solana.rpc.commitment import Confirmed
        print("✅ Dependencias cargadas")
    except ImportError as e:
        print(f"❌ Faltan dependencias: {e}")
        print("\n💡 Instala: pip install solders solana")
        return
    
    # Configurar RPC
    rpc_url = getattr(config, 'HELIUS_BASE_URL', 'https://api.mainnet-beta.solana.com')
    if hasattr(config, 'HELIUS_VOICEINDIGO_API_KEY') and config.HELIUS_VOICEINDIGO_API_KEY:
        if "helius" in rpc_url.lower():
            rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
    
    print(f"\n🌐 Conectando a: {rpc_url[:50]}...")
    
    # Configurar timeout más largo
    client = AsyncClient(
        rpc_url, 
        commitment=Confirmed, 
        timeout=30
    )
    
    try:
        # Crear keypair
        print("🔐 Creando keypair...")
        keypair = Keypair.from_bytes(private_key_bytes)
        wallet_address = str(keypair.pubkey())
        print(f"✅ Keypair creado: {wallet_address[:8]}...")
        
        # Verificar conexión
        print("\n🔍 Probando conexión RPC...")
        if not await check_rpc_health(client):
            print("❌ No se pudo conectar al RPC")
            return
        
        # 1. BALANCE DE SOL
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
            else:
                print("   ❌ No se pudo obtener balance")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 2. BALANCE DE USDC
        print("\n2️⃣ BALANCE DE USDC:")
        try:
            from spl.token.associated import get_associated_token_address
            
            usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            ata = get_associated_token_address(keypair.pubkey(), usdc_mint)
            
            start_time = time.time()
            balance_info = await client.get_token_account_balance(ata)
            elapsed = time.time() - start_time
            
            if balance_info.value:
                usdc_amount = float(balance_info.value.ui_amount_string)
                print(f"   💰 Balance: {usdc_amount:.2f} USDC")
                print(f"   ⏱️  Tiempo: {elapsed:.2f}s")
                
                # Para swap de prueba
                if usdc_amount >= 5.0:
                    print(f"   ✅ Suficiente para swap de prueba (5 USDC)")
                else:
                    print(f"   ❌ Insuficiente para swap de prueba")
                    print(f"   💡 Necesitas {5.0 - usdc_amount:.2f} USDC más")
                
                # Para trading
                min_usdc = getattr(config, 'MIN_USDC_BALANCE', 10.0)
                if usdc_amount >= min_usdc:
                    print(f"   ✅ Suficiente para trading ({min_usdc} USDC)")
                else:
                    print(f"   ⚠️  Insuficiente para trading mínimo")
                    
            else:
                print("   ❌ No se encontró cuenta de USDC")
                print("   💡 Necesitas tener USDC en tu wallet")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print("   💡 Es posible que no tengas cuenta de USDC aún")
        
        # 3. VERIFICAR WALLET ACTIVA
        print("\n3️⃣ INFORMACIÓN DE WALLET:")
        try:
            # Obtener información de la cuenta
            account_info = await client.get_account_info(keypair.pubkey())
            
            if account_info.value:
                print(f"   ✅ Wallet activa en Solana")
                print(f"   💾 Espacio usado: {account_info.value.data_len} bytes")
                
                # Verificar si es una cuenta ejecutable
                if account_info.value.executable:
                    print(f"   ⚡ Es una cuenta ejecutable (program)")
                else:
                    print(f"   👛 Es una wallet normal")
            else:
                print(f"   ⚠️  Wallet no encontrada en blockchain")
                print(f"   💡 Puede ser una wallet nueva sin transacciones")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. RESUMEN
        print("\n" + "="*60)
        print("📊 RESUMEN FINAL")
        print("="*60)
        
        sol_ok = 'sol_amount' in locals() and sol_amount >= getattr(config, 'MIN_SOL_FEES', 0.05)
        usdc_ok = 'usdc_amount' in locals() and usdc_amount >= 5.0
        
        if sol_ok and usdc_ok:
            print("\n🎉 ¡LISTO PARA SWAP DE PRUEBA!")
            print("💡 Ejecuta: python swap_test_updated.py")
        elif sol_ok and not usdc_ok:
            print("\n⚠️  FALTA USDC:")
            print(f"   - Tienes {sol_amount:.6f} SOL (suficiente)")
            print(f"   - Necesitas al menos 5 USDC para el swap")
        elif not sol_ok and usdc_ok:
            print("\n⚠️  FALTA SOL:")
            min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
            print(f"   - Tienes {usdc_amount:.2f} USDC (suficiente)")
            print(f"   - Necesitas al menos {min_sol} SOL para fees")
        else:
            print("\n⚠️  FALTAN AMBOS:")
            min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
            print(f"   - Necesitas {min_sol} SOL para fees")
            print(f"   - Necesitas 5 USDC para el swap")
        
        # Mostrar balances si existen
        if 'sol_amount' in locals() and 'usdc_amount' in locals():
            print(f"\n💰 Balances actuales:")
            print(f"   SOL: {sol_amount:.6f}")
            print(f"   USDC: {usdc_amount:.2f}")
        
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