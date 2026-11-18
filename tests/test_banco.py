"""Testes do comportamento do banco de dados. 
  
Os primeiros testes da suíte que **não** rodam só em memória: eles gravam, 
consultam e esperam que o banco recuse o que não deve aceitar. É o nível de 
**integração** — a conversa entre o modelo e o banco. 
  
Cada teste recebe um banco vazio, criado pela fixture `banco_limpo` do 
`conftest.py` — que nenhum teste pede pelo nome, porque ela é `autouse`. 
""" 
  
import pytest 
from sqlalchemy import inspect, text 
from sqlalchemy.exc import IntegrityError 
  
from app.database import SessionLocal, engine 
from app.models import Tarefa, Usuario 
  
  
# ------------------------------------------------------- a estrutura do banco 
  
def test_as_duas_tabelas_existem_no_banco(): 
    """Olha o banco, e não o `metadata`.""" 
    assert set(inspect(engine).get_table_names()) == {"usuarios", "tarefas"} 
  
  
def test_a_tabela_usuarios_tem_as_colunas_esperadas(): 
    colunas = {coluna["name"] for coluna in inspect(engine).get_columns("usuarios")} 
    assert colunas == {"id", "nome", "email", "senha_hash", "criado_em"} 
  
  
def test_a_coluna_do_banco_se_chama_senha_hash_e_nao_senha(): 
    """O atributo Python é `_senha_hash`; a coluna é `senha_hash`.""" 
    assert Usuario.__table__.columns["senha_hash"].name == "senha_hash"
    
# ----------------------------------------------------- gravando e consultando 
  
def test_tarefa_com_usuario_existente_e_aceita(): 
    """Uma tarefa de um usuário que existe é gravada normalmente. 
  
    Este teste abre e fecha a sessão **à mão**, de propósito: é o jeito 
    "antes da fixture". Compare com os testes abaixo, que pedem a `sessao` 
    pronta e não precisam do `try/finally`. 
    """ 
    sessao = SessionLocal() 
    try: 
        usuario = Usuario(nome="Ana", email="ana@exemplo.com") 
        usuario._senha_hash = "hash-qualquer" 
        sessao.add(usuario) 
        sessao.commit() 
  
        sessao.add(Tarefa(usuario_id=usuario.id, titulo="Tarefa válida")) 
        sessao.commit() 
  
        assert sessao.query(Tarefa).count() == 1 
    finally: 
        sessao.rollback() 
        sessao.close() 
 
@pytest.fixture 
def sessao() -> pytest.Session: 
    """Sessão de banco para os testes que precisam gravar direto. 
O `rollback()` antes do `close()` desfaz qualquer transação que o teste 
tenha deixado aberta. Sem ele, um teste que falha no meio de um `commit()` 
deixaria a sessão em estado inconsistente para o próximo. 
""" 

    sessao = SessionLocal() 
    try: 
        yield sessao 
    finally: 
        sessao.rollback() 
        sessao.close() 
        

def test_email_duplicado_e_recusado_pelo_banco(sessao, hasher): 
    """A RN-01 tem duas camadas de defesa. 
  
    O serviço de cadastro consulta antes de inserir, para devolver uma 
    mensagem clara. Mas entre a consulta e a inserção há uma janela em que 
    outra requisição pode cadastrar o mesmo e-mail. O `unique` da coluna é o 
    que fecha essa janela — e é ele que este teste verifica. 
    """ 
    for _ in range(2): 
        usuario = Usuario(nome="Ana", email="ana@exemplo.com") 
        usuario.definir_senha("senha123", hasher) 
        sessao.add(usuario) 
  
    with pytest.raises(IntegrityError): 
        sessao.commit() 
 

# ----------------------------------------------- RN-04: a chave estrangeira 
  
def test_verificacao_de_chave_estrangeira_esta_ligada(): 
    """Confere o PRAGMA diretamente na conexão.""" 
    with engine.connect() as conexao: 
        ligado = conexao.execute(text("PRAGMA foreign_keys")).scalar() 
    assert ligado == 1, "a verificação de chave estrangeira do SQLite está desligada" 
  
  
def test_tarefa_orfa_e_recusada_pelo_banco(sessao): 
    """RN-04 no nível do banco, e não apenas no do serviço. 
  
    O serviço já verifica se o usuário existe antes de criar a tarefa. Este 
    teste é a segunda linha de defesa: mesmo que alguém grave direto pela 
    sessão, passando por cima do serviço, o banco recusa uma tarefa cujo 
    dono não existe. 
    """ 
    sessao.add(Tarefa(usuario_id=9999, titulo="Tarefa de usuário inexistente")) 
    with pytest.raises(IntegrityError): 
        sessao.commit() 
 
