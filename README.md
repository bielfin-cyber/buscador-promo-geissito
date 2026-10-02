# Buscador Promo do Geissito

Versão funcional para pesquisar as ofertas publicadas em
`https://www.afiliadointeligente.com.br/promo-do-geissito`.

## Forma mais simples no Windows

1. Extraia o ZIP inteiro para uma pasta.
2. Clique duas vezes em `INICIAR.bat`.
3. No primeiro uso, o iniciador cria um ambiente isolado e instala os componentes.
4. O navegador abrirá em `http://127.0.0.1:7860`.

O iniciador ignora o falso atalho `python.exe` da Microsoft Store e procura, em
ordem, uma instalação Python válida no sistema, no Codex e no Pinokio. Assim, em
um computador que já tenha Codex ou Pinokio, normalmente não é necessário
instalar Python separadamente.

O buscador continua funcionando em segundo plano e a janela do iniciador fecha
automaticamente. Nas próximas execuções, basta abrir `INICIAR.bat` novamente.
Use `ENCERRAR.bat` quando desejar desligar o servidor local. Para executar os
testes locais e ao vivo, use `VERIFICAR.bat` depois da primeira inicialização.

## Executar no Google Colab

1. Envie esta pasta (ou o ZIP entregue junto) ao Colab.
2. Em uma célula, entre na pasta e instale as dependências:

   ```python
   %cd /content/buscador-promo-geissito
   !pip -q install -r requirements.txt
   ```

3. Em outra célula, execute:

   ```python
   !python app.py
   ```

4. O notebook inicia o servidor e abre a porta 7860 em uma janela do Colab.

Também há um notebook pronto: abra `Buscador_Promo_do_Geissito.ipynb`, execute as
células e selecione a pasta deste projeto quando solicitado.

## Executar em um computador ou servidor

```text
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python app.py
```

Em Linux/macOS, a ativação é `source .venv/bin/activate`.

## Hospedagem 24/7

O pacote inclui `Dockerfile` e `render.yaml`. Ele pode ser colocado em um
repositório privado e implantado como serviço Docker no Render ou em outro
provedor compatível. O servidor respeita as variáveis `HOST`, `PORT` e
`OPEN_BROWSER`; para hospedagem, utilize `HOST=0.0.0.0` e `OPEN_BROWSER=0`.

Não publique uma cópia sem antes confirmar os termos de uso e limites de acesso
do Afiliado Inteligente. O plano de hospedagem é cobrado pelo provedor escolhido.

## Como os dados são obtidos

A inspeção técnica realizada em 02/10/2026 encontrou:

- aplicação pública em Next.js;
- 12 ofertas serializadas no HTML inicial;
- paginação feita pelo próprio front-end por tRPC;
- procedimento real: `site.getProductsBySlugPaginated`;
- cada produto retorna `title`, `price`, `old_price`, `image`, `stores`, `tags`
  e `link`.

O buscador consulta esse mesmo procedimento público, carrega as páginas em
paralelo, mantém um cache em memória por 15 minutos e pesquisa localmente. A
interface usa apenas recursos nativos do Python, sem Gradio ou outro servidor
pesado. Não foram inventados feeds ou endpoints alternativos.

## Proteção dos links afiliados

- O botão usa **exatamente** o valor de `product.link` recebido da fonte.
- O código nunca reconstrói, encurta, resolve redirecionamentos ou substitui a
  URL por links encontrados em `caption`/`description`.
- URLs ausentes, relativas, não HTTP(S), com credenciais ou caracteres de quebra
  de linha são rejeitadas.
- A deduplicação usa ID e SHA-256 da URL original, sem modificar a URL.
- `rel="sponsored nofollow noopener"` identifica o link e protege a nova aba sem
  alterar o destino.

Isto preserva a URL configurada no Afiliado Inteligente. A atribuição final de
comissão continua dependendo de cookies, sessão, regras e disponibilidade da
plataforma de afiliados; nenhum software externo pode garanti-la.

## Limitações reais

- O procedimento tRPC é público e usado pelo site, mas não foi documentado como
  uma API pública estável. Uma mudança no site pode exigir ajuste no coletor.
- Ofertas e totais mudam continuamente; resultados de teste variam com o catálogo.
- Preço e desconto só aparecem quando a fonte fornece números válidos. Zero ou
  valores ausentes são exibidos como “Preço não informado”; descontos só são
  calculados quando `old_price > price > 0`.
- O Colab é adequado para teste, não para operação 24/7. Para produção, hospede
  os mesmos arquivos em um serviço Python persistente e adicione monitoramento.
- Antes de uso contínuo/comercial, confirme os termos de uso e limites de acesso
  do Afiliado Inteligente e das plataformas afiliadas.

## Testes

Execute:

```text
python -m unittest -v test_core.py
python smoke_test_live.py
```

O primeiro teste é determinístico e não acessa a internet. O segundo consulta o
catálogo atual e testa `air fryer`, `TV 50` e `tênis masculino`.

