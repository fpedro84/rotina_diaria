import sqlite3
import os
from flask import g

DATABASE = os.path.join(os.path.dirname(__file__), 'instance', 'tea.db')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    cur = conn.cursor()

    cur.executescript('''
        -- Usuários (pais, terapeutas, educadores)
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT NOT NULL,
            email     TEXT UNIQUE NOT NULL,
            senha     TEXT NOT NULL,
            perfil    TEXT NOT NULL DEFAULT 'responsavel',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Crianças (dono = quem cadastrou)
        CREATE TABLE IF NOT EXISTS criancas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            nome           TEXT NOT NULL,
            idade          INTEGER,
            nivel_tea      TEXT DEFAULT 'Nível 1',
            observacoes    TEXT,
            foto           TEXT,
            avatar         TEXT,
            responsavel_id INTEGER NOT NULL,
            criado_em      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
        );

        -- Vínculo multiusuário: outros usuários vinculados a uma criança
        CREATE TABLE IF NOT EXISTS vinculos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            papel      TEXT NOT NULL DEFAULT 'visualizador',  -- visualizador | colaborador
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(crianca_id, usuario_id),
            FOREIGN KEY (crianca_id) REFERENCES criancas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        -- Convites por e-mail para vincular usuários
        CREATE TABLE IF NOT EXISTS convites (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id INTEGER NOT NULL,
            email      TEXT NOT NULL,
            papel      TEXT NOT NULL DEFAULT 'visualizador',
            token      TEXT NOT NULL UNIQUE,
            usado      INTEGER DEFAULT 0,
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crianca_id) REFERENCES criancas(id)
        );

        -- Itens de rotina
        CREATE TABLE IF NOT EXISTS rotina_itens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id INTEGER NOT NULL,
            titulo     TEXT NOT NULL,
            descricao  TEXT,
            horario    TEXT,
            icone      TEXT DEFAULT '⭐',
            ordem      INTEGER DEFAULT 0,
            ativo      INTEGER DEFAULT 1,
            FOREIGN KEY (crianca_id) REFERENCES criancas(id)
        );

        -- Registros de evolução diária
        CREATE TABLE IF NOT EXISTS registros_evolucao (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id    INTEGER NOT NULL,
            item_id       INTEGER NOT NULL,
            data          TEXT NOT NULL,
            concluido     INTEGER DEFAULT 0,
            registrado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crianca_id) REFERENCES criancas(id),
            FOREIGN KEY (item_id)    REFERENCES rotina_itens(id)
        );

        -- Observações compartilhadas entre todos os vinculados
        CREATE TABLE IF NOT EXISTS observacoes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            texto      TEXT NOT NULL,
            criado_em  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crianca_id) REFERENCES criancas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );
    ''')

    # ── Dados demo ────────────────────────────────────────────────
    existente = cur.execute("SELECT id FROM usuarios WHERE email='demo@tea.com'").fetchone()
    if not existente:
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
            ('Maria (Responsável)', 'demo@tea.com', '1234', 'responsavel')
        )
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
            ('Dr. Carlos (Terapeuta)', 'terapeuta@tea.com', '1234', 'terapeuta')
        )
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (?, ?, ?, ?)",
            ('Profa. Ana (Educadora)', 'escola@tea.com', '1234', 'educador')
        )
        cur.execute(
            "INSERT INTO criancas (nome, idade, nivel_tea, observacoes, responsavel_id) VALUES (?, ?, ?, ?, 1)",
            ('Lucas', 7, 'Nível 2', 'Gosta de música e cores vibrantes.')
        )
        # Vincular terapeuta e educadora à criança Lucas (id=1)
        cur.execute(
            "INSERT INTO vinculos (crianca_id, usuario_id, papel) VALUES (1, 2, 'colaborador')"
        )
        cur.execute(
            "INSERT INTO vinculos (crianca_id, usuario_id, papel) VALUES (1, 3, 'visualizador')"
        )
        # Observações demo
        cur.execute(
            "INSERT INTO observacoes (crianca_id, usuario_id, texto) VALUES (1, 1, 'Lucas teve um dia difícil hoje, ficou agitado após o almoço.')"
        )
        cur.execute(
            "INSERT INTO observacoes (crianca_id, usuario_id, texto) VALUES (1, 2, 'Na sessão de hoje ele respondeu bem aos estímulos visuais. Continuar usando cartões coloridos.')"
        )
        itens_demo = [
            (1,'Acordar','Hora de levantar da cama','07:00','🌅',1),
            (1,'Escovar os dentes','Escovação completa por 2 minutos','07:15','🦷',2),
            (1,'Café da manhã','Tomar o café da manhã','07:30','🥞',3),
            (1,'Tomar banho','Banho com sabonete e xampu','08:00','🚿',4),
            (1,'Ir para a escola','Pegar a mochila e ir para a escola','08:30','🎒',5),
            (1,'Lição de casa','Fazer a lição do dia','16:00','📚',6),
            (1,'Atividade livre','Brincar ou atividade de lazer','17:00','🎮',7),
            (1,'Jantar','Hora de jantar em família','19:00','🍽️',8),
            (1,'Escovar os dentes','Escovação noturna','20:30','🦷',9),
            (1,'Hora de dormir','Boa noite!','21:00','🌙',10),
        ]
        cur.executemany(
            'INSERT INTO rotina_itens (crianca_id,titulo,descricao,horario,icone,ordem) VALUES (?,?,?,?,?,?)',
            itens_demo
        )

    # Migration: adicionar colunas foto e avatar se não existirem
    cols = [row[1] for row in conn.execute("PRAGMA table_info(criancas)").fetchall()]
    if 'foto' not in cols:
        conn.execute("ALTER TABLE criancas ADD COLUMN foto TEXT")
        print("Migration: coluna foto adicionada")
    if 'avatar' not in cols:
        conn.execute("ALTER TABLE criancas ADD COLUMN avatar TEXT")
        print("Migration: coluna avatar adicionada")
    conn.commit()
    conn.close()

def ensure_lembretes(conn):
    """Migration: criar tabela lembretes se não existir."""
    tbls = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'lembretes' not in tbls:
        conn.execute('''CREATE TABLE lembretes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            crianca_id  INTEGER NOT NULL,
            titulo      TEXT NOT NULL,
            descricao   TEXT,
            data        TEXT NOT NULL,
            horario     TEXT NOT NULL,
            recorrencia TEXT DEFAULT 'nenhuma',
            concluido   INTEGER DEFAULT 0,
            criado_por  INTEGER NOT NULL,
            criado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (crianca_id) REFERENCES criancas(id),
            FOREIGN KEY (criado_por) REFERENCES usuarios(id)
        )''')
        conn.commit()
        print("Migration: tabela lembretes criada")
