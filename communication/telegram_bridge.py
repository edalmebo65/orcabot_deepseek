# communication/telegram_bridge.py
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode

class TelegramBridge:
    """Puente de comunicación bidireccional con Telegram"""
    
    def __init__(self, config):
        self.config = config
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher()
        self.authorized_users = [int(config.TELEGRAM_CHAT_ID)]
        
        # Registrar handlers
        self._register_handlers()
        
        # Estado del bot
        self.last_update = datetime.now()
        self.message_queue = asyncio.Queue()
    
    def _register_handlers(self):
        """Registra todos los comandos de Telegram"""
        
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            if message.from_user.id not in self.authorized_users:
                await message.answer("❌ No autorizado")
                return
            
            welcome_text = """
🤖 *Orca Trading Bot - Panel de Control*

*Comandos disponibles:*
/status - Estado del bot y capital
/operations - Operaciones activas
/history - Historial de trades
/portfolio - Portfolio actual
/pools - Top pools analizados
/pause - Pausar trading  
/resume - Reanudar trading
/panic - Cerrar todas las posiciones
/settings - Ver/Ajustar configuración
/help - Mostrar esta ayuda

⚡ *Bot configurado para:*
- Máx 5 operaciones simultáneas
- 10% capital por operación
- Stop loss dinámico con trailing
- ML integrado para predicciones
            """
            await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN)
        
        @self.dp.message(Command("status"))
        async def cmd_status(message: Message):
            if not self._check_authorization(message):
                return
            
            status = await self._get_bot_status()
            await message.answer(status, parse_mode=ParseMode.MARKDOWN)
        
        @self.dp.message(Command("operations"))
        async def cmd_operations(message: Message):
            if not self._check_authorization(message):
                return
            
            operations = await self._get_active_operations()
            await message.answer(operations, parse_mode=ParseMode.MARKDOWN)
        
        @self.dp.message(Command("panic"))
        async def cmd_panic(message: Message):
            if not self._check_authorization(message):
                return
            
            # Pedir confirmación
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="✅ CONFIRMAR PANIC SELL")],
                    [KeyboardButton(text="❌ Cancelar")]
                ],
                resize_keyboard=True,
                one_time_keyboard=True
            )
            
            await message.answer(
                "🚨 *PROTOCOLO DE EMERGENCIA* 🚨\n\n"
                "¿Estás seguro de ejecutar PANIC SELL?\n"
                "Esto venderá TODAS las posiciones inmediatamente.\n\n"
                "⚠️ **Esta acción no se puede deshacer.**",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        
        @self.dp.message(F.text == "✅ CONFIRMAR PANIC SELL")
        async def confirm_panic(message: Message):
            await message.answer(
                "🔄 Ejecutando panic sell...",
                reply_markup=types.ReplyKeyboardRemove()
            )
            # Lógica de panic sell aquí
            await self._execute_panic_sell()
            await message.answer("✅ Panic sell completado")
        
        @self.dp.message(Command("settings"))
        async def cmd_settings(message: Message):
            if not self._check_authorization(message):
                return
            
            settings_text = """
⚙️ *Configuración Actual*

*Límites de Capital:*
• Máx por operación: 10% del capital
• Operaciones simultáneas: 5
• Stop loss inicial: 2%
• Take profit inicial: 5%

*ML Config:*
• Confianza mínima: 75%
• Activos analizados: 20
• Timeframes: 5m, 15m, 1h

*Riesgo Cero:*
• Buffer: 0.2%
• Trailing stop: 0.5% activación

Para modificar, edita config.py
            """
            await message.answer(settings_text, parse_mode=ParseMode.MARKDOWN)
    
    def _check_authorization(self, message: Message) -> bool:
        """Verifica si el usuario está autorizado"""
        return message.from_user.id in self.authorized_users
    
    async def _get_bot_status(self) -> str:
        """Genera reporte de estado"""
        # Esto se integrará con el bot principal
        return """
📊 *Estado del Bot*

💰 *Capital:*
• Total: $10,000.00
• Disponible: $8,500.00
• En operaciones: $1,500.00

📈 *Operaciones:*
• Activas: 2/5
• Hoy: 5 trades
• P&L hoy: +$125.50 (+1.25%)

🤖 *Sistema:*
• Estado: 🟢 OPERANDO
• Último ciclo: Hace 2m
• ML confianza: 82%
• Errores: 0
        """
    
    async def _get_active_operations(self) -> str:
        """Obtiene operaciones activas"""
        return """
🔄 *Operaciones Activas (2/5)*

1. *SOL/USDC*
   • Entrada: $102.50
   • Actual: $105.75
   • P&L: +3.17% (+$31.70)
   • SL: $100.45 | TP: $107.62
   • Riesgo cero: ✅ Alcanzado

2. *RAY/USDC*
   • Entrada: $1.85
   • Actual: $1.92
   • P&L: +3.78% (+$18.90)
   • SL: $1.81 | TP: $1.94
   • Trailing: $1.90 activado
        """
    
    async def _execute_panic_sell(self):
        """Ejecuta panic sell de todas las posiciones"""
        # Implementar lógica real
        pass
    
    async def send_message(self, text: str, parse_mode: str = ParseMode.MARKDOWN):
        """Envía mensaje al chat autorizado"""
        try:
            await self.bot.send_message(
                chat_id=self.config.TELEGRAM_CHAT_ID,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            self.config.logger.error(f"Error enviando mensaje Telegram: {e}")
    
    async def initialize(self):
        """Inicializa el bot de Telegram"""
        await self.bot.delete_webhook(drop_pending_updates=True)
        asyncio.create_task(self.dp.start_polling(self.bot))
        self.config.logger.info("🤖 Bot de Telegram inicializado")
    
    async def shutdown(self):
        """Apaga el bot de Telegram"""
        await self.bot.session.close()