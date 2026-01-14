# check_balances_fixed.py
"""
Check balances CON LA DECODIFICACIÓN CORREGIDA
"""
import asyncio
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(__file__))

# Importar configuración
try:
    import config
    print("✅ config.py cargado")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

def decode_private_key(key_str: str) -> bytes:
    """Decodificar clave privada de cualquier formato - ROBUSTO"""
    if not key_str:
        return None
    
    print(f"🔍 Decodificando clave ({len(key_str)} chars)...")
    
    # Limpiar
    clean_key = key_str.strip()
    
    # INTENTAR DIFERENTES FORMATOS
    
    # 1. Base64
    try:
        # Base64 standard
        decoded = base64.b64decode(clean_key, validate=True)
        print(f"   ✅ Base64 -> {len(decoded)} bytes")
        return decoded
    except:
        pass
    
    # 2. Base64 URL safe
    try:
        decoded = base64.urlsafe_b64decode(clean_key + '=' * (4 - len(clean_key) % 4))
        print(f"   ✅ Base64 URL Safe -> {len(decoded)} bytes")
        return decoded
    except:
        pass
    
    # 3. Hexadecimal
    try:
        # Limpiar hex
        hex_clean = clean_key.replace('0x', '').replace(' ', '').replace('\n', '')
        if all(c in '0123456789abcdefABCDEF' for c in hex_clean):
            decoded = bytes.fromhex(hex_clean)
            print(f"   ✅ Hex -> {len(decoded)} bytes")
            return decoded
    except:
        pass
    
    # 4. Array de bytes
    if clean_key.startswith('[') and clean_key.endswith(']'):
        try:
            import ast
            byte_list = ast.literal_eval(clean_key)
            decoded = bytes(byte_list)
            print(f"   ✅ Array -> {len(decoded)} bytes")
            return decoded
        except:
            pass
    
    # 5. Como último recurso, tratar como string
    try:
        decoded = clean_key.encode('utf-8')
        print(f"   ⚠️  String -> {len(decoded)} bytes")
        return decoded
    except:
        pass
    
    print(f"   ❌ No se pudo decodificar")
    return None

async def main():
    """Función principal"""
    print("\n" + "="*60)
    print("💰 VERIFICACIÓN DE BALANCES - VERSIÓN CORREGIDA")
    print("="*60)
    
    # Verificar configuración
    if not hasattr(config, 'PHANTOM_PRIVATE_KEY_BYTES') or not config.PHANTOM_PRIVATE_KEY_BYTES:
        print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
        print("💡 Ejecuta: update_key.bat o start_orcabat.bat")
        return
    
    print(f"\n👛 Wallet: {config.PHANTOM_WALLET[:8]}...")
    
    # Decodificar clave
    private_key_bytes = decode_private_key(config.PHANTOM_PRIVATE_KEY_BYTES)
    
    if not private_key_bytes:
        print("❌ No se pudo decodificar la clave privada")
        print("💡 Usa convert_to_base64.py para convertir tu clave")
        return
    
    print(f"🔑 Clave decodificada: {len(private_key_bytes)} bytes")
    
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
    rpc_url = config.HELIUS_BASE_URL
    if hasattr(config, 'HELIUS_VOICEINDIGO_API_KEY') and config.HELIUS_VOICEINDIGO_API_KEY:
        if "helius" in rpc_url.lower():
            rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
    
    print(f"\n🌐 Conectando a: {rpc_url[:50]}...")
    
    client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
    
    try:
        # Crear keypair
        print("🔐 Creando keypair...")
        try:
            keypair = Keypair.from_bytes(private_key_bytes)
            wallet_address = str(keypair.pubkey())
            print(f"✅ Keypair creado: {wallet_address[:8]}...")
        except Exception as e:
            print(f"❌ Error creando keypair: {e}")
            print(f"   📏 Bytes de clave: {len(private_key_bytes)}")
            print(f"   💡 Deberían ser 64 bytes para Solana")
            return
        
        # Verificar conexión
        print("\n🔍 Probando conexión RPC...")
        try:
            health = await client.get_health()
            if health.value == "ok":
                print("✅ RPC conectado")
            else:
                print(f"⚠️ RPC: {health.value}")
        except Exception as e:
            print(f"❌ Error RPC: {e}")
            return
        
        # 1. BALANCE DE SOL
        print("\n1️⃣ BALANCE DE SOL:")
        try:
            sol_balance = await client.get_balance(keypair.pubkey())
            if sol_balance.value:
                sol_amount = sol_balance.value / 1_000_000_000
                print(f"   💰 Balance: {sol_amount:.6f} SOL")
                
                min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
                if sol_amount >= min_sol:
                    print(f"   ✅ Suficiente para fees (necesitas {min_sol} SOL)")
                else:
                    print(f"   ❌ Insuficiente para fees")
                    print(f"   💡 Necesitas {min_sol - sol_amount:.6f} SOL más")
            else:
                print("   ❌ No se pudo obtener balance")
        except Exception as e:
            print(f"   ❌ Error SOL: {e}")
        
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
                    print(f"   ⚠️ Insuficiente para trading mínimo")
                    print(f"   💡 Para trading necesitas {min_usdc} USDC")
            else:
                print("   ❌ No se encontró cuenta de USDC")
                print("   💡 Necesitas tener USDC en tu wallet")
                
        except Exception as e:
            print(f"   ❌ Error USDC: {e}")
            print("   💡 Es posible que no tengas USDC aún")
        
        # 3. RESUMEN
        print("\n" + "="*60)
        print("📊 RESUMEN FINAL")
        print("="*60)
        
        sol_ok = 'sol_amount' in locals() and sol_amount >= getattr(config, 'MIN_SOL_FEES', 0.05)
        usdc_ok = 'usdc_amount' in locals() and usdc_amount >= 5.0
        
        if sol_ok and usdc_ok:
            print("\n🎉 ¡LISTO PARA SWAP DE PRUEBA!")
            print("💡 Ejecuta: python swap_test_simple.py")
        else:
            print("\n⚠️  FALTAN FONDOS:")
            if not sol_ok:
                min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
                print(f"   - Necesitas al menos {min_sol} SOL para fees")
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
    # Configurar Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    asyncio.run(main())
    input("\nPresiona Enter para salir...")