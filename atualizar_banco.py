import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

try:
    cursor.execute("""
        ALTER TABLE veiculos
        ADD COLUMN condutor TEXT
    """)

    print("Coluna condutor adicionada com sucesso!")

except Exception as e:
    print("Erro:", e)

conn.commit()
conn.close()