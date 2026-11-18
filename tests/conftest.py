"""Configuração comum dos testes. 
  
O pytest encontra este arquivo sozinho e aplica o que há nele a **todos** os 
testes da pasta — não é preciso importá-lo em lugar nenhum. É isso que faz dele 
o lugar das fixtures compartilhadas. 
""" 
  
import os 
  
# As variáveis de ambiente são definidas **antes** de importar a aplicação, e a 
# ordem é o que importa aqui: a configuração é carregada na primeira importação 
# e fica em cache. Definir depois do import não teria efeito nenhum. 
# 
# `sqlite://` sem caminho é o banco **em memória**: ele existe enquanto a 
# conexão existir e desaparece ao final. Nenhum arquivo é criado, e o banco de 
# trabalho em `todo_list.db` não é tocado pela suíte. 
os.environ["DATABASE_URL"] = "sqlite://" 
  
# A aplicação exige um segredo de token para subir. Valor fixo e previsível, 
# para que as falhas sejam reproduzíveis. Não é o segredo da aplicação — a 
# configuração real vem do `.env`, que a suíte deixa de precisar. 
os.environ["JWT_SECRET"] = "segredo-de-teste-nao-usar-em-producao" 
  
import pytest  # noqa: E402 

from app.security import HashBcrypt  # noqa: E402 
  
  
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
    
    