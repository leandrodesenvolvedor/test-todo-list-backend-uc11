import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "segredo-de-teste-nao-usar-em-producao"

import pytest
from fastapi.testclient import TestClient

from app.dependencies import obter_hasher
from app.main import app
from app.security import HashBcrypt, HashDeSenha  
  
# ============================================================================= 
# Dia 4 — a primeira fixture compartilhada 
# ============================================================================= 
  
@pytest.fixture 
def hasher() -> HashBcrypt: 
    """O hash de senha **de verdade**, com o custo no mínimo. 
  
    Está aqui, e não dentro de um arquivo de teste, porque dois arquivos a 
    usam: `test_seguranca.py` e `test_dominio.py`. Fixture que serve a mais de 
    um arquivo sobe para o `conftest.py`. 
  
    O `custo=4` é o mínimo aceito pelo bcrypt e deixa cada hash em poucos 
    milissegundos. Nenhum comportamento verificado depende do custo; em 
    produção vale o padrão de 12, definido em `HashBcrypt.__init__`. 
    """ 
    return HashBcrypt(custo=4)

import pytest  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402 
from app.database import Base, SessionLocal, criar_tabelas, engine  # noqa: E402 
from app.security import HashBcrypt  # noqa: E402

# =============================================================================
# Dia 5 — o banco: limpo antes, limpo depois 
# ============================================================================= 

@pytest.fixture(autouse=True) 
def banco_limpo(): 
    """Garante um banco vazio no início e no fim de cada teste. 
    `autouse=True` aplica esta fixture a todos os testes, sem que nenhum precise 
    pedi-la. É o que torna o isolamento uma garantia e não uma disciplina: não 
    existe teste que "esqueceu" de limpar o banco. 
    O que vem antes do `yield` roda antes do teste; o que vem depois, ao final — 
    inclusive se o teste falhar. 
    """ 
    
    #Base.metadata.drop_all(bind=engine) 
    criar_tabelas() 
    yield 
    #Base.metadata.drop_all(bind=engine)
    
    # =============================================================================
# Dia 7 — HTTP: o dublê e o cliente
# =============================================================================
class HashFake(HashDeSenha):

    def gerar(self, senha: str) -> str:
        return f"fake${senha}"

    def verificar(self, senha: str, hash_armazenado: str) -> bool:
        return hash_armazenado == self.gerar(senha)


@pytest.fixture
def cliente(banco_limpo) -> TestClient:
    app.dependency_overrides[obter_hasher] = HashFake

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sessao_aberta(cliente: TestClient) -> dict:
    resposta = cliente.post(
        "/usuarios",
        json={
            "nome": "Ana Souza",
            "email": "ana@exemplo.com",
            "senha": "senha123"
        },
    )

    assert resposta.status_code == 201, resposta.text

    return resposta.json()


@pytest.fixture
def usuario(sessao_aberta: dict) -> dict:
    return sessao_aberta["usuario"]