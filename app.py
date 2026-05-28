from datetime import datetime
import webbrowser
from flask import Flask, render_template, request, redirect, session, send_file
from numpy import conj
from werkzeug.utils import secure_filename
import sqlite3
import os
import base64
import pandas as pd
from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
from datetime import datetime


app = Flask("Controle de Ferramentas")
app.config["KIT_SIGNATURE_FOLDER"] = "static/assinaturas_kits"
print("🔥 APP CARREGADO")
if not os.path.exists(app.config["KIT_SIGNATURE_FOLDER"]):
    os.makedirs(app.config["KIT_SIGNATURE_FOLDER"])
app.secret_key = "chave_secreta_ferramentas_123"
app.config["UPLOAD_FOLDER"] = "static/uploads"
app.config["SIGNATURE_FOLDER"] = "static/assinaturas"

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

if not os.path.exists(app.config["SIGNATURE_FOLDER"]):
    os.makedirs(app.config["SIGNATURE_FOLDER"])

def atualizar():
    raise NotImplementedError

def salvar():
    raise NotImplementedError

@app.route("/some_endpoint", methods=["GET", "POST"])
def some_endpoint():
    if request.method == "POST":
        salvar()
        atualizar()
        return redirect("/")  # Or appropriate response

    return render_template("some_template.html")  # Assuming template is a template name


def conectar():
    return sqlite3.connect("database.db")


def admin_logado():
    return "usuario" in session


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""

    if request.method == "POST":
        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            (usuario, senha)
        )
        user = cursor.fetchone()

        conn.close()

        if user:
            session["usuario"] = usuario
            return redirect("/")
        else:
            erro = "Usuário ou senha inválidos"

    return render_template("login.html", erro=erro)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def dashboard():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # TOTAL VEÍCULOS
    cursor.execute("""
        SELECT COUNT(*)
        FROM veiculos
    """)
    total_veiculos = cursor.fetchone()[0]

    # DISPONÍVEIS
    cursor.execute("""
        SELECT COUNT(*)
        FROM veiculos
        WHERE status = 'Disponível'
    """)
    disponiveis = cursor.fetchone()[0]

    # EM USO
    cursor.execute("""
        SELECT COUNT(*)
        FROM veiculos
        WHERE status = 'Em uso'
    """)
    em_uso = cursor.fetchone()[0]

    # MANUTENÇÃO
    cursor.execute("""
        SELECT COUNT(*)
        FROM veiculos
        WHERE status = 'Manutenção'
    """)
    manutencao = cursor.fetchone()[0]

    # DADOS DO GRÁFICO
    cursor.execute("""
        SELECT status, COUNT(*)
        FROM veiculos
        GROUP BY status
    """)

    dados_status = cursor.fetchall()

    labels_status = []
    valores_status = []

    for item in dados_status:
        labels_status.append(item[0])
        valores_status.append(item[1])

    conn.close()

    return render_template(
        "dashboard.html",

        total_veiculos=total_veiculos,
        disponiveis=disponiveis,
        em_uso=em_uso,
        manutencao=manutencao,

        labels_status=labels_status,
        valores_status=valores_status
    )
@app.route("/ferramentas")
def ferramentas():

    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM ferramentas
        ORDER BY id DESC
    """)

    ferramentas = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        ferramentas=ferramentas
    )
@app.route("/nova_ferramenta", methods=["GET", "POST"])
def nova_ferramenta():
    if not admin_logado():
        return redirect("/login")

    if request.method == "POST":
        nome = request.form["nome"]
        codigo = request.form["codigo"]

        nome_arquivo = ""

        if "foto" in request.files:
            foto = request.files["foto"]

            if foto and foto.filename != "":
                extensao = os.path.splitext(foto.filename)[1]
                nome_arquivo = secure_filename(f"{codigo}{extensao}")
                caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_arquivo)
                foto.save(caminho)

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO ferramentas (
            nome, codigo, status, tecnico, data_retirada, data_devolucao, foto, assinatura
        )
        VALUES (?, ?, 'Disponível', '', '', '', ?, '')
        """, (nome, codigo, nome_arquivo))

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("nova_ferramenta.html")


@app.route("/retirar/<int:id>", methods=["GET", "POST"])
def retirar(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        tecnico = request.form["tecnico"]
        assinatura_base64 = request.form.get("assinatura", "")
        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        if not assinatura_base64:
            conn.close()
            return "Assinatura obrigatória.", 400

        nome_assinatura = ""

        if assinatura_base64.startswith("data:image/png;base64,"):
            dados_imagem = assinatura_base64.split(",")[1]
            bytes_imagem = base64.b64decode(dados_imagem)

            nome_assinatura = f"assinatura_{id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            caminho_assinatura = os.path.join(app.config["SIGNATURE_FOLDER"], nome_assinatura)

            with open(caminho_assinatura, "wb") as f:
                f.write(bytes_imagem)
        else:
            conn.close()
            return "Formato de assinatura inválido.", 400

        cursor.execute("""
        UPDATE ferramentas
        SET status='Em uso',
            tecnico=?,
            data_retirada=?,
            data_devolucao='',
            assinatura=?
        WHERE id=?
        """, (tecnico, data, nome_assinatura, id))

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute("SELECT * FROM tecnicos")
    tecnicos = cursor.fetchall()

    conn.close()

    return render_template("retirar.html", id=id, tecnicos=tecnicos)


@app.route("/devolver/<int:id>")
def devolver(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    data = datetime.now().strftime("%d/%m/%Y %H:%M")

    cursor.execute("""
    SELECT nome, tecnico, data_retirada, assinatura
    FROM ferramentas
    WHERE id=?
    """, (id,))
    ferramenta = cursor.fetchone()

    if ferramenta:
        nome, tecnico, retirada, assinatura = ferramenta

        cursor.execute("""
        INSERT INTO historico (ferramenta, tecnico, data_retirada, data_devolucao, assinatura)
        VALUES (?, ?, ?, ?, ?)
        """, (nome, tecnico, retirada, data, assinatura))

        cursor.execute("""
        UPDATE ferramentas
        SET status='Disponível',
            tecnico='',
            data_retirada='',
            data_devolucao=?,
            assinatura=''
        WHERE id=?
        """, (data, id))

        conn.commit()

    conn.close()

    return redirect("/")


@app.route("/historico")
def historico():
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM historico ORDER BY id DESC")
    dados = cursor.fetchall()

    conn.close()

    return render_template("historico.html", historico=dados)


@app.route("/tecnicos", methods=["GET", "POST"])
def tecnicos():
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        cursor.execute("INSERT INTO tecnicos (nome) VALUES (?)", (nome,))
        conn.commit()

    cursor.execute("SELECT * FROM tecnicos")
    lista = cursor.fetchall()

    conn.close()

    return render_template("tecnicos.html", tecnicos=lista)


@app.route("/excluir_ferramenta/<int:id>")
def excluir_ferramenta(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT status FROM ferramentas WHERE id=?", (id,))
    ferramenta = cursor.fetchone()

    if ferramenta and ferramenta[0] == "Disponível":
        cursor.execute("DELETE FROM ferramentas WHERE id=?", (id,))
        conn.commit()

    conn.close()

    return redirect("/")


@app.route("/excluir_tecnico/<int:id>")
def excluir_tecnico(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM tecnicos WHERE id=?", (id,))
    conn.commit()

    conn.close()

    return redirect("/tecnicos")


@app.route("/editar_ferramenta/<int:id>", methods=["GET", "POST"])
def editar_ferramenta(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        codigo = request.form["codigo"]

        cursor.execute("""
        UPDATE ferramentas
        SET nome=?, codigo=?
        WHERE id=?
        """, (nome, codigo, id))

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute("SELECT * FROM ferramentas WHERE id=?", (id,))
    ferramenta = cursor.fetchone()

    conn.close()

    return render_template("editar_ferramenta.html", ferramenta=ferramenta)


@app.route("/editar_tecnico/<int:id>", methods=["GET", "POST"])
def editar_tecnico(id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]

        cursor.execute("UPDATE tecnicos SET nome=? WHERE id=?", (nome, id))
        conn.commit()
        conn.close()

        return redirect("/tecnicos")

    cursor.execute("SELECT * FROM tecnicos WHERE id=?", (id,))
    tecnico = cursor.fetchone()

    conn.close()

    return render_template("editar_tecnico.html", tecnico=tecnico)


@app.route("/alterar_senha", methods=["GET", "POST"])
def alterar_senha():
    if not admin_logado():
        return redirect("/login")

    mensagem = ""

    if request.method == "POST":
        senha_atual = request.form["senha_atual"]
        nova_senha = request.form["nova_senha"]

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario=? AND senha=?",
            ("admin", senha_atual)
        )
        user = cursor.fetchone()

        if user:
            cursor.execute(
                "UPDATE usuarios SET senha=? WHERE usuario='admin'",
                (nova_senha,)
            )
            conn.commit()
            mensagem = "Senha alterada com sucesso!"
        else:
            mensagem = "Senha atual incorreta!"

        conn.close()

    return render_template("alterar_senha.html", mensagem=mensagem)

@app.route("/kits")
def kits():
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT kits.id, kits.nome_kit, tecnicos.nome, kits.data_criacao, kits.status
    FROM kits
    INNER JOIN tecnicos ON kits.tecnico_id = tecnicos.id
    ORDER BY kits.id DESC
    """)
    lista_kits = cursor.fetchall()

    conn.close()

    return render_template("kits.html", kits=lista_kits)


@app.route("/novo_kit", methods=["GET", "POST"])
def novo_kit():
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        tecnico_id = request.form["tecnico_id"]
        nome_kit = request.form["nome_kit"]
        data_criacao = datetime.now().strftime("%d/%m/%Y %H:%M")
        status = "Ativo"

        cursor.execute("""
        INSERT INTO kits (tecnico_id, nome_kit, data_criacao, status)
        VALUES (?, ?, ?, ?)
        """, (tecnico_id, nome_kit, data_criacao, status))

        conn.commit()
        conn.close()

        return redirect("/kits")

    cursor.execute("SELECT * FROM tecnicos")
    tecnicos = cursor.fetchall()

    conn.close()

    return render_template("novo_kit.html", tecnicos=tecnicos)


@app.route("/kit/<int:kit_id>")
def ver_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT kits.id, kits.nome_kit, tecnicos.nome, kits.data_criacao, kits.status
    FROM kits
    INNER JOIN tecnicos ON kits.tecnico_id = tecnicos.id
    WHERE kits.id = ?
    """, (kit_id,))
    kit = cursor.fetchone()

    cursor.execute("""
    SELECT kit_itens.id, ferramentas.nome, ferramentas.codigo, kit_itens.quantidade,
           kit_itens.estado_inicial, kit_itens.observacao
    FROM kit_itens
    INNER JOIN ferramentas ON kit_itens.ferramenta_id = ferramentas.id
    WHERE kit_itens.kit_id = ?
    ORDER BY kit_itens.id DESC
    """, (kit_id,))
    itens = cursor.fetchall()

    conn.close()

    return render_template("ver_kit.html", kit=kit, itens=itens)


@app.route("/adicionar_item_kit/<int:kit_id>", methods=["GET", "POST"])
def adicionar_item_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        ferramentas_ids = request.form.getlist("ferramenta_id")
        estado_inicial = request.form["estado_inicial"]
        observacao = request.form["observacao"]

        for ferramenta_id in ferramentas_ids:
            quantidade = request.form.get(f"quantidade_{ferramenta_id}", "0")

            if quantidade and int(quantidade) > 0:
                cursor.execute("""
                INSERT INTO kit_itens (kit_id, ferramenta_id, quantidade, estado_inicial, observacao)
                VALUES (?, ?, ?, ?, ?)
                """, (kit_id, ferramenta_id, int(quantidade), estado_inicial, observacao))

        conn.commit()
        conn.close()

        return redirect(f"/kit/{kit_id}")

    cursor.execute("SELECT * FROM ferramentas ORDER BY nome")
    ferramentas = cursor.fetchall()

    conn.close()

    return render_template(
        "adicionar_item_kit.html",
        kit_id=kit_id,
        ferramentas=ferramentas
    )
@app.route("/editar_kit/<int:kit_id>", methods=["GET", "POST"])
def editar_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        nome_kit = request.form["nome_kit"]
        tecnico_id = request.form["tecnico_id"]
        status = request.form["status"]

        cursor.execute("""
        UPDATE kits
        SET nome_kit=?, tecnico_id=?, status=?
        WHERE id=?
        """, (nome_kit, tecnico_id, status, kit_id))

        conn.commit()
        conn.close()

        return redirect("/kits")

    cursor.execute("SELECT * FROM kits WHERE id=?", (kit_id,))
    kit = cursor.fetchone()

    cursor.execute("SELECT * FROM tecnicos ORDER BY nome")
    tecnicos = cursor.fetchall()

    conn.close()

    return render_template("editar_kit.html", kit=kit, tecnicos=tecnicos)


@app.route("/excluir_kit/<int:kit_id>")
def excluir_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM kit_itens WHERE kit_id=?", (kit_id,))
    cursor.execute("DELETE FROM kits WHERE id=?", (kit_id,))

    conn.commit()
    conn.close()

    return redirect("/kits")
@app.route("/editar_item_kit/<int:item_id>", methods=["GET", "POST"])
def editar_item_kit(item_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        ferramenta_id = request.form["ferramenta_id"]
        quantidade = request.form["quantidade"]
        estado_inicial = request.form["estado_inicial"]
        observacao = request.form["observacao"]

        cursor.execute("""
        UPDATE kit_itens
        SET ferramenta_id=?, quantidade=?, estado_inicial=?, observacao=?
        WHERE id=?
        """, (ferramenta_id, quantidade, estado_inicial, observacao, item_id))

        conn.commit()

        cursor.execute("SELECT kit_id FROM kit_itens WHERE id=?", (item_id,))
        kit_id = cursor.fetchone()[0]

        conn.close()
        return redirect(f"/kit/{kit_id}")

    cursor.execute("SELECT * FROM kit_itens WHERE id=?", (item_id,))
    item = cursor.fetchone()

    cursor.execute("SELECT * FROM ferramentas ORDER BY nome")
    ferramentas = cursor.fetchall()

    conn.close()

    return render_template("editar_item_kit.html", item=item, ferramentas=ferramentas)


@app.route("/excluir_item_kit/<int:item_id>")
def excluir_item_kit(item_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT kit_id FROM kit_itens WHERE id=?", (item_id,))
    resultado = cursor.fetchone()

    if not resultado:
        conn.close()
        return redirect("/kits")

    kit_id = resultado[0]

    cursor.execute("DELETE FROM kit_itens WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

    return redirect(f"/kit/{kit_id}")
@app.route("/importar_ferramentas", methods=["GET", "POST"])
def importar_ferramentas():
    if not admin_logado():
        return redirect("/login")

    mensagem = ""
    detalhes = []

    if request.method == "POST":
        arquivo = request.files.get("arquivo")

        if not arquivo or arquivo.filename == "":
            mensagem = "Selecione um arquivo para importar."
            return render_template("importar_ferramentas.html", mensagem=mensagem, detalhes=detalhes)

        nome_arquivo = arquivo.filename.lower()

        try:
            if nome_arquivo.endswith(".xlsx"):
                df = pd.read_excel(arquivo)
            elif nome_arquivo.endswith(".csv"):
                df = pd.read_csv(arquivo, encoding="utf-8")
            else:
                mensagem = "Formato inválido. Envie um arquivo .xlsx ou .csv"
                return render_template("importar_ferramentas.html", mensagem=mensagem, detalhes=detalhes)

            # Padronizar nomes das colunas
            df.columns = [col.strip().lower() for col in df.columns]

            if "nome" not in df.columns or "codigo" not in df.columns:
                mensagem = "A planilha precisa ter as colunas: nome e codigo"
                return render_template("importar_ferramentas.html", mensagem=mensagem, detalhes=detalhes)

            conn = conectar()
            cursor = conn.cursor()

            importados = 0
            ignorados = 0
            erros = 0

            for index, linha in df.iterrows():
                try:
                    nome = str(linha["nome"]).strip() if pd.notna(linha["nome"]) else ""
                    codigo = str(linha["codigo"]).strip() if pd.notna(linha["codigo"]) else ""

                    # Ignorar linhas vazias
                    if not nome or not codigo or nome.lower() == "nan" or codigo.lower() == "nan":
                        ignorados += 1
                        detalhes.append(f"Linha {index + 2}: ignorada por estar vazia ou incompleta.")
                        continue

                    # Verificar duplicidade no banco
                    cursor.execute("SELECT id FROM ferramentas WHERE codigo = ?", (codigo,))
                    existente = cursor.fetchone()

                    if existente:
                        ignorados += 1
                        detalhes.append(f"Linha {index + 2}: código '{codigo}' já existe e foi ignorado.")
                        continue

                    cursor.execute("""
                    INSERT INTO ferramentas (
                        nome, codigo, status, tecnico, data_retirada, data_devolucao, foto, assinatura
                    )
                    VALUES (?, ?, 'Disponível', '', '', '', '', '')
                    """, (nome, codigo))

                    importados += 1

                except Exception as e:
                    erros += 1
                    detalhes.append(f"Linha {index + 2}: erro ao importar ({str(e)}).")

            conn.commit()
            conn.close()

            mensagem = f"Importação finalizada. Importados: {importados} | Ignorados: {ignorados} | Erros: {erros}"

        except Exception as e:
            mensagem = f"Erro ao processar arquivo: {str(e)}"

    return render_template("importar_ferramentas.html", mensagem=mensagem, detalhes=detalhes)
@app.route("/relatorio_entrega_kit/<int:kit_id>", methods=["GET", "POST"])
def relatorio_entrega_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":
        assinatura_tecnico_base64 = request.form.get("assinatura_tecnico", "")
        assinatura_responsavel_base64 = request.form.get("assinatura_responsavel", "")
        data_entrega = datetime.now().strftime("%d/%m/%Y %H:%M")

        nome_ass_tecnico = ""
        nome_ass_responsavel = ""

        if assinatura_tecnico_base64.startswith("data:image/png;base64,"):
            dados = assinatura_tecnico_base64.split(",")[1]
            img_bytes = base64.b64decode(dados)
            nome_ass_tecnico = f"kit_{kit_id}_tecnico_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            caminho = os.path.join(app.config["KIT_SIGNATURE_FOLDER"], nome_ass_tecnico)
            with open(caminho, "wb") as f:
                f.write(img_bytes)

        if assinatura_responsavel_base64.startswith("data:image/png;base64,"):
            dados = assinatura_responsavel_base64.split(",")[1]
            img_bytes = base64.b64decode(dados)
            nome_ass_responsavel = f"kit_{kit_id}_responsavel_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            caminho = os.path.join(app.config["KIT_SIGNATURE_FOLDER"], nome_ass_responsavel)
            with open(caminho, "wb") as f:
                f.write(img_bytes)

        cursor.execute("""
        UPDATE kits
        SET data_entrega=?,
            assinatura_tecnico=?,
            assinatura_responsavel=?,
            status='Entregue'
        WHERE id=?
        """, (data_entrega, nome_ass_tecnico, nome_ass_responsavel, kit_id))

        conn.commit()
        conn.close()

        return redirect(f"/kit/{kit_id}")

    cursor.execute("""
    SELECT kits.id, kits.nome_kit, tecnicos.nome, kits.data_criacao, kits.status,
           kits.data_entrega, kits.assinatura_tecnico, kits.assinatura_responsavel
    FROM kits
    INNER JOIN tecnicos ON kits.tecnico_id = tecnicos.id
    WHERE kits.id = ?
    """, (kit_id,))
    kit = cursor.fetchone()

    cursor.execute("""
    SELECT kit_itens.id, ferramentas.nome, ferramentas.codigo, kit_itens.quantidade,
           kit_itens.estado_inicial, kit_itens.observacao
    FROM kit_itens
    INNER JOIN ferramentas ON kit_itens.ferramenta_id = ferramentas.id
    WHERE kit_itens.kit_id = ?
    ORDER BY ferramentas.nome
    """, (kit_id,))
    itens = cursor.fetchall()

    conn.close()

    return render_template("relatorio_entrega_kit.html", kit=kit, itens=itens)
@app.route("/baixar_relatorio_kit/<int:kit_id>")
def baixar_relatorio_kit(kit_id):
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT kits.id, kits.nome_kit, tecnicos.nome, kits.data_criacao, kits.status,
           kits.data_entrega, kits.assinatura_tecnico, kits.assinatura_responsavel
    FROM kits
    INNER JOIN tecnicos ON kits.tecnico_id = tecnicos.id
    WHERE kits.id = ?
    """, (kit_id,))
    kit = cursor.fetchone()

    cursor.execute("""
    SELECT ferramentas.nome, ferramentas.codigo, kit_itens.quantidade,
           kit_itens.estado_inicial, kit_itens.observacao
    FROM kit_itens
    INNER JOIN ferramentas ON kit_itens.ferramenta_id = ferramentas.id
    WHERE kit_itens.kit_id = ?
    ORDER BY ferramentas.nome
    """, (kit_id,))
    itens = cursor.fetchall()

    conn.close()

    if not kit:
        return "Kit não encontrado.", 404

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    largura, altura = A4

    y = altura - 40

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Relatório de Entrega do Kit")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, f"ID do Kit: {kit[0]}")
    y -= 18
    pdf.drawString(40, y, f"Nome do Kit: {kit[1]}")
    y -= 18
    pdf.drawString(40, y, f"Técnico: {kit[2]}")
    y -= 18
    pdf.drawString(40, y, f"Data de Criação: {kit[3]}")
    y -= 18
    pdf.drawString(40, y, f"Status: {kit[4]}")
    y -= 18
    pdf.drawString(40, y, f"Data de Entrega: {kit[5] if kit[5] else ''}")
    y -= 30

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Ferramenta")
    pdf.drawString(220, y, "Código")
    pdf.drawString(300, y, "Qtd")
    pdf.drawString(340, y, "Estado")
    pdf.drawString(430, y, "Observação")
    y -= 15

    pdf.setFont("Helvetica", 10)

    for item in itens:
        if y < 120:
            pdf.showPage()
            y = altura - 40

        ferramenta = str(item[0])[:28]
        codigo = str(item[1])[:12]
        quantidade = str(item[2])
        estado = str(item[3])[:12]
        observacao = str(item[4])[:22] if item[4] else ""

        pdf.drawString(40, y, ferramenta)
        pdf.drawString(220, y, codigo)
        pdf.drawString(300, y, quantidade)
        pdf.drawString(340, y, estado)
        pdf.drawString(430, y, observacao)
        y -= 15

    y -= 25

    # Assinatura do técnico
    if kit[6]:
        caminho_tecnico = os.path.join(app.config["KIT_SIGNATURE_FOLDER"], kit[6])
        if os.path.exists(caminho_tecnico):
            try:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(40, y, "Assinatura do Técnico")
                y -= 10
                pdf.drawImage(ImageReader(caminho_tecnico), 40, y - 80, width=180, height=80, preserveAspectRatio=True, mask='auto')
            except:
                pass

    # Assinatura do responsável
    if kit[7]:
        caminho_resp = os.path.join(app.config["KIT_SIGNATURE_FOLDER"], kit[7])
        if os.path.exists(caminho_resp):
            try:
                pdf.setFont("Helvetica-Bold", 11)
                pdf.drawString(300, y + 10, "Assinatura do Responsável")
                pdf.drawImage(ImageReader(caminho_resp), 300, y - 80, width=180, height=80, preserveAspectRatio=True, mask='auto')
            except:
                pass

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"relatorio_kit_{kit_id}.pdf",
        mimetype="application/pdf"
    )
# TODAS AS ROTAS AQUI EM CIMA

@app.route("/veiculos")
def veiculos():
    if not admin_logado():
        return redirect("/login")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome, placa, status, condutor FROM veiculos")
    lista = cursor.fetchall()

    conn.close()

    return render_template("veiculos.html", veiculos=lista)

@app.route("/checklist/<int:veiculo_id>/<tipo>", methods=["GET", "POST"])
def checklist(veiculo_id, tipo):

    conn = conectar()
    cursor = conn.cursor()

    if request.method == "POST":

        # DADOS

        condutor = request.form["condutor"]
        km = request.form["km"]
        observacoes = request.form["observacoes"]

        # CHECKBOXES

        macaco = "OK" if request.form.get("macaco") else "NÃO"
        estepe = "OK" if request.form.get("estepe") else "NÃO"
        chave_roda = "OK" if request.form.get("chave_roda") else "NÃO"
        farois = "OK" if request.form.get("farois") else "NÃO"
        oleo = "OK" if request.form.get("oleo") else "NÃO"
        agua = "OK" if request.form.get("agua") else "NÃO"
        documentos = "OK" if request.form.get("documentos") else "NÃO"
        pneus = "OK" if request.form.get("pneus") else "NÃO"

        data = datetime.now().strftime("%d/%m/%Y %H:%M")

        # SALVA CHECKLIST

        cursor.execute("""
            INSERT INTO checklist (
                veiculo_id,
                tecnico,
                tipo,
                km,
                observacoes,
                data,
                macaco,
                estepe,
                chave_roda,
                farois,
                oleo,
                agua,
                documentos,
                pneus
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            veiculo_id,
            condutor,
            tipo,
            km,
            observacoes,
            data,
            macaco,
            estepe,
            chave_roda,
            farois,
            oleo,
            agua,
            documentos,
            pneus
        ))

        # DEFINE STATUS

        if tipo == "retirada":
            status_veiculo = "Em uso"
        else:
            status_veiculo = "Disponível"
            condutor = ""

        # ATUALIZA VEÍCULO

        cursor.execute("""
            UPDATE veiculos
            SET status = ?,
                condutor = ?
            WHERE id = ?
        """, (
            status_veiculo,
            condutor,
            veiculo_id
        ))

        conn.commit()
        conn.close()

        return redirect("/veiculos")

    return render_template(
        "checklist.html",
        veiculo_id=veiculo_id,
        tipo=tipo
    )

@app.route("/checklist")
def lista_checklist():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, v.nome 
        FROM checklist c
        JOIN veiculos v ON v.id = c.veiculo_id
        ORDER BY c.id DESC
    """)

    dados = cursor.fetchall()
    conn.close()

    lista = []

    for d in dados:
        itens = [
            d[7], d[8], d[9], d[10],
            d[11], d[12], d[13], d[14]
        ]

        ok = sum(1 for i in itens if i == "OK")
        problema = sum(1 for i in itens if i != "OK")

        lista.append({
            "id": d[0],
            "veiculo": d[-1],
            "tecnico": d[2],
            "tipo": d[3],
            "km": d[4],
            "data": d[6],
            "ok": ok,
            "problema": problema
        })

    return render_template("lista_checklist.html", lista=lista)


@app.route("/relatorio_excel")
def relatorio_excel():

    conn = conectar()

    df = pd.read_sql_query("""
        SELECT c.*, v.nome, v.placa
        FROM checklist c
        JOIN veiculos v ON c.veiculo_id = v.id
    """, conn)

    conn.close()

    caminho = "relatorio_checklist.xlsx"
    df.to_excel(caminho, index=False)

    return send_file(caminho, as_attachment=True)

@app.route("/retirar_veiculo/<int:veiculo_id>")
def retirar_veiculo(veiculo_id):
    return redirect(f"/checklist/{veiculo_id}/retirada")
def gerar_pdf_checklist(dados):
    nome_arquivo = f"static/checklists/checklist_{dados['veiculo_id']}.pdf"

    c = canvas.Canvas(nome_arquivo, pagesize=A4)

    c.setFont("Helvetica", 12)

    c.drawString(50, 800, "CHECKLIST DE VEÍCULO")
    c.drawString(50, 770, f"Técnico: {dados['tecnico']}")
    c.drawString(50, 750, f"KM: {dados['km']}")
    c.drawString(50, 730, f"Data: {dados['data']}")

    c.drawString(50, 700, "Itens:")

    y = 680

    itens = [
        ("Macaco", dados['macaco']),
        ("Estepe", dados['estepe']),
        ("Chave de roda", dados['chave_roda']),
        ("Faróis", dados['farois']),
        ("Óleo", dados['oleo']),
        ("Água", dados['agua']),
        ("Documentos", dados['documentos']),
        ("Pneus", dados['pneus'])
    ]

    for nome, valor in itens:
        status = "OK" if valor == 1 else "NÃO"
        c.drawString(50, y, f"{nome}: {status}")
        y -= 20

    c.drawString(50, y-10, "Observações:")
    c.drawString(50, y-30, dados['observacoes'])

    c.save()

    return nome_arquivo
@app.route("/enviar_manutencao/<int:id>")
def enviar_manutencao(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE veiculos 
        SET status = 'Manutenção'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/veiculos")
@app.route("/finalizar_manutencao/<int:id>")
def finalizar_manutencao(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE veiculos 
        SET status = 'Disponível'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/veiculos")

@app.route("/checklist_detalhe/<int:id>")
def checklist_detalhe(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT c.*, v.nome
        FROM checklist c
        JOIN veiculos v ON v.id = c.veiculo_id
        WHERE c.id = ?
    """, (id,))

    d = cursor.fetchone()
    conn.close()

    checklist = {
        "id": d[0],
        "veiculo": d[-1],
        "tecnico": d[2],
        "tipo": d[3],
        "km": d[4],
        "observacoes": d[5],
        "data": d[6],
        "macaco": d[7],
        "estepe": d[8],
        "chave_roda": d[9],
        "farois": d[10],
        "oleo": d[11],
        "agua": d[12],
        "documentos": d[13],
        "pneus": d[14],
    }

    return render_template("checklist_detalhe.html", c=checklist)
@app.route("/deletar_checklist/<int:id>")
def deletar_checklist(id):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM checklist WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/checklist")
@app.route("/relatorios")
def relatorios():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # GASTOS DETALHADOS
    cursor.execute("""

        SELECT
            v.nome,
            v.placa,
            m.descricao,
            m.valor,
            m.data,
            m.pagamento,
            m.id

        FROM manutencoes m

        JOIN veiculos v
            ON v.id = m.veiculo_id

        ORDER BY m.id DESC

    """)

    gastos_detalhados = cursor.fetchall()

    # TOTAL GASTO
    total_gasto = 0

    for item in gastos_detalhados:

        if item[3]:

            total_gasto += float(item[3])

    # GASTOS POR VEÍCULO
    gastos_veiculos = cursor.execute("""

        SELECT
            veiculos.nome,
            veiculos.placa,
            COALESCE(SUM(manutencoes.valor), 0)

        FROM veiculos

        LEFT JOIN manutencoes
            ON manutencoes.veiculo_id = veiculos.id

        GROUP BY veiculos.id

    """).fetchall()

    # DADOS DO GRÁFICO
    labels_gastos = []
    valores_gastos = []

    for g in gastos_detalhados:

        labels_gastos.append(f"{g[0]} - {g[1]}")

        try:
            valor = float(g[3] or 0)

        except:
            valor = 0

        valores_gastos.append(valor)

    conn.close()

    return render_template(

        "relatorios.html",

        gastos_veiculos=gastos_veiculos,
        gastos_detalhados=gastos_detalhados,

        labels_gastos=labels_gastos,
        valores_gastos=valores_gastos,

        total_gasto=total_gasto

    )
@app.route("/manutencao/<int:id>", methods=["GET", "POST"])
def visualizar_manutencao(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""

        SELECT
            v.nome,
            v.placa,
            m.descricao,
            m.valor,
            m.data,
            m.pagamento

        FROM manutencoes m

        JOIN veiculos v
            ON v.id = m.veiculo_id

        WHERE m.id = ?

    """, (id,))

    manutencao = cursor.fetchone()

    conn.close()

    return render_template(
        "manutencao.html",
        manutencao=manutencao
    )
@app.route("/excluir_manutencao/<int:id>")
def excluir_manutencao(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM manutencoes
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/relatorios")
@app.route("/editar_manutencao/<int:id>", methods=["GET", "POST"])
def editar_manutencao(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = request.form["valor"]

        cursor.execute("""
            UPDATE manutencoes
            SET descricao=?, valor=?
            WHERE id=?
        """, (
            descricao,
            valor,
            id
        ))

        conn.commit()

        return redirect("/relatorios")

    cursor.execute("""
        SELECT id, descricao, valor
        FROM manutencoes
        WHERE id=?
    """, (id,))

    manutencao = cursor.fetchone()

    conn.close()

    return render_template(
        "editar_manutencao.html",
        manutencao=manutencao
    )
@app.route("/pagar_manutencao/<int:id>")
def pagar_manutencao(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE manutencoes
        SET pagamento = 'Pago'
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/relatorios")
@app.route("/nova_manutencao/<int:veiculo_id>", methods=["GET", "POST"])
def nova_manutencao(veiculo_id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        descricao = request.form["descricao"]
        valor = request.form["valor"]

        cursor.execute("""

            INSERT INTO manutencoes (
                veiculo_id,
                descricao,
                valor,
                data,
                pagamento
            )

            VALUES (?, ?, ?, datetime('now'), ?)

        """, (
            veiculo_id,
            descricao,
            valor,
            "Pendente"
        ))

        conn.commit()

        conn.close()

        return redirect("/relatorios")

    return render_template(
        "manutencao.html"
    )
@app.route("/editar_veiculo/<int:id>", methods=["GET", "POST"])
def editar_veiculo(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        nome = request.form["nome"]
        placa = request.form["placa"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE veiculos
            SET nome = ?, placa = ?, status = ?
            WHERE id = ?
        """, (nome, placa, status, id))

        conn.commit()
        conn.close()

        return redirect("/veiculos")

    cursor.execute("""
        SELECT * FROM veiculos
        WHERE id = ?
    """, (id,))

    veiculo = cursor.fetchone()

    conn.close()

    return render_template(
        "editar_veiculo.html",
        veiculo=veiculo
    )
@app.route("/excluir_veiculo/<int:id>")
def excluir_veiculo(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM veiculos
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/veiculos")
@app.route("/pagar/<int:id>")
def pagar(id):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""

        UPDATE manutencoes
        SET pagamento = 'Pago'
        WHERE id = ?

    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/relatorios")  

# 🔥 SEMPRE ÚLTIMA PARTE DO ARQUIVO
if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        webbrowser.open("http://127.0.0.1:5000")

    app.run(
    host="0.0.0.0",
    port=5000,
    debug=True
)

