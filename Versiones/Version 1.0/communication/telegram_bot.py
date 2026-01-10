# communication/telegram_bot.py
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import pandas as pd
from pathlib import Path
import json

class TradingTelegramBot:
    def __init__(self, token: str, trading_engine):
        self.token = token
        self.trading_engine = trading_engine
        self.app = Application.builder().token(token).build()
        
        self._setup_commands()
    
    def _setup_commands(self):
        commands = [
            BotCommand("status", "Auditoría instantánea de wallet y operaciones"),
            BotCommand("historico", "Verificación de archivos históricos"),
            BotCommand("panic_sell", "Venta de emergencia a USDC"),
            BotCommand("ayuda", "Manual rápido de comandos"),
            BotCommand("portfolio", "Desglose detallado del portfolio"),
            BotCommand("metrics", "Métricas de rendimiento del bot"),
            BotCommand("pools", "Top 10 pools activos analizados"),
            BotCommand("pause", "Pausar trading temporalmente"),
            BotCommand("resume", "Reanudar trading"),
            BotCommand("adjust_risk", "Ajustar parámetros de riesgo"),
            BotCommand("simulate", "Ejecutar simulación con datos históricos"),
        ]
        
        self.app.bot.set_my_commands(commands)
        
        # Handlers
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(CommandHandler("historico", self.historico_command))
        self.app.add_handler(CommandHandler("panic_sell", self.panic_sell_command))
        self.app.add_handler(CommandHandler("ayuda", self.ayuda_command))
        self.app.add_handler(CommandHandler("portfolio", self.portfolio_command))
        self.app.add_handler(CommandHandler("metrics", self.metrics_command))
        self.app.add_handler(CommandHandler("pools", self.pools_command))
        self.app.add_handler(CommandHandler("pause", self.pause_command))
        self.app.add_handler(CommandHandler("resume", self.resume_command))
        self.app.add_handler(CommandHandler("adjust_risk", self.adjust_risk_command))
        self.app.add_handler(CommandHandler("simulate", self.simulate_command))
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status mejorado"""
        try:
            # Obtener saldos en tiempo real
            balances = await self.trading_engine.get_wallet_balances()
            active_trades = self.trading_engine.get_active_trades()
            bot_status = self.trading_engine.get_bot_status()
            
            message = "🔍 **AUDITORÍA INSTANTÁNEA**\n\n"
            message += f"🟢 Estado: {bot_status['state']}\n"
            message += f"⏰ Última actualización: {bot_status['last_update']}\n\n"
            
            message += "💰 **SALDOS WALLET**\n"
            for token, balance in balances.items():
                message += f"• {token}: {balance:.4f}\n"
            
            message += f"\n📊 **CAPITAL TOTAL:** ${bot_status['total_value']:.2f}\n"
            message += f"📈 **PNL 24h:** {bot_status['daily_pnl']:.2%}\n"
            
            if active_trades:
                message += "\n🔄 **OPERACIONES ACTIVAS**\n"
                for trade in active_trades:
                    message += f"• {trade['pair']}: {trade['side']} {trade['amount']:.4f}"
                    message += f" @ ${trade['entry']:.4f} (SL: ${trade['stop_loss']:.4f})\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error en auditoría: {str(e)}")
    
    async def panic_sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando de emergencia con confirmación"""
        try:
            confirm_message = "⚠️ **PROTOCOLO DE EMERGENCIA** ⚠️\n\n"
            confirm_message += "¿Está seguro de ejecutar PANIC SELL?\n"
            confirm_message += "Esto venderá TODAS las posiciones a USDC.\n\n"
            confirm_message += "Escriba 'CONFIRMAR PANIC' para proceder."
            
            await update.message.reply_text(confirm_message, parse_mode='Markdown')
            
            # Esperar confirmación
            def check_confirmation(update):
                return update.message.text == "CONFIRMAR PANIC"
            
            # Implementar lógica de confirmación...
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error en protocolo de emergencia: {str(e)}")
    
    async def metrics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Métricas avanzadas de rendimiento"""
        metrics = self.trading_engine.get_performance_metrics()
        
        message = "📊 **MÉTRICAS DE RENDIMIENTO**\n\n"
        message += f"🎯 Precisión ML: {metrics['ml_accuracy']:.2%}\n"
        message += f"📈 Win Rate: {metrics['win_rate']:.2%}\n"
        message += f"💰 Profit Factor: {metrics['profit_factor']:.2f}\n"
        message += f"📉 Máximo Drawdown: {metrics['max_drawdown']:.2%}\n"
        message += f"⚡ Sharpe Ratio: {metrics['sharpe_ratio']:.2f}\n"
        message += f"🔢 Total Operaciones: {metrics['total_trades']}\n"
        message += f"🔄 Última Operación: {metrics['last_trade_result']}\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')