# Inteligência Política

Dashboard multipágina em Streamlit para análise eleitoral de candidaturas em Minas Gerais. A aplicação cruza votação territorial, perfil demográfico, despesas de campanha, emendas parlamentares e potencial de expansão com malhas oficiais do IBGE.

Este README é a referência técnica do projeto. A aparência, a hierarquia de informação, os estados de tela e as interações estão documentados no [briefing visual](Visual.md).

## Escopo atual

| Rota | Arquivo | Responsabilidade |
| --- | --- | --- |
| `/raio-x-eleitoral` | `pages/raio_x_do_voto.py` | Votação estadual e intramunicipal, concentração, atuação parlamentar e custo do voto |
| `/dna-eleitoral` | `pages/dna_eleitor.py` | Card do eleitor ideal, distribuição demográfica, clusters de ICP e estrutura inicial da matriz de potencial |
| `/expansao-2030` | `pages/expansao_2030.py` | Classificação municipal de proteção de base e oportunidade demográfica |

`app.py` registra as três rotas com `st.navigation`, descobre as pastas de candidatos na raiz configurada do Hugging Face e mantém a seleção em `st.session_state`. A troca de página preserva o candidato selecionado.

Dois blocos seguem parcialmente implementados:

- **Força da política local**, no Raio X, cruza o capital político local do stage 7a com o market share municipal, colore os quatro quadrantes estratégicos e resume cada classe em um card lateral interativo.
- **Matriz de Potencial Demográfico**, no DNA, exibe a malha intramunicipal em cor neutra e quatro cards vazios. A rotina analítica de compatibilidade existente em `pages/dna_eleitor.py` não é chamada pela rota atual.

## Arquitetura

```text
.
├── app.py                         # Configuração, índice de candidatos e navegação
├── hf_sync.py                     # Acesso ao Hugging Face, descoberta e leitura dos arquivos
├── pages/
│   ├── raio_x_do_voto.py          # Página analítica principal
│   ├── dna_eleitor.py             # Página de perfil eleitoral e estilos locais do card ICP
│   └── expansao_2030.py           # Página de expansão territorial
├── src/eleitoral/
│   ├── common/
│   │   ├── shared_header.py       # Hero, navegação interna, CSS global e seleção compartilhada
│   │   └── dna_copy.py            # Normalização de textos do DNA
│   ├── dna/
│   │   ├── cluster_cards.py       # Cards expansíveis dos perfis de ICP
│   │   ├── dna_distribution.py    # Rosca e filtros demográficos
│   │   └── dna_expansion.py       # Cálculo e mapa categórico de expansão
│   └── maps/
│       ├── choropleth_maps.py      # Coropléticos estaduais e parlamentar
│       ├── dna_geo_reference.py   # Leitura, CRS e referências geográficas
│       └── territorial_mesh.py    # Malha detalhada de bairro/área/setor
├── scripts/                        # Preparação e auditoria de malhas fora do runtime
├── assets/background.png           # Fundo compartilhado da interface
├── .streamlit/config.toml          # Telemetria do Streamlit desativada
├── requirements.txt                # Dependências da aplicação
├── scripts/requirements.txt        # Dependência adicional dos scripts geográficos
└── Dockerfile                      # Imagem Python 3.12, porta 8503
```

Os módulos auxiliares ficam fora de `pages/` para que o Streamlit não os registre como páginas.

### Fluxo de execução

```text
.env / variáveis do processo
        ↓
HfFileSystem + listagem remota
        ↓
índice de candidatos pelo caminho dos arquivos
        ↓
seleção persistida em st.session_state
        ↓
file_by_kind() resolve o parquet da seção
        ↓
leitura em cache → cálculo pandas/numpy → Plotly/HTML/Streamlit
```

Não há sincronização obrigatória para disco local: o runtime abre os arquivos diretamente no bucket. Apesar do nome, `sync_deputados()` atualiza a listagem/cache e não baixa a base para `data/`.

## Configuração

Crie `.env` a partir de `.env.example` e preencha o token quando o bucket não for público:

```env
HF_BUCKET_URL="hf://buckets/amichianalista/mkt-politico"
HF_VISUALIZACAO_PREFIX=""
HF_GEOGRAPHY_PREFIX="IBGE/malha_mapas"
HF_GEOGRAPHY_REFERENCE_PREFIX="IBGE/MG/dadosterritorio"
HF_TOKEN="seu_token"
```

| Variável | Uso |
| --- | --- |
| `HF_BUCKET_URL` | Raiz do bucket acessado pelo `HfFileSystem`; obrigatória |
| `HF_VISUALIZACAO_PREFIX` | Prefixo opcional dentro do bucket; vazio para descobrir candidatos na raiz |
| `HF_GEOGRAPHY_PREFIX` | GeoParquets otimizados usados nos mapas |
| `HF_GEOGRAPHY_REFERENCE_PREFIX` | Tabelas auxiliares de códigos e nomes territoriais |
| `HF_TOKEN` | Autenticação do Hugging Face; não deve ser versionada |

O prefixo de visualização fica vazio por padrão: a aplicação descobre as pastas de candidatos diretamente em `HF_BUCKET_URL` e ignora as pastas compartilhadas do bucket. Variáveis do ambiente, como as configuradas no EasyPanel, têm precedência sobre `.env`, inclusive quando o valor é vazio. `HF_VISUALIZACAO_PREFIX` continua disponível para instalações que guardem os candidatos sob outro prefixo; o valor legado `vereadores` é tratado como vazio para evitar que configurações antigas apontem para o caminho removido. `HF_TOKEN` é necessário quando o bucket exige autenticação.

### Descoberta de candidatos

O formato canônico é:

```text
{pasta_do_candidato}/{ano}/...
```

`hf_sync.deputado_parts()` reconhece a pasta do candidato e o ano nos caminhos remotos. A barra lateral lista candidatos que possuem uma pasta anual padrão, exibindo nome e slug; a seleção filtra os arquivos pelo candidato e pelo ano. O ano padrão é 2026 e as páginas usam a pasta simples `{pasta_do_candidato}/2026/`. Pastas com recortes próprios, como `bh_2026`, não entram nas consultas gerais; o mapa de Belo Horizonte lê essa pasta para comparar 2020/2024 com 2026 e exibir as categorias estratégicas da projeção 2028. Como o formato novo não codifica o cargo, os candidatos na raiz são classificados como vereadores. `selected_deputado_files()` aplica o recorte da pasta, do ano e, quando pedido por uma seção específica, do recorte territorial.

Na consulta do bucket em 8 de outubro de 2026, os candidatos encontrados diretamente na raiz foram `bruno_miranda` e `marcela_tropia`. O bucket também contém pastas compartilhadas de geografia e processamento, que não são listadas como candidatos.

## Contrato de dados eleitorais

`hf_sync.file_by_kind()` resolve os artefatos abaixo pelo sufixo do caminho. Os nomes são parte do contrato entre a preparação dos dados e a visualização.

| Grupo | Arquivo esperado | Consumidor principal |
| --- | --- | --- |
| Território | `territorio/stage01a_municipios.parquet` | Cabeçalho (partido), mapa estadual, concentração, KPIs e votos totais |
| Território | `territorio/stage01b_bairros.parquet` | Mapa intramunicipal e detalhamento por bairro |
| Comparação de BH | `{candidato}/bh_2026/territorio/stage01b_bairros.parquet` | Votos de 2020/2024 e comparação de participação com 2026 no mapa de Belo Horizonte |
| Projeção estratégica de BH | `{candidato}/bh_2026/territorio/stage07_bairros_estrategicos.parquet` | Categorias estratégicas por bairro no filtro **Projeção 2028** |
| Emendas de BH | `{candidato}/bh_2026/emendas/emendas_municipais.parquet` | Resumo e detalhamento municipal de emendas na visualização de Belo Horizonte |
| Demografia | `demografico/stage02_genero.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_idade.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_escolaridade.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_estado_civil.parquet` | Distribuição do eleitorado |
| Perfil | `perfil/stage04_icp_geral_geo.parquet` | Eleitor ideal |
| Perfil | `perfil/stage04_icp_clusters_geo.parquet` | Base eleitoral e perfis de expansão |
| Gastos | `gastos/despesas_campanha.parquet` | Treemap e KPIs de custo |
| Gastos | `gastos/gastos_territoriais_por_tipo.parquet` | Custo de referência por tipo e território |
| Gastos | `gastos/gastos_territoriais.parquet` | Fallback com rateio territorial |
| Emendas | `gastos/emendas_legislativa.parquet` (ou `emendas/emendas_municipais.parquet`, quando fornecido) | Mapa de atuação parlamentar e detalhamento |
| Força local | `forca_local/stage07a_capital_local_municipios.parquet` | Quadrantes de efetividade da estrutura política municipal |
| Força local | `forca_local/stage07b_afinidade_eleitos.parquet` | Composição nominal de prefeitos e vereadores no detalhe municipal |
| Censo | `IBGE/censo/genero_apond.parquet` | Cálculo da expansão |
| Censo | `IBGE/censo/idade_apond.parquet` | Cálculo da expansão |
| Censo | `IBGE/censo/escolaridade_apond.parquet` | Cálculo da expansão |
| Potencial | `potencial_demografico/stage08c_potencial_demografico_icp_geral.parquet` | Expansão para o eleitor ideal |
| Potencial | `potencial_demografico/stage08c_potencial_demografico_icp_clusters.parquet` | Expansão por classificação de ICP |

### Card do eleitor ideal — DNA Eleitoral

`pages/dna_eleitor.py` consolida o parquet `perfil/stage04_icp_geral_geo.parquet` para apresentar a persona predominante como badges por atributo. Gênero, faixa etária, escolaridade e estado civil aparecem em quatro sub-cards centralizados; cada percentual válido usa um gauge `go.Indicator(mode="gauge+number")` exibido com `st.plotly_chart`. Os percentuais são dimensões independentes, não partes de uma distribuição de 100%. O card usa contêineres nativos com borda e o mesmo fundo do painel de base eleitoral; seu CSS específico fica na própria página para não afetar o cabeçalho compartilhado.

O app também reconhece CSV, JSON, JSONL, XLS/XLSX e imagens ao listar o bucket, mas as seções analíticas atuais leem os artefatos tabulares acima como Parquet. JPG, JPEG e PNG podem fornecer a foto do candidato.

Na auditoria do bucket em 8 de outubro de 2026, cada candidato tinha 29 Parquets na pasta `2026/`. Os esquemas dos dois candidatos têm os mesmos nomes e tipos de coluna; somente a ordem das colunas difere em `IBGE/censo/genero_apond.parquet` e `IBGE/censo/idade_apond.parquet`. O leitor usa nomes, então essa diferença não altera as consultas. As contagens de linhas variam entre candidatos.

O arquivo anual `gastos/emendas_legislativa.parquet` tem esquema, mas está vazio para os dois candidatos; por isso o mapa estadual de atuação parlamentar exibe ausência de dados. A pasta especial `bh_2026/emendas/emendas_municipais.parquet` contém emendas para Belo Horizonte e alimenta o recorte por bairros. Esses registros estão no nível municipal, então seus valores são exibidos como total de BH, sem rateio entre bairros. Os demais arquivos de força local e gastos territoriais consultados estão presentes: `forca_local/stage07a_capital_local_municipios.parquet`, `forca_local/stage07b_afinidade_eleitos.parquet`, `forca_local/stage07b_afinidade_municipios.parquet`, `gastos/gastos_territoriais.parquet` e `gastos/gastos_territoriais_por_tipo.parquet`.

O leitor de emendas aceita os campos `valor_pago_atualizado`, `valor_empenhado_ano`, `valor_indicado` ou `valor_emenda`; combina identificadores de município por código IBGE ou nome e lê finalidade/tipo dos campos disponíveis no arquivo.

Na pasta especial `bh_2026`, `territorio/stage01b_bairros.parquet` traz votos históricos e os campos `diff_market_share_bairro_pp_vs_2020` e `diff_market_share_bairro_pp_vs_2024`. A comparação do mapa agrega os registros por bairro e calcula a diferença de participação em pontos percentuais usando os locais correspondidos entre as eleições.

O arquivo `bh_2026/territorio/stage07_bairros_estrategicos.parquet` classifica os bairros pelo campo `segmento_estrategico`. No filtro **Projeção 2028**, **Base crítica** aparece em azul (Base Crítica/Fortaleza), **Vulnerável** em amarelo e **Oportunidade de crescimento** em verde; as demais categorias ficam neutras. O mapa associa os bairros do arquivo estratégico aos códigos territoriais de 2026 e os cards laterais permanecem nos indicadores de 2026.

### Semântica dos gastos territoriais

Quando `gastos_territoriais_por_tipo.parquet` existe, cada linha municipal repete o total de campanha do tipo de despesa. O dashboard conta esse total uma vez e o divide pelos votos do território; o resultado é um **custo de referência**, não gasto observado naquele município.

Sem esse arquivo, o app usa `gastos_territoriais.parquet`, aplica o rateio proporcional disponível e informa a limitação na interface.

### Semântica da força política local

O mapa cruza `capital_local_0a100`, do stage 7a, com `pct_market_share`, do stage 1a. A nota é considerada alta acima de 50/100, corte que coincide com a entrada na faixa alta dos dados atuais. O market share municipal é considerado alto quando alcança ou supera a participação estadual do próprio candidato, calculada pela soma dos votos dividida pela soma dos votos válidos municipais.

`faixa_capital_local` não controla a cor porque possui três níveis (`baixa`, `media` e `alta`), enquanto a matriz visual exige dois eixos binários.

Os quatro cards laterais apresentam quantidade de municípios, participação nos votos do candidato, município líder e recomendação estratégica. Ao clicar em um card, sua classe permanece colorida e as demais são atenuadas; um segundo clique restaura o mapa completo.

O clique em um município usa a seleção de pontos do Plotly e abre um `st.dialog`. A janela combina votos e market share do stage 1a, indicadores de capital político do stage 7a e a composição nominal do stage 7b. O recorte geográfico mostra apenas o polígono municipal com a mesma cor do mapa estadual; a lista ao lado reúne prefeito e vereadores, com partido, vínculo político e afinidade.

## Geografia e mapas

As malhas são carregadas de `HF_GEOGRAPHY_PREFIX`:

| Arquivo | Papel |
| --- | --- |
| `MG_municipios_2022.parquet` | Moldura dos 853 municípios e mapas estaduais |
| `MG_mesorregioes_2022.parquet` | Polígonos e rótulos mesorregionais |
| `MG_bairros_CD2022.parquet` | Primeira opção da malha intramunicipal |
| `MG_AreaPonderada_CD2022.parquet` | Segunda opção da malha intramunicipal |
| `MG_setores_mapa_CD2022.parquet` | Fallback completo por município |

As referências `municipios_mg_mesorregioes.parquet`, `setor_bairro_lookup.parquet` e `crosswalk_setor_bairro.parquet` permanecem em `HF_GEOGRAPHY_REFERENCE_PREFIX`. O último arquivo relaciona os bairros do TSE aos setores censitários de referência e permite nomear, no tooltip, setores em que o candidato não recebeu votos.

O pipeline geográfico é:

```text
GeoParquet → metadados de CRS → WKB/Shapely → EPSG:4326 → GeoJSON → Plotly
```

As geometrias estaduais são simplificadas antes da conversão. O carregamento por setor usa filtro de `code_muni`, evitando ler toda a malha estadual em cada seleção.

Para o mapa intramunicipal, `territorial_mesh.municipality_mesh()` escolhe:

1. bairros oficiais, se cobrirem ao menos 95% do município;
2. áreas ponderadas, se houver pelo menos duas unidades;
3. todos os setores censitários quando o município possuir uma única área ponderada.

Linhas eleitorais sem código territorial aproveitável podem ser associadas por latitude/longitude ao polígono que contém o local de votação, ou ao polígono mais próximo dentro da tolerância definida. O contorno municipal é desenhado por cima da subdivisão escolhida.

O mapa estadual usa `log1p(votos)` para distribuir a intensidade. No mapa detalhado, a escala é linear até 5 mil votos no município e logarítmica acima desse total. No mapa **Como foi sua votação em Belo Horizonte**, a escala logarítmica de 2026 aplica gamma 0,8 após a normalização para suavizar a compressão e destacar variações entre bairros com votos baixos e médios; bairros com zero votos recebem cinza e ficam fora da escala. Esses ajustes são opcionais em `municipality_mesh_map()` e não alteram os demais mapas que usam os valores padrão.

## Cache e estado

- A listagem remota tem TTL de 600 segundos.
- Leituras de Parquet, malhas e referências usam `st.cache_data` sem TTL explícito.
- O `HfFileSystem` usa `st.cache_resource` por token.
- `sync_deputados(force=True)` limpa a listagem remota e os caches tabulares de `hf_sync.py`.
- A troca de deputado limpa `territorial_context`; os demais controles têm chaves próprias por seção.

Após substituir arquivos mantendo o mesmo caminho, reinicie o processo ou limpe o cache do Streamlit para evitar leitura antiga.

## Execução local

Requisitos: Python 3.12 recomendado e acesso ao bucket configurado.

```powershell
Copy-Item .env.example .env
python -m pip install -r requirements.txt
streamlit run app.py
```

O endereço padrão é `http://localhost:8501`.

Os scripts de preparação geográfica têm dependência separada:

```powershell
python -m pip install -r scripts/requirements.txt
```

Eles não são executados na inicialização do dashboard.

## Docker e deploy

A imagem usa Python 3.12 slim, executa o Streamlit na porta `8503` e possui healthcheck em `/_stcore/health`:

```powershell
docker build -t inteligencia-politica .
docker run --env-file .env -p 8503:8503 inteligencia-politica
```

Configuração usada no painel de deploy:

- repositório: `amichiautomacoes/inteligencia-politica`;
- branch: `main`;
- contexto de build: `/`;
- porta: `8503`.

O `Dockerfile` copia somente o necessário ao runtime (`app.py`, `hf_sync.py`, `pages/`, `src/`, `assets/` e `.streamlit/config.toml`). Dados locais, caches, `.env` e scripts de preparação ficam fora da imagem.

## Validação e manutenção

Não há suíte automatizada de testes neste repositório. Antes de publicar, execute ao menos:

```powershell
python -m compileall -q app.py pages src
git diff --check
streamlit run app.py
```

No smoke test, abra as três rotas, troque o deputado, altere os seletores territoriais e confirme os estados com e sem dados.

Regras de manutenção:

- não coloque módulos auxiliares em `pages/`;
- não versione `.env`, tokens, dados locais ou caches;
- preserve códigos territoriais como texto para não perder zeros nem alterar junções;
- ao mudar nomes de artefatos, atualize `file_by_kind()` e este contrato;
- ao mudar ordem, texto, cor, layout ou interação da interface, atualize também [Visual.md](Visual.md).
