# swap_test_simple.py
"""
Swap de prueba simplificado 5 USDC → SOL
"""
import asyncio
import sys
import os
import base64
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# Importar configuración
try:
    import config
    print("✅ Configuración cargada")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

class SimpleSwapTester:
    def __init__(self):
        self.client = None
        self.keypair = None
        
    async def connect(self):
        """Conectar a Solana"""
        try:
            from solders.keypair import Keypair
            from solana.rpc.async_api import AsyncClient
            from solana.rpc.commitment import Confirmed
            import aiohttp
        except ImportError:
            print("❌ Instala dependencias: pip install solders solana aiohttp")
            return False
        
        # Configurar RPC
        rpc_url = config.HELIUS_BASE_URL
        if config.HELIUS_VOICEINDIGO_API_KEY and "helius" in rpc_url.lower():
            rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
        
        self.client = AsyncClient(rpc_url, commitment=Confirmed)
        
        # Cargar wallet
        private_key_bytes = config.get_private_key()
        if not private_key_bytes:
            print("❌ Error con clave privada")
            return False
        
        self.keypair = Keypair.from_bytes(private_key_bytes)
        print(f"✅ Wallet: {str(self.keypair.pubkey())[:8]}...")
        
        return True
    
    async def check_balance(self):
        """Verificar balance de SOL"""
        balance = await self.client.get_balance(self.keypair.pubkey())
        if balance.value:
            return balance.value / 1_000_000_000
        return 0
    
    async def swap_5_usdc_to_sol(self):
        """Realizar swap de 5 USDC a SOL"""
        print("\n🔄 PREPARANDO SWAP DE 5 USDC → SOL")
        
        # 1. Verificar balance SOL
        sol_balance = await self.check_balance()
        print(f"💰 Balance SOL actual: {sol_balance:.6f}")
        
        if sol_balance < config.MIN_SOL_FEES:
            print(f"❌ SOL insuficiente para fees (necesitas {config.MIN_SOL_FEES})")
            return False
        
        # 2. Obtener quote de Jupiter
        print("\n🔍 Obteniendo cotización...")
        quote = await self.get_jupiter_quote()
        if not quote:
            return False
        
        # 3. Mostrar detalles
        print(f"\n📊 DETALLES DEL SWAP:")
        print(f"   Entrada: 5 USDC")
        print(f"   Salida estimada: {quote['out_sol']:.6f} SOL")
        print(f"   Price impact: {quote['price_impact']*100:.4f}%")
        print(f"   Fees estimados: ~0.0001 SOL")
        
        # 4. Confirmar
        print("\n" + "="*50)
        confirm = input("¿Ejecutar swap REAL? (s/n): ").lower()
        if confirm != 's':
            print("🛑 Cancelado")
            return False
        
        # 5. Crear y enviar transacción
        print("\n⚡ Creando transacción...")
        tx_result = await self.create_and_send_swap(quote)
        
        if tx_result:
            print(f"\n✅ SWAP EXITOSO!")
            print(f"🔗 TX: {tx_result}")
            print(f"📅 {datetime.now().strftime('%H:%M:%S')}")
            
            # Verificar nuevo balance
            await asyncio.sleep(3)
            new_balance = await self.check_balance()
            print(f"💰 Nuevo balance SOL: {new_balance:.6f}")
            print(f"📈 Cambio: {new_balance - sol_balance:+.6f} SOL")
            
            return True
        else:
            print("❌ Swap falló")
            return False
    
    async def get_jupiter_quote(self):
        """Obtener quote de Jupiter"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "outputMint": "So11111111111111111111111111111111111111112",
                    "amount": "5000000",  # 5 USDC en lamports (6 decimales)
                    "slippageBps": "50",  # 0.5%
                    "userPublicKey": str(self.keypair.pubkey())
                }
                
                async with session.get(
                    "https://quote-api.jup.ag/v6/quote",
                    params=params,
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('routes'):
                            route = data['routes'][0]
                            return {
                                'route': route,
                                'out_sol': int(route['outAmount']) / 1_000_000_000,
                                'price_impact': float(route['priceImpactPct'])
                            }
                    return None
                    
        except Exception as e:
            print(f"❌ Error quote: {e}")
            return None
    
    async def create_and_send_swap(self, quote):
        """Crear y enviar transacción de swap"""
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "quoteResponse": quote['route'],
                    "userPublicKey": str(self.keypair.pubkey()),
                    "wrapUnwrapSOL": True
                }
                
                async with session.post(
                    "https://quote-api.jup.ag/v6/swap",
                    json=payload,
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        swap_tx = data.get('swapTransaction')
                        
                        if swap_tx:
                            # Decodificar y firmar
                            from solders.transaction import Transaction
                            
                            tx_bytes = base64.b64decode(swap_tx)
                            transaction = Transaction.deserialize(tx_bytes)
                            transaction.sign_partial(self.keypair)
                            
                            # Enviar
                            result = await self.client.send_transaction(transaction)
                            
                            if result.value:
                                tx_hash = result.value
                                
                                # Esperar confirmación
                                print("⏳ Esperando confirmación...", end="", flush=True)
                                for i in range(30):
                                    await asyncio.sleep(1)
                                    status = await self.client.get_signature_statuses([tx_hash])
                                    
                                    if status.value and status.value[0]:
                                        if status.value[0].confirmation_status in ["confirmed", "finalized"]:
                                            print(f"✅ ({i+1}s)")
                                            return tx_hash
                                        elif status.value[0].err:
                                            print(f"❌ Error: {status.value[0].err}")
                                            return None
                                
                                print("⚠️ Tiempo agotado")
                                return None
                    
                    return None
                    
        except Exception as e:
            print(f"❌ Error swap: {e}")
            return None
    
    async def close(self):
        """Cerrar conexión"""
        if self.client:
            await self.client.close()

async def main():
    """Función principal"""
    print("\n" + "="*60)
    print("🎯 SWAP DE PRUEBA - 5 USDC → SOL")
    print("="*60)
    
    print("\n⚠️  ADVERTENCIA:")
    print("   • Esto es una transacción REAL en mainnet")
    print("   • Se cobrarán fees de red (~0.0001 SOL)")
    print("   • El swap es irreversible")
    print("   • Solo usa fondos que puedas perder")
    
    confirm = input("\n¿Continuar? (s/n): ").lower()
    if confirm != 's':
        print("🛑 Cancelado")
        return
    
    tester = SimpleSwapTester()
    
    try:
        if not await tester.connect():
            return
        
        await tester.swap_5_usdc_to_sol()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Interrumpido por usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.close()

if __name__ == "__main__":
    # Configurar Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    asyncio.run(main())
    input("\nPresiona Enter para salir...")