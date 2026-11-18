"""Testes do hash de senha — com o bcrypt de verdade. 
  
Este arquivo verifica a implementação real do algoritmo: o salt aleatório, a 
conferência e o limite de bytes. Nada disso pode ser verificado sobre um 
substituto. 
  
O `hasher` usado aqui não é criado em nenhum teste: ele vem da fixture de mesmo 
nome, no `conftest.py`. Ela fica lá, e não neste arquivo, porque 
`test_dominio.py` também precisa dela — e fixture que serve a mais de um 
arquivo sobe para o `conftest.py`. 
""" 
  
import pytest 
  
from app.exceptions import ValorInvalido 
from app.security import LIMITE_DE_BYTES_DO_BCRYPT, HashDeSenha
from tests.conftest import hasher 
  
  
# ------------------------------------------------------------------ o contrato 
  
def test_hash_bcrypt_cumpre_o_contrato(hasher): 
    assert isinstance(hasher, HashDeSenha) 
  
  
def test_contrato_nao_pode_ser_instanciado_direto(): 
    with pytest.raises(TypeError): 
        HashDeSenha() 
  
  
def test_implementacao_incompleta_nao_pode_ser_instanciada(): 
    """Esquecer um método do contrato falha na criação, não no login.""" 
  
    class HashPelaMetade(HashDeSenha): 
        def gerar(self, senha: str) -> str: 
            return senha 
  
        # `verificar` ficou de fora de propósito
        
    with pytest.raises(TypeError): 
        HashPelaMetade()
        
   # --------------------------------------------------------------- RN-05: a senha 
  
def test_hash_nao_e_a_senha_em_texto_puro(hasher): 
    assert hasher.gerar("senha123") != "senha123" 
  
  
def test_mesma_senha_gera_hashes_diferentes(hasher): 
    """O salt é aleatório por senha: dois usuários com a mesma senha não têm 
    o mesmo hash, o que impede identificá-los comparando a coluna.""" 
    assert hasher.gerar("senha123") != hasher.gerar("senha123") 
  
  
def test_hash_gerado_confere_com_a_senha(hasher): 
    assert hasher.verificar("senha123", hasher.gerar("senha123")) is True 
  
  
def test_senha_errada_nao_confere(hasher): 
    assert hasher.verificar("errada", hasher.gerar("senha123")) is False 
  
  
def test_hash_cabe_na_coluna_do_banco(hasher): 
    """O bcrypt produz sempre 60 caracteres. A coluna tem 255: folga para 
    trocar de algoritmo sem migração.""" 
    assert len(hasher.gerar("senha123")) == 60       
    
# ------------------------------------------------------- o limite de 72 *bytes* 
def test_senha_no_limite_de_bytes_e_aceita(hasher): 
    senha = "a" * LIMITE_DE_BYTES_DO_BCRYPT 
    assert hasher.verificar(senha, hasher.gerar(senha)) is True 

def test_senha_acima_do_limite_de_bytes_e_recusada(hasher): 
    with pytest.raises(ValorInvalido): 
        hasher.gerar("a" * (LIMITE_DE_BYTES_DO_BCRYPT + 1)) 

def test_o_limite_conta_bytes_e_nao_caracteres(hasher): 
    """40 caracteres acentuados são 80 bytes em UTF-8 — acima do limite, ainda 
    que o campo da API aceite até 72 caracteres.""" 
    senha = "ã" * 40 
    assert len(senha) < LIMITE_DE_BYTES_DO_BCRYPT 
    assert len(senha.encode("utf-8")) > LIMITE_DE_BYTES_DO_BCRYPT 
    with pytest.raises(ValorInvalido): 
        hasher.gerar(senha) 
        
# ---------------------------------------------------------- entrada malformada 
def test_hash_invalido_nao_derruba_a_verificacao(hasher): 
    """Uma coluna corrompida devolve "senha não confere", não erro 500."""
    assert hasher.verificar("senha123", "isto-nao-e-um-hash") is False