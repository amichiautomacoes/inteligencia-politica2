# Inteligência Política

Dashboard multipágina em Streamlit para inteligência eleitoral de deputados estaduais em Minas Gerais. RaioX Territorial reúne votação territorial e concentração; DNA Eleitoral reúne perfil demográfico e potencial de expansão; DRE Campanha concentra toda a seção EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO; Impacto político reúne força da política local e atuação parlamentar de acordo com os votos. Os dados eleitorais são lidos do prefixo configurado no bucket do Hugging Face, por candidato e ano.

Este README é a referência técnica do projeto. A aparência, a hierarquia de informação, os estados de tela e as interações estão documentados no [briefing visual](Visual.md).

### Regra vigente — sem áreas ponderadas nos mapas

Na página 1, todos os mapas setoriais também usam a malha completa por município, preservam geometrias vinculadas do crosswalk e desenham o contorno municipal IBGE. Votação atual usa cinza nos setores sem votos associados; históricos usam cinza sem comparação; Projeção 2030 usa cinza nos setores sem vínculo ou diagnóstico. Bairros oficiais e mapas estaduais mantêm suas malhas. Esta regra substitui as referências anteriores à cobertura restrita ao crosswalk na página 1.

No Potencial demográfico municipal, a cobertura é a malha completa `MG_setores_mapa_CD2022.parquet` por município, com o contorno externo de `MG_municipios_2022.parquet`, ambos em `HF_GEOGRAPHY_PREFIX`. Setores com vínculo TSE usam a geometria do crosswalk, recortada ao limite municipal; setores sem vínculo ou sem diagnóstico ficam cinza. A malha completa complementa os setores ausentes do crosswalk. Os cards continuam contando apenas bairros TSE vinculados, sem inventar bairros para setores sem relação. Esta regra substitui a cobertura limitada ao crosswalk descrita anteriormente para essa seção.

Os cards do Potencial demográfico municipal contam bairros TSE distintos (`cd_bairro`) ligados aos setores exibidos em cada classe, em todas as cidades. Vários setores do mesmo bairro na mesma classe contam uma vez; um bairro com setores em classes diferentes pode entrar em mais de um card. O mapa e os critérios permanecem setoriais. Esta regra substitui a indicação anterior de contagem de setores nos cards.

O Potencial demográfico municipal não lê `setor_bairro_lookup.parquet` nem atributos IBGE de bairro: o diagnóstico liga diretamente ao código do setor e os nomes TSE vêm do crosswalk com geometria. O helper de vínculos IBGE permanece disponível para outros componentes que ainda agregam por bairros oficiais.

Na página DNA Eleitoral, a seção **Potencial demográfico municipal** usa exclusivamente setores censitários em todas as cidades, inclusive Belo Horizonte. Não agrega diagnósticos nem geometrias por bairro nessa seção. Os cards contam setores censitários e os cortes permanecem calculados no nível setorial antes do filtro municipal. Esta regra substitui as descrições anteriores da exceção de BH para esse bloco; não altera outros mapas.

Nenhum mapa usa áreas ponderadas. Quando a visualização não usa municípios, mesorregiões ou bairros oficiais, usa setores censitários de `crosswalk_setor_bairro.parquet`, em `HF_GEOGRAPHY_REFERENCE_PREFIX=IBGE/MG/dadosterritorio`. Não existe mais corte por quantidade de áreas ponderadas para escolher a malha. Esta regra substitui as descrições históricas abaixo sobre geometrias de áreas ponderadas. Dados censitários legados por área podem continuar compondo agregados municipais, sem desenhar áreas ponderadas.

### Histórico da atualização das malhas intramunicipais — crosswalks com geometry

Esta regra substitui as referências abaixo ao uso de `MG_AreaPonderada_CD2022.parquet`, `MG_setores_mapa_CD2022.parquet` e coordenadas para vincular votos a essas unidades. Todos os mapas que precisam de áreas ponderadas ou setores usam, respectivamente, `crosswalk_area_ponderada_bairro.parquet` e `crosswalk_setor_bairro.parquet`, em `HF_GEOGRAPHY_REFERENCE_PREFIX` (padrão `IBGE/MG/dadosterritorio`). A coluna `geometry` fornece os polígonos, decodificados conforme o CRS do GeoParquet e convertidos para EPSG:4326. Mapas estaduais e bairros oficiais mantêm suas malhas próprias, inclusive as exceções de BH.

`cd_ibge_municipio` delimita o município; `cd_bairro` do TSE cruza os registros eleitorais e `id_unidade` identifica o polígono. Os códigos numéricos do crosswalk são normalizados sem o sufixo decimal `.0`, preservando códigos TSE textuais. Geometrias repetidas por bairro são exibidas uma vez por unidade; votos de bairros diferentes na mesma unidade são somados sem multiplicação de registros. Vínculos ausentes ou ambíguos não recebem associação por proximidade. Os históricos usam o mesmo vínculo; os diagnósticos stage 09b continuam ligados pelo código exato do setor, preservando sua semântica demográfica.

A cobertura intramunicipal passa a ser a das unidades com geometria presentes no crosswalk, não a malha completa de setores do município. Unidades representadas sem diagnóstico permanecem cinza; setores fora do crosswalk não são desenhados. Os limites de quantidade de áreas ponderadas para escolher a granularidade permanecem, contando as unidades disponíveis no crosswalk.

Documentação atualizada em 16 de outubro de 2026 para o escopo exclusivo de deputados estaduais. As auditorias históricas do bucket abaixo não representam uma nova consulta remota.

## Escopo atual

| Rota | Arquivo | Responsabilidade |
| --- | --- | --- |
| `/raio-x-eleitoral` | `pages/raio_x_do_voto.py` | Votação estadual e intramunicipal e concentração territorial dos votos |
| `/dre-campanha` | `pages/dre_campanha.py` | Toda a seção EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO: balanço macro, receita, execução e origem/destino dos recursos |
| `/dna-eleitoral` | `pages/dna_eleitor.py` | Card do eleitor ideal, distribuição demográfica, clusters de ICP e expansão territorial para 2030 e potencial demográfico municipal |
| `/impacto-politico` | `pages/impacto_politico.py` | Força da política local e Mapa da atuação parlamentar de acordo com os votos, com indicadores, filtros e detalhes municipais |

`app.py` registra as quatro rotas com `st.navigation(position="hidden")`. A navegação ocorre no sidebar: abaixo do selectbox Candidato ficam os botões RaioX Territorial, DNA do Eleitor, DRE Campanha e Impacto político, nessa ordem e empilhados. Todos navegam e destacam a página ativa. Não há título adicional, botão de atualização ou seletor de cargo. O fundo da barra usa glassmorphism azul com 60% de opacidade e blur de 18 px, definido em `shared_header.py` para as quatro páginas. A troca de página preserva o deputado selecionado. O prefixo configurado no ambiente determina a pasta consultada no Hugging Face. Sem candidatos, o selectbox permanece desabilitado; avisos de ausência ou erro aparecem na área principal.

Os principais blocos implementados são:

- **RaioX Territorial:** força eleitoral estadual, votação por bairros e concentração territorial.
- **Impacto político:** força da política local e atuação parlamentar, com os mesmos mapas, cards, filtros de classe e diálogos municipais anteriores.
- **DRE Campanha:** balanço macro e liquidez de caixa, estrutura da receita, contratado × pago e origem/destino dos recursos, com os mesmos indicadores, filtros, gráficos e tabelas financeiros anteriores.
- **DNA:** eleitor ideal, distribuição demográfica, base eleitoral por clusters, expansão municipal para 2030 e potencial demográfico intramunicipal.
- **Potencial municipal:** diagnósticos setoriais stage 09b; em BH, agregação por bairro oficial IBGE; nos demais municípios, polígonos de setores censitários.

### Escopo exclusivo de deputados estaduais

RaioX Territorial, DNA Eleitoral, DRE Campanha e Impacto político atendem exclusivamente deputados estaduais. Não há seletor de cargo nem páginas compartilhadas entre cargos. A votação histórica exclusiva dos vereadores de BH e a comparação capital/interior foram removidas. O RaioX Territorial encerra com concentração; força da política local e emendas ficam exclusivamente em Impacto político, nessa ordem. Toda a análise financeira fica exclusivamente em DRE Campanha.

## Arquitetura

As quatro páginas compartilham a hierarquia das faixas: seções principais com barra ciano de 12 px e brilho neon; subseções com barra neutra de 3 px, sem brilho. Os estilos comuns de cabeçalho e KPIs estão em `shared_header.py`; o modelo visual local do RaioX Territorial mantém os estilos específicos de seus blocos.

```text
.
├── app.py                         # Configuração, índice de candidatos e navegação
├── hf_sync.py                     # Acesso ao Hugging Face, descoberta e leitura dos arquivos
├── pages/
│   ├── raio_x_do_voto.py          # Página analítica principal
│   ├── dna_eleitor.py             # Página de perfil eleitoral e estilos locais do card ICP
│   ├── dre_campanha.py            # Seção financeira completa da campanha
│   └── impacto_politico.py        # Força política local e atuação parlamentar
├── src/eleitoral/
│   ├── common/
│   │   ├── shared_header.py       # Hero, navegação, estilos e leitura da seleção compartilhada
│   │   ├── local_political_strength.py # Força local, cards e diálogo municipal
│   │   └── dna_copy.py            # Normalização de textos do DNA
│   ├── deputados/                 # Emendas e atuação parlamentar de deputados estaduais
│   ├── dna/
│   │   ├── cluster_cards.py       # Cards expansíveis dos perfis de ICP
│   │   ├── dna_distribution.py    # Rosca e filtros demográficos
│   │   ├── dna_expansion.py       # Expansão municipal: stage 09b e fallback stage 08c
│   │   ├── sector_expansion.py    # Potencial por setores e agregação por bairro em BH
│   │   └── demographic_alignment.py # Cálculos auxiliares de alinhamento
│   └── maps/
│       ├── choropleth_maps.py      # Coropléticos estaduais e de força política local
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

### Organização dos componentes

`app.py` é a entrada única das quatro páginas de deputados estaduais. Não há desvio de renderização por cargo nem estado `candidate_group`.

- `src/eleitoral/deputados/emendas.py` e `emendas_map.py`: atuação parlamentar, indicadores, legendas, diálogo e mapa.
- `src/eleitoral/deputados/neighborhood_elections.py`: seletor 2018/2022/2026/Projeção 2030, históricos e diagnóstico de expansão na votação por bairros.
- `src/eleitoral/common/neighborhood_voting.py`: votação por bairros dentro dos municípios, logo após o Mapa de Força Eleitoral e antes da concentração territorial no RaioX.
- `src/eleitoral/common/local_political_strength.py`: mapa, cards de classe e diálogo da força política local, usados por Impacto político.
- `src/eleitoral/common/`: cabeçalho, perfis, cards, mapas eleitorais e componentes financeiros reutilizados pela aplicação.
- `src/eleitoral/dna/` e `maps/`: demografia, expansão e referências geográficas.

As quatro páginas usam `read_selected_parquet()` de `shared_header.py` para resolver a seleção, ler os arquivos via `hf_sync.py` e apresentar os mesmos avisos de indisponibilidade. DRE Campanha e Impacto político compõem seus componentes sem importar ou executar outra página. O cabeçalho usa `render_page_header()`; as seções principais usam `major_section_header()` e as subseções financeiras usam `section_header(..., compact=True)`, com os estilos centralizados no CSS compartilhado. Módulos auxiliares ficam fora de `pages/`.

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
HF_VISUALIZACAO_PREFIX="dep_estadual"
HF_GEOGRAPHY_PREFIX="IBGE/malha_mapas"
HF_GEOGRAPHY_REFERENCE_PREFIX="IBGE/MG/dadosterritorio"
HF_TOKEN="seu_token"
```

| Variável | Uso |
| --- | --- |
| `HF_BUCKET_URL` | Raiz do bucket acessado pelo `HfFileSystem`; obrigatória |
| `HF_VISUALIZACAO_PREFIX` | Pasta dos deputados estaduais; padrão `dep_estadual`, também usado quando o valor está vazio |
| `HF_GEOGRAPHY_PREFIX` | GeoParquets otimizados usados nos mapas |
| `HF_GEOGRAPHY_REFERENCE_PREFIX` | Tabelas auxiliares de códigos e nomes territoriais |
| `HF_TOKEN` | Autenticação do Hugging Face; não deve ser versionada |

O prefixo padrão é `dep_estadual`; um valor vazio também resolve para essa pasta. Não há seleção de cargo nem substituição do prefixo pelo estado da sessão. Configure `HF_VISUALIZACAO_PREFIX="dep_estadual"` também no EasyPanel quando houver variável de processo definida. Variáveis do processo prevalecem sobre `.env`. Nunca versione tokens.

Os dados precisam estar publicados nessa pasta no bucket. Alterar o prefixo não renomeia nem move os arquivos remotos; não há fallback para os grupos antigos.

O nome precisa coincidir exatamente com a pasta existente no bucket: para acessar os dados em `dep_estaduais/`, configure `HF_VISUALIZACAO_PREFIX="dep_estaduais"`. O ambiente local usa esse valor enquanto os dados estiverem nessa pasta. O cargo exibido permanece Deputado Estadual, independentemente do nome do prefixo.

### Descoberta de candidatos

O formato canônico é:

```text
dep_estadual/
└── {pasta_do_candidato}/
    └── {ano}/
        ├── territorio/
        ├── demografico/
        ├── perfil/
        ├── potencial_demografico/
        ├── forca_local/
        ├── emendas/
        └── gastos/
```

`hf_sync.deputado_parts()` reconhece candidato e ano dentro do prefixo configurado e identifica o cargo como **Deputado Estadual**. O seletor exige uma pasta anual com quatro dígitos, prefere `2026` e usa o ano numérico mais recente quando necessário. As consultas usam somente a pasta anual do candidato selecionado. Pastas especiais como `bh_2026` e grupos antigos não alimentam as páginas. A listagem remota usa cache de 600 segundos, renovado no próximo acesso após expirar. O helper `sync_deputados(force=True)` continua disponível no código para renovar a listagem e os caches tabulares, sem botão na interface.

As pastas compartilhadas do bucket, como IBGE, não são candidaturas. A árvore acima descreve o contrato de caminhos, sem representar uma nova auditoria remota do conteúdo.

## Contrato de dados eleitorais

`hf_sync.file_by_kind()` resolve os artefatos abaixo pelo sufixo do caminho. Os nomes são parte do contrato entre a preparação dos dados e a visualização. Os caminhos anuais são relativos a `dep_estadual/{candidato}/{ano}/`, ou ao prefixo equivalente configurado no ambiente.

| Grupo | Arquivo esperado | Consumidor principal |
| --- | --- | --- |
| Território | `territorio/stage01a_municipios.parquet` | Cabeçalho (partido), mapa estadual, concentração, KPIs e votos totais |
| Território | `territorio/stage01b_bairros.parquet` | Mapa intramunicipal e detalhamento por bairro |



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
| Emendas | `emendas/emendas_legislativa.parquet` (fallback para `emendas/emendas_municipais.parquet` e `gastos/emendas_legislativa.parquet`) | Atuação parlamentar, exclusiva de deputados |
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







### Base eleitoral por clusters — DNA Eleitoral

O alias `icp_clusters` prioriza o stage 03 e mantém fallback para o stage 04 antigo. Usa-se um único nível territorial, priorizando município e depois bairro. A participação de cada cluster é a soma de `votos_candidato` dividida por `total_votos_candidato` quando fornecido; na ausência desse total, usa-se a soma dos votos dos registros classificados. Não se somam market shares locais. Cada cluster conserva atributos, classificação e justificativa; clusters da mesma classe permanecem separados.

### Expansão estadual e potencial intramunicipal — DNA Eleitoral

No hover dos mapas do DNA, ausência de associação ao diagnóstico exibe **0 votos** apenas como valor de apresentação; votos nulos em registros existentes continuam **Indisponível**. O mapa estadual identifica o município oficial. No Potencial demográfico municipal, inclusive em BH, os setores mostram nomes TSE pelo vínculo exato do crosswalk, sem códigos; nomes vazios não geram rótulos em branco e ausência de referência mostra **Bairro sem referência disponível**. As classes, estimativas, métricas e contagens dos cards não são alteradas por esse tratamento do hover. População e participação ausentes permanecem indisponíveis.

`dna_expansion.render_vote_expansion()` usa o diagnóstico municipal stage 09b quando a leitura do diagnóstico geral retorna um DataFrame, mesmo vazio. Sem essa fonte, mantém o cálculo legado stage 08c com Censo por área ponderada, agregado por município. O seletor oferece **ELEITOR IDEAL** e classificações estratégicas. No stage 09b, as classificações são ligadas aos identificadores de perfil do arquivo de clusters.

O diagnóstico agrega votos e população estimada do ICP, mantém a população de referência uma vez por território e exige cobertura completa, referência positiva e parcela do ICP entre 0 e 100%. Os cortes são relativos ao perfil: azul tem prioridade e identifica votos positivos no quartil superior; verde exige população estimada positiva no quartil superior e parcela na referência igual ou superior à mediana; amarelo indica população estimada positiva fora desses critérios; os demais ficam cinza. O diagnóstico cobre setores associados e não representa totais completos dos municípios. Clusters usam votos probabilísticos. O tooltip mostra votos associados, população estimada do ICP e sua parcela na referência. O fallback stage 08c conserva oportunidade por diferenças marginais e similaridade, com legenda e nota próprias.

`sector_expansion.render_municipal_expansion()` usa exclusivamente os diagnósticos setoriais stage 09b, sem fallback para áreas ponderadas. Os filtros são **Mesorregião → Município → Perfil para expansão**. A malha completa de setores é carregada por `code_muni` e ligada por `cd_setor_censitario = code_tract`. Referência repetida por cluster é usada uma vez por setor; votos e população estimada são somados com preservação de ausências. As classes são calculadas sobre todos os setores disponíveis do perfil antes do filtro municipal.

Os nomes e códigos de bairros vêm do crosswalk (`id_unidade`, `ibge_codigo_bairro_do_ponto`, `ibge_bairro_do_ponto`) e do índice oficial `setor_bairro_lookup.parquet`, por código exato de setor. Em BH (`3106200`), apenas vínculos com código único de bairro IBGE entram na agregação: votos, população estimada e referência são somados uma vez por setor diagnosticado, e os cortes são recalculados entre bairros. A geometria é `MG_bairros_CD2022.parquet`. Isso não completa a população nem os votos ausentes do bairro. Nos demais municípios, a geometria continua setorial.

O mapa tem 640 px; os quatro cards contam **Bairros** em BH e **Áreas** nos demais municípios. O hover identifica **Bairro: nome**, sem códigos territoriais visíveis, seguido da classe, votos associados, população estimada e parcela do ICP na referência. Áreas sem diagnóstico permanecem cinza e valores ausentes aparecem como indisponíveis. Votos associados a locais de votação não indicam residência; potencial demográfico não é previsão de votos.

### DRE Campanha — EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO

Esta seção inteira pertence exclusivamente a `pages/dre_campanha.py`, na rota `/dre-campanha`. O RaioX Territorial não renderiza nem carrega seus cinco artefatos financeiros. A nova página usa o hero padrão com foto, nome, cargo, partido e total de votos do candidato, além do mesmo sidebar e navegação. Os cálculos, recortes, componentes e chaves dos filtros financeiros foram preservados.

Os quatro cabeçalhos internos usam a classe `financial-subsection`, com largura integral, composição compacta, títulos menores que os da seção principal, fundo azul discreto e faixa lateral para identificar as subseções.

Layout atual da subseção 1: a composição das receitas ocupa a coluna esquerda (50%); a coluna direita (50%) reúne os cards de funil e comprometimento orçamentário empilhados. O gauge deixa de ocupar uma linha independente centralizada.

Na metade direita do ranking de doadores, dois cards empilhados mostram a concentração e o ranking completo. A rosca usa a participação do Top 10; quando a cobertura é conhecida, separa os demais doadores identificados da receita sem atribuição. O ranking completo usa `st.dataframe` somente para leitura dentro de expander, com posição, nome, CPF/CNPJ como texto, valor em reais, percentual com barra de progresso e quantidade de receitas vinculadas. Ambos usam doadores imediatos; visualizações sem dados são omitidas.

Após os KPIs da receita, o ranking **Top 10 Doadores** usa barras horizontais `go.Bar` com `nm_doador` e `valor_atribuido` dos ranks 1 a 10 de doadores imediatos. Ocupa os 50% esquerdos da linha. Registros sem nome/valor válido são omitidos, sem promover ranks posteriores ao décimo; sem dados válidos, o gráfico fica oculto.

Os KPIs de doadores usam somente `tipo_doador=imediato` quando a coluna existe, evitando misturar o ranking originário com o imediato. Cada KPI sem dados é omitido; sem indicadores disponíveis, a linha de cards não é desenhada. Essa regra substitui a exibição de Indisponível nos KPIs da estrutura da receita.

A subseção Estrutura da Receita usa `gastos/stage05b_concentracao_doadores.parquet` (alias `concentracao_doadores`) do candidato selecionado. Quatro KPIs mostram nome/valor do rank 1, soma de `pct_receita_total` dos ranks 1 a 10, valor único de `cobertura_atribuicao_pct` e quantidade de registros do ranking unificado. Com menos de dez doadores, soma os existentes. Cobertura repetida não é somada; campos ausentes ou inconsistentes ficam indisponíveis. A leitura e os cards são reutilizados na aplicação.

Após as visualizações do balanço macro, a subseção 2 **ESTRUTURA DA RECEITA**, com subtítulo **Origem e concentração dos recursos da campanha**, apresenta seu card de cabeçalho interno, da aplicação de deputados estaduais. O conteúdo analítico será definido em etapa posterior.

Centralizado abaixo da rosca e do funil, o gauge de comprometimento calcula `despesa_contratada / receita_total * 100`. Exige receita positiva e despesas não negativas; ausências não viram zero. O percentual não é limitado a 100%; acima disso, a escala se amplia e uma nota explica o excesso de compromissos.

As visualizações financeiras ocupam duas colunas iguais (50%/50%): rosca de receitas à esquerda e funil de DRE simplificada à direita. O funil usa os campos `receita_total`, `receita_financeira`, `despesa_contratada` e `despesa_paga`, nessa ordem, do stage 05a, preservando valores sem exigir redução entre etapas. Não infere receita total ausente. A rosca mantém a legenda abaixo para aproveitar a largura da coluna.

Após os cards, `common/financial_charts.py` apresenta a rosca **Composição das Receitas** usando a mesma leitura do resumo financeiro. A proporção usa `receita_financeira` e `receita_estimavel`; o centro mostra a soma das duas. Valores ausentes, negativos ou soma zero recebem mensagem no lugar do gráfico; zero em uma categoria é válido quando a outra é positiva.

Logo abaixo do subtítulo de Balanço Macro & Liquidez de Caixa, quatro cards expansíveis apresentam **Arrecadação (Receitas)**, **Compromissos (Despesas)**, **Liquidez & Saúde do Caixa** e **Volume de Lançamentos**. O componente compartilhado `src/eleitoral/common/financial_cards.py` usa HTML `details/summary`, com quatro colunas em telas largas, duas abaixo de 1100 px e uma abaixo de 600 px. Os títulos usam badges verdes com texto branco em negrito. Os três primeiros cards exibem indicadores do alias `resumo_financeiro`, que resolve `gastos/stage05a_resumo_financeiro.parquet` na base anual do candidato selecionado. O quarto permanece vazio. A fonte contém uma linha de resumo por candidato; múltiplas linhas não são somadas. Campos ausentes ou inválidos aparecem como indisponíveis, preservando zero válido. Valores monetários usam reais com duas casas decimais. Resultado = receita_financeira − despesa_paga; saldo a pagar = despesa_contratada − despesa_paga. Os cálculos usam Decimal e não incluem receita estimável na liquidez.

A seção renderiza o cabeçalho com o título **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO** e o subtítulo `Análise do retorno do investimento eleitoral: veja onde o orçamento foi alocado e quanto custou a conquista de cada voto.`. Abaixo, `section_header(..., compact=True)` introduz **BALANÇO MACRO & LIQUIDEZ DE CAIXA**, com o subtítulo `Raio-x executivo da arrecadação e dos compromissos financeiros: monitore o saldo real de caixa, o volume contratado e a saúde orçamentária da campanha.`. A subseção apresenta indicadores nos três primeiros cards expansíveis; não há gráficos. O fluxo da página não carrega `gastos_por_tipo.parquet` nem executa os cálculos e componentes de gastos. As funções auxiliares anteriores permanecem no código, fora do fluxo de renderização.

As fontes continuam reconhecidas pelo leitor: `gastos_por_tipo.parquet` registra totais por tipo, enquanto `gastos_municipais_teoricos.parquet` contém rateio proporcional aos votos, não gasto municipal observado. Nenhuma delas alimenta a interface atual.

### Semântica da força política local

A seção pertence exclusivamente a Impacto político e é renderizada por `src/eleitoral/common/local_political_strength.py`, preservando mapa, filtros, cards e diálogo municipal.

O parágrafo explicativo acima das legendas não é renderizado. As quatro legendas têm texto ampliado e maior destaque de cor e borda; os critérios analíticos permanecem os mesmos.

O mapa cruza `capital_local_0a100`, do stage 7a, com `pct_market_share`, do stage 1a. A nota é considerada alta acima de 50/100, corte que coincide com a entrada na faixa alta dos dados atuais. O market share municipal é considerado alto quando alcança ou supera a participação estadual do próprio candidato, calculada pela soma dos votos dividida pela soma dos votos válidos municipais.

`faixa_capital_local` não controla a cor porque possui três níveis (`baixa`, `media` e `alta`), enquanto a matriz visual exige dois eixos binários.

Os quatro cards laterais apresentam quantidade de municípios, participação nos votos do candidato, município líder e recomendação estratégica. Ao clicar em um card, sua classe permanece colorida e as demais são atenuadas; um segundo clique restaura o mapa completo.

O clique em um município usa a seleção de pontos do Plotly e abre um `st.dialog`. A janela combina votos e market share do stage 1a, indicadores de capital político do stage 7a e a composição nominal do stage 7b. O recorte geográfico mostra apenas o polígono municipal com a mesma cor do mapa estadual; a lista ao lado reúne prefeito e vereadores, com partido, vínculo político e afinidade.

### Emendas e atuação parlamentar

A seção **Mapa da atuação parlamentar de acordo com os votos** pertence exclusivamente a Impacto político, após **Força da política local**, usando o cabeçalho de seção compartilhado.

`render_emendas()` usa a votação municipal anual e as emendas do mesmo candidato em `dep_estadual/{candidato}/{ano}/`. O bucket é o configurado no `.env` deste projeto; as referências usam `HF_GEOGRAPHY_REFERENCE_PREFIX=IBGE/MG/dadosterritorio`.

As funções da seção original foram preservadas. Os valores priorizam `valor_pago_atualizado`, depois `valor_empenhado_ano` e `valor_indicado`. Totais municipais e classificação pré-calculados são usados quando presentes. Na ausência de classificação, o componente original usa Sem Expressão nos municípios com emendas; votos sem emendas e ausência de ambos recebem classes próprias. Não são inferidas classificações estratégicas novas. O indicador de reciprocidade mantém a regra original de ranking municipal quando disponível, com fallback para os três maiores totais de votos.

Os arquivos atuais trazem `cd_municipio` e nomes; o adaptador relaciona códigos TSE/IBGE e, como fallback, nomes normalizados únicos nas referências, acrescentando `cd_ibge_municipio` para o mapa e o diálogo. O diálogo agrupa `valor_indicado` por `funcao_descricao` e `tipo_indicacao`; o total do mapa pode usar valor pago. Sua nota informa que indicação e pagamento podem diferir.

Na consulta de 13 de outubro de 2026, Amanda tinha 53 registros, Lud 261 e Fernando um arquivo vazio. As fontes não tinham `classificacao_retorno_parlamentar` nem totais municipais pré-calculados. Arquivo vazio mantém o estado de indisponibilidade da seção original.

## Geografia e mapas

### Eleições no Mapa de Força Eleitoral

O mapa estadual tem o seletor **Eleição exibida no mapa**, de deputados estaduais, com **2018 / 2022 / 2026 / Projeção 2030** e padrão 2026. O estado é independente do mapa de bairros e separado por candidato. Votação atual e históricos usam somente `territorio/stage01a_municipios.parquet`; Mesorregião agrega os municípios dessa fonte, sem ler um artefato eleitoral mesorregional separado.

Os históricos usam `qt_votos_candidato_{ano}` e `diff_market_share_pp_vs_{ano}`. Verde, azul, vermelho e cinza indicam aumento, estabilidade, queda e ausência de comparação com 2026. Mesorregiões com cobertura completa calculam a diferença entre as participações agregadas, usando as somas de votos do candidato e votos válidos (`qt_votos_validos_{ano}` / `qt_votos_validos_municipio`), sem média de percentuais municipais. Ausências não viram zero; zero informado é válido. Registros municipais duplicados tornam o mapa histórico indisponível. Principal reduto e cards laterais acompanham o ano selecionado, considerando somente votos conhecidos e informando cobertura parcial.

O clique mostra municípios da mesorregião ou bairros do município no ano selecionado; o histórico por bairros usa `qt_votos_candidato_bairro_{ano}` do stage 01b. Sem dados desse ano, o detalhamento fica indisponível. Os demais blocos e o total do hero mantêm a base atual.

**Projeção 2030** usa `potencial_demografico/stage09b_diagnostico_geral_municipio.parquet` e os critérios do eleitor ideal do DNA (`_diagnostic_city_frame`). Mesorregiões somam votos associados, população estimada e referência municipal uma vez por município, exigem cobertura completa e recalculam os cortes relativos entre mesorregiões. Municípios ou mesorregiões sem diagnóstico completo ficam cinza; sem a fonte, o mapa fica indisponível. Cards e detalhamento preservam 2026. O diagnóstico cobre setores associados e não prevê votos futuros.

Em **Votação por Bairros dentro dos municípios**, o hover atual e histórico mostra os nomes dos bairros e seus votos, sem exibir `cd_bairro` entre parênteses. O código TSE permanece como chave interna de vínculo e agrupamento.

Em BH, na votação atual por bairros, polígonos sem registro do candidato mostram o nome oficial `name_neighborhood` da malha de bairros e **0 votos**, mantendo cinza. Registros existentes com votos nulos continuam indisponíveis. Nomes TSE do candidato têm prioridade; o nome da malha serve apenas como identificação alternativa, sem alterar a junção exata por código IBGE.

Na votação atual de **Votação por Bairros dentro dos municípios**, setores sem votos associados ao candidato mostram **0 votos** e os nomes dos bairros TSE vinculados pelo código exato do setor no crosswalk. A referência fornece apenas o nome, sem alterar votos ou cores. Sem nome na referência, o hover mostra **Bairro sem referência disponível: 0 votos**.

### Votação por bairros dentro dos municípios — RaioX Territorial

A nota de rodapé da votação setorial sobre escala, malha IBGE e crosswalk foi removida. O card do mapa e o conjunto dos cinco cards laterais alinham suas bordas superiores e inferiores em telas largas; em telas menores, permanece o empilhamento.

A seção foi copiada de `D:\MktPolitica\deputados_streamlit` e usa as bases anuais `territorio/stage01a_municipios.parquet` e `territorio/stage01b_bairros.parquet` do deputado selecionado. Os filtros Mesorregião → Município têm estado próprio por candidato e mesorregião. A seleção inicial prioriza o município com mais votos e sua mesorregião. O mapa e as cinco métricas laterais seguem os componentes originais, com indicadores específicos do município selecionado.

Nesta seção, somente BH usa bairros oficiais. Nos demais municípios, as votações usam áreas ponderadas somente com 8 ou mais unidades; abaixo desse corte, usam-se setores censitários com identificação pelo bairro TSE de maior votação. O parâmetro `min_weighted_areas=8` é exclusivo desta seção e não altera o padrão dos outros mapas. Os cards agregam bairros pelo nome normalizado, mostram votos municipais, bairro líder, dependência do líder, bairros com voto e densidade média; a contagem de bairros com votos não presume o total da malha oficial. Dados ausentes mantêm os avisos e estados vazios originais. As referências geográficas continuam em `IBGE/MG/dadosterritorio`.

**Exceção exclusiva de BH nesta seção:** `common/bh_neighborhood_voting.py` lê somente códigos e geometrias de `HF_GEOGRAPHY_REFERENCE_PREFIX/MG_bairros_CD2022.parquet`, filtrando `code_muni=3106200`. A junção é exata entre `code_neighborhood` da malha e `cd_ibge_bairro` de `stage01b_bairros.parquet`; `cd_bairro` do TSE identifica os bairros eleitorais e controla os cards e o detalhamento; o código IBGE serve somente ao vínculo com a geometria. Não há associação por nome, coordenadas, setor ou área ponderada. Nomes e votos do hover vêm exclusivamente do stage 01b, agregados por código IBGE, preservando o detalhamento por `cd_bairro` do TSE; os cards agrupam por esse código eleitoral. Bairros da malha sem dados ficam cinza com votos indisponíveis; códigos do candidato sem correspondência são informados abaixo do mapa. A malha não fornece atributos analíticos nem nomes exibidos. A exceção é restrita a Belo Horizonte.

As malhas são carregadas de `HF_GEOGRAPHY_PREFIX`:

Na seção de bairros, o seletor oferece as opções **2018 / 2022 / 2026 / Projeção 2030**, inicialmente em 2026. Os históricos usam `qt_votos_candidato_bairro_{ano}` no stage 01b anual. Coluna ausente ou inteiramente nula no município gera indisponibilidade, sem inferir ausência de candidatura. Zero informado é válido. Os cards históricos consideram apenas registros com votos conhecidos e identificam o ano; cobertura parcial recebe nota. O hover preserva os bairros TSE e mostra votos históricos e de 2026. Verde/azul/vermelho/cinza indicam aumento/estabilidade/queda/sem comparação. A diferença por polígono é a média de `diff_market_share_bairro_pp_vs_{ano}`, ponderada por `qt_votos_validos_bairro_{ano}`, entre registros comparáveis; não se presume uma comparação de locais correspondidos, pois esses campos não existem nas fontes atuais.

**Projeção 2030**, escolhida para usar a fonte stage 09b existente, apresenta o diagnóstico do eleitor ideal com os mesmos critérios de `sector_scores()` e `_diagnostic_city_frame()` do DNA. Em BH, agrega setores com vínculo exato de bairro e recalcula os cortes entre bairros; usa a malha oficial das referências e nomes/votos TSE do stage 01b. Nos demais municípios, desenha setores censitários e mantém os cortes setoriais calculados antes do filtro municipal, como no DNA. As estimativas populacionais vêm do diagnóstico, não do stage 01b. Os cards permanecem em 2026. A legenda mostra Proteger a base, Oportunidade alta, Potencial a desenvolver e Sem potencial ou dados incompletos; diagnósticos ausentes não geram projeção fictícia. Potencial demográfico não é previsão de votos para 2030.

| Arquivo | Papel |
| --- | --- |
| `MG_municipios_2022.parquet` | Moldura dos 853 municípios e mapas estaduais |
| `MG_mesorregioes_2022.parquet` | Polígonos e rótulos mesorregionais |
| `MG_bairros_CD2022.parquet` | Primeira opção da malha intramunicipal |
| `MG_AreaPonderada_CD2022.parquet` | Segunda opção da malha intramunicipal |
| `MG_setores_mapa_CD2022.parquet` | Fallback completo por município |

Para a Projeção 2030 dos deputados em BH, o vínculo setor → bairro também pode usar `MG_setores_CD2022.parquet` sob `HF_GEOGRAPHY_REFERENCE_PREFIX`, lendo apenas códigos e filtrando BH. Esse índice oficial completa os vínculos quando `setor_bairro_lookup.parquet` não existe; setores com códigos de bairro conflitantes são excluídos da agregação, sem inferência espacial.

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

O mapa estadual usa `log1p(votos)` para distribuir a intensidade. Na seção Votação por Bairros dentro dos municípios, a escala é linear até 1.000 votos municipais e logarítmica acima desse total. Históricos e Projeção 2030 usam classes categóricas, preservando a distinção entre intensidade de votos e diagnóstico.

## Cache e estado

- A listagem remota tem TTL de 600 segundos.
- O resultado da listagem, inclusive vazio após falha, é reutilizado por todas as seções na mesma execução. Uma pasta ausente gera um único aviso sobre `HF_VISUALIZACAO_PREFIX`, sem sugerir falha de token nem repetir a consulta em cada componente.
- Leituras de Parquet, malhas e referências usam `st.cache_data` sem TTL explícito.
- O `HfFileSystem` usa `st.cache_resource` por token.
- Se a leitura de Parquet falhar com `ArrowInvalid` (por exemplo, rodapé não encontrado após substituir um arquivo no mesmo caminho), `load_parquet()` invalida os metadados desse caminho e tenta uma única leitura integral, sem depender do tamanho em cache nem de leituras por intervalo. Arquivos realmente inválidos continuam gerando erro; não há troca de candidato ou fallback para outra pasta.
- `sync_deputados(force=True)` limpa a listagem remota e os caches tabulares de `hf_sync.py`.
- A troca de candidato limpa `territorial_context`; os demais controles têm chaves próprias por seção.


Após substituir arquivos mantendo o mesmo caminho, reinicie o processo ou limpe o cache do Streamlit para evitar leitura antiga.

## Execução local

No Windows, dê dois cliques em `abrir_visualizacao.cmd` para iniciar o app e abrir `http://localhost:8501` no navegador. Se o servidor já estiver rodando, o arquivo abre a visualização existente. Quando o inicializador abrir um terminal, mantenha-o aberto enquanto usa o app; `Ctrl+C` encerra o servidor. Alterações salvas são recarregadas automaticamente.

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

- repositório: `amichiautomacoes/inteligencia-politica2`;
- branch: `main`;
- contexto de build: `/`;
- porta: `8503`.

O `Dockerfile` copia somente o necessário ao runtime (`app.py`, `hf_sync.py`, `pages/`, `src/`, `assets/` e `.streamlit/config.toml`). Dados locais, caches, `.env` e scripts de preparação ficam fora da imagem.

## Validação e manutenção

Há testes de regressão do leitor remoto para arquivos substituídos e inválidos. Antes de publicar, execute ao menos:

```powershell
python -m unittest discover -s tests
python -m compileall -q app.py pages src
git diff --check
streamlit run app.py
```

No smoke test, confirme a seleção de deputados no prefixo configurado e abra as quatro rotas pelos botões do sidebar, verificando o candidato e o destaque da página ativa. O RaioX Territorial deve terminar na concentração territorial, sem as seções de força política local, emendas ou finanças. Impacto político deve exibir o hero padrão, Força da política local e Mapa da atuação parlamentar, nessa ordem; confira os filtros de classe, os KPIs e os diálogos por município nos dois mapas. DRE Campanha deve exibir o hero padrão e todos os blocos de EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO: Balanço Macro, Estrutura da Receita, Contratado × Pago e Da origem ao destino. Verifique os filtros financeiros por candidato, os gráficos e tabelas, os históricos territoriais de 2018/2022, a Projeção 2030 e os estados com e sem dados. As seções exclusivas de vereadores não integram o app.

Regras de manutenção:

- não coloque módulos auxiliares em `pages/`;
- não versione `.env`, tokens, dados locais ou caches;
- preserve códigos territoriais como texto para não perder zeros nem alterar junções;
- ao mudar nomes de artefatos, atualize `file_by_kind()` e este contrato;
- ao mudar ordem, texto, cor, layout ou interação da interface, atualize também [Visual.md](Visual.md).

Nesta seção, áreas ponderadas servem somente ao vínculo geométrico. Toda a informação eleitoral vem de `stage01b_bairros.parquet`, com bairros identificados por `cd_bairro` do TSE. Nas áreas ponderadas, o hover lista cada bairro apenas com nome TSE e votos, sem códigos ou parênteses; a soma dos votos associados ao polígono aparece ao final. O código TSE continua sendo a chave interna de agrupamento. Nos históricos, mostra também as somas de cada ano. Cards agrupam por `cd_bairro` em todos os municípios. Nomes e códigos de área ponderada não aparecem no hover, nos cards ou na legenda. A Projeção 2030 mantém o diagnóstico por setores fora de BH, identificando-os pelo bairro TSE mais votado em 2026.

Nos municípios com menos de 8 áreas ponderadas, `cd_setor_censitario` do stage 01b serve somente para o vínculo exato com `code_tract` da malha. Nenhum nome de setor ou bairro é obtido da referência geográfica e não há associação por coordenadas/proximidade nesse modo. Em divergências, os votos são somados por `cd_bairro` dentro de cada setor e o bairro com mais votos identifica o polígono; empate usa o código TSE em ordem crescente. Nos históricos, a prioridade usa os votos do ano selecionado; na Projeção 2030, usa 2026. O tooltip informa o bairro vencedor e seus votos, enquanto o total do polígono preserva todos os votos associados. Os cards continuam calculados por bairro TSE, sem descartar bairros perdedores na disputa pela identificação do setor.

O primeiro card lateral da votação por bairros mostra o título Total de votos no Município, percentual dos votos do município na votação do candidato e badge verde Total municipal com os votos absolutos. Numerador e denominador vêm do stage01b do candidato para o ano exibido; Projeção 2030 mantém 2026. Sem denominador válido, o percentual fica indisponível.

Na seção Votação por Bairros dentro dos municípios, o mapa de intensidade usa somente o total de votos municipal para escolher a escala: linear até 1.000 (inclusive) e logarítmica acima de 1.000. Não há cor uniforme para municípios pequenos nem fator de cobertura por quantidade de bairros, áreas ou setores. O máximo de votos associado usa toda a faixa de intensidade. Os históricos comparativos e a Projeção 2030 mantêm suas cores categóricas, pois representam classes e não intensidade.

A abertura de Votação por Bairros dentro dos municípios usa major_section_header(), compartilhando a faixa principal das demais seções do RaioX Territorial.


### Alinhamento do Balanço Macro

O Balanço Macro & Liquidez de Caixa apresenta somente três cards expansíveis: Arrecadação (Receitas), Compromissos (Despesas) e Liquidez & Saúde do Caixa. Volume de Lançamentos foi removido. Os três dividem igualmente toda a largura do cabeçalho da subseção, com espaçamento de 16 px; abaixo de 900 px, ficam empilhados. Esta regra substitui as referências anteriores a quatro cards.

O card Composição das Receitas e sua rosca usam altura extensível para acompanhar o conjunto DRE Simplificada e Comprometimento Orçamentário na coluna direita. As bordas superiores e inferiores ficam alinhadas, eliminando a sobra externa abaixo do card esquerdo. O layout mantém duas colunas de mesma largura e o empilhamento responsivo do Streamlit.

### Subseção 4 — Contratado × Pago

Os três cards usam `details/summary`, inicialmente fechados, com apenas título e seta visíveis. Cabeçalhos e badges compartilham tamanho e espaçamento; cada card revela seus indicadores ao expandir.

Atualização vigente: Indicadores de Alerta / Distorções foi removido. Restam três cards em colunas iguais, ocupando toda a largura da seção: Total Contratado vs. Total Pago, Taxa de Execução Geral e Saldo em Aberto. O primeiro usa `details/summary`, começa fechado e revela os dois totais ao expandir. A grade empilha abaixo de 900 px. Esta regra substitui a composição anterior de quatro cards.

Após a Estrutura da Receita, o cabeçalho interno **Contratado × Pago** usa o subtítulo **A importância da análise de passivos, prazos e distorções entre contratos e pagamentos.** Quatro cards executivos aparecem lado a lado: Total Contratado vs. Total Pago, Taxa de Execução Geral, Saldo em Aberto e Indicadores de Alerta / Distorções. O último é expansível e começa fechado, mostrando ao abrir excesso pago conhecido, contratado sem pagamento e defasagem média conhecida em dias. O layout segue os cards azuis e badges verdes, passando para duas colunas abaixo de 1100 px e uma abaixo de 600 px.

O alias `execucao_resumo` lê `gastos/stage05d_execucao_resumo.parquet` da base anual selecionada. Usa exclusivamente a linha `recorte=global`, sem somar categorias e fornecedores. Campos monetários usam Decimal. O saldo prioriza `saldo_em_aberto`; o fallback `saldo_liquido` recebe identificação e explicação próprias. A taxa vem de `taxa_execucao_pct`, sem média de percentuais dos recortes nem limite em 100%. A badge indica execução não iniciada (0%), parcial (entre 0 e 100%), integral (100%) ou pagamento acima do contratado (>100%); não infere atraso por calendário. Ausências, valores inválidos e resumo global ambíguo aparecem como Indisponível. Zero válido e defasagem negativa são preservados. A subseção é das páginas de deputados estaduais e independente dos filtros de doadores.

### Filtros de Contratado × Pago

Antes dos KPIs, **Recorte da análise** alterna Global / Geral da Campanha, Por Categoria de Despesa e Por Fornecedor. Global é o padrão e usa a linha global nos KPIs, mantendo o comparativo por categorias ou Top 10 Fornecedores no gráfico. Categoria e Fornecedor exibem um segundo selectbox para escolher o grupo; os quatro cards e o gráfico passam a usar exclusivamente esse grupo, sem somar outros recortes nem fazer médias de taxas e prazos. Os rótulos priorizam `categoria` e `nm_fornecedor` quando presentes, com fallback para `grupo_descricao` do resumo atual. A chave de seleção é `grupo_chave`, preservando fornecedores homônimos como grupos distintos. Seleções têm estado por candidato e tipo de recorte. Ausência de grupos gera mensagem e indicadores indisponíveis. Esta regra substitui a restrição anterior dos KPIs ao resumo global.

### Gráfico comparativo de Contratado × Pago

Abaixo dos quatro cards, um card de largura integral apresenta barras horizontais agrupadas: Contratado em azul e Pago em ciano, com valores em reais nas pontas. O seletor **Comparar por** alterna Categoria e Top 10 Fornecedores, usando exclusivamente o respectivo `recorte` do stage 05d. A ordem usa o maior valor entre contratado e pago; fornecedores ficam limitados aos dez primeiros, sem promover posições posteriores quando um registro tem dados inválidos. Nomes quebram em linhas e a altura acompanha os grupos. O hover informa valores e diferença, distinguindo saldo ainda não pago de pagamento acima do contratado. Zero válido aparece como zero; dados incompletos não viram zero e recebem nota de cobertura. Grupos duplicados tornam a comparação indisponível. A nota explica que diferenças de volume não comprovam atraso, retenção ou adiantamento sem datas e prazos contratuais. O seletor tem estado por candidato e não altera os KPIs globais.

### Última subseção — Da origem ao destino

Após o gráfico de Contratado × Pago, o card introdutório usa o título **DA ORIGEM AO DESTINO: O CAMINHO DOS RECURSOS** e o subtítulo **Cruze as fontes de financiamento (FEFC, Fundo Partidário e Doações) com os pagamentos efetuados por categoria e fornecedor para entender para onde foi cada real da campanha.** O componente reutiliza `section_header(..., compact=True)`, com o mesmo fundo azul, borda, cantos arredondados e hierarquia dos demais cabeçalhos internos. É da aplicação de deputados estaduais. Nesta etapa contém apenas a introdução, sem indicadores, filtros ou gráficos próprios.

### De onde vem? — Recursos por fonte

Na última subseção, **De onde vem?** ocupa os 50% esquerdos da página, em card azul com gráfico Plotly de barras horizontais agrupadas: Arrecadado (`receita_total`, azul) e Efetivamente pago (`despesa_paga`, ciano), por `fonte_descricao`, em ordem decrescente de arrecadação. A metade direita fica disponível para o próximo gráfico. O alias `receita_despesa_fontes` resolve `gastos/stage05e_receita_despesa_fontes.parquet` do candidato selecionado. Cada `fonte_chave` deve ser única; duplicações geram indisponibilidade.

Os rótulos das fontes mostram saldo financeiro observado e taxa de utilização financeira, também disponíveis no hover junto à receita financeira e aos valores das barras. Os indicadores vêm diretamente de `saldo_financeiro_observado` e `taxa_utilizacao_financeira_pct`: valores ausentes não viram zero, saldos negativos e taxas superiores a 100% são preservados. A nota esclarece que arrecadação total inclui receita estimável, enquanto saldo e utilização se referem à parcela financeira e não representam saldo bancário conciliado. Valores inválidos nas barras são omitidos com nota de cobertura. Não há novos KPIs ou filtros nesta etapa. Esta implementação substitui a indicação anterior de introdução sem gráficos.

### Para onde vai? — Destinação por fonte

O título e os dois filtros ocupam a mesma linha superior. CPF/CNPJ e Natureza são excluídos apenas da tabela renderizada, preservando os campos na preparação dos dados.

Os dois cards de **Da origem ao destino** usam contêineres com `height="stretch"`, alinhando suas bordas inferiores. Notas de rodapé explicativas foram removidas; avisos de indisponibilidade e cobertura incompleta permanecem como mensagens de informação. As regras de cálculo descritas abaixo continuam válidas.

Os 50% direitos da última subseção apresentam o card **Para onde vai?**, com tabela somente para leitura baseada no alias `destinacao_fontes`, que resolve `gastos/stage05e_destinacao_fontes.parquet`. O filtro **Fonte de financiamento** oferece Todas as fontes e as fontes disponíveis no resumo ou na destinação. **Destinação por** alterna Categoria de Despesa e Fornecedor, mantendo os recortes separados para evitar dupla contagem.

A tabela ordena `valor_pago` em ordem decrescente e mostra fonte, `grupo_descricao`, `nr_cpf_cnpj_fornecedor`, natureza da despesa quando disponível, valor pago em reais e `pct_total_pago`. CPF/CNPJ permanece texto, preservando zeros iniciais; valores ausentes não viram zero. Os percentuais mantêm o total pago da campanha como referência, sem renormalização após filtrar fonte. Filtros têm estado por candidato e atuam apenas na tabela. Ausência de fonte ou recorte recebe mensagem específica, sem impedir o gráfico esquerdo. Esta composição substitui a reserva anterior da metade direita para um gráfico futuro.

### Filtros da Estrutura da Receita

O ranking começa expandido. Os contêineres do gráfico de doadores e da tabela usam `height="stretch"` para padronizar a altura dos dois cards lado a lado.

A tabela Ranking do recorte não exibe CPF/CNPJ. O documento permanece na base de dados, mas é excluído da tabela renderizada.

O card Índice de Concentração da Receita foi removido da renderização. O gráfico de doadores e o Ranking do recorte ficam lado a lado em duas colunas iguais, alinhadas pelo topo e ocupando a largura da seção. Quando somente um deles tem dados, ocupa a largura disponível sem coluna vazia. Os filtros e KPIs permanecem. Esta regra substitui as referências anteriores à rosca de concentração.

Acima dos cards, três selectboxes controlam toda a subseção: **Tipo de Doador** (Imediato ou Originário), **Top 10 vs. Todos** e **Cobertura & Status da Atribuição** (todas as situações ou um status disponível). O padrão é Imediato / Top 10 / Todas as situações. O recorte se aplica aos KPIs, barras, concentração e tabela; Todos expande também as barras. `eh_top10` controla o recorte, com fallback para ranks 1 a 10 quando a coluna não existe. Ranks não são recalculados ao filtrar status. Esta regra substitui a restrição anterior a doadores imediatos.

A badge apresenta `cobertura_atribuicao_pct`, `situacao_atribuicao` e `qt_vinculos_pendentes`. Cobertura e pendências repetidas usam valores únicos válidos, sem soma; ausências ou divergências ficam indisponíveis. Status diferente de completa ou pendências positivas geram aviso. Percentuais mantêm a receita total como referência; a concentração representa os registros Top 10 presentes no recorte. A tabela se chama Ranking do recorte. Seleções são independentes por candidato e status por tipo de doador. Recorte vazio recebe mensagem explícita.
