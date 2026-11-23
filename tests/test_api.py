
"""Testes dos endpoints: a aplicação inteira, atravessada por HTTP.
Os arquivos anteriores chamam funções e métodos diretamente. Este faz
**requisições**: chega pela rota, passa pelo serviço, pelo repositório e pelo
modelo, e volta como JSON. É o nível que prova que as camadas conversam.
| | Teste de domínio | Teste de API |
|---|---|---|
| O que prova | que a regra está certa | que a regra chega ao cliente |
| Quando falha | diz exatamente qual regra | diz que algo no caminho quebrou |
| Custo | microssegundos | milissegundos |
Nenhum dos dois substitui o outro.
"""
from fastapi.testclient import TestClient
#: Corpo de cadastro válido, reaproveitado com `{**USUARIO_VALIDO, "campo": ...}`.
#:
#: É o mesmo papel das fábricas `nova_tarefa` e `novo_usuario` do Dia 1: um
#: ponto único a alterar quando o contrato de entrada mudar.
USUARIO_VALIDO = {
 "nome": "Bruno Lima",
 "email": "bruno@exemplo.com",
 "senha": "senha123",
}
# =============================================================================
# Dia 7 — `TestClient`: os endpoints públicos
# =============================================================================
def test_raiz_responde(cliente: TestClient):
 """O teste mais simples do arquivo, e o que falha primeiro quando a
 aplicação nem sobe. Serve de *smoke test*: se este falha, não vale
 investigar os outros."""
 assert cliente.get("/").status_code == 200
def test_cadastrar_usuario_devolve_201_com_sessao_aberta(cliente: TestClient):
 """O cadastro já devolve o token: quem criou a conta está autenticado.
 Três coisas são verificadas de uma vez, e cada uma é parte do contrato: o
 **código** 201 (recurso criado), o **corpo** com o token, e o **formato**
 dos nomes de campo — `criadoEm`, em camelCase, e não `criado_em`.
 """
 resposta = cliente.post("/usuarios", json=USUARIO_VALIDO)
 assert resposta.status_code == 201
 corpo = resposta.json()
 assert corpo["accessToken"]
 assert corpo["tokenType"] == "bearer"
 assert corpo["usuario"]["nome"] == "Bruno Lima"
 assert "criadoEm" in corpo["usuario"], "o contrato usa camelCase"
 
def test_cadastro_nao_expoe_a_senha(cliente: TestClient):
 """Nem a senha nem o hash dela podem aparecer na resposta (RN-05).
 A verificação é feita sobre `resposta.text` — o JSON como texto, antes de
 ser interpretado — de propósito: assim ela não depende de saber em qual
 campo o vazamento aconteceria.
 As duas grafias são procuradas porque a API traduz nomes na borda: o que no
 Python se chama `senha_hash` chegaria ao cliente como `senhaHash`.
 """
 resposta = cliente.post("/usuarios", json=USUARIO_VALIDO)
 inteiro = resposta.text
 assert "senha123" not in inteiro
 assert "senhaHash" not in inteiro and "senha_hash" not in inteiro
 
def test_cadastrar_com_email_repetido_devolve_409(cliente: TestClient):
 """409 Conflict: o pedido está correto, o estado atual é que não permite."""
 cliente.post("/usuarios", json=USUARIO_VALIDO)
 resposta = cliente.post("/usuarios", json=USUARIO_VALIDO)
 assert resposta.status_code == 409
 assert resposta.json()["detail"] == "E-mail já cadastrado."
def test_email_duplicado_ignora_maiusculas_e_espacos(cliente: TestClient):
 """RN-01 de verdade: o mesmo endereço escrito de outra forma é duplicata."""
 cliente.post("/usuarios", json=USUARIO_VALIDO)
 resposta = cliente.post(
 "/usuarios", json={**USUARIO_VALIDO, "email": " BRUNO@Exemplo.com "}
 )
 assert resposta.status_code == 409
def test_email_malformado_devolve_422(cliente: TestClient):
 """422 vem do Pydantic, antes de a requisição chegar ao serviço."""
 resposta = cliente.post("/usuarios", json={**USUARIO_VALIDO, "email": "bruno@"})
 assert resposta.status_code == 422
def test_senha_curta_devolve_422(cliente: TestClient):
 resposta = cliente.post("/usuarios", json={**USUARIO_VALIDO, "senha": "123"})
 assert resposta.status_code == 422
 
def test_login_correto_devolve_200_com_token(cliente: TestClient, usuario: dict):
 """200 e não 201: o login não cria recurso nenhum, só abre sessão.
 O usuário já existe porque o teste pediu a fixture `usuario`, que faz o
 cadastro antes do teste começar.
 """
 resposta = cliente.post(
 "/usuarios/login", json={"email": "ana@exemplo.com", "senha": "senha123"}
 )
 assert resposta.status_code == 200
 corpo = resposta.json()
 assert corpo["usuario"]["id"] == usuario["id"]
 assert corpo["accessToken"]
def test_login_com_senha_errada_devolve_401(cliente: TestClient, usuario: dict):
 resposta = cliente.post(
 "/usuarios/login", json={"email": "ana@exemplo.com", "senha": "errada"}
 )
 assert resposta.status_code == 401
def test_login_com_email_inexistente_devolve_401_com_a_mesma_mensagem(
 cliente: TestClient, usuario: dict
):
 """Mensagem idêntica nos dois casos: não revela quais e-mails existem.
 Repare no formato do teste: ele não verifica *qual* é a mensagem, e sim que
 as duas são **iguais**. É uma propriedade, não um valor.
 """
 inexistente = cliente.post(
 "/usuarios/login", json={"email": "ninguem@exemplo.com", "senha": "senha123"}
 )
 senha_errada = cliente.post(
 "/usuarios/login", json={"email": "ana@exemplo.com", "senha": "errada"}
 )
 assert inexistente.status_code == senha_errada.status_code == 401
 assert inexistente.json()["detail"] == senha_errada.json()["detail"]
def test_nao_existe_mais_busca_de_usuario_por_id(cliente: TestClient):
 """`GET /usuarios/{id}` saiu da API — era enumeração de contas.
 Um teste que verifica a **ausência** de um endpoint impede que a rota volte
 numa refatoração futura "porque o front-end precisava".
 """
 assert cliente.get("/usuarios/1").status_code == 404
 assert cliente.get("/usuarios/9999").status_code == 404
def test_consultar_a_propria_conta_exige_token(cliente: TestClient):
 """401 e não 403: o servidor não sabe quem está pedindo."""
 assert cliente.get("/usuarios/eu").status_code == 401
def test_openapi_expoe_os_sete_endpoints(cliente: TestClient):
 """A API documenta exatamente o que tem — nada a mais.
 Uma rota acrescentada sem intenção, ou uma que devia ter saído e ficou,
 muda este número.
 """
caminhos = cliente.get("/openapi.json").json()["paths"]
operacoes = sum(len(metodos) for metodos in caminhos.values())
assert operacoes == 8, "7 endpoints da API + a rota raiz"

