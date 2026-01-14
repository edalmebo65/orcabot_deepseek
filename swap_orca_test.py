# swap_orca_test.py
"""
Script TODO EN UNO: Verifica, swap y monitorea
"""
import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))

class OrcaSwapTester:
    """Tester completo de swaps en Orca/Jupiter"""
    
    def __init__(self):
        self.config = None
        self.client = None
        self.keypair = None
        self.wallet_address = None
        
    async def initialize(self):
        """Inicializar todo"""
        print("🔧 Inicializando tester de swaps...")
        
        # Cargar configuración
        try:
            import config
            self.config = config
            print("✅ Configuración cargada")
        except ImportError as e:
            print(f"❌ Error cargando config: {e}")
            return False
        
        # Cargar dependencias
        try:
            from solders.keypair import Keypair
            from solders.pubkey import Pubkey
            from solana.rpc.async_api import AsyncClient
            from solana.rpc.commitment import Confirmed
            import aiohttp
            print("✅ Dependencias cargadas")
        except ImportError as e:
            print(f"❌ Faltan dependencias: {e}")
            return False
        
        # Configurar RPC
        if self.config.HELIUS_VOICEINDIGO_API_KEY:
            rpc_url = f"{self.config.HELIUS_BASE_URL}/?api-key={self.config.HELIUS_VOICEINDIGO_API_KEY}"
        else:
            rpc_url = self.config.HELIUS_BASE_URL
        
        self.client = AsyncClient(rpc_url, commitment=Confirmed, timeout=30)
        
        # Cargar wallet
        private_key_bytes = self.config.get_private_key()
        if not private_key_bytes:
            print("❌ No se pudo decodificar clave privada")
            return False
        
        self.keypair = Keypair.from_bytes(private_key_bytes)
        self.wallet_address = str(self.keypair.pubkey())
        
        print(f"✅ Wallet: {self.wallet_address[:8]}...")
        
        # Verificar conexión
        try:
            health = await self.client.get_health()
            if health.value == "ok":
                print("✅ Conexión RPC establecida")
                return True
            else:
                print("❌ RPC no saludable")
                return False
        except Exception as e:
            print(f"❌ Error conectando a RPC: {e}")
            return False
    
    async def check_balances(self) -> tuple:
        """Verificar balances de SOL y USDC"""
        print("\n💰 VERIFICANDO BALANCES...")
        
        # SOL balance
        sol_balance = await self.client.get_balance(self.keypair.pubkey())
        sol_amount = sol_balance.value / 1_000_000_000 if sol_balance.value else 0
        
        print(f"   SOL: {sol_amount:.6f} (mínimo: {self.config.MIN_SOL_FEES})")
        
        # USDC balance
        usdc_amount = await self._get_usdc_balance()
        print(f"   USDC: {usdc_amount:.2f} (test: 5.0, trading: {self.config.MIN_USDC_BALANCE})")
        
        return sol_amount, usdc_amount
    
    async def _get_usdc_balance(self) -> float:
        """Obtener balance de USDC"""
        try:
            from solders.pubkey import Pubkey
            from spl.token.associated import get_associated_token_address
            
            usdc_mint = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            ata = get_associated_token_address(self.keypair.pubkey(), usdc_mint)
            
            balance_info = await self.client.get_token_account_balance(ata)
            
            if balance_info.value:
                return float(balance_info.value.ui_amount_string)
            
            return 0.0
            
        except Exception as e:
            print(f"⚠️ Error obteniendo USDC: {e}")
            return 0.0
    
    async def get_jupiter_quote(self, amount_usdc: float):
        """Obtener quote de Jupiter"""
        print(f"\n🔍 OBTENIENDO QUOTE PARA {amount_usdc} USDC...")
        
        amount_lamports = int(amount_usdc * 1_000_000)  # USDC tiene 6 decimales
        
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                params = {
                    "inputMint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                    "outputMint": "So11111111111111111111111111111111111111112",
                    "amount": str(amount_lamports),
                    "slippageBps": int(self.config.MAX_SLIPPAGE_PERCENT * 100),
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
                            route = data['routes'][0]
                            
                            quote = {
                                'input_amount': amount_lamports,
                                'output_amount': int(route['outAmount']),
                                'output_sol': int(route['outAmount']) / 1_000_000_000,
                                'price_impact': float(route['priceImpactPct']) * 100,
                                'route': route
                            }
                            
                            print(f"✅ Quote obtenido:")
                            print(f"   📤 Entrada: {amount_usdc} USDC")
                            print(f"   📥 Salida: {quote['output_sol']:.6f} SOL")
                            print(f"   📉 Price impact: {quote['price_impact']:.4f}%")
                            
                            return quote
                        else:
                            print("❌ No hay rutas disponibles")
                            return None
                    else:
                        print(f"❌ Error API: {response.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Error obteniendo quote: {e}")
            return None
    
    async def execute_swap(self, quote: dict) -> bool:
        """Ejecutar swap real"""
        print("\n⚡ EJECUTANDO SWAP...")
        
        try:
            import aiohttp
            import base64
            from solders.transaction import Transaction
            
            # Crear transacción
            async with aiohttp.ClientSession() as session:
                payload = {
                    "quoteResponse": quote['route'],
                    "userPublicKey": self.wallet_address,
                    "wrapUnwrapSOL": True
                }
                
                async with session.post(
                    "https://quote-api.jup.ag/v6/swap",
                    json=payload,
                    timeout=10
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        swap_transaction = data.get('swapTransaction')
                        
                        if not swap_transaction:
                            print("❌ No se pudo crear transacción")
                            return False
                        
                        # Decodificar y firmar
                        transaction_bytes = base64.b64decode(swap_transaction)
                        transaction = Transaction.deserialize(transaction_bytes)
                        transaction.sign_partial(self.keypair)
                        
                        print("✅ Transacción creada y firmada")
                        
                        # SIMULAR PRIMERO
                        print("🔬 Simulando transacción...")
                        simulate_result = await self.client.simulate_transaction(transaction)
                        
                        if simulate_result.value and simulate_result.value.err is None:
                            print("✅ Simulación exitosa")
                        else:
                            print("❌ Simulación falló")
                            if simulate_result.value and simulate_result.value.err:
                                print(f"   Error: {simulate_result.value.err}")
                            return False
                        
                        # CONFIRMAR EJECUCIÓN
                        confirm = input("\n¿Ejecutar transacción REAL? (s/n): ").lower()
                        if confirm != 's':
                            print("🛑 Transacción cancelada")
                            return False
                        
                        # ENVIAR TRANSACCIÓN
                        print("🚀 Enviando transacción...")
                        send_result = await self.client.send_transaction(transaction)
                        
                        if send_result.value:
                            signature = send_result.value
                            print(f"✅ Transacción enviada: {signature}")
                            print(f"🔗 Explorer: https://solscan.io/tx/{signature}")
                            
                            # ESPERAR CONFIRMACIÓN
                            print("⏳ Esperando confirmación...")
                            for i in range(30):
                                await asyncio.sleep(1)
                                
                                status = await self.client.get_signature_statuses([signature])
                                
                                if status.value and status.value[0]:
                                    if status.value[0].confirmation_status in ["confirmed", "finalized"]:
                                        print(f"✅ Confirmada en {i+1}s")
                                        return True
                                    elif status.value[0].err:
                                        print(f"❌ Transacción falló: {status.value[0].err}")
                                        return False
                            
                            print("⚠️ No confirmada en 30s")
                            return False
                            
                        else:
                            print("❌ Error enviando transacción")
                            return False
                            
                    else:
                        error_text = await response.text()
                        print(f"❌ Error creando swap: {error_text}")
                        return False
                        
        except Exception as e:
            print(f"❌ Error ejecutando swap: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def run_test_swap(self, amount_usdc: float = 5.0):
        """Ejecutar swap de prueba completo"""
        print("\n" + "="*60)
        print(f"🔄 SWAP DE PRUEBA: {amount_usdc} USDC → SOL")
        print("="*60)
        
        # 1. Verificar balances
        sol_balance, usdc_balance = await self.check_balances()
        
        # Verificar requisitos
        if sol_balance < self.config.MIN_SOL_FEES:
            print(f"❌ SOL insuficiente: {sol_balance:.6f} < {self.config.MIN_SOL_FEES}")
            return False
        
        if usdc_balance < amount_usdc:
            print(f"❌ USDC insuficiente: {usdc_balance:.2f} < {amount_usdc}")
            return False
        
        print("\n✅ Balances OK para swap")
        
        # 2. Obtener quote
        quote = await self.get_jupiter_quote(amount_usdc)
        if not quote:
            return False
        
        # 3. Mostrar resumen
        print("\n📊 RESUMEN DEL SWAP:")
        print(f"   📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   👛 Wallet: {self.wallet_address[:8]}...")
        print(f"   💱 Par: USDC → SOL")
        print(f"   📤 Cantidad: {amount_usdc} USDC")
        print(f"   📥 Recibirás: ~{quote['output_sol']:.6f} SOL")
        print(f"   💸 Fees estimados: 0.0001-0.001 SOL")
        print(f"   📉 Price impact: {quote['price_impact']:.4f}%")
        
        # 4. Confirmar
        print("\n" + "="*60)
        confirm = input("¿Continuar con el swap? (s/n): ").lower()
        
        if confirm != 's':
            print("🛑 Swap cancelado")
            return False
        
        # 5. Ejecutar swap
        success = await self.execute_swap(quote)
        
        if success:
            # 6. Verificar resultado
            print("\n📈 VERIFICANDO RESULTADO...")
            await asyncio.sleep(3)  # Esperar a que se actualice
            
            new_sol, new_usdc = await self.check_balances()
            
            print("\n" + "="*60)
            print("✅ SWAP COMPLETADO EXITOSAMENTE!")
            print("="*60)
            print(f"\n💰 Balances finales:")
            print(f"   SOL: {new_sol:.6f} (cambio: {new_sol - sol_balance:+.6f})")
            print(f"   USDC: {new_usdc:.2f} (cambio: {new_usdc - usdc_balance:+.2f})")
            
            # Guardar log
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'wallet': self.wallet_address,
                'input_amount': amount_usdc,
                'input_token': 'USDC',
                'output_amount': quote['output_sol'],
                'output_token': 'SOL',
                'success': True
            }
            
            with open('swap_test_log.json', 'w') as f:
                json.dump(log_entry, f, indent=2)
            
            print(f"\n📝 Log guardado en: swap_test_log.json")
            
            return True
        else:
            print("\n❌ SWAP FALLIDO")
            return False
    
    async def cleanup(self):
        """Limpiar recursos"""
        if self.client:
            await self.client.close()
            print("✅ Cliente RPC cerrado")

async def main():
    """Función principal"""
    tester = OrcaSwapTester()
    
    try:
        # Inicializar
        if not await tester.initialize():
            print("❌ No se pudo inicializar")
            return
        
        # Menú principal
        while True:
            print("\n" + "="*60)
            print("🎯 TESTER DE SWAPS - ORCABOT DEEPSEEK")
            print("="*60)
            print("\n1. Verificar balances")
            print("2. Swap de prueba (5 USDC → SOL)")
            print("3. Swap personalizado")
            print("4. Salir")
            
            option = input("\nSelecciona opción (1-4): ")
            
            if option == '1':
                sol, usdc = await tester.check_balances()
                
                print("\n" + "="*60)
                print("📊 RESUMEN DE BALANCES")
                print("="*60)
                print(f"SOL: {sol:.6f} | USDC: {usdc:.2f}")
                
                # Verificar si está listo para trading
                if sol >= tester.config.MIN_SOL_FEES and usdc >= tester.config.MIN_USDC_BALANCE:
                    print("\n🎉 ¡LISTO PARA TRADING!")
                else:
                    print("\n⚠️  FALTAN FONDOS")
                    if sol < tester.config.MIN_SOL_FEES:
                        print(f"   - Necesitas {tester.config.MIN_SOL_FEES - sol:.6f} SOL más")
                    if usdc < tester.config.MIN_USDC_BALANCE:
                        print(f"   - Necesitas {tester.config.MIN_USDC_BALANCE - usdc:.2f} USDC más")
            
            elif option == '2':
                await tester.run_test_swap(5.0)
                input("\nPresiona Enter para continuar...")
            
            elif option == '3':
                try:
                    amount = float(input("Cantidad de USDC a swap: "))
                    if amount <= 0:
                        print("❌ Cantidad debe ser positiva")
                    else:
                        await tester.run_test_swap(amount)
                        input("\nPresiona Enter para continuar...")
                except ValueError:
                    print("❌ Cantidad no válida")
            
            elif option == '4':
                print("👋 Saliendo...")
                break
            
            else:
                print("❌ Opción no válida")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Interrumpido por usuario")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    # Configurar Windows
    if sys.platform == 'win32':
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Ejecutar
    asyncio.run(main())