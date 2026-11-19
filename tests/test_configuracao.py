"""Testes da configuração e da escolha do banco de dados. 
  
Estes testes protegem a troca de ambiente: garantem que a URL que as 
plataformas de hospedagem entregam é aceita como vem, que configuração ausente 
é erro e não padrão silencioso, e que o segredo do token é forte o bastante. 
  
O arquivo nasce com uma função pura (`normalizar_url`), que só precisa de 
`parametrize`. A leitura do ambiente entra depois, junto com o `monkeypatch`. 
""" 
  
import pytest 
  
# ==from app.config import normalizar_url 
from app.config import (
 CAMINHO_DO_ENV,
 ORIGENS_PADRAO,
 RAIZ_DO_PROJETO,
 SEGREDO_DE_EXEMPLO,
 TAMANHO_MINIMO_DO_SEGREDO,
 Configuracao,
 normalizar_url,
)
  
  
# ============================================================================= 
# Dia 3 — `parametrize` numa função pura: a normalização da URL 
# ============================================================================= 
  
@pytest.mark.parametrize( 
    "url_recebida", 
    [ 
        "postgres://usuario:senha@host:5432/banco", 
        "postgresql://usuario:senha@host:5432/banco", 
    ], 
) 
def test_url_de_postgres_recebe_o_driver_do_projeto(url_recebida): 
    """A URL entregue pela hospedagem deve funcionar colada como veio.""" 
    normalizada = normalizar_url(url_recebida) 
    assert normalizada.startswith("postgresql+psycopg://") 
    assert normalizada.endswith("usuario:senha@host:5432/banco") 
  
  
def test_driver_declarado_explicitamente_e_respeitado(): 
    """Quem escreveu o driver na URL sabe o que quer — não sobrescrever.""" 
    url = "postgresql+psycopg2://usuario:senha@host:5432/banco" 
    assert normalizar_url(url) == url 
  
  
def test_url_de_sqlite_nao_e_alterada(): 
    assert normalizar_url("sqlite:///./todo_list.db") == "sqlite:///./todo_list.db" 
  
  
def test_parametros_da_url_sao_preservados(): 
    """Banco gerenciado costuma exigir SSL, que vem como parâmetro na URL.""" 
    url = "postgres://u:s@host:5432/banco?sslmode=require" 
    assert normalizar_url(url).endswith("?sslmode=require")
    
# =============================================================================
# Dia 6 — `monkeypatch`: a DATABASE_URL é obrigatória
# =============================================================================
def test_sem_database_url_a_aplicacao_recusa_subir(monkeypatch):
 """Não existe banco padrão silencioso.
 Cair em SQLite quando a variável falta esconde um problema: quando o
 padrão coincide com o valor esperado, não há como saber se o `.env` foi
 lido ou se a aplicação apenas caiu no padrão.
 """
 monkeypatch.delenv("DATABASE_URL", raising=False)
 with pytest.raises(RuntimeError):
    Configuracao.do_ambiente()

@pytest.mark.parametrize("valor_vazio", ["", " "])
def test_database_url_vazia_conta_como_ausente(monkeypatch, valor_vazio):
 """Variável declarada mas sem valor é o erro de digitação mais comum no
 `.env`, e precisa falhar igual à variável ausente."""
 monkeypatch.setenv("DATABASE_URL", valor_vazio)
 with pytest.raises(RuntimeError):
    Configuracao.do_ambiente()
def test_a_mensagem_de_erro_diz_onde_o_env_foi_procurado(monkeypatch):
 """O caminho na mensagem é o que resolve o caso mais frequente: o `.env`
 existe, mas em outra pasta.
 `pytest.raises(...) as erro` guarda a exceção para inspecioná-la depois.
 """
 monkeypatch.delenv("DATABASE_URL", raising=False)
 with pytest.raises(RuntimeError, match="DATABASE_URL") as erro:
    Configuracao.do_ambiente()
 assert str(CAMINHO_DO_ENV) in str(erro.value)
 
# ------------------------------------------------------- leitura do ambiente
def test_postgres_e_reconhecido_como_banco_em_servidor(monkeypatch):
 monkeypatch.setenv("DATABASE_URL", "postgres://u:s@host:5432/banco")
 configuracao = Configuracao.do_ambiente()
 assert configuracao.dialeto == "postgresql"
 assert configuracao.banco_em_servidor is True
 assert configuracao.banco_em_memoria is False
def test_sqlite_em_memoria_e_reconhecido(monkeypatch):
 monkeypatch.setenv("DATABASE_URL", "sqlite://")
 assert Configuracao.do_ambiente().banco_em_memoria is True
def test_sem_variavel_de_ambiente_as_origens_sao_as_de_desenvolvimento(monkeypatch):
 monkeypatch.delenv("ORIGENS_PERMITIDAS", raising=False)
 monkeypatch.setenv("DATABASE_URL", "sqlite://")
 assert Configuracao.do_ambiente().origens_permitidas == ORIGENS_PADRAO
def test_origens_permitidas_aceita_lista_separada_por_virgula(monkeypatch):
 monkeypatch.setenv(
 "ORIGENS_PERMITIDAS", "https://a.com , https://b.com ,, https://c.com"
 )
 origens = Configuracao.do_ambiente().origens_permitidas
 assert origens == ("https://a.com", "https://b.com", "https://c.com")
@pytest.mark.parametrize("valor", ["1", "true", "TRUE", "sim"])
def test_echo_sql_ligado(monkeypatch, valor):
 monkeypatch.setenv("ECHO_SQL", valor)
 assert Configuracao.do_ambiente().echo_sql is True
@pytest.mark.parametrize("valor", ["", "0", "false", "nao"])
def test_echo_sql_desligado(monkeypatch, valor):
 monkeypatch.setenv("ECHO_SQL", valor)
 assert Configuracao.do_ambiente().echo_sql is False
def test_configuracao_e_imutavel():
 """Configuração alterada em tempo de execução é defeito difícil de achar."""
 configuracao = Configuracao(url_banco="sqlite://", segredo_jwt="segredo")
 with pytest.raises(Exception):
    configuracao.url_banco = "sqlite:///outro.db" 
    
# ------------------------------------------------------- de onde vem o `.env`
def test_o_env_e_procurado_na_raiz_do_projeto():
 """A raiz é a pasta que contém `app/` — a mesma do `requirements.txt`."""
 assert CAMINHO_DO_ENV.name == ".env"
 assert CAMINHO_DO_ENV.parent == RAIZ_DO_PROJETO
 assert (RAIZ_DO_PROJETO / "requirements.txt").exists()
 assert (RAIZ_DO_PROJETO / "app").is_dir()
def test_o_caminho_do_env_e_absoluto():
 """É o que torna a leitura independente do diretório de trabalho.
 Com um caminho relativo, rodar `uvicorn` de outra pasta faria o `.env` ser
 ignorado em silêncio.
 """
 assert CAMINHO_DO_ENV.is_absolute()
def test_variavel_do_ambiente_vence_o_arquivo_env(tmp_path, monkeypatch):
 """Garantia da qual a própria suíte depende.
 O `conftest.py` define `DATABASE_URL=sqlite://` antes de importar a
 aplicação. Se o `.env` da máquina sobrescrevesse esse valor, rodar os
 testes apagaria o banco de trabalho do desenvolvedor.
 `tmp_path` é outra fixture embutida do pytest: uma pasta temporária,
 exclusiva deste teste, apagada depois.
 """
 from dotenv import load_dotenv
 arquivo = tmp_path / ".env"
 arquivo.write_text(
 "DATABASE_URL=postgresql+psycopg://do-arquivo/banco", encoding="utf-8"
 )
 monkeypatch.setenv("DATABASE_URL", "sqlite://")
 load_dotenv(arquivo)
 assert Configuracao.do_ambiente().url_banco == "sqlite://"