#!/bin/bash
# scripts/init_bot.sh
# Script de inicialización segura del bot

echo "🚀 Inicializando OrcaBot - Configuración Segura"
echo "=============================================="

# Verificar que .env existe
if [ ! -f ".env" ]; then
    echo "❌ Archivo .env no encontrado"
    echo "Creando template desde .env.example..."
    cp .env.example .env
    echo "⚠️  Por favor, edita el archivo .env con tus credenciales"
    exit 1
fi

# Cargar variables de entorno
source .env

# Verificar variables críticas
if [ -z "$PHANTOM_PRIVATE_KEY_BYTES" ]; then
    echo "❌ PHANTOM_PRIVATE_KEY_BYTES no configurado en .env"
    exit 1
fi

if [ -z "$ENCRYPTION_PASSWORD" ]; then
    echo "❌ ENCRYPTION_PASSWORD no configurado"
    exit 1
fi

# Encriptar clave privada
echo "🔐 Encriptando clave privada..."
python scripts/encrypt_key.py

# Verificar encriptación
if [ $? -eq 0 ]; then
    echo "✅ Clave privada encriptada exitosamente"
    
    # Opcional: Eliminar clave en texto plano
    read -p "¿Eliminar clave privada en texto plano del .env? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i '/^PHANTOM_PRIVATE_KEY_BYTES=/d' .env
        echo "✅ Clave en texto plano eliminada"
    fi
else
    echo "❌ Error encriptando clave privada"
    exit 1
fi

# Crear estructura de directorios
echo "📁 Creando estructura de directorios..."
python -c "from config import Config; Config.setup_directories()"

# Verificar permisos
echo "🔒 Configurando permisos..."
chmod 600 .env
chmod 700 scripts/
chmod 600 config.py

echo "🎉 Configuración completada exitosamente!"
echo "Para iniciar el bot: python main.py"