# check_balances.py
"""
Verificar balances antes del swap
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    import config
    from solders.keypair import Keypair
    from solders.pubkey import Pubkey
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Confirmed
    from spl.token.associated import get_associated_token_address
    print("✅ Dependencias cargadas")
except ImportError as e:
    print(f"❌ Faltan dependencias: {e}")
    print("💡 Ejecuta: pip install solders solana")
    sys.exit(1)

async def check_all_balances():
    """Verificar todos los balances"""
    print("\n" + "="*60)
    print("💰 VERIFICACIÓN DE BALANCES")
    print("="*60)
    
    # Configurar cliente
    if config.HELIUS_VOICEINDIGO_API_KEY:
        rpc_url = f"{config.HELIUS_BASE_URL}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
    else:
        rpc_url = config.HELIUS_BASE_URL
    
    client = AsyncClient(rpc_url, commitment=Confirmed)
    
    try:
        # Cargar wallet
        private_key_bytes = config.get_private_key()
        if not private_key_bytes:
            print("❌ No se pudo cargar la clave privada")
            return
        
        keypair = Keypair.from_bytes(private_key_bytes)
        wallet_address = str(keypair.pubkey())
        
        print(f"\n👛 Wallet: {wallet_address}")
        
        # 1. Balance de SOL
        print("\n1️⃣ BALANCE DE SOL (para fees):")
        sol_balance = await client.get_balance(keypair.pubkey())
        if sol_balance.value:
            sol_amount = sol_balance.value / 1_000_000_000
            print(f"   💰 Balance: {sol_amount:.6f} SOL")
            
            # Verificar mínimo
            min_sol = config.MIN_SOL_FEES
            if sol_amount >= min_sol:
                print(f"   ✅ Suficiente para fees (mínimo: {min_sol} SOL)")
            else:
                print(f"   ❌ Insuficiente (mínimo: {min_sol} SOL)")
                print(f"   💡 Necesitas depositar {min_sol - sol_amount:.6f} SOL más")
        else:
            print("   ❌ No se pudo obtener balance")
        
        # 2. Balance de USDC
        print("\n2️⃣ BALANCE DE USDC (para trading):")
        usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        ata = get_associated_token_address(keypair.pubkey(), usdc_mint)
        
        try:
            balance_info = await client.get_token_account_balance(ata)
            
            if balance_info.value:
                usdc_amount = float(balance_info.value.ui_amount_string)
                print(f"   💰 Balance: {usdc_amount:.2f} USDC")
                
                # Verificar mínimo para swap de prueba
                min_usdc_test = 5.0
                if usdc_amount >= min_usdc_test:
                    print(f"   ✅ Suficiente para swap de prueba ({min_usdc_test} USDC)")
                else:
                    print(f"   ❌ Insuficiente para swap de prueba")
                    print(f"   💡 Necesitas depositar {min_usdc_test - usdc_amount:.2f} USDC más")
                
                # Verificar mínimo para trading real
                min_usdc_trading = config.MIN_USDC_BALANCE
                if usdc_amount >= min_usdc_trading:
                    print(f"   ✅ Suficiente para trading ({min_usdc_trading} USDC)")
                else:
                    print(f"   ⚠️ Insuficiente para trading mínimo")
                    print(f"   💡 Para trading real necesitas {min_usdc_trading} USDC mínimo")
            else:
                print("   ❌ No se encontró cuenta de USDC")
                print("   💡 Necesitas tener al menos 5 USDC para la prueba")
                
        except Exception as e:
            print(f"   ❌ Error obteniendo USDC: {e}")
            print("   💡 Es posible que no tengas cuenta de USDC aún")
        
        # 3. Resumen
        print("\n" + "="*60)
        print("📊 RESUMEN PARA SWAP DE PRUEBA:")
        print("="*60)
        
        # Obtener valores finales
        sol_final = sol_balance.value / 1_000_000_000 if sol_balance.value else 0
        usdc_final = usdc_amount if 'usdc_amount' in locals() else 0
        
        requirements = {
            "SOL para fees": (sol_final >= config.MIN_SOL_FEES, f"{sol_final:.6f}/{config.MIN_SOL_FEES} SOL"),
            "USDC para swap": (usdc_final >= 5.0, f"{usdc_final:.2f}/5.0 USDC"),
            "USDC para trading": (usdc_final >= config.MIN_USDC_BALANCE, f"{usdc_final:.2f}/{config.MIN_USDC_BALANCE} USDC")
        }
        
        all_met = True
        for req, (met, value) in requirements.items():
            status = "✅" if met else "❌"
            print(f"   {status} {req}: {value}")
            if not met:
                all_met = False
        
        if all_met:
            print("\n🎉 ¡TODO LISTO PARA EL SWAP DE PRUEBA!")
            print("💡 Ejecuta: python test_swap.py")
        else:
            print("\n⚠️  FALTAN REQUISITOS")
            print("💡 Depósita los fondos necesarios y vuelve a verificar")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await client.close()

if __name__ == "__main__":
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(check_all_balances())
    input("\nPresiona Enter para salir...")