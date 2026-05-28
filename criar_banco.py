import sqlite3

# =========================
# CONEXÃO
# =========================
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# =========================
# USUÁRIOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT
)
""")

# ADMIN PADRÃO
cursor.execute("""
INSERT OR IGNORE INTO usuarios (usuario, senha)
VALUES ('admin', '123')
""")

# =========================
# FERRAMENTAS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS ferramentas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    codigo TEXT UNIQUE,
    status TEXT,
    tecnico TEXT,
    data_retirada TEXT,
    data_devolucao TEXT,
    foto TEXT,
    assinatura TEXT
)
""")

# =========================
# TÉCNICOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS tecnicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT
)
""")

# =========================
# HISTÓRICO
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ferramenta TEXT,
    tecnico TEXT,
    data_retirada TEXT,
    data_devolucao TEXT,
    assinatura TEXT
)
""")

# =========================
# KITS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS kits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tecnico_id INTEGER,
    nome_kit TEXT,
    data_criacao TEXT,
    status TEXT,
    data_entrega TEXT,
    assinatura_tecnico TEXT,
    assinatura_responsavel TEXT
)
""")

# =========================
# ITENS DOS KITS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS kit_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kit_id INTEGER,
    ferramenta_id INTEGER,
    quantidade INTEGER,
    estado_inicial TEXT,
    observacao TEXT
)
""")

# =========================
# VEÍCULOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT,
    placa TEXT,
    status TEXT,
    km_atual TEXT
)
""")

# =========================
# CHECKLIST
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS checklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER,
    tecnico TEXT,
    tipo TEXT,
    km TEXT,
    observacoes TEXT,
    data TEXT,

    macaco TEXT,
    estepe TEXT,
    chave_roda TEXT,
    farois TEXT,
    oleo TEXT,
    agua TEXT,
    documentos TEXT,
    pneus TEXT
)
""")

# =========================
# MANUTENÇÕES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS manutencoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER,
    descricao TEXT,
    valor REAL,
    data TEXT,
    status TEXT DEFAULT 'Pendente'
)
""")

# =========================
# ADICIONAR COLUNA STATUS
# CASO O BANCO JÁ EXISTA
# =========================
try:
    cursor.execute("""
        ALTER TABLE manutencoes
        ADD COLUMN status TEXT DEFAULT 'Pendente'
    """)
    print("Coluna status criada!")
except:
    print("Coluna status já existe")

# =========================
# ADICIONAR CONDUTOR
# =========================
try:
    cursor.execute("""
        ALTER TABLE veiculos
        ADD COLUMN condutor TEXT
    """)
    print("Coluna condutor criada!")
except:
    print("Coluna condutor já existe")

# =========================
# SALVAR
# =========================
conn.commit()

# =========================
# FECHAR
# =========================
conn.close()

print("Banco criado com sucesso!")