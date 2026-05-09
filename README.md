#RotinaDiária — Plataforma Digital Adaptativa de Rotina Visual

**Projeto Integrador – Engenharia de Computação – UNIVESP Botucatu 2026**

Plataforma web para apoio a crianças com Transtorno do Espectro Autista (TEA),
com foco em rotinas visuais e monitoramento de evolução.

---

## 🚀 Como rodar

### 1. Pré-requisitos
- Python 3.10+

### 2. Instalar dependências
```bash
pip install flask
```

### 3. Iniciar a aplicação
```bash
python app.py
```

Acesse: **http://localhost:5000**

---

## 🔑 Acesso teste

| Campo | Valor         |
|-------|---------------|
| Email | demo@tea.com  |
| Senha | 1234          |

---

## 📁 Estrutura do projeto

```
tea_plataforma/
├── app.py              # Aplicação Flask (rotas)
├── database.py         # Banco de dados SQLite
├── requirements.txt
├── instance/
│   └── tea.db          # Banco de dados (gerado automaticamente)
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── cadastro.html
│   ├── dashboard.html
│   ├── perfil_crianca.html
│   ├── nova_crianca.html
│   ├── editar_crianca.html
│   ├── novo_item.html
│   └── evolucao.html
└── static/
    ├── css/style.css
    └── img
    └── js/main.js
```

---

## ✅ Funcionalidades

- **Autenticação** – login, cadastro, perfis (responsável, educador, terapeuta)
- **Gestão de crianças** – cadastro com nome, idade, nível TEA, observações
- **Rotina visual** – lista de atividades diárias com ícone, horário e descrição
- **Check diário** – marcar/desmarcar atividades do dia (salvo em tempo real via API)
- **Barra de progresso** – visualização do avanço do dia
- **Gráfico de evolução** – dois gráficos (barras + linha) com dados dos últimos 30 dias
- **Estatísticas** – total de dias registrados, média de conclusão, melhor dia

---

## 🗄️ Banco de dados

Tabelas: `usuarios`, `criancas`, `rotina_itens`, `registros_evolucao`

---

## 👥 Autores

Anderson Luiz · Breno Rafael · Daniel Amoroso · Edilson Craveiro ·
Lucas Smith · Marcos Fabrício · Melquizedeque Andrade · Willy Johnson

Orientador: Ricardo Balarin Meneguel — Polo Botucatu (DRP05)
