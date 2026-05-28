import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

colunas = []

cursor.execute("PRAGMA table_info(kits)")
for coluna in cursor.fetchall():
    colunas.append(coluna[1])

if "data_entrega" not in colunas:
    cursor.execute("ALTER TABLE kits ADD COLUMN data_entrega TEXT")

if "assinatura_tecnico" not in colunas:
    cursor.execute("ALTER TABLE kits ADD COLUMN assinatura_tecnico TEXT")

if "assinatura_responsavel" not in colunas:
    cursor.execute("ALTER TABLE kits ADD COLUMN assinatura_responsavel TEXT")

conn.commit()
conn.close()

print("Tabela kits atualizada com sucesso!")