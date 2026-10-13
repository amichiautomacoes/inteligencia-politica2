# Inteligência Política

Dashboard multipágina em Streamlit para análise eleitoral de candidaturas em Minas Gerais. A aplicação cruza votação territorial, perfil demográfico, despesas de campanha, emendas parlamentares e potencial de expansão com malhas oficiais do IBGE.

Este README é a referência técnica do projeto. A aparência, a hierarquia de informação, os estados de tela e as interações estão documentados no [briefing visual](Visual.md).

Documentação revisada em 12 de outubro de 2026 a partir das rotas e componentes chamados pelo código atual. As auditorias históricas do bucket abaixo não representam uma nova consulta remota.

## Escopo atual

| Rota | Arquivo | Responsabilidade |
| --- | --- | --- |
| `/raio-x-eleitoral` | `pages/raio_x_do_voto.py` | Votação estadual e de BH, força política local e concentração; seção de custo apenas com título |
| `/dna-eleitoral` | `pages/dna_eleitor.py` | Card do eleitor ideal, distribuição demográfica, clusters de ICP e expansão territorial para 2030 e potencial demográfico municipal |

`app.py` registra as duas rotas com `st.navigation`, descobre as pastas de candidatos na raiz configurada do Hugging Face e mantém a seleção em `st.session_state`. A troca de página preserva o candidato selecionado.

Os principais blocos implementados são:

- **Raio X:** força eleitoral estadual, histórico de votação em BH, força da política local, concentração territorial e cabeçalho de eficiência por custo do voto (sem conteúdo analítico).
- **DNA:** eleitor ideal, comparação BH/interior, distribuição demográfica, base eleitoral por clusters, expansão municipal para 2030 e potencial demográfico intramunicipal.
- **Potencial municipal:** diagnósticos setoriais stage 09b; em BH, agregação por bairro oficial IBGE; nos demais municípios, polígonos de setores censitários.

A seção de atuação parlamentar tem funções e leitores no código, mas não é chamada no fluxo atual do Raio X. Não constitui uma seção visível da página.

## Arquitetura

```text
.
├── app.py                         # Configuração, índice de candidatos e navegação
├── hf_sync.py                     # Acesso ao Hugging Face, descoberta e leitura dos arquivos
├── pages/
│   ├── raio_x_do_voto.py          # Página analítica principal
│   ├── dna_eleitor.py             # Página de perfil eleitoral e estilos locais do card ICP
├── src/eleitoral/
│   ├── common/
│   │   ├── shared_header.py       # Hero, navegação interna, CSS global e seleção compartilhada
│   │   └── dna_copy.py            # Normalização de textos do DNA
│   ├── dna/
│   │   ├── cluster_cards.py       # Cards expansíveis dos perfis de ICP
│   │   ├── dna_distribution.py    # Rosca e filtros demográficos
│   │   ├── dna_expansion.py       # Expansão municipal: stage 09b e fallback stage 08c
│   │   ├── sector_expansion.py    # Potencial por setores e agregação por bairro em BH
│   │   └── demographic_alignment.py # Cálculos auxiliares de alinhamento
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
HF_VISUALIZACAO_PREFIX="vereadores"
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

O prefixo padrao e `vereadores`. Valores vazios tambem resolvem para esse grupo. Variaveis do processo prevalecem sobre `.env`; outros prefixos explicitos continuam disponiveis. O grupo `dep_estaduais` fica fora da visualizacao atual.

### Descoberta de candidatos

O formato canônico é:

```text
vereadores/{pasta_do_candidato}/{ano}/...
```

`hf_sync.deputado_parts()` reconhece candidato e ano. O seletor exige uma pasta anual, como `2026`, preferindo esse ano. As consultas gerais usam somente a pasta anual; `bh_2026` fica reservado as consultas especificas de BH. **Atualizar candidatos** renova a listagem e limpa os caches tabulares.

Na consulta do bucket em 8 de outubro de 2026, os candidatos encontrados diretamente na raiz foram `bruno_miranda` e `marcela_tropia`. O bucket também contém pastas compartilhadas de geografia e processamento, que não são listadas como candidatos.

## Contrato de dados eleitorais

`hf_sync.file_by_kind()` resolve os artefatos abaixo pelo sufixo do caminho. Os nomes são parte do contrato entre a preparação dos dados e a visualização.

| Grupo | Arquivo esperado | Consumidor principal |
| --- | --- | --- |
| Território | `territorio/stage01a_municipios.parquet` | Cabeçalho (partido), mapa estadual, concentração, KPIs e votos totais |
| Território | `territorio/stage01b_bairros.parquet` | Mapa intramunicipal e detalhamento por bairro |
| Comparação de BH | `{candidato}/bh_2026/territorio/stage01b_bairros.parquet` | Votos de 2020/2024 e comparação de participação com 2026 no mapa de Belo Horizonte |
| Potencial demográfico de BH | `{candidato}/bh_2026/potencial_demografico/stage08c_potencial_demografico_icp_bairro.parquet` | Votos e comparação ICP/população por bairro e dimensão no filtro **Projeção 2028** |
| Emendas de BH | `{candidato}/bh_2026/emendas/emendas_municipais.parquet` | Leitor de emendas de BH; seção não chamada no fluxo atual |
| Demografia | `demografico/stage02_genero.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_idade.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_escolaridade.parquet` | Distribuição do eleitorado |
| Demografia | `demografico/stage02_estado_civil.parquet` | Distribuição do eleitorado |
| Perfil | `perfil/stage04_icp_geral_geo.parquet` | Eleitor ideal |
| Perfil | `perfil/stage03_icp_clusters_geo.parquet`, com fallback para `perfil/stage04_icp_clusters_geo.parquet` | Base eleitoral e classificações estratégicas |
| Diagnóstico municipal | `potencial_demografico/stage09b_diagnostico_geral_municipio.parquet` | Expansão estadual do eleitor ideal |
| Diagnóstico municipal | `potencial_demografico/stage09b_diagnostico_clusters_municipio.parquet` | Expansão estadual por classificação de clusters |
| Diagnóstico setorial | `potencial_demografico/stage09b_diagnostico_geral_setor.parquet` | Potencial intramunicipal do eleitor ideal |
| Diagnóstico setorial | `potencial_demografico/stage09b_diagnostico_clusters_setor.parquet` | Potencial intramunicipal por classificação de clusters |
| Gastos | `gastos/gastos_por_tipo.parquet` | Leitor disponível; sem consumo na seção atual de custo do voto |
| Gastos | `gastos/gastos_municipais_teoricos.parquet` | Disponível no bucket; ainda não utilizado na interface |
| Emendas | `gastos/emendas_legislativa.parquet` (ou `emendas/emendas_municipais.parquet`, quando fornecido) | Funções de atuação parlamentar; seção não chamada no fluxo atual |
| Força local | `forca_local/stage07a_capital_local_municipios.parquet` | Quadrantes de efetividade da estrutura política municipal |
| Força local | `forca_local/stage07b_afinidade_eleitos.parquet` | Composição nominal de prefeitos e vereadores no detalhe municipal |
| Censo | `IBGE/censo/genero_apond.parquet` | Cálculo da expansão |
| Censo | `IBGE/censo/idade_apond.parquet` | Cálculo da expansão |
| Censo | `IBGE/censo/escolaridade_apond.parquet` | Cálculo da expansão |
| Potencial | `potencial_demografico/stage08c_potencial_demografico_icp_geral.parquet` | Expansão para o eleitor ideal |
| Potencial | `potencial_demografico/stage08c_potencial_demografico_icp_clusters.parquet` | Expansão por classificação de ICP |

### Card do eleitor ideal — DNA Eleitoral

`pages/dna_eleitor.py` consolida o parquet `perfil/stage04_icp_geral_geo.parquet` para apresentar a persona predominante como badges por atributo. Gênero, faixa etária, escolaridade e estado civil aparecem em quatro sub-cards centralizados; cada percentual válido usa um gauge `go.Indicator(mode="gauge+number")` exibido com `st.plotly_chart`. Os percentuais são dimensões independentes, não partes de uma distribuição de 100%. O leitor prioriza `pct_{dimensao}_principal` e usa `pct_{dimensao}_principal_global` quando a coluna local não existe; não usa o percentual conjunto como percentual marginal. O card usa contêineres nativos com borda e o mesmo fundo do painel de base eleitoral; seu CSS específico fica na própria página para não afetar o cabeçalho compartilhado.

O app também reconhece CSV, JSON, JSONL, XLS/XLSX e imagens ao listar o bucket, mas as seções analíticas atuais leem os artefatos tabulares acima como Parquet. JPG, JPEG e PNG podem fornecer a foto do candidato.

Na auditoria do bucket em 8 de outubro de 2026, cada candidato tinha 29 Parquets na pasta `2026/`. Os esquemas dos dois candidatos têm os mesmos nomes e tipos de coluna; somente a ordem das colunas difere em `IBGE/censo/genero_apond.parquet` e `IBGE/censo/idade_apond.parquet`. O leitor usa nomes, então essa diferença não altera as consultas. As contagens de linhas variam entre candidatos.

O arquivo anual `gastos/emendas_legislativa.parquet` tem esquema, mas está vazio para os dois candidatos; essas fontes não alimentam uma seção visível de atuação parlamentar no fluxo atual. A pasta especial `bh_2026/emendas/emendas_municipais.parquet` contém emendas para Belo Horizonte e pode ser lida pelas funções de atuação parlamentar, atualmente fora do fluxo de renderização. Esses registros estão no nível municipal, então seus valores são exibidos como total de BH, sem rateio entre bairros. Os arquivos de força local consultados estão presentes: `forca_local/stage07a_capital_local_municipios.parquet`, `forca_local/stage07b_afinidade_eleitos.parquet` e `forca_local/stage07b_afinidade_municipios.parquet`. Em `2026/gastos`, os arquivos atuais são `gastos_por_tipo.parquet` e `gastos_municipais_teoricos.parquet`.

O leitor de emendas aceita os campos `valor_pago_atualizado`, `valor_empenhado_ano`, `valor_indicado` ou `valor_emenda`; combina identificadores de município por código IBGE ou nome e lê finalidade/tipo dos campos disponíveis no arquivo.

Na pasta especial `bh_2026`, `territorio/stage01b_bairros.parquet` traz votos históricos e os campos `diff_market_share_bairro_pp_vs_2020` e `diff_market_share_bairro_pp_vs_2024`. A comparação do mapa agrega os registros por bairro e calcula a diferença de participação em pontos percentuais usando os locais correspondidos entre as eleições.

O filtro **Projeção 2028** usa `bh_2026/potencial_demografico/stage08c_potencial_demografico_icp_bairro.parquet` do candidato selecionado, encontrado nesse caminho na consulta de 8 de outubro de 2026, e não em `IBGE/censo`. O alias `bh_potencial_bairro` resolve essa fonte. `src/eleitoral/maps/bh_projection.py` calcula a média simples de `pct_icp_categoria - pct_populacao_categoria` em gênero, idade e escolaridade, exigindo as três comparações válidas e `situacao_icp=calculado`. As dimensões são marginais independentes; a média não descreve um perfil conjunto individual. Os votos repetidos por dimensão não são somados: usa-se `qt_votos_candidato_bairro` uma vez por bairro (máximo).

Base forte significa votos iguais ou superiores à mediana dos bairros com voto do candidato. Base forte com índice não negativo recebe **Base Crítica (Fortaleza)** (azul); base forte com índice negativo recebe **Vulnerável** (amarelo); votação abaixo da mediana com índice negativo recebe **Oportunidade** (verde); demais situações e comparações incompletas ficam neutras. “Vulnerável” indica espaço demográfico na base existente, sem inferir queda histórica ou risco causal. Não é previsão de votos para 2028.

A associação geográfica usa `cd_bairro` do TSE no arquivo territorial de `bh_2026`; o nome normalizado é fallback apenas quando é único na fonte de potencial. O código municipal TSE `41238` corresponde ao IBGE `3106200` nessa seção. Os tooltips exibem votos de referência e diferença média em pontos percentuais. As quatro pílulas mantêm os rótulos e cores, sem parágrafo de critérios abaixo da legenda; a nota analítica permanece abaixo do mapa. Os cards laterais permanecem nos indicadores de 2026. A fonte antiga `stage07_bairros_estrategicos.parquet` não alimenta mais esse filtro.

### Comparação entre capital e interior — DNA Eleitoral

A capital procura `bh_vereador/perfil/icp_geral_por_bairro.parquet`, com fallback para `bh_2026/perfil/icp_geral_por_bairro.parquet`. A raiz do candidato e identificada na base selecionada, anual ou BH. Em BH, `qt_votos_candidato_bairro` fornece os pesos e `situacao_icp=calculado` delimita os perfis válidos.

O interior exclui BH e usa um único nível territorial do perfil geral. Quando `metodo_icp_geo` indica o perfil estadual replicado, o cálculo usa as distribuições municipais stage 02, excluindo BH. Para perfis locais, a categoria predominante reúne o maior peso em votos e seu percentual é a média ponderada entre os territórios onde lidera. As barras representam dimensões independentes. A interface mostra badges e barras, sem rodapé de metodologia ou fonte.

### Base eleitoral por clusters — DNA Eleitoral

O alias `icp_clusters` prioriza o stage 03 e mantém fallback para o stage 04 antigo. Usa-se um único nível territorial, priorizando município e depois bairro. A participação de cada cluster é a soma de `votos_candidato` dividida por `total_votos_candidato` quando fornecido; na ausência desse total, usa-se a soma dos votos dos registros classificados. Não se somam market shares locais. Cada cluster conserva atributos, classificação e justificativa; clusters da mesma classe permanecem separados.

### Expansão estadual e potencial intramunicipal — DNA Eleitoral

`dna_expansion.render_vote_expansion()` usa o diagnóstico municipal stage 09b quando a leitura do diagnóstico geral retorna um DataFrame, mesmo vazio. Sem essa fonte, mantém o cálculo legado stage 08c com Censo por área ponderada, agregado por município. O seletor oferece **ELEITOR IDEAL** e classificações estratégicas. No stage 09b, as classificações são ligadas aos identificadores de perfil do arquivo de clusters.

O diagnóstico agrega votos e população estimada do ICP, mantém a população de referência uma vez por território e exige cobertura completa, referência positiva e parcela do ICP entre 0 e 100%. Os cortes são relativos ao perfil: azul tem prioridade e identifica votos positivos no quartil superior; verde exige população estimada positiva no quartil superior e parcela na referência igual ou superior à mediana; amarelo indica população estimada positiva fora desses critérios; os demais ficam cinza. O diagnóstico cobre setores associados e não representa totais completos dos municípios. Clusters usam votos probabilísticos. O tooltip mostra votos associados, população estimada do ICP e sua parcela na referência. O fallback stage 08c conserva oportunidade por diferenças marginais e similaridade, com legenda e nota próprias.

`sector_expansion.render_municipal_expansion()` usa exclusivamente os diagnósticos setoriais stage 09b, sem fallback para áreas ponderadas. Os filtros são **Mesorregião → Município → Perfil para expansão**. A malha completa de setores é carregada por `code_muni` e ligada por `cd_setor_censitario = code_tract`. Referência repetida por cluster é usada uma vez por setor; votos e população estimada são somados com preservação de ausências. As classes são calculadas sobre todos os setores disponíveis do perfil antes do filtro municipal.

Os nomes e códigos de bairros vêm do crosswalk (`id_unidade`, `ibge_codigo_bairro_do_ponto`, `ibge_bairro_do_ponto`) e do índice oficial `setor_bairro_lookup.parquet`, por código exato de setor. Em BH (`3106200`), apenas vínculos com código único de bairro IBGE entram na agregação: votos, população estimada e referência são somados uma vez por setor diagnosticado, e os cortes são recalculados entre bairros. A geometria é `MG_bairros_CD2022.parquet`. Isso não completa a população nem os votos ausentes do bairro. Nos demais municípios, a geometria continua setorial.

O mapa tem 640 px; os quatro cards contam **Bairros** em BH e **Áreas** nos demais municípios. O hover identifica **Bairro: nome**, sem códigos territoriais visíveis, seguido da classe, votos associados, população estimada e parcela do ICP na referência. Áreas sem diagnóstico permanecem cinza e valores ausentes aparecem como indisponíveis. Votos associados a locais de votação não indicam residência; potencial demográfico não é previsão de votos.

### EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO

A seção renderiza o cabeçalho com o título **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO** e o subtítulo `Análise do retorno do investimento eleitoral: veja onde o orçamento foi alocado e quanto custou a conquista de cada voto.`. Abaixo, `_section_header()` introduz **BALANÇO MACRO & LIQUIDEZ DE CAIXA**, com o subtítulo `Raio-x executivo da arrecadação e dos compromissos financeiros: monitore o saldo real de caixa, o volume contratado e a saúde orçamentária da campanha.`. Ainda não há indicadores ou gráficos nessa subseção. O fluxo da página não carrega `gastos_por_tipo.parquet` nem executa os cálculos e componentes de gastos. As funções auxiliares anteriores permanecem no código, fora do fluxo de renderização.

As fontes continuam reconhecidas pelo leitor: `gastos_por_tipo.parquet` registra totais por tipo, enquanto `gastos_municipais_teoricos.parquet` contém rateio proporcional aos votos, não gasto municipal observado. Nenhuma delas alimenta a interface atual.

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

No smoke test, abra as duas rotas, troque o deputado, altere os seletores territoriais e confirme os estados com e sem dados.

Regras de manutenção:

- não coloque módulos auxiliares em `pages/`;
- não versione `.env`, tokens, dados locais ou caches;
- preserve códigos territoriais como texto para não perder zeros nem alterar junções;
- ao mudar nomes de artefatos, atualize `file_by_kind()` e este contrato;
- ao mudar ordem, texto, cor, layout ou interação da interface, atualize também [Visual.md](Visual.md).

## Atualizacao de caminhos HF (13/10/2026)

Esta organizacao substitui o layout na raiz descrito anteriormente. O prefixo padrao agora e `vereadores`; configuracoes vazias tambem usam esse grupo. O seletor lista candidatos com dados em pasta anual. O grupo `dep_estaduais` fica fora desta visualizacao.

O formato atual e `vereadores/{candidato}/{ano}/...`. Todos os vereadores seguem o mesmo contrato: pasta anual para consultas gerais e `bh_2026` para consultas especificas de BH. Marcela possui ambas; Bruno e Pablo ainda aguardam suas pastas `2026` e so aparecem no seletor quando houver arquivos anuais. Fontes ausentes mantem os estados de indisponibilidade.

A navegacao usa `st.navigation(position="hidden")`: as rotas continuam registradas e os botoes do hero fazem a troca. A barra lateral apresenta Cargo Atual (Vereadores) e Candidato, com nomes sem slug.

## Selecao por cargo e remocao de emendas (13/10/2026)

Cargo Atual oferece Vereadores (`vereadores/`) e Deputados Estaduais (`dep_estaduais/`). A escolha determina a raiz consultada no HF e filtra os candidatos pela pasta. Ao trocar cargo, os estados da candidatura e das visualizacoes sao reiniciados; a navegacao continua pelos botoes do hero. O contrato exige pasta anual nos dois grupos. Esta regra substitui as referencias anteriores a um unico cargo.

Para deputados estaduais, Raio X oculta Como foi sua votacao em Belo Horizonte e DNA oculta Eleitor de BH x Eleitor do Interior. Vereadores conservam essas secoes. As demais secoes permanecem compartilhadas. O componente antigo de atuacao parlamentar/emendas, incluindo mapa, cards, dialogo e tabelas, foi removido a pedido; nenhuma nova secao de emendas foi implementada. Referencias anteriores a essas funcoes descrevem o estado historico. Os arquivos do HF foram preservados.
