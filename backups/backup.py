import shutil
import os
from datetime import datetime

# Nome do banco
BANCO = "database.db"

# Pasta de backup
PASTA_BACKUP = "backups"

# Criar pasta se não existir
if not os.path.exists(PASTA_BACKUP):
    os.makedirs(PASTA_BACKUP)

# Gerar nome com data e hora
agora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nome_backup = f"backup_{agora}.db"

# Caminho completo
destino = os.path.join(PASTA_BACKUP, nome_backup)

# Fazer cópia
try:
    shutil.copy2(BANCO, destino)
    print(f"Backup criado com sucesso: {destino}")
except Exception as e:
    print(f"Erro ao fazer backup: {e}")