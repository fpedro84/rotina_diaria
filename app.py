from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from database import init_db, get_db, ensure_lembretes
from datetime import datetime, date
import secrets
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'tea_plataforma_secret_2026'


@app.template_filter('br_date')
def br_date_filter(data_str):
    """Converte YYYY-MM-DD para DD/MM/YYYY."""
    try:
        a, m, d = str(data_str).split('-')
        return f'{d}/{m}/{a}'
    except Exception:
        return data_str


@app.template_filter('days_until')
def days_until_filter(data_str):
    """Retorna quantos dias faltam para a data (str YYYY-MM-DD)."""
    try:
        from datetime import date
        alvo = date.fromisoformat(str(data_str))
        return (alvo - date.today()).days
    except Exception:
        return 99


UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 MB


def allowed_file(fname):
    return '.' in fname and fname.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def salvar_foto(file, crianca_id):
    if not file or file.filename == '':
        return None
    if not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    nome = f'crianca_{crianca_id}.{ext}'
    for e in ALLOWED_EXTENSIONS:
        old_path = os.path.join(UPLOAD_FOLDER, f'crianca_{crianca_id}.{e}')
        if os.path.exists(old_path) and e != ext:
            os.remove(old_path)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    file.save(os.path.join(UPLOAD_FOLDER, nome))
    return nome

# ── helpers ───────────────────────────────────────────────────────────────────


def criancas_do_usuario(uid):
    db = get_db()
    return db.execute(
        '''SELECT c.*, u.nome AS responsavel_nome,
                  CASE WHEN c.responsavel_id = ? THEN 'dono' ELSE v.papel END AS meu_papel
           FROM criancas c
           JOIN usuarios u ON u.id = c.responsavel_id
           LEFT JOIN vinculos v ON v.crianca_id = c.id AND v.usuario_id = ?
           WHERE c.responsavel_id = ? OR v.usuario_id = ?
           ORDER BY c.nome''',
        (uid, uid, uid, uid)
    ).fetchall()


def pode_editar(cid, uid):
    db = get_db()
    c = db.execute(
        'SELECT responsavel_id FROM criancas WHERE id=?', (cid,)).fetchone()
    if not c:
        return False
    if c['responsavel_id'] == uid:
        return True
    v = db.execute(
        'SELECT papel FROM vinculos WHERE crianca_id=? AND usuario_id=?', (cid, uid)).fetchone()
    return v and v['papel'] == 'colaborador'


def pode_ver(cid, uid):
    db = get_db()
    c = db.execute(
        'SELECT responsavel_id FROM criancas WHERE id=?', (cid,)).fetchone()
    if not c:
        return False
    if c['responsavel_id'] == uid:
        return True
    return bool(db.execute('SELECT 1 FROM vinculos WHERE crianca_id=? AND usuario_id=?', (cid, uid)).fetchone())

# ── autenticação ──────────────────────────────────────────────────────────────


@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'usuario_id' in session else url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        db = get_db()
        u = db.execute(
            'SELECT * FROM usuarios WHERE email=? AND senha=?', (email, senha)).fetchone()
        if u:
            session.update(
                usuario_id=u['id'], usuario_nome=u['nome'], usuario_perfil=u['perfil'])
            _aceitar_convites_pendentes(email, u['id'])
            return redirect(url_for('dashboard'))
        flash('E-mail ou senha inválidos.', 'erro')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        perfil = request.form['perfil']
        db = get_db()
        if db.execute('SELECT id FROM usuarios WHERE email=?', (email,)).fetchone():
            flash('E-mail já cadastrado.', 'erro')
        else:
            db.execute('INSERT INTO usuarios (nome,email,senha,perfil) VALUES (?,?,?,?)',
                       (nome, email, senha, perfil))
            db.commit()
            u = db.execute(
                'SELECT id FROM usuarios WHERE email=?', (email,)).fetchone()
            _aceitar_convites_pendentes(email, u['id'])
            flash('Cadastro realizado! Faça login.', 'sucesso')
            return redirect(url_for('login'))
    return render_template('cadastro.html')


def _aceitar_convites_pendentes(email, uid):
    db = get_db()
    convites = db.execute(
        'SELECT * FROM convites WHERE email=? AND usado=0', (email,)).fetchall()
    for conv in convites:
        if not db.execute('SELECT 1 FROM vinculos WHERE crianca_id=? AND usuario_id=?',
                          (conv['crianca_id'], uid)).fetchone():
            db.execute('INSERT INTO vinculos (crianca_id,usuario_id,papel) VALUES (?,?,?)',
                       (conv['crianca_id'], uid, conv['papel']))
        db.execute('UPDATE convites SET usado=1 WHERE id=?', (conv['id'],))
    db.commit()

# ── dashboard ─────────────────────────────────────────────────────────────────


@app.route('/dashboard')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    uid = session['usuario_id']
    criancas = criancas_do_usuario(uid)
    hoje = date.today().isoformat()
    db = get_db()
    stats = {}
    for c in criancas:
        total = db.execute(
            'SELECT COUNT(*) as t FROM rotina_itens WHERE crianca_id=?', (c['id'],)).fetchone()['t']
        conc = db.execute(
            'SELECT COUNT(*) as t FROM registros_evolucao WHERE crianca_id=? AND data=? AND concluido=1',
            (c['id'], hoje)).fetchone()['t']
        stats[c['id']] = {'total': total, 'concluidos': conc}
    return render_template('dashboard.html', criancas=criancas, stats=stats, hoje=hoje)

# ── crianças ──────────────────────────────────────────────────────────────────


@app.route('/criancas/nova', methods=['GET', 'POST'])
def nova_crianca():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO criancas (nome,idade,nivel_tea,observacoes,responsavel_id) VALUES (?,?,?,?,?)',
                   (request.form['nome'], request.form['idade'], request.form['nivel_tea'],
                    request.form.get('observacoes', ''), session['usuario_id']))
        db.commit()
        # foto — precisa do ID gerado
        nova = db.execute('SELECT id FROM criancas WHERE responsavel_id=? ORDER BY id DESC LIMIT 1',
                          (session['usuario_id'],)).fetchone()
        foto = request.files.get('foto')
        avatar = request.form.get('avatar', '')
        if foto and nova:
            nome_foto = salvar_foto(foto, nova['id'])
            if nome_foto:
                db.execute(
                    'UPDATE criancas SET foto=?, avatar=NULL WHERE id=?', (nome_foto, nova['id']))
                db.commit()
        elif avatar and nova:
            db.execute(
                'UPDATE criancas SET avatar=?, foto=NULL WHERE id=?', (avatar, nova['id']))
            db.commit()
        flash('Criança cadastrada com sucesso!', 'sucesso')
        return redirect(url_for('dashboard'))
    return render_template('nova_crianca.html')


@app.route('/criancas/<int:cid>')
def perfil_crianca(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    uid = session['usuario_id']
    if not pode_ver(cid, uid):
        flash('Acesso negado.', 'erro')
        return redirect(url_for('dashboard'))
    db = get_db()
    crianca = db.execute(
        'SELECT * FROM criancas WHERE id=?', (cid,)).fetchone()
    itens = db.execute(
        '''SELECT * FROM rotina_itens WHERE crianca_id=?
           ORDER BY CASE WHEN horario='' OR horario IS NULL THEN 1 ELSE 0 END,
                    horario ASC, ordem ASC''', (cid,)
    ).fetchall()
    hoje = date.today().isoformat()
    status_hoje = {r['item_id']: r['concluido'] for r in
                   db.execute('SELECT item_id,concluido FROM registros_evolucao WHERE crianca_id=? AND data=?',
                              (cid, hoje)).fetchall()}
    obs = db.execute(
        '''SELECT o.*, u.nome AS autor_nome, u.perfil AS autor_perfil
           FROM observacoes o JOIN usuarios u ON u.id=o.usuario_id
           WHERE o.crianca_id=? ORDER BY o.criado_em DESC''', (cid,)
    ).fetchall()
    equipe = db.execute(
        '''SELECT u.id, u.nome, u.perfil, v.papel, v.id AS vinculo_id
           FROM vinculos v JOIN usuarios u ON u.id=v.usuario_id
           WHERE v.crianca_id=?''', (cid,)
    ).fetchall()
    resp = db.execute(
        'SELECT id,nome,perfil FROM usuarios WHERE id=(SELECT responsavel_id FROM criancas WHERE id=?)', (
            cid,)
    ).fetchone()
    convites_pendentes = db.execute(
        'SELECT email,papel FROM convites WHERE crianca_id=? AND usado=0', (
            cid,)
    ).fetchall()
    # lembretes próximos (próximos 30 dias)
    from datetime import timedelta
    hoje_dt = date.today()
    limite = (hoje_dt + timedelta(days=30)).isoformat()
    try:
        lembretes = db.execute(
            '''SELECT l.*, u.nome AS criado_por_nome
               FROM lembretes l JOIN usuarios u ON u.id=l.criado_por
               WHERE l.crianca_id=? AND l.data >= ? AND l.data <= ? AND l.concluido=0
               ORDER BY l.data ASC, l.horario ASC''',
            (cid, hoje, limite)
        ).fetchall()
        lembretes_passados = db.execute(
            '''SELECT l.*, u.nome AS criado_por_nome
               FROM lembretes l JOIN usuarios u ON u.id=l.criado_por
               WHERE l.crianca_id=? AND (l.data < ? OR l.concluido=1)
               ORDER BY l.data DESC, l.horario DESC LIMIT 5''',
            (cid, hoje)
        ).fetchall()
    except Exception:
        lembretes = []
        lembretes_passados = []
    return render_template('perfil_crianca.html', crianca=crianca, itens=itens,
                           status_hoje=status_hoje, hoje=hoje, observacoes=obs,
                           equipe=equipe, responsavel=resp,
                           convites_pendentes=convites_pendentes,
                           pode_editar=pode_editar(cid, uid),
                           e_dono=(crianca['responsavel_id'] == uid),
                           lembretes=lembretes,
                           lembretes_passados=lembretes_passados)


@app.route('/criancas/<int:cid>/editar', methods=['GET', 'POST'])
def editar_crianca(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if not pode_editar(cid, session['usuario_id']):
        flash('Sem permissão para editar.', 'erro')
        return redirect(url_for('perfil_crianca', cid=cid))
    db = get_db()
    crianca = db.execute(
        'SELECT * FROM criancas WHERE id=?', (cid,)).fetchone()
    if request.method == 'POST':
        db.execute('UPDATE criancas SET nome=?,idade=?,nivel_tea=?,observacoes=? WHERE id=?',
                   (request.form['nome'], request.form['idade'], request.form['nivel_tea'],
                    request.form.get('observacoes', ''), cid))
        db.commit()
        foto = request.files.get('foto')
        avatar = request.form.get('avatar', '')
        if foto and foto.filename:
            nome_foto = salvar_foto(foto, cid)
            if nome_foto:
                db.execute(
                    'UPDATE criancas SET foto=?, avatar=NULL WHERE id=?', (nome_foto, cid))
                db.commit()
        elif avatar:
            # avatar escolhido: limpar foto anterior se houver
            crianca_atual = db.execute(
                'SELECT foto FROM criancas WHERE id=?', (cid,)).fetchone()
            if crianca_atual and crianca_atual['foto']:
                caminho = os.path.join(UPLOAD_FOLDER, crianca_atual['foto'])
                if os.path.exists(caminho):
                    os.remove(caminho)
            db.execute(
                'UPDATE criancas SET avatar=?, foto=NULL WHERE id=?', (avatar, cid))
            db.commit()
        elif request.form.get('remover_foto') == '1':
            crianca_atual = db.execute(
                'SELECT foto FROM criancas WHERE id=?', (cid,)).fetchone()
            if crianca_atual and crianca_atual['foto']:
                caminho = os.path.join(UPLOAD_FOLDER, crianca_atual['foto'])
                if os.path.exists(caminho):
                    os.remove(caminho)
            db.execute(
                'UPDATE criancas SET foto=NULL, avatar=NULL WHERE id=?', (cid,))
            db.commit()
        flash('Dados atualizados!', 'sucesso')
        return redirect(url_for('perfil_crianca', cid=cid))
    return render_template('editar_crianca.html', crianca=crianca)

# ── observações ───────────────────────────────────────────────────────────────


@app.route('/criancas/<int:cid>/observacao', methods=['POST'])
def nova_observacao(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    uid = session['usuario_id']
    if not pode_ver(cid, uid):
        flash('Acesso negado.', 'erro')
        return redirect(url_for('dashboard'))
    texto = request.form.get('texto', '').strip()
    if texto:
        db = get_db()
        db.execute(
            'INSERT INTO observacoes (crianca_id,usuario_id,texto) VALUES (?,?,?)', (cid, uid, texto))
        db.commit()
        flash('Observação registrada!', 'sucesso')
    return redirect(url_for('perfil_crianca', cid=cid) + '#observacoes')


@app.route('/observacao/<int:oid>/excluir', methods=['POST'])
def excluir_observacao(oid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    obs = db.execute('SELECT * FROM observacoes WHERE id=?', (oid,)).fetchone()
    if obs and obs['usuario_id'] == session['usuario_id']:
        cid = obs['crianca_id']
        db.execute('DELETE FROM observacoes WHERE id=?', (oid,))
        db.commit()
        flash('Observação removida.', 'sucesso')
        return redirect(url_for('perfil_crianca', cid=cid) + '#observacoes')
    return redirect(url_for('dashboard'))

# ── vínculos / convites ───────────────────────────────────────────────────────


@app.route('/criancas/<int:cid>/convidar', methods=['GET', 'POST'])
def convidar(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    uid = session['usuario_id']
    db = get_db()
    crianca = db.execute(
        'SELECT * FROM criancas WHERE id=? AND responsavel_id=?', (cid, uid)).fetchone()
    if not crianca:
        flash('Apenas o responsável pode convidar.', 'erro')
        return redirect(url_for('perfil_crianca', cid=cid))
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        papel = request.form['papel']
        alvo = db.execute(
            'SELECT id FROM usuarios WHERE email=?', (email,)).fetchone()
        if alvo:
            if alvo['id'] == uid:
                flash('Você já é o responsável.', 'erro')
            elif db.execute('SELECT 1 FROM vinculos WHERE crianca_id=? AND usuario_id=?', (cid, alvo['id'])).fetchone():
                flash('Usuário já vinculado.', 'erro')
            else:
                db.execute('INSERT INTO vinculos (crianca_id,usuario_id,papel) VALUES (?,?,?)',
                           (cid, alvo['id'], papel))
                db.commit()
                flash('Usuário vinculado!', 'sucesso')
                return redirect(url_for('perfil_crianca', cid=cid))
        else:
            token = secrets.token_urlsafe(20)
            db.execute('INSERT INTO convites (crianca_id,email,papel,token) VALUES (?,?,?,?)',
                       (cid, email, papel, token))
            db.commit()
            flash(
                f'Convite registrado para {email}. Ao se cadastrar, o acesso será liberado automaticamente.', 'sucesso')
            return redirect(url_for('perfil_crianca', cid=cid))
    return render_template('convidar.html', crianca=crianca)


@app.route('/vinculos/<int:vid>/remover', methods=['POST'])
def remover_vinculo(vid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    v = db.execute('SELECT * FROM vinculos WHERE id=?', (vid,)).fetchone()
    if v:
        c = db.execute('SELECT responsavel_id FROM criancas WHERE id=?',
                       (v['crianca_id'],)).fetchone()
        if c and c['responsavel_id'] == session['usuario_id']:
            cid = v['crianca_id']
            db.execute('DELETE FROM vinculos WHERE id=?', (vid,))
            db.commit()
            flash('Vínculo removido.', 'sucesso')
            return redirect(url_for('perfil_crianca', cid=cid))
    return redirect(url_for('dashboard'))

# ── rotina ────────────────────────────────────────────────────────────────────


@app.route('/criancas/<int:cid>/rotina/novo', methods=['GET', 'POST'])
def novo_item_rotina(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if not pode_editar(cid, session['usuario_id']):
        flash('Sem permissão.', 'erro')
        return redirect(url_for('perfil_crianca', cid=cid))
    if request.method == 'POST':
        db = get_db()
        horario = request.form.get('horario', '')
        m = db.execute(
            'SELECT COALESCE(MAX(ordem),0) as m FROM rotina_itens WHERE crianca_id=?', (cid,)).fetchone()['m']
        db.execute('INSERT INTO rotina_itens (crianca_id,titulo,descricao,horario,icone,ordem) VALUES (?,?,?,?,?,?)',
                   (cid, request.form['titulo'], request.form.get('descricao', ''),
                    horario, request.form.get('icone', '⭐'), m+1))
        db.commit()
        flash('Item adicionado à rotina!', 'sucesso')
        return redirect(url_for('perfil_crianca', cid=cid))
    return render_template('novo_item.html', crianca_id=cid)


@app.route('/rotina/item/<int:iid>/excluir', methods=['POST'])
def excluir_item(iid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    item = db.execute(
        'SELECT crianca_id FROM rotina_itens WHERE id=?', (iid,)).fetchone()
    if item and pode_editar(item['crianca_id'], session['usuario_id']):
        # apagar registros de evolução vinculados antes de apagar o item
        db.execute('DELETE FROM registros_evolucao WHERE item_id=?', (iid,))
        db.execute('DELETE FROM rotina_itens WHERE id=?', (iid,))
        db.commit()
    return redirect(url_for('perfil_crianca', cid=item['crianca_id']))

# ── evolução / API ────────────────────────────────────────────────────────────


@app.route('/api/registrar', methods=['POST'])
def registrar_atividade():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401
    data = request.get_json()
    cid, iid, conc = data['crianca_id'], data['item_id'], data['concluido']
    if not pode_ver(cid, session['usuario_id']):
        return jsonify({'erro': 'Negado'}), 403
    hoje = date.today().isoformat()
    db = get_db()
    ex = db.execute('SELECT id FROM registros_evolucao WHERE crianca_id=? AND item_id=? AND data=?',
                    (cid, iid, hoje)).fetchone()
    if ex:
        db.execute('UPDATE registros_evolucao SET concluido=? WHERE id=?',
                   (1 if conc else 0, ex['id']))
    else:
        db.execute('INSERT INTO registros_evolucao (crianca_id,item_id,data,concluido) VALUES (?,?,?,?)',
                   (cid, iid, hoje, 1 if conc else 0))
    db.commit()
    return jsonify({'ok': True})


@app.route('/api/evolucao/<int:cid>')
def api_evolucao(cid):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401
    if not pode_ver(cid, session['usuario_id']):
        return jsonify({'erro': 'Negado'}), 403
    db = get_db()
    dados = db.execute(
        'SELECT data, SUM(concluido) as concluidos, COUNT(id) as total FROM registros_evolucao WHERE crianca_id=? GROUP BY data ORDER BY data DESC LIMIT 30',
        (cid,)).fetchall()
    return jsonify([{'data': d['data'], 'concluidos': d['concluidos'], 'total': d['total']} for d in reversed(dados)])


@app.route('/criancas/<int:cid>/evolucao')
def evolucao(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if not pode_ver(cid, session['usuario_id']):
        flash('Acesso negado.', 'erro')
        return redirect(url_for('dashboard'))
    crianca = get_db().execute('SELECT * FROM criancas WHERE id=?', (cid,)).fetchone()
    return render_template('evolucao.html', crianca=crianca)


# ── lembretes ─────────────────────────────────────────────────────────────────

@app.route('/criancas/<int:cid>/lembretes/novo', methods=['GET', 'POST'])
def novo_lembrete(cid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    if not pode_ver(cid, session['usuario_id']):
        flash('Acesso negado.', 'erro')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        db = get_db()
        db.execute(
            'INSERT INTO lembretes (crianca_id,titulo,descricao,data,horario,recorrencia,criado_por) VALUES (?,?,?,?,?,?,?)',
            (cid, request.form['titulo'], request.form.get('descricao', ''),
             request.form['data'], request.form['horario'],
             request.form.get('recorrencia', 'nenhuma'), session['usuario_id'])
        )
        db.commit()
        flash('Lembrete criado!', 'sucesso')
        return redirect(url_for('perfil_crianca', cid=cid) + '#lembretes')
    db = get_db()
    crianca = db.execute(
        'SELECT * FROM criancas WHERE id=?', (cid,)).fetchone()
    return render_template('novo_lembrete.html', crianca=crianca)


@app.route('/lembretes/<int:lid>/concluir', methods=['POST'])
def concluir_lembrete(lid):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autorizado'}), 401
    db = get_db()
    l = db.execute('SELECT * FROM lembretes WHERE id=?', (lid,)).fetchone()
    if l and pode_ver(l['crianca_id'], session['usuario_id']):
        db.execute('UPDATE lembretes SET concluido=1 WHERE id=?', (lid,))
        db.commit()
        return jsonify({'ok': True})
    return jsonify({'erro': 'Negado'}), 403


@app.route('/lembretes/<int:lid>/excluir', methods=['POST'])
def excluir_lembrete(lid):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    l = db.execute('SELECT * FROM lembretes WHERE id=?', (lid,)).fetchone()
    if l and (l['criado_por'] == session['usuario_id'] or pode_editar(l['crianca_id'], session['usuario_id'])):
        cid = l['crianca_id']
        db.execute('DELETE FROM lembretes WHERE id=?', (lid,))
        db.commit()
        flash('Lembrete removido.', 'sucesso')
        return redirect(url_for('perfil_crianca', cid=cid) + '#lembretes')
    return redirect(url_for('dashboard'))

# ── main ──────────────────────────────────────────────────────────────────────


if __name__ == '__main__':
    import sqlite3
    from database import DATABASE
    init_db()
    _c = sqlite3.connect(DATABASE)
    ensure_lembretes(_c)
    _c.close()
    app.run(debug=True, port=5000)
