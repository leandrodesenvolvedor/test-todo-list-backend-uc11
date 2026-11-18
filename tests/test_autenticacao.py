"""Testes da autenticação: do token emitido ao isolamento entre contas. 
O arquivo cresce em três etapas, cada uma com uma seção nova no final: 
1. a mecânica do token, sem HTTP — chamando `TokenDeAcesso` diretamente; 
2. o cabeçalho `Authorization`, pela API; 
3. o isolamento entre contas — uma conta não alcança os dados da outra. 
""" 
import jwt
import pytest
from datetime import timedelta 
from app.exceptions import NaoAutenticado, SessaoExpirada 
from app.tokens import ALGORITMO, TokenDeAcesso 
#: Segredo próprio deste arquivo, com mais de 32 bytes. 
SEGREDO = "segredo-de-teste-com-mais-de-trinta-e-dois-bytes" 
@pytest.fixture 
def tokens() -> TokenDeAcesso: 
    """Fixture **local**: só este arquivo precisa de um emissor de tokens. 
    Compare com a `hasher`, que mora no `conftest.py` porque dois arquivos a 
    usam. O lugar de uma fixture é decidido pelo **alcance** de quem precisa 
    dela. 
    """ 
    return TokenDeAcesso(segredo=SEGREDO, validade=timedelta(hours=1)) 

# ============================================================================= 
# Dia 4 — a mecânica do token, sem HTTP 
# ============================================================================= 
def test_token_emitido_devolve_o_mesmo_usuario(tokens: TokenDeAcesso): 
    """O caminho normal, em uma linha: o que entra é o que sai.""" 
    assert tokens.ler(tokens.emitir(42)) == 42 
  
def test_token_nao_e_o_id_em_texto_puro(tokens: TokenDeAcesso): 
    """O token é assinado: não dá para fabricar um escrevendo o id.""" 
    assert tokens.emitir(42) != "42" 
    assert len(tokens.emitir(42)) > 40 
  
def test_token_assinado_com_outro_segredo_e_recusado(tokens: TokenDeAcesso): 
    """O caso que a assinatura existe para impedir.""" 
    intruso = TokenDeAcesso( 
        segredo="outro-segredo-tambem-com-trinta-e-dois-bytes", 
        validade=timedelta(hours=1), 
    ) 
    with pytest.raises(NaoAutenticado): 
        tokens.ler(intruso.emitir(42)) 
  
def test_token_alterado_e_recusado(tokens: TokenDeAcesso): 
    """Trocar um caractere invalida a assinatura.""" 
    token = tokens.emitir(42) 
    adulterado = token[:-2] + ("ab" if not token.endswith("ab") else "cd") 
    with pytest.raises(NaoAutenticado): 
        tokens.ler(adulterado) 
 
@pytest.mark.parametrize( 
    "texto_invalido", ["", "   ", "nao-e-um-token", "a.b.c", "Bearer abc"] 
) 
def test_texto_que_nao_e_token_e_recusado( 
    tokens: TokenDeAcesso, texto_invalido: str 
): 
    """Cinco representantes de "isto não é um token" — o `parametrize` do Dia 3.""" 
    with pytest.raises(NaoAutenticado): 
        tokens.ler(texto_invalido) 
  
  
def test_token_expirado_e_recusado_com_excecao_propria(tokens: TokenDeAcesso): 
    """A validade negativa é o truque que torna o teste instantâneo: o token 
    nasce vencido há dez segundos.""" 
    vencido = TokenDeAcesso(segredo=SEGREDO, validade=timedelta(seconds=-10)) 
    with pytest.raises(SessaoExpirada): 
        tokens.ler(vencido.emitir(42)) 
  
  
def test_sessao_expirada_tambem_e_nao_autenticado(): 
    """A herança é o que faz as duas responderem 401 com um só tratador.""" 
    assert issubclass(SessaoExpirada, NaoAutenticado) 
  
  
def test_token_sem_sub_utilizavel_e_recusado(tokens: TokenDeAcesso): 
    """Token assinado por nós, mas com conteúdo inesperado.""" 
    sem_sub = jwt.encode({"outro": "campo"}, SEGREDO, algorithm=ALGORITMO) 
    with pytest.raises(NaoAutenticado): 
        tokens.ler(sem_sub) 
  
  
def test_token_nao_guarda_dados_pessoais(tokens: TokenDeAcesso): 
    """O conteúdo de um JWT é legível por qualquer um que tenha o token.""" 
    conteudo = jwt.decode(tokens.emitir(42), SEGREDO, algorithms=[ALGORITMO])
    assert set(conteudo) == {"sub", "iat", "exp"}