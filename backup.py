import shutil
from datetime import datetime

origem = "database.db"
destino = f"backups/backup_{datetime.now().strftime('%Y%m%d_%H%M')}.db"

shutil.copy(origem, destino)

print("Backup criado com sucesso!")