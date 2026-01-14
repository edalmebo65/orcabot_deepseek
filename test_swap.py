# test_swap.py
"""
Script para probar swaps USDC → SOL en Orca/Jupiter
Realiza una transacción de prueba de 5 USDC
"""
import asyncio
import json
import base64
from typing import Dict, Optional, Tuple
from datetime import datetime
import sys
import os

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

# Importar configuración
try:
    import config
    print("✅ Configuración cargada")
except ImportError as e:
    print(f"❌ Error cargando config.py: {e}")
    sys.exit(1)

async def test_swap_5_usdc_to_sol():
    """Realizar swap de prueba de 5 USDC a SOL"""
    print("\n" + "="*60)
    print("🔄 SWAP DE PRUEBA: 5 USDC → SOL")
    print("="*60)
    
    # Verificar configuración
    print("\n🔍 VERIFICANDO CONFIGURACIÓN...")
    
    if not config.PHANTOM_PRIVATE_KEY_BYTES:
        print("❌ PHANTOM_PRIVATE_KEY_BYTES no configurada")
        return False
    
    if not config.PHANTOM_WALLET:
        print("❌ PHANTOM_WALLET no configurada")
        return False
    
    print(f"✅ Wallet: {config.PHANTOM_WALLET[:8]}...")
    print(f"✅ RPC: {'Helius' if config.HELIUS_VOICEINDIGO_API_KEY else 'Público'}")
    
    # Importar dependencias
    try:
        from solders.keypair import Keypair
        from solders.pubkey import Pubkey
        from solana.rpc.async_api import AsyncClient
        from solana.rpc.commitment import Confirmed
        import aiohttp
        print("✅ Dependencias cargadas")
    except ImportError as e:
        print(f"❌ Faltan dependencias: {e}")
        print("💡 Ejecuta: pip install solders solana")
        return False
    
    try:
        # 1. CONFIGURAR CLIENTE SOLANA
        print("\n🌐 CONECTANDO A SOLANA...")
        
        if config.HELIUS_VOICEINDIGO_API_KEY:
            rpc_url = f"{config.HELIUS_BASE_URL}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
        else:
            rpc_url = config.HELIUS_BASE_URL
        
        client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
        
        # Probar conexión
        health = await client.get_health()
        if not health.value == "ok":
            print("❌ RPC no está saludable")
            return False
        
        print("✅ Conexión RPC establecida")
        
        # 2. CARGAR WALLET
        print("\n👛 CARGANDO WALLET...")
        
        # Decodificar clave privada
        private_key_bytes = config.get_private_key()
        if not private_key_bytes:
            print("❌ No se pudo decodificar la clave privada")
            return False
        
        # Crear keypair
        try:
            keypair = Keypair.from_bytes(private_key_bytes)
            wallet_address = str(keypair.pubkey())
            print(f"✅ Wallet cargada: {wallet_address}")
        except Exception as e:
            print(f"❌ Error cargando wallet: {e}")
            return False
        
        # 3. VERIFICAR BALANCES
        print("\n💰 VERIFICANDO BALANCES...")
        
        # Obtener balance de SOL
        sol_balance = await client.get_balance(keypair.pubkey())
        if sol_balance.value:
            sol_amount = sol_balance.value / 1_000_000_000
            print(f"✅ Balance SOL: {sol_amount:.4f} SOL")
            
            # Verificar mínimo para fees
            if sol_amount < config.MIN_SOL_FEES:
                print(f"⚠️ SOL insuficiente para fees (mínimo: {config.MIN_SOL_FEES} SOL)")
                print("💡 Necesitas depositar SOL para fees de transacción")
                return False
        else:
            print("❌ No se pudo obtener balance de SOL")
            return False
        
        # 4. OBTENER QUOTE DE JUPITER
        print("\n🔍 OBTENIENDO COTIZACIÓN DE JUPITER...")
        
        amount_in_lamports = 5_000_000  # 5 USDC (6 decimales)
        
        quote = await get_jupiter_quote(
            amount_in_lamports,
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC mint
            "So11111111111111111111111111111111111111112",   # SOL mint
            wallet_address
        )
        
        if not quote:
            print("❌ No se pudo obtener quote de Jupiter")
            return False
        
        print(f"✅ Quote obtenido:")
        print(f"   💱 Input: 5 USDC")
        print(f"   💰 Output: {quote['outAmount'] / 1_000_000_000:.6f} SOL")
        print(f"   📉 Price impact: {quote['priceImpactPct']*100:.4f}%")
        print(f"   ⚡ Slippage: {config.MAX_SLIPPAGE_PERCENT}%")
        
        # 5. CREAR TRANSACCIÓN DE SWAP
        print("\n⚡ CREANDO TRANSACCIÓN...")
        
        swap_transaction = await create_swap_transaction(
            quote,
            keypair.pubkey()
        )
        
        if not swap_transaction:
            print("❌ No se pudo crear la transacción")
            return False
        
        print("✅ Transacción creada")
        
        # 6. FIRMAR Y ENVIAR TRANSACCIÓN
        print("\n✍️ FIRMANDO TRANSACCIÓN...")
        
        # Firmar transacción
        transaction_bytes = base64.b64decode(swap_transaction)
        transaction = Transaction.deserialize(transaction_bytes)
        transaction.sign_partial(keypair)
        
        print("✅ Transacción firmada")
        
        # 7. SIMULAR TRANSACCIÓN (PRIMERO)
        print("\n🔬 SIMULANDO TRANSACCIÓN...")
        
        simulate_result = await client.simulate_transaction(transaction)
        
        if simulate_result.value and simulate_result.value.err is None:
            print("✅ Simulación exitosa")
            
            # Mostrar logs de simulación
            if simulate_result.value.logs:
                print("   📝 Logs de simulación:")
                for log in simulate_result.value.logs[:5]:  # Primeros 5 logs
                    print(f"     - {log}")
        else:
            print("❌ Simulación falló")
            if simulate_result.value and simulate_result.value.err:
                print(f"   Error: {simulate_result.value.err}")
            return False
        
        # 8. CONFIRMAR Y EJECUTAR
        confirm = input("\n¿Ejecutar transacción real? (s/n): ").lower()
        if confirm != 's':
            print("🛑 Transacción cancelada")
            return True
        
        print("\n🚀 ENVIANDO TRANSACCIÓN...")
        
        # Enviar transacción
        send_result = await client.send_transaction(transaction)
        
        if send_result.value:
            signature = send_result.value
            print(f"✅ Transacción enviada: {signature}")
            print(f"🔗 Explorer: https://solscan.io/tx/{signature}")
            
            # 9. CONFIRMAR TRANSACCIÓN
            print("\n⏳ ESPERANDO CONFIRMACIÓN...")
            
            confirmed = False
            for i in range(30):  # Esperar hasta 30 segundos
                await asyncio.sleep(1)
                
                status = await client.get_signature_statuses([signature])
                
                if status.value and status.value[0]:
                    if status.value[0].confirmation_status in ["confirmed", "finalized"]:
                        confirmed = True
                        print(f"✅ Transacción confirmada en {i+1} segundos")
                        break
                    elif status.value[0].err:
                        print(f"❌ Transacción falló: {status.value[0].err}")
                        return False
            
            if confirmed:
                # 10. VERIFICAR BALANCE FINAL
                print("\n📊 VERIFICANDO RESULTADO...")
                await asyncio.sleep(2)  # Esperar a que se actualice
                
                final_balance = await client.get_balance(keypair.pubkey())
                if final_balance.value:
                    final_sol = final_balance.value / 1_000_000_000
                    sol_change = final_sol - sol_amount
                    
                    print(f"💰 Cambio en SOL: {sol_change:+.6f} SOL")
                    print(f"💵 Balance final SOL: {final_sol:.6f} SOL")
                    
                    # Calcular precio efectivo
                    effective_price = 5 / (sol_change if sol_change > 0 else 0.000001)
                    print(f"📈 Precio efectivo: 1 SOL = ${effective_price:.2f} USDC")
                    
                    return True
                else:
                    print("⚠️ No se pudo verificar balance final")
                    return True
            else:
                print("⚠️ Transacción no confirmada en 30 segundos")
                return False
        else:
            print("❌ Error enviando transacción")
            return False
            
    except Exception as e:
        print(f"❌ Error durante el swap: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cerrar cliente
        try:
            await client.close()
        except:
            pass

async def get_jupiter_quote(
    amount: int,
    input_mint: str,
    output_mint: str,
    wallet_address: str
) -> Optional[Dict]:
    """Obtener quote de Jupiter para swap"""
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": int(config.MAX_SLIPPAGE_PERCENT * 100),
                "userPublicKey": wallet_address,
                "wrapUnwrapSOL": True,
                "computeUnitPriceMicroLamports": "auto"
            }
            
            async with session.get(
                "https://quote-api.jup.ag/v6/quote",
                params=params,
                timeout=10
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    # Verificar que haya rutas
                    if not data.get('routes'):
                        print("❌ No hay rutas disponibles")
                        return None
                    
                    # Tomar la mejor ruta
                    best_route = data['routes'][0]
                    
                    return {
                        'route': best_route,
                        'inAmount': amount,
                        'outAmount': int(best_route['outAmount']),
                        'priceImpactPct': float(best_route['priceImpactPct']),
                        'slippageBps': int(config.MAX_SLIPPAGE_PERCENT * 100)
                    }
                else:
                    print(f"❌ Error API Jupiter: {response.status}")
                    return None
                    
    except Exception as e:
        print(f"❌ Error obteniendo quote: {e}")
        return None

async def create_swap_transaction(
    quote: Dict,
    wallet_pubkey: Pubkey
) -> Optional[str]:
    """Crear transacción de swap"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "quoteResponse": quote['route'],
                "userPublicKey": str(wallet_pubkey),
                "wrapUnwrapSOL": True,
                "computeUnitPriceMicroLamports": "auto",
                "asLegacyTransaction": False  # Usar versión transaction
            }
            
            async with session.post(
                "https://quote-api.jup.ag/v6/swap",
                json=payload,
                timeout=10
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data.get('swapTransaction')
                else:
                    error_text = await response.text()
                    print(f"❌ Error creando transacción: {error_text}")
                    return None
                    
    except Exception as e:
        print(f"❌ Error creando transacción: {e}")
        return None

async def check_usdc_balance(client: AsyncClient, wallet_pubkey: Pubkey) -> float:
    """Verificar balance de USDC"""
    try:
        # Token USDC
        usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        
        # Obtener cuenta asociada
        from solders.instruction import Instruction
        from spl.token.constants import TOKEN_PROGRAM_ID
        from spl.token.associated import get_associated_token_address
        
        ata = get_associated_token_address(wallet_pubkey, usdc_mint)
        
        # Obtener balance
        balance_info = await client.get_token_account_balance(ata)
        
        if balance_info.value:
            return float(balance_info.value.ui_amount_string)
        
        return 0.0
        
    except Exception as e:
        print(f"⚠️ Error verificando USDC: {e}")
        return 0.0

def print_welcome():
    """Mostrar mensaje de bienvenida"""
    print("\n" + "="*60)
    print("🎯 SWAP DE PRUEBA - ORCABOT DEEPSEEK")
    print("="*60)
    print("\nEste script realizará un swap de prueba de:")
    print("   5 USDC → SOL")
    print("\n✅ PRERREQUISITOS:")
    print("   1. Wallet Phantom configurada")
    print("   2. Balance mínimo de 5 USDC")
    print("   3. Balance mínimo de 0.05 SOL para fees")
    print("   4. Conexión a internet estable")
    print("\n⚠️  ADVERTENCIA:")
    print("   - Esto realizará una transacción REAL en mainnet")
    print("   - Se cobrarán fees de red (~0.0001-0.001 SOL)")
    print("   - El swap es irreversible")
    print("="*60)

async def main():
    """Función principal"""
    print_welcome()
    
    # Confirmar antes de continuar
    confirm = input("\n¿Continuar con el swap de prueba? (s/n): ").lower()
    if confirm != 's':
        print("🛑 Operación cancelada")
        return
    
    # Ejecutar swap
    success = await test_swap_5_usdc_to_sol()
    
    if success:
        print("\n" + "="*60)
        print("✅ SWAP COMPLETADO EXITOSAMENTE")
        print("="*60)
        print("\n🎉 ¡Felicidades! El bot funciona correctamente.")
        print("📊 El swap de 5 USDC a SOL se ejecutó con éxito.")
        print("\n🚀 Ahora puedes proceder con:")
        print("   1. Probar el selector de tokens")
        print("   2. Probar el sistema ML")
        print("   3. Ejecutar el bot completo")
    else:
        print("\n" + "="*60)
        print("❌ SWAP FALLIDO")
        print("="*60)
        print("\n💡 Posibles soluciones:")
        print("   1. Verifica que tengas suficiente SOL para fees")
        print("   2. Verifica que tengas al menos 5 USDC")
        print("   3. Verifica tu conexión a internet")
        print("   4. Revisa que las claves estén correctas")

if __name__ == "__main__":
    # Para Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Operación cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
    
    input("\nPresiona Enter para salir...")