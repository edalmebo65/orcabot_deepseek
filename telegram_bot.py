#!/usr/bin/env python3
"""
Bot de Telegram para OrcaBot con comandos avanzados
"""
import asyncio
import logging
from typing import Optional, Dict, Any
import aiohttp

logger = logging.getLogger(__name__)

class TelegramBot:
    """Cliente de Telegram para notificaciones y comandos"""
    
    def __init__(self, token: str, chat_id: str, admin_id: str = ""):
        self.token = token
        self.chat_id = chat_id
        self.admin_id = admin_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = None
        self.is_configured = bool(token and chat_id)
        
        if self.is_configured:
            logger.info("Telegram bot configurado")
        else:
            logger.warning("Telegram no configurado - usando modo console")
    
    async def __aenter__(self):
        if self.is_configured:
            self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Envía mensaje al chat configurado"""
        if not self.is_configured:
            logger.info(f"Telegram (simulado): {text[:100]}...")
            return True
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"Mensaje enviado a Telegram: {text[:50]}...")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Error enviando a Telegram: {response.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Excepción enviando a Telegram: {e}")
            return False
    
    async def send_alert(self, alert_type: str, message: str) -> bool:
        """Envía alerta formateada"""
        emoji = {
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "info": "ℹ️",
            "buy": "📈",
            "sell": "📉"
        }.get(alert_type, "🔔")
        
        formatted_message = f"{emoji} {message}"
        return await self.send_message(formatted_message)
    
    async def send_admin_message(self, text: str) -> bool:
        """Envía mensaje solo al admin"""
        if not self.admin_id:
            return await self.send_message(f"👑 ADMIN: {text}")
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                "chat_id": self.admin_id,
                "text": text,
                "parse_mode": "HTML"
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(url, json=payload) as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error enviando mensaje admin: {e}")
            return False
    
    def is_configured(self) -> bool:
        """Verifica si Telegram está configurado"""
        return self.is_configured
    
    async def test_connection(self) -> bool:
        """Prueba la conexión con Telegram"""
        if not self.is_configured:
            return False
        
        try:
            url = f"{self.base_url}/getMe"
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        logger.info(f"Telegram bot conectado: @{data['result']['username']}")
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error probando conexión Telegram: {e}")
            return False