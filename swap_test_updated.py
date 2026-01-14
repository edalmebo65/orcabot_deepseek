# swap_test_updated.py
"""
Swap de prueba con métodos actualizados
"""
import asyncio
import sys
import os
import base64
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

# Importar configuración
try:
    import config
    print("✅ Configuración cargada")
except ImportError as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

class UpdatedSwapTester:
    def __init__(self):
        self.client = None
        self.keypair = None
        self.wallet_address = None
        
    async def connect(self):
        """Conectar a Solana"""
        try:
            from solders.keypair import Keypair
            from solders.pubkey import Pubkey
            from solana.rpc.async_api import AsyncClient
            from solana.rpc.commitment import Confirmed
            import aiohttp
        except ImportError:
            print("❌ Instala dependencias:")
            print("   pip install solders solana aiohttp")
            return False
        
        # Configurar RPC
        rpc_url = getattr(config, 'HELIUS_BASE_URL', 'https://api.mainnet-beta.solana.com')
        if hasattr(config, 'HELIUS_VOICEINDIGO_API_KEY') and config.HELIUS_VOICEINDIGO_API_KEY:
            if "helius" in rpc_url.lower():
                rpc_url = f"{rpc_url}/?api-key={config.HELIUS_VOICEINDIGO_API_KEY}"
        
        print(f"🌐 Conectando a: {rpc_url[:50]}...")
        
        self.client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
        
        # Decodificar y cargar wallet
        try:
            key_str = config.PHANTOM_PRIVATE_KEY_BYTES
            private_key_bytes = base64.b64decode(key_str.strip())
            
            self.keypair = Keypair.from_bytes(private_key_bytes)
            self.wallet_address = str(self.keypair.pubkey())
            
            print(f"✅ Wallet: {self.wallet_address[:8]}...")
            return True
            
        except Exception as e:
            print(f"❌ Error cargando wallet: {e}")
            return False
    
    async def check_balance(self):
        """Verificar balance de SOL"""
        try:
            balance = await self.client.get_balance(self.keypair.pubkey())
            if balance.value:
                return balance.value / 1_000_000_000
        except Exception as e:
            print(f"⚠️ Error obteniendo balance: {e}")
        return 0
    
    async def get_jupiter_quote(self, amount_usdc: float = 5.0):
        """Obtener quote de Jupiter"""
        print(f"\n🔍 Obteniendo quote para {amount_usdc} USDC...")
        
        import aiohttp
        
        amount_lamports = int(amount_usdc * 1_000_000)  # USDC tiene 6 decimales
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
                    "outputMint": "So11111111111111111111111111111111111111112",   # SOL
                    "amount": str(amount_lamports),
                    "slippageBps": "50",  # 0.5%
                    "userPublicKey": self.wallet_address,
                    "wrapUnwrapSOL": True
                }
                
                async with session.get(
                    "https://quote-api.jup.ag/v6/quote",
                    params=params,
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get('routes'):
                            best_route = data['routes'][0]
                            
                            quote = {
                                'route': best_route,
                                'input_amount': amount_lamports,
                                'output_amount': int(best_route['outAmount']),
                                'output_sol': int(best_route['outAmount']) / 1_000_000_000,
                                'price_impact': float(best_route['priceImpactPct']) * 100
                            }
                            
                            print(f"✅ Quote obtenido:")
                            print(f"   📤 Entrada: {amount_usdc} USDC")
                            print(f"   📥 Salida: {quote['output_sol']:.6f} SOL")
                            print(f"   📉 Price impact: {quote['price_impact']:.4f}%")
                            
                            return quote
                        else:
                            print("❌ No hay rutas disponibles")
                    else:
                        print(f"❌ Error API: {response.status}")
                        
        except Exception as e:
            print(f"❌ Error obteniendo quote: {e}")
        
        return None
    
    async def execute_swap(self, quote):
        """Ejecutar swap"""
        import aiohttp
        
        print("\n⚡ Creando transacción de swap...")
        
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "quoteResponse": quote['route'],
                    "userPublicKey": self.wallet_address,
                    "wrapUnwrapSOL": True
                }
                
                async with session.post(
                    "https://quote-api.jup.ag/v6/swap",
                    json=payload,
                    timeout=15
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
                            
                            print("✅ Transacción creada y firmada")
                            
                            # SIMULAR PRIMERO
                            print("🔬 Simulando transacción...")
                            try:
                                simulate_result = await self.client.simulate_transaction(transaction)
                                if simulate_result.value and simulate_result.value.err is None:
                                    print("✅ Simulación exitosa")
                                else:
                                    print("❌ Simulación falló")
                                    return None
                            except Exception as e:
                                print(f"⚠️ Error en simulación: {e}")
                            
                            # ENVIAR TRANSACCIÓN REAL
                            print("🚀 Enviando transacción...")
                            send_result = await self.client.send_transaction(transaction)
                            
                            if send_result.value:
                                tx_hash = send_result.value
                                print(f"✅ Transacción enviada: {tx_hash}")
                                print(f"🔗 Explorer: https://solscan.io/tx/{tx_hash}")
                                
                                # ESPERAR CONFIRMACIÓN
                                print("⏳ Esperando confirmación...", end="", flush=True)
                                
                                for i in range(30):
                                    await asyncio.sleep(1)
                                    print(".", end="", flush=True)
                                    
                                    try:
                                        status = await self.client.get_signature_statuses([tx_hash])
                                        
                                        if status.value and status.value[0]:
                                            if status.value[0].confirmation_status in ["confirmed", "finalized"]:
                                                print(f"\n✅ Confirmada en {i+1}s")
                                                return tx_hash
                                            elif status.value[0].err:
                                                print(f"\n❌ Transacción falló: {status.value[0].err}")
                                                return None
                                    except:
                                        continue
                                
                                print("\n⚠️ Tiempo de espera agotado")
                                return None
                                
                        else:
                            print("❌ No se pudo crear transacción")
                    else:
                        error_text = await response.text()
                        print(f"❌ Error API: {error_text}")
                        
        except Exception as e:
            print(f"❌ Error en swap: {e}")
            import traceback
            traceback.print_exc()
        
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
    
    print("\n⚠️  ADVERTENCIA IMPORTANTE:")
    print("   • Esta es una transacción REAL en mainnet")
    print("   • Se cobrarán fees (~0.0001 SOL)")
    print("   • El swap es IRREVERSIBLE")
    print("   • Solo usa fondos que puedas perder")
    
    confirm = input("\n¿Continuar? (s/n): ").lower()
    if confirm != 's':
        print("🛑 Operación cancelada")
        return
    
    tester = UpdatedSwapTester()
    
    try:
        # Conectar
        print("\n🔌 Conectando...")
        if not await tester.connect():
            return
        
        # Verificar balance SOL
        print("\n💰 Verificando balance SOL...")
        sol_balance = await tester.check_balance()
        print(f"   Balance actual: {sol_balance:.6f} SOL")
        
        min_sol = getattr(config, 'MIN_SOL_FEES', 0.05)
        if sol_balance < min_sol:
            print(f"❌ SOL insuficiente (necesitas {min_sol} SOL)")
            return
        
        # Obtener quote
        quote = await tester.get_jupiter_quote(5.0)
        if not quote:
            return
        
        # Mostrar resumen
        print("\n" + "="*50)
        print("📊 RESUMEN DEL SWAP")
        print("="*50)
        print(f"📅 Fecha: {datetime.now().strftime('%H:%M:%S')}")
        print(f"👛 Wallet: {tester.wallet_address[:8]}...")
        print(f"💱 Par: USDC → SOL")
        print(f"📤 Entrada: 5.0 USDC")
        print(f"📥 Salida estimada: {quote['output_sol']:.6f} SOL")
        print(f"💸 Fees estimados: ~0.0001 SOL")
        print(f"📉 Price impact: {quote['price_impact']:.4f}%")
        
        # Confirmar final
        print("\n" + "="*50)
        final_confirm = input("¿EJECUTAR SWAP REAL? (s/n): ").lower()
        
        if final_confirm != 's':
            print("🛑 Swap cancelado")
            return
        
        # Ejecutar swap
        tx_hash = await tester.execute_swap(quote)
        
        if tx_hash:
            # Verificar resultado
            print("\n📈 VERIFICANDO RESULTADO...")
            await asyncio.sleep(3)
            
            new_balance = await tester.check_balance()
            sol_change = new_balance - sol_balance
            
            print("\n" + "="*60)
            print("✅ SWAP COMPLETADO EXITOSAMENTE!")
            print("="*60)
            print(f"\n💰 Resultado:")
            print(f"   Balance anterior: {sol_balance:.6f} SOL")
            print(f"   Balance actual: {new_balance:.6f} SOL")
            print(f"   Cambio: {sol_change:+.6f} SOL")
            print(f"\n🔗 Transacción: {tx_hash}")
            print(f"📅 Hora: {datetime.now().strftime('%H:%M:%S')}")
            
            # Calcular precio efectivo
            if sol_change > 0:
                effective_price = 5.0 / sol_change
                print(f"💱 Precio efectivo: 1 SOL = ${effective_price:.2f}")
            
            # Guardar log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'wallet': tester.wallet_address,
                'tx_hash': tx_hash,
                'input': {'amount': 5.0, 'token': 'USDC'},
                'output': {'amount': quote['output_sol'], 'token': 'SOL'},
                'fees_estimated': 0.0001
            }
            
            import json
            with open('swap_success_log.json', 'w') as f:
                json.dump(log_entry, f, indent=2)
            
            print(f"\n📝 Log guardado: swap_success_log.json")
            
        else:
            print("\n❌ SWAP FALLIDO")
            print("💡 Revisa los errores anteriores")
        
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