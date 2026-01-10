# scripts/test_blockchain.py
#!/usr/bin/env python3
"""
Script para probar la conexión con blockchain y Orca
"""

import asyncio
import sys
from pathlib import Path

# Agregar directorio padre al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG
from core.blockchain.wallet_manager import WalletManager
from core.blockchain.orca_integration import OrcaIntegration

async def test_wallet_connection():
    """Prueba conexión de wallet"""
    print("🔗 Probando conexión de wallet...")
    
    try:
        wallet = WalletManager(CONFIG)
        await wallet.connect()
        
        # Obtener saldos
        balances = await wallet.get_wallet_balances()
        print(f"✅ Wallet conectada: {CONFIG.PHANTOM_WALLET[:8]}...")
        print(f"💰 Saldos: {balances}")
        
        # Verificar viabilidad
        viable, message = await wallet.check_operation_viability(0.001)
        print(f"📊 Viabilidad: {message}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error conectando wallet: {e}")
        return False

async def test_orca_swap():
    """Prueba swap simple en testnet"""
    print("\n🔄 Probando swap en Orca...")
    
    try:
        wallet = WalletManager(CONFIG)
        await wallet.connect()
        
        orca = OrcaIntegration(CONFIG, wallet)
        
        # Usar tokens de testnet
        input_mint = "So11111111111111111111111111111111111111112"  # SOL
        output_mint = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
        
        # Monto pequeño para prueba
        amount = 0.001  # 0.001 SOL
        
        print(f"Probando swap: {amount} SOL → USDC")
        
        success, message, tx_details = await orca.execute_swap(
            input_mint=input_mint,
            output_mint=output_mint,
            amount=amount,
            slippage_bps=100  # 1% slippage para prueba
        )
        
        if success:
            print(f"✅ Swap exitoso!")
            print(f"📝 TX: {tx_details.get('signature', 'N/A')}")
            print(f"💰 Output: {tx_details.get('output_amount', 'N/A')}")
            return True
        else:
            print(f"❌ Swap falló: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Error en swap: {e}")
        return False

async def test_rpc_connection():
    """Prueba conexión RPC"""
    print("\n🌐 Probando conexión RPC...")
    
    try:
        from solana.rpc.async_api import AsyncClient
        from solana.rpc.commitment import Confirmed
        
        client = AsyncClient(CONFIG.RPC_ENDPOINT, commitment=Confirmed)
        
        # Obtener slot actual
        slot = await client.get_slot()
        print(f"✅ RPC conectado. Slot actual: {slot.value}")
        
        # Obtener versión
        version = await client.get_version()
        print(f"🔄 Versión Solana: {version.value}")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"❌ Error RPC: {e}")
        return False

async def test_telegram():
    """Prueba conexión Telegram"""
    print("\n🤖 Probando conexión Telegram...")
    
    if CONFIG.TELEGRAM_BOT_TOKEN == "optional":
        print("⏭️  Telegram no configurado, saltando...")
        return True
    
    try:
        from communication.telegram_bridge import TelegramBridge
        
        telegram = TelegramBridge(CONFIG)
        
        # Test simple
        await telegram.send_message("✅ Bot de prueba conectado correctamente")
        print("✅ Telegram conectado")
        
        return True
        
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
        return False

async def main():
    """Función principal de pruebas"""
    print("="*60)
    print("🧪 PRUEBAS DEL BOT ORCA")
    print("="*60)
    
    tests = [
        ("Conexión RPC", test_rpc_connection),
        ("Wallet", test_wallet_connection),
        ("Orca Swap", test_orca_swap),
        ("Telegram", test_telegram)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}...")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Error ejecutando test: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESULTADOS DE PRUEBAS")
    print("="*60)
    
    passed = 0
    for test_name, success in results:
        status = "✅ PASÓ" if success else "❌ FALLÓ"
        print(f"{status} - {test_name}")
        if success:
            passed += 1
    
    print(f"\n🎯 {passed}/{len(tests)} pruebas exitosas")
    
    if passed == len(tests):
        print("\n🚀 ¡Todas las pruebas pasaron! El bot está listo.")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa la configuración.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())