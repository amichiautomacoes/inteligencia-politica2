# Briefing visual — Visualização Eleitoral

Este documento registra a interface das quatro páginas dedicadas exclusivamente a deputados estaduais. Ele descreve aparência, ordem de leitura, controles, interações e estados sem dados. O [README](README.md) concentra arquitetura e fontes. Não há páginas compartilhadas entre cargos nem seletor de cargo.

Atualizado em 16 de outubro de 2026 para o escopo exclusivo de deputados estaduais.

### Regra vigente — sem áreas ponderadas nos mapas

Na página 1, a votação setorial atual, os históricos e a Projeção 2030 desenham a malha completa de setores e o contorno municipal IBGE. Setores sem votos associados ficam cinza na intensidade; sem comparação ficam cinza no histórico; sem vínculo ou diagnóstico ficam cinza na projeção. Assim, o interior municipal permanece preenchido entre os setores classificados. A cobertura não se limita aos setores presentes no crosswalk.

No Potencial demográfico municipal, o contorno externo usa a malha municipal IBGE e a subdivisão cobre todos os setores dentro do município. Setores sem relação TSE no crosswalk ou sem diagnóstico aparecem cinza, preenchendo os espaços entre os setores classificados. As geometrias vinculadas continuam vindo do crosswalk e ficam restritas ao limite municipal. Os cards contam bairros TSE. Esta regra substitui a cobertura limitada às geometrias do crosswalk descrita anteriormente nessa seção.

No Potencial demográfico municipal, os cards laterais mostram **Bairros**: bairros TSE únicos ligados aos setores de cada categoria. O mapa permanece por setores em todas as cidades. Uma nota explica que bairros com setores em categorias diferentes podem aparecer em mais de um card. Esta atualização substitui o rótulo anterior **Setores censitários** nos cards.

Na seção **Potencial demográfico municipal** da página DNA, todas as cidades, inclusive Belo Horizonte, mostram setores censitários do crosswalk. Bairros TSE identificam os setores no hover, sem agregação por bairro. Os quatro cards usam o rótulo **Setores censitários**; os cortes de classificação permanecem setoriais. Esta regra substitui a exceção de BH descrita historicamente neste bloco e não altera os demais mapas.

Nenhum mapa desenha áreas ponderadas. Os níveis geográficos são municípios, mesorregiões, bairros oficiais e setores censitários. Quando bairros oficiais não forem usados, a subdivisão municipal usa diretamente setores do `crosswalk_setor_bairro.parquet`, sem considerar a quantidade de áreas ponderadas. Cores, escalas, filtros e vínculos TSE são preservados. Esta regra prevalece sobre as descrições históricas de áreas ponderadas abaixo.

### Histórico — geometrias dos crosswalks

Esta atualização prevalece sobre as descrições abaixo de malha completa de setores e vínculo de áreas/setores por coordenadas. Quando um mapa usa setores censitários ou áreas ponderadas, os polígonos vêm da coluna `geometry` dos crosswalks `crosswalk_setor_bairro.parquet` e `crosswalk_area_ponderada_bairro.parquet`, em `HF_GEOGRAPHY_REFERENCE_PREFIX=IBGE/MG/dadosterritorio`. Cada unidade aparece uma vez, mesmo com vários bairros TSE associados. Votos atuais e históricos são vinculados pelo `cd_bairro` TSE dentro do município; ausência ou ambiguidade de vínculo não recebe associação por proximidade. Os diagnósticos demográficos mantêm a junção por código de setor, com identificação TSE do crosswalk fora de BH.

Somente unidades representadas com geometria no crosswalk são desenhadas; ausência de diagnóstico nessas unidades continua cinza. A interface informa essa cobertura junto ao mapa. Cores, escalas e controles permanecem os mesmos. Mapas estaduais, contorno municipal de referência e mapas de bairros oficiais mantêm suas fontes próprias, incluindo BH.

A implementação mantém uma entrada única em `app.py` e quatro páginas de deputados estaduais. `src/eleitoral/deputados/` contém emendas e históricos intramunicipais; `common/`, `dna/` e `maps/` fornecem os demais componentes. Não há componentes de candidaturas a vereador no fluxo.

## 1. Visão geral da experiência

O produto é um painel de inteligência eleitoral de deputados estaduais, com quatro rotas. **RaioX Territorial** apresenta votação, distribuição e concentração territorial. **DNA Eleitoral** apresenta eleitor predominante, perfis e oportunidades demográficas. **DRE Campanha** concentra toda a análise financeira. **Impacto político** apresenta força da política local e atuação parlamentar de acordo com os votos. O ano padrão é 2026, com fallback para o ano numérico mais recente disponível. As quatro páginas preservam o candidato selecionado, fundo, hero, tipografia e família de cards.

O percurso é vertical. Uma capa apresenta o deputado; faixas de seção delimitam cada pergunta analítica; os cards contêm números, mapas ou gráficos. A barra lateral reúne o seletor de candidato e quatro botões empilhados logo abaixo. A navegação nativa fica oculta; RaioX Territorial, DNA do Eleitor, DRE Campanha e Impacto político alternam as páginas e destacam a opção ativa.

### Barra lateral e seleção de deputado

A barra lateral usa fundo glassmorphism azul (`rgba(11, 31, 77, 0.60)`), com 60% de opacidade, blur de 18 px, saturação de 140%, borda direita clara e sombra discreta. O efeito se aplica somente ao fundo, mantendo textos e controles legíveis. O conteúdo apresenta o selectbox com o rótulo **Candidato**, seguido dos botões **RaioX Territorial**, **DNA do Eleitor**, **DRE Campanha** e **Impacto político**, nessa ordem. Os quatro botões abrem suas páginas e destacam a página ativa. Não há título adicional, botão de atualização ou seletor de cargo. As opções exibem somente o nome do deputado, como Fernando Breno ou Lud Falcão, sem nome de pasta. Não há legenda inferior com ano ou slug. Sem candidatos, o seletor permanece visível e desabilitado com **Nenhum candidato disponível**; mensagens de ausência ou erro aparecem na área principal.

As opções vêm exclusivamente do prefixo configurado em `HF_VISUALIZACAO_PREFIX`, cujo padrão é `dep_estadual`. Cada deputado precisa de uma pasta anual como `2026`. Trocar página pelos botões do sidebar preserva a seleção. As seções de votação histórica de vereadores de BH e comparação capital/interior foram removidas. O RaioX Territorial encerra com concentração. Força da política local e atuação parlamentar ficam exclusivamente em Impacto político, nessa ordem. Toda a análise financeira pertence à página DRE Campanha.

### 1.1 Sistema visual compartilhado

Regra vigente para as quatro páginas: todas as faixas principais usam barra lateral de 12 px em gradiente ciano (#67e8f9 → #22d3ee → #06b6d4), com brilho neon em três camadas. Cabeçalhos de subseção usam barra fina de 3 px em azul acinzentado (#64748b), sem brilho na barra. Essa hierarquia também vale para as subseções financeiras e substitui as cores e espessuras anteriores.

| Elemento | Aparência atual | Função |
| --- | --- | --- |
| Fundo da página | Imagem `assets/background.png`, cobrindo a área de conteúdo, centralizada e fixa | Criar profundidade sem disputar atenção com os dados |
| Hero | Retângulo amplo com imagem escurecida, gradiente azul quase preto, borda clara fina e sombra profunda; cantos retos | Abrir a narrativa e identificar o candidato |
| Faixa principal de seção | Card de cantos arredondados, gradiente azul, brilho radial discreto e barra vertical branca/azul à esquerda | Separar os grandes capítulos da análise |
| Cabeçalho interno | Card azul mais leve, com título e subtítulo em duas linhas de hierarquia | Introduzir uma visualização dentro da seção |
| Cards de conteúdo | Azul profundo translúcido, borda azul clara fina, sombra e leve blur | Agrupar informação sem esconder o fundo |
| Gráficos Plotly | Fundo transparente, textos claros e grades discretas | Integrar gráfico e card |
| Mapas | Coropléticos Plotly no RaioX, DNA e Impacto político, sem mapa-base de ruas | Mostrar votos por intensidade, força política por classe, malhas neutras ou oportunidades |
| Mensagens de ausência | Aviso ou informação textual dentro do espaço da visualização | Explicar falta de dados sem simular um resultado |

A base cromática é `#eaf2ff` para texto, `#f8fbff` para títulos e números, `#b7c7e6` para descrição e legendas. Os cards usam gradientes próximos de `rgba(11,31,77,.76)` e `rgba(7,24,54,.68)`, com bordas azuis próximas de `rgba(59,130,246,.24)`. Azul claro (`#60a5fa`), azul médio (`#2563eb`) e azul profundo (`#0b1f4d`) expressam intensidade ou seleção; verde, vermelho, amarelo, laranja e cinza têm significado específico nos mapas categóricos.

Os preenchimentos dos mapas são opacos e aparecem sobre fundo transparente, sem nomes de ruas sob os polígonos. Os tooltips usam fundo escuro e texto claro. Os 853 municípios de Minas Gerais compõem os mapas estaduais; os polígonos municipais são simplificados com tolerância pequena para preservar a leitura dos limites. O mapa detalhado de votação usa bairros oficiais quando a malha cobre pelo menos 95% do município; caso contrário, usa áreas ponderadas quando existem duas ou mais unidades. A malha completa de setores censitários fica restrita aos municípios que possuem uma única área ponderada.

### 1.2 Hierarquia de texto e formatação

O hero usa título grande e pesado, subtítulo menor e nome/cargo/partido em maiúsculas. Quando exibido, o total de votos segue a mesma tipografia dessas linhas de identificação. Os títulos principais de seção são largos, brancos e densos; subtítulos ficam em azul claro. Labels dos KPIs gerais são compactos; no card do eleitor ideal, os títulos das dimensões têm fonte ampliada. Cards e legendas não devem exigir que a cor sozinha explique um resultado: os textos e tooltips dão o nome da categoria, a unidade e o recorte. Números de votos usam separador de milhar; percentuais e valores monetários aparecem com unidade explícita. Onde os dados são estimados ou rateados, a interface informa isso junto à visualização.

### 1.3 Capa comum às quatro páginas

O hero ocupa toda a largura do conteúdo principal com título da página, subtítulo curto e uma linha com foto e dados do candidato. Os botões de navegação ficam exclusivamente no sidebar, sem coluna reservada na capa. A foto é vertical, com cantos levemente arredondados, borda clara e sombra; quando não há imagem remota, o espaço permanece como um bloco neutro. Os dados aparecem como `NOME:`, `CARGO:` e `PARTIDO:` em caixa alta. O partido é lido do campo `sg_partido` da base territorial do candidato. `TOTAL DE VOTOS:` aparece logo abaixo do partido nas quatro páginas, com a mesma tipografia das demais linhas, sem card próprio; o valor é calculado a partir do parquet territorial selecionado. O ano integra o título do RaioX Territorial.

No sidebar, abaixo do seletor de candidato, ficam quatro botões empilhados: **RaioX Territorial**, **DNA do Eleitor**, **DRE Campanha** e **Impacto político**. Os quatro navegam e destacam a página ativa. Cada botão ocupa toda a largura disponível, com altura mínima de 4 rem, fonte de 1 rem, borda azul clara, cantos de 14 px, texto branco em negrito, gradiente e sombra. O conjunto tem espaçamento superior de 1 rem e gap de 0,75 rem. A página ativa recebe azul mais intenso; a outra mantém fundo azul escuro. O hover clareia o botão e o eleva discretamente; o foco por teclado recebe contorno visível. A troca preserva o candidato selecionado e funciona também no sidebar recolhível de telas menores.

| Página | Título do hero | Subtítulo |
| --- | --- | --- |
| RaioX Territorial | `RaioX Territorial 2026` (ano numérico mais recente disponível quando não há 2026) | `Análises descritivas geográficas e do perfil do eleitor na última eleição.` |
| DNA | `DNA do Eleitor` | `Quem é, onde está e como se comporta o eleitor determinante da candidatura.` |
| DRE Campanha | `DRE Campanha` | `Análise da arrecadação, dos compromissos e da aplicação dos recursos da campanha.` |
| Impacto político | `Impacto político` | `Força da política local e atuação parlamentar nos municípios da sua votação.` |

## 2. Página 1 — RaioX Territorial

A ordem do RaioX Territorial é: **Mapa de Força Eleitoral → Votação por Bairros dentro dos municípios → Concentração territorial dos votos**. A análise financeira fica em DRE Campanha; força da política local e atuação parlamentar ficam em Impacto político.

### 2.1 Mapa de Força Eleitoral

Os controles **Eleição exibida no mapa** (à esquerda, 70%) e **Filtro territorial** (à direita, 30%) ficam na mesma linha, alinhados pelo topo, dentro do card do mapa.

Atualização vigente: no topo do card do mapa, acima do filtro territorial, **Eleição exibida no mapa** oferece **2018 / 2022 / 2026 / Projeção 2030**, com 2026 selecionado inicialmente, no mesmo padrão de botões segmentados do mapa de bairros. Está disponível nas páginas de deputados estaduais e tem estado próprio por candidato, independente dos demais mapas. **Mesorregião / Município** continua controlando a malha estadual em todos os modos.

Em 2018/2022, cores categóricas mostram aumento (verde), estabilidade (azul), queda (vermelho) ou ausência de comparação (cinza) com 2026. O hover mostra território, votos do ano escolhido, votos de 2026 e diferença de participação em pontos percentuais. Mesorregiões comparam participações calculadas a partir de totais agregados de votos e votos válidos. O card Principal reduto e os quatro cards laterais mostram o ano escolhido, identificado acima dos indicadores. O clique abre o detalhamento do mesmo ano; cobertura parcial recebe nota e falta de histórico recebe mensagem, preservando zero legítimo.

Em **Projeção 2030**, pílulas apresentam Proteger a base (azul), Oportunidade alta (verde), Potencial a desenvolver (amarelo) e Sem potencial ou dados incompletos (cinza). O hover mostra diagnóstico do eleitor ideal, votos nos setores associados, população estimada e parcela na referência. Mesorregiões agregam diagnósticos e recalculam as classes, sem fabricar dados faltantes. Principal reduto, cards e detalhamento mantêm os votos de 2026; uma nota identifica esse recorte e esclarece que potencial não é previsão de votos. Em 2026, o mapa mantém a intensidade azul atual. Estas regras substituem as descrições abaixo de intensidade azul em todos os modos.

**Pergunta visual:** onde estão os votos e quais localidades lideram?

A faixa **Mapa de Força Eleitoral** apresenta o subtítulo `Onde estão concentrados seus votos e a força da sua votação.`. Logo abaixo, antes do mapa e dos cards laterais, o card horizontal de **Principal reduto eleitoral** destaca a mesorregião mais votada e seu volume. Uma badge verde **Maior base eleitoral** aparece no canto superior direito, e o rodapé informa `{votos} votos recebidos` com maior peso visual. O total de votos do candidato fica no hero, abaixo do partido e no mesmo padrão tipográfico das demais linhas de identificação.

O seletor **Mesorregião / Município** fica sozinho no canto superior direito, dentro do card do mapa. Ele altera o agrupamento do mapa estadual.

O card do mapa ocupa **70% da largura** disponível e tem cerca de 560 px de altura. Os 30% restantes contêm quatro cards empilhados: **Município principal (Top 1)** (nome, participação no total e votos da cidade líder, com alerta acima de 30%), **Dependência do reduto principal** (parcela dos votos no município líder, com alerta acima de 30%), **Penetração territorial** (municípios com votos sobre os municípios do estado) e **Densidade média por município** (votos divididos apenas pelos municípios com voto). No modo municipal, cada município de Minas Gerais é um polígono Plotly; o hover informa nome e votos. A intensidade progride do azul muito claro ao azul profundo, com transformação logarítmica dos votos. No modo mesorregional, cada mesorregião é um único polígono da malha oficial, colorido pelo total de seus votos; o hover informa nome e votos da mesorregião. Áreas sem votos continuam desenhadas na cor mínima. As linhas visíveis correspondem à malha selecionada.

O gráfico de barras aparece em uma janela de detalhamento após o clique no mapa. No modo mesorregional, mostra todos os municípios da mesorregião selecionada. No modo municipal, mostra todos os bairros com registros de votos do município selecionado. A altura cresce generosamente conforme a quantidade de linhas, permitindo rolar a janela até o último território sem comprimir as barras. As barras são espessas; os nomes dos municípios ou bairros e os textos de votos e participação usam tipografia ampliada. O comprimento expressa votos e a cor também varia em azul. O hover repete território, votos e percentual.

Se a malha ou os votos não puderem ser carregados, o mapa cede lugar a uma mensagem de indisponibilidade. O detalhamento também informa quando faltam dados. A interface não preenche municípios ou bairros com valores fictícios.

### 2.2 Votação por Bairros dentro dos municípios

A nota de rodapé da votação setorial sobre escala, malha IBGE e crosswalk foi removida. Em telas largas, o card do mapa e o conjunto dos cinco cards laterais têm as bordas superiores e inferiores alinhadas, distribuindo a altura entre os cards laterais. Em telas menores, as colunas continuam empilhando.

O hover atual e histórico exibe somente o nome do bairro e os votos, sem código TSE entre parênteses; por exemplo, **VIÚVA: 35 votos**.

Em BH, bairros sem registro do candidato mostram o nome da malha oficial de bairros e **0 votos** no hover, mantendo cinza. Nomes do candidato continuam prioritários; votos nulos em registros existentes permanecem **Indisponível**. Esta regra substitui a descrição anterior de ausência de nomes provenientes da malha para esses bairros.

Na votação atual, o hover dos setores sem votos do candidato exibe **Total de votos: 0** e o nome dos bairros TSE correspondentes no crosswalk, seguido de **0 votos**. Sem referência nominal, exibe **Bairro sem referência disponível: 0 votos**. Os setores continuam cinza.

A seção **Votação por Bairros dentro dos municípios**, copiada de `deputados_streamlit`, aparece logo após **Mapa de Força Eleitoral**, antes de **Força da política local**.

A faixa principal segue o mesmo padrão de Mapa de Força Eleitoral, com gradiente azul, barra vertical à esquerda, cantos arredondados e tipografia ampliada, e mantém o título **Votação por Bairros dentro dos municípios** e o subtítulo `Votos por bairro no município selecionado.`. O card do mapa fica à esquerda (70%), com os filtros **Mesorregião → Município** e mapa Plotly de **560 px**. A seleção inicial destaca o município mais votado do candidato e sua mesorregião. Os controles têm chaves próprias por candidato; o controle municipal também é separado por mesorregião.

À direita (30%), cinco cards empilhados mostram **Total de votos no Município** com a participação percentual e badge verde do total municipal, **Bairro principal (Top 1)**, **Dependência do bairro principal**, **Penetração por bairros** e **Densidade média por bairro**. O visual, as badges e os critérios seguem a seção original. Penetração informa a quantidade de bairros com voto; não calcula uma proporção sem conhecer o total de bairros.

Nesta seção, somente Belo Horizonte usa malha de bairros. Nos demais municípios, as votações usam áreas ponderadas somente quando existem 8 ou mais unidades; abaixo desse corte, usam-se setores censitários com identificação pelo bairro TSE de maior votação. Essa regra também vale para os históricos de 2018 e 2022 dos deputados. A Projeção 2030 mantém bairros apenas em BH e setores nos demais municípios. A intensidade usa escala linear até 1.000 votos municipais e logarítmica acima de 1.000, sem azul uniforme nem ajuste pela quantidade ou proporção de polígonos com votos. O tooltip e a nota inferior mantêm a identificação territorial e a explicação da escala. Falta de dados, malha ou opções de município apresenta a mensagem específica da seção original.

**Somente para BH neste bloco**, todos os bairros são desenhados a partir de `IBGE/MG/dadosterritorio/MG_bairros_CD2022.parquet`, com vínculo exato por código IBGE de bairro ao stage 01b do candidato. Não há fallback para outras malhas ou associação por coordenadas. O hover usa nomes e votos do candidato, sem nomes vindos da malha; bairros sem registro mostram informação indisponível em cinza. Os cards de BH agrupam pelo `cd_bairro` do TSE, e o hover detalha os votos desses bairros eleitorais mesmo quando compartilham um polígono IBGE. A nota explica a origem da geometria e dos valores e informa registros sem correspondência. Essa exceção é restrita a Belo Horizonte.

O topo do card inclui **Eleição exibida no mapa**, com botões **2018**, **2022**, **2026** e **Projeção 2030**; 2026 é o padrão. A troca preserva os filtros territoriais. Em 2018/2022, os cards acompanham os votos conhecidos do ano e o mapa mostra aumento (verde), estabilidade (azul), queda (vermelho) ou ausência de comparação (cinza) em relação a 2026. O hover detalha os bairros TSE, os votos dos dois anos e a diferença média ponderada de participação. Anos sem valores no candidato/município apresentam indisponibilidade, sem tratar ausência como zero. Cobertura histórica parcial recebe nota.

Em **Projeção 2030**, a legenda usa **Proteger a base** (azul), **Oportunidade alta** (verde), **Potencial a desenvolver** (amarelo) e **Sem potencial ou dados incompletos** (cinza), com diagnóstico stage09b do eleitor ideal e os mesmos critérios do DNA. BH preserva bairros oficiais vinculados pelo código IBGE e nomes/votos TSE do candidato; os outros municípios mostram setores censitários. As estimativas demográficas são identificadas como diagnóstico. Os cinco cards continuam em 2026. A nota explica a cobertura e que potencial não prevê votos.

### 2.3 Concentração territorial dos votos

**Pergunta visual:** a candidatura depende de poucos redutos ou distribui votos por muitos municípios?

Uma faixa principal apresenta o título e a frase `Quanto da votação total está concentrada nos municípios onde o candidato mais recebeu votos.`. O conteúdo está em um único card. Na parte superior há **quatro cards**: Top 1, Top 5, Top 15 e Top 20. Cada card mostra o rótulo Top em caixa alta, com fonte ampliada de 1,15 rem e texto branco dentro de uma badge verde (#15803d), com borda sutil e cantos arredondados, seguido pelo total de votos acumulados em fonte grande e negrito, com `votos` como legenda discreta. Nomes de municípios e contagem de municípios não aparecem no cabeçalho dos cards. A rosca Plotly mostra o percentual acumulado em relação a 100% dos votos em formato de gauge circular: trilho escuro e arco ativo têm a mesma espessura, as pontas do progresso são arredondadas e o tom do azul evolui sutilmente de Top 1 a Top 20, chegando a `#60a5fa`. O texto de instrução de clique não aparece abaixo delas.

Um clique na rosca abre uma janela com a composição incremental até aquele Top: Top 1, municípios 2 a 5, 6 a 15 e 16 a 20, conforme o card selecionado. Cada etapa mostra sua contribuição percentual e votos absolutos, seguida do total acumulado.

Antes da curva, uma frase automática nomeia o líder e destaca o peso dos 15 municípios principais. Os expansores `Ver municípios do Top 5`, `Top 15` e `Top 20` aparecem em seguida, ainda antes da curva. As listas preenchem cada coluna de cima para baixo e continuam na coluna seguinte à direita, com três colunas em telas largas, duas até 900 px e uma até 600 px. Em seguida, uma curva Plotly mostra a participação acumulada em função da posição do município até **100% da votação**. O eixo horizontal usa escala logarítmica para separar melhor os primeiros marcos de concentração. A linha azul, a área translúcida, os marcadores e as referências percentuais permitem ver a velocidade da concentração. Os marcadores da curva são **Top 1**, **Top 5**, **Top 15**, **Top 20** e **Todos**; eles servem como leitura visual e não abrem janela ao clique. Sem linhas municipais válidas, o card exibe aviso e não fabrica uma curva.

## 3. Página 2 — DNA Eleitoral

O DNA segue: **Identidade da Base Eleitoral → Distribuição do Perfil do Eleitorado → BASE ELEITORAL DO CANDIDATO → Expansão & Oportunidades para 2030 → Potencial demográfico municipal**. Sunburst, heatmap e composição demográfica por pontos não integram a interface atual.

### 3.1 Identidade da Base Eleitoral

**Pergunta visual:** quem é o eleitor predominante do candidato?

A faixa principal usa o subtítulo `Quem é o eleitor-chave e quais atributos definem o perfil do seu eleitor.`. Ela é seguida pelo card de eleitor ideal, ocupando a largura do conteúdo.

#### 3.1.1 Eleitor ideal do candidato

O card principal é um `st.container(border=True)` com borda, fundo em gradiente azul e sombra. O título `Eleitor ideal do candidato` fica centralizado, com tipografia ampliada, forte e responsiva. Os badges coloridos dos atributos aparecem centralizados logo abaixo, com fonte ampliada e responsiva (1,15 a 1,35 rem), altura mínima de 3,2 rem, espaçamento interno generoso, bordas suaves e sombra discreta. Não há subtítulo, linha divisória nem rótulo PERFIL PREDOMINANTE. Quando o resumo agrega informação, aparece abaixo com emoji de fala; se apenas repete a persona, é ocultado. **A confiança do modelo não aparece no card.**

Na base do card, **quatro sub-cards com borda**, em `st.columns`, apresentam Gênero, Faixa etária, Escolaridade e Estado civil. Cada sub-card também usa `st.container(border=True)`. Títulos e categorias dominantes ficam centralizados. Cada percentual válido aparece em um gauge semicircular de 0 a 100, feito com `go.Indicator(mode="gauge+number")` dentro de `st.plotly_chart`; a cor do arco acompanha a dimensão. Os percentuais das quatro dimensões são independentes; não formam fatias de uma soma de 100%. Se o percentual não é válido ou não existe, o card não inventa o número. Os estilos desses badges e sub-cards são locais à página DNA; o hero e a navegação seguem o CSS compartilhado.

### 3.2 Distribuição do Perfil do Eleitorado

**Pergunta visual:** como se repartem as categorias demográficas e quais perfis sustentam a candidatura?

A faixa principal traz `Distribuição demográfica estimada dos votos, com recorte por município e perfil.`. A distribuição ocupa esta seção. A base eleitoral aparece em uma seção própria logo abaixo.

#### 3.2.1 Distribuição do eleitorado

O conteúdo está em um card com borda, gradiente azul, raio e sombra. No topo, em lugar do título e subtítulo internos, dois seletores lado a lado apresentam **MESORREGIÃO** e **MUNICÍPIO**. O primeiro oferece `Todas`; o segundo oferece `Todos os municípios` e apenas os municípios do candidato pertencentes à mesorregião selecionada, usando as referências geográficas compartilhadas. A seleção municipal tem estado próprio por mesorregião, evitando seleções incompatíveis. Com todos os municípios selecionados, a rosca e o total de votos respeitam o recorte mesorregional.

A composição abaixo usa **três colunas alinhadas verticalmente ao centro: categorias à esquerda (30%), rosca ao centro (40%) e quatro seletores à direita (30%)**, descontados os espaços entre colunas. A altura acompanha o maior conteúdo da linha, sem empilhar a legenda sobre a rosca nem reservar espaço adicional ao final. Cada seletor lista as categorias da sua dimensão, com a opção `Todas as categorias`. Seus títulos aparecem em badges destacados: **Gênero** verde, **Faixa etária** azul, **Escolaridade** roxo e **Estado Civil** amarelo com texto escuro. Alterar um seletor ativa sua dimensão na rosca e destaca a categoria escolhida, sem cruzar as quatro dimensões. Seletores sem dados ficam desabilitados com explicação.

Na coluna esquerda, a legenda da dimensão ativa mostra cor, categoria e percentual em linhas, no lugar da antiga badge de categoria dominante. Um badge identifica a dimensão exibida. A rosca Plotly centralizada mantém o total de votos do recorte no centro e os percentuais de fatias com pelo menos 1% fora do gráfico; as demais continuam no hover e na legenda. Gênero usa azul para feminino, laranja para masculino e cinza para não informado. A categoria selecionada recebe um afastamento discreto na rosca. A nota abaixo das três colunas explica que os percentuais descrevem dimensões separadas, sem cruzamentos individuais. Dados ausentes geram mensagem no lugar do gráfico.

### 3.3 BASE ELEITORAL DO CANDIDATO

A seção possui uma faixa principal no mesmo padrão de Distribuição do Perfil do Eleitorado, com título `BASE ELEITORAL DO CANDIDATO` e subtítulo `Quais perfis sustentam a candidatura e qual o peso de cada um na votação?`. O card de conteúdo abaixo começa diretamente na composição dos perfis, sem repetir título e subtítulo internos. Uma **barra de composição** apresenta a participação das classificações na votação do candidato: azul para Base eleitoral, ciano para Eleitor consolidado e verde para Eleitor emergente. A barra tem 72 px de altura e cantos arredondados. Cada segmento apresenta seu nome e percentual centralizados dentro da própria cor, sem legenda externa. Texto escuro nos segmentos ciano e verde reforça o contraste. Segmentos estreitos abreviam visualmente o nome com reticências; o tooltip preserva nome e percentual completos. Classificações sem participação não criam segmentos; uma parcela sem classificação aparece em cinza azulado com seu rótulo interno.

A lista abaixo contém **uma linha expansível por ICP**, ordenada dentro da classificação pelo peso eleitoral. A linha fechada mostra uma badge de maturidade (`🎯 Base Principal`, `🛡️ Eleitor Consolidado` ou `🚀 Eleitor Emergente`), com fonte de 1,95 rem (2,5 vezes os 0,78 rem dos chips), seguida dos atributos demográficos dominantes em chips. Os identificadores ICP não aparecem. A linha também mostra, percentual da votação e votos absolutos; uma seta sugere abertura. A linha aberta recebe borda mais clara e revela quatro blocos demográficos em grade de duas colunas. Cada bloco mostra dimensão, categoria dominante, percentual e uma barra azul individual. Uma nota esclarece que os percentuais descrevem categorias dominantes **dentro do perfil**. O bloco final `Leitura estratégica` traz a justificativa textual disponível. Dois ICPs com o mesmo rótulo estratégico continuam separados. Ausência de perfis gera mensagem, não um ICP fictício.

### 3.4 Expansão & Oportunidades para 2030

No hover, municípios sem associação ao diagnóstico mostram seu nome oficial e **0 votos**. Votos nulos em registros existentes, população estimada e participação ausentes aparecem como **Indisponível**, sem texto `nan` ou percentual de indisponibilidade. As cores permanecem ligadas ao diagnóstico.

**Pergunta visual:** onde proteger a base existente e onde há oportunidade demográfica relativa ao ICP escolhido?

O diagnóstico municipal stage 09b tem prioridade. Quando essa fonte não é lida, o componente usa o cálculo legado stage 08c com Censo, mantendo o mapa agregado por município.

A faixa principal apresenta `Mapeamento municipal de oportunidades demográficas e da base eleitoral para orientar a expansão territorial.`. **A implementação exibida logo abaixo é municipal**: não há mapa de bairros nem de áreas ponderadas nesta seção. Um seletor à direita alterna **ELEITOR IDEAL** e classificações estratégicas.

O conteúdo usa **mapa em card à esquerda (70%) e quatro cards de legenda empilhados à direita (30%)**, no padrão do Mapa de Força Eleitoral do RaioX Territorial. O seletor de ICP fica no canto superior direito, dentro do card do mapa. Os cards laterais têm borda tonalizada, sombra, gradiente com iluminação na cor da classe, badge de cor e títulos destacados: **Oportunidade de expansão** (verde), **Proteger a base** (azul), **Potencial a desenvolver** (amarelo) e **Baixa similaridade** (cinza). Cada um mantém a explicação da legenda original. A legenda torna o mapa categórico; cores não representam uma sequência contínua.

O mapa municipal é um **coroplético Plotly** com cerca de **560 px** de altura, dentro do card azul com borda e cantos arredondados. Cada município recebe uma das quatro classes; a barra categórica do Plotly fica oculta porque os cards laterais apresentam a legenda. No diagnóstico stage 09b, o hover informa município, leitura da classe, votos nos setores associados, população estimada do ICP e sua parcela na população de referência. No fallback stage 08c, informa votos, oportunidade e similaridade. A nota inferior explica a cobertura dos setores associados, os cortes relativos, os votos probabilísticos dos clusters e que potencial **não é previsão de votos**. No stage 09b, azul identifica o quartil superior de votos; verde exige população estimada no quartil superior e parcela na referência igual ou superior à mediana; amarelo identifica população estimada positiva fora desses critérios. Azul tem prioridade. A legenda cinza passa a **Sem potencial ou dados incompletos**. No fallback stage 08c, permanecem as explicações de oportunidade e similaridade. Se não houver dados completos de Censo/potencial ou a malha municipal falhar, o card mostra uma informação textual no lugar do mapa, mantendo as explicações laterais. Em telas estreitas as colunas seguem o empilhamento do Streamlit.

### 3.5 Potencial demográfico municipal

Atualização vigente: o hover dos setores sem associação exibe **Votos associados: 0** e o nome do bairro TSE correspondente no crosswalk, inclusive em BH. Sem nome de referência, exibe **Bairro sem referência disponível** e **0 votos**. Votos nulos em diagnósticos existentes continuam **Indisponível**; estimativas e percentuais ausentes também permanecem indisponíveis. Os nomes não incluem códigos TSE entre parênteses, e setores sem diagnóstico continuam cinza. Esta regra substitui a descrição anterior de votos indisponíveis em todo setor sem associação.

Uma faixa principal no mesmo padrão de Identidade da Base Eleitoral e Distribuição do Perfil do Eleitorado abre o bloco, com título **Potencial demográfico municipal** e subtítulo `Explore as oportunidades demográficas e a aderência ao perfil do eleitor em cada município.`.

O bloco usa os diagnósticos **stage 09b por setor**, com filtros **Mesorregião → Município → Perfil para expansão**, independentes da expansão estadual. Não há seletor de unidade intramunicipal nem fallback para áreas ponderadas.

O mapa ocupa 70% da largura e tem **640 px** de altura; quatro cards empilhados ocupam os 30% restantes. Em **Belo Horizonte**, a malha é de bairros oficiais IBGE, com diagnósticos setoriais agregados por código exato de bairro e cortes relativos recalculados entre bairros. Nos demais municípios, todos os setores censitários da malha municipal são desenhados; os nomes de bairros identificam as unidades no hover, sem mudar sua geometria setorial.

Os cards apresentam **Oportunidade alta** (verde), **Proteger a base** (azul), **Potencial a desenvolver** (amarelo) e **Sem potencial ou dados incompletos** (cinza). Os títulos ficam em badges arredondados na cor da classe, com texto branco em negrito e quebra de linha. Abaixo, a contagem usa o rótulo **Bairros** em BH e **Áreas** nos demais municípios, seguida da explicação. Fundo azul em gradiente, borda clara, raio de 16 px, padding de 20 px e sombra integram mapa e cards. Os cards acompanham o conteúdo; não há regra específica que force sua altura a preencher a coluna do mapa.

O tooltip mostra **Bairro: nome**, classe, votos associados, população estimada do ICP e parcela do ICP na população de referência. Não mostra código de setor ou bairro. Sem vínculo de bairro, usa **Bairro: Sem bairro vinculado**. Valores ausentes aparecem como **Indisponível**, e polígonos sem diagnóstico permanecem cinza.

As classes seguem os critérios relativos stage 09b da expansão estadual; fora de BH, os cortes são calculados antes do filtro municipal. A nota abaixo do mapa explica a agregação de BH, os vínculos exatos, as áreas sem diagnóstico e que votos associados a locais de votação não representam residência dos eleitores. Potencial demográfico não é previsão de votos. Falta de malha, diagnóstico ou vínculos recebe mensagem específica.

## 4. Página 3 — DRE Campanha

A página **DRE Campanha** concentra toda a seção **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO**, removida do RaioX Territorial. Sua rota é `/dre-campanha` e seu script é `pages/dre_campanha.py`, no mesmo padrão das outras páginas, com inicialização visual, hero e composição das seções.

O hero usa **DRE Campanha** como título e **Análise da arrecadação, dos compromissos e da aplicação dos recursos da campanha.** como subtítulo. Mantém fundo, foto, nome, cargo, partido e total de votos do candidato. O botão DRE Campanha fica destacado no sidebar enquanto essa página está ativa.

A ordem do conteúdo é **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO → Balanço Macro & Liquidez de Caixa → Estrutura da Receita → Contratado × Pago → Da origem ao destino**. São preservados todos os cards expansíveis, indicadores, gráficos, tabelas, filtros e estados sem dados descritos abaixo. As fontes continuam sendo os cinco artefatos financeiros do candidato selecionado. Não há cópia da análise no RaioX Territorial.

### 4.1 EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO

Os quatro cabeçalhos de subseção (Balanço Macro, Estrutura da Receita, Contratado × Pago e Da origem ao destino) ocupam toda a largura disponível, com padding de 1 rem por 1,35 rem, fundo azul discreto e faixa lateral azul de 4 px. Os títulos usam fonte responsiva de 1,25 a 1,6 rem, peso 800 e subtítulos de 0,95 rem em azul claro. A composição é mais compacta que a faixa principal para preservar a hierarquia visual.

Na subseção 1, o arranjo atual segue a mesma composição da subseção 2: uma coluna de 50% à esquerda com o card da rosca; à direita, os outros 50% contêm dois cards empilhados, DRE Simplificada da Campanha e Comprometimento Orçamentário. O gauge permanece centralizado dentro de seu próprio card, logo abaixo do funil. Este arranjo substitui a linha independente anterior do gauge. Em telas estreitas, as colunas seguem o empilhamento do Streamlit.

Os 50% à direita do Top 10 recebem dois cards empilhados. **Índice de Concentração da Receita** apresenta rosca de 340 px com abertura 60%, percentual do Top 10 centralizado, legenda inferior e cores azul (Top 10), ciano (demais identificados) e cinza (sem atribuição, quando conhecida). **Ranking Completo** traz um expander inicialmente fechado com tabela de auditoria somente para leitura: posição, doador, CPF/CNPJ, valor atribuído, percentual da receita com barra de progresso e receitas vinculadas. Documentos preservam zeros iniciais e valores usam reais. Os cards mantêm fundo, borda e tipografia do dashboard; ausência de dados oculta o card correspondente.

O primeiro gráfico da Estrutura da Receita é **Top 10 Doadores**, abaixo dos KPIs, na metade esquerda de uma linha 50%/50%. Seu card mantém borda e fundo padrão. Barras horizontais azuis mostram valores em reais nas pontas; os maiores doadores aparecem no topo, seguindo o ranking. Nomes completos quebram em linhas no eixo, sem reticências; a altura acompanha os rótulos e o tooltip preserva nome e valor. Fundo transparente, textos claros e grade discreta integram o Plotly ao dashboard. Registros ausentes ficam ocultos.

Na Estrutura da Receita, cards de KPIs sem dados são ocultos, e os disponíveis dividem a largura da linha. Sem dados para nenhum KPI, a linha não aparece. O ranking exibido é o de doadores imediatos, separado dos originários; esta regra substitui a exibição anterior de Indisponível nesses cards.

Sob o subtítulo de **ESTRUTURA DA RECEITA**, quatro cards de KPIs apresentam **Maior Doador (Top 1)**, **Concentração no Top 10**, **Cobertura da Atribuição** e **Total de Doadores Unificados**. Usam títulos em badges verdes, valores brancos destacados e descrições em azul claro, com fundo azul em gradiente, borda fina, sombra e cantos de 14 px. O Top 1 mostra valor em reais e nome completo do doador, com quebra de linha. Os dois percentuais têm uma casa decimal e a contagem usa separador de milhar. Quatro colunas passam para duas abaixo de 1100 px e uma abaixo de 600 px. Dados insuficientes mostram Indisponível. Esta implementação substitui a indicação anterior de subseção sem conteúdo analítico.

A subseção 2, **ESTRUTURA DA RECEITA**, começa após o gauge de comprometimento, com subtítulo **Origem e concentração dos recursos da campanha**. Seu card usa `section_header(..., compact=True)`, com o mesmo fundo azul translúcido, borda fina, cantos arredondados e hierarquia dos cabeçalhos internos. Nesta etapa exibe título e subtítulo, sem conteúdo analítico. Integra a aplicação de deputados estaduais.

Logo abaixo da linha de rosca e funil, **Comprometimento Orçamentário** ocupa um card centralizado de meia largura (colunas 1:2:1), com título centralizado e gauge semicircular idêntico ao DNA: `go.Indicator(mode="gauge+number")`, 170 px, arco azul claro de espessura 0,48, trilho translúcido, fundo transparente e número branco de 25 px com uma casa decimal. O cálculo é despesas contratadas / receita total × 100, com valores de referência e fórmula abaixo. Percentuais acima de 100% são preservados e ampliam a escala, com nota explicativa. Receita zero, dados ausentes ou inválidos geram mensagem. O card acompanha o empilhamento responsivo do Streamlit.

Layout atualizado das visualizações: dois cards lado a lado, cada um com 50% da largura disponível. **Composição das Receitas** fica à esquerda com a rosca e, abaixo, duas colunas de legenda. **DRE Simplificada da Campanha** fica à direita com funil Plotly de 400 px, fundo transparente, texto claro e barras azul, ciano, índigo e verde. As etapas são Receita Total → Receita Financeira → Despesa Contratada → Despesa Paga, com valores em reais nas barras e no hover. A nota explica que são totais de cada etapa, sem subtração, e que compromissos podem superar receitas. Dados incompletos, negativos ou todos zerados geram mensagem. Em telas estreitas, o Streamlit empilha as colunas. Esta composição substitui o layout anterior de legenda à esquerda da rosca.

Logo abaixo dos quatro cards fica **Composição das Receitas**, em contêiner nativo com borda, seguindo o fundo azul e a tipografia do RaioX Territorial. À esquerda (40%), a legenda mostra títulos, valores em reais e percentuais com marcas azuis; à direita (60%), a rosca Plotly de 400 px usa abertura de 60%, fundo transparente, azul #2563eb para Entrada Financeira (Dinheiro) e ciano #38bdf8 para Bens e Serviços (Estimável). O total das duas receitas aparece no centro. Fatias de pelo menos 1% mostram o percentual externo; todas têm valor e percentual no hover e na legenda. A nota esclarece que receita estimável não é dinheiro em caixa. Ausências, valores negativos e soma zero mostram mensagem, sem fabricar proporções. As colunas seguem o empilhamento do Streamlit em telas estreitas.

Atualização dos indicadores: os três primeiros cards agora usam `gastos/stage05a_resumo_financeiro.parquet` da base anual selecionada. Arrecadação apresenta Dinheiro / Espécie e Bens e Serviços Doados; Compromissos apresenta Despesas Contratadas e Despesas Pagas; Liquidez apresenta Saldo Líquido / Resultado e Saldo a Pagar. Cada indicador ocupa um bloco com título, valor em reais destacado e descrição; uma linha discreta separa os blocos. Resultado = receita financeira − despesas pagas; saldo a pagar = despesas contratadas − despesas pagas. O resultado recebe badge verde para caixa positivo, vermelha para déficit temporário de liquidez ou neutra para caixa equilibrado. Dados ausentes aparecem como Indisponível. Somente o quarto card permanece vazio. Esta atualização substitui as referências abaixo aos interiores vazios e à ausência de indicadores.

Após o subtítulo de **BALANÇO MACRO & LIQUIDEZ DE CAIXA**, aparecem quatro cards expansíveis da aplicação de deputados estaduais: **Arrecadação (Receitas)**, **Compromissos (Despesas)**, **Liquidez & Saúde do Caixa** e **Volume de Lançamentos**. São quatro colunas de mesma largura em telas largas, duas abaixo de 1100 px e uma abaixo de 600 px. Cada card mantém fundo azul em gradiente, borda clara e cantos arredondados; o título usa badge verde (#15803d), texto branco em negrito e fonte de 1,1 a 1,5 rem. Uma seta gira quando o card se expande. Clique ou teclado abre e recolhe cada card independentemente. Todos começam fechados; o interior permanece vazio nesta etapa, aguardando os indicadores do stage 05a de `2026/gastos`. As referências abaixo à ausência de conteúdo analítico continuam válidas; os cards já estão implementados.

A seção abre com o card de cabeçalho com o título **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO** e o subtítulo `Análise do retorno do investimento eleitoral: veja onde o orçamento foi alocado e quanto custou a conquista de cada voto.`, no mesmo padrão visual das faixas principais.

Logo abaixo, um card de subseção apresenta **BALANÇO MACRO & LIQUIDEZ DE CAIXA** e o subtítulo `Raio-x executivo da arrecadação e dos compromissos financeiros: monitore o saldo real de caixa, o volume contratado e a saúde orçamentária da campanha.`. Ele reutiliza o cabeçalho interno (`mapa-section-card`), com fundo azul translúcido mais suave, borda fina de 1 px, cantos arredondados e tipografia menor que a faixa principal. Não há indicadores, gráficos, filtros, notas ou mensagens de ausência abaixo dele.

## 5. Página 4 — Impacto político

O script `pages/impacto_politico.py` aplica o modelo visual compartilhado e o hero padrão, com título, subtítulo, foto, nome, cargo, partido e total de votos. A página segue a ordem **Força da política local → Mapa da atuação parlamentar de acordo com os votos**. As duas seções foram transferidas integralmente do RaioX Territorial, preservando os mapas, cores, indicadores, cards e diálogos. Os componentes ficam em `common/local_political_strength.py` e `deputados/emendas.py`, sem executar outra página. Cabeçalhos e estilos dos KPIs são compartilhados com as demais páginas.

### 5.1 Força da política local

Atualização vigente: o parágrafo explicativo acima das legendas foi removido. As quatro legendas usam fonte de 1 rem em negrito, texto claro, preenchimento mais intenso na cor da classe, borda de 2 px e maior espaçamento interno, com altura mínima de 4,5 rem. Mantêm quatro colunas em telas largas, duas abaixo de 900 px e uma abaixo de 560 px.


A faixa principal usa o título `Força da política local` e o subtítulo `Veja se vereadores e prefeitos das cidades foram decisivos na sua votação`. A estrutura repete a proporção 70/30 do Mapa de Força Eleitoral.

À esquerda há um card com o filtro territorial fixado em **Município** e a malha completa de Minas Gerais, com divisões municipais brancas e contorno estadual mais espesso. O card tem altura alinhada ao fim dos quatro cards laterais, para que o contorno do mapa termine no mesmo eixo visual do último card. Antes do mapa, uma explicação centralizada e em negrito informa que a seção avalia a eficácia de prefeitos e vereadores aliados na transferência de votos e considera votação alta quando o percentual do candidato na cidade supera sua média no estado. Abaixo, quatro pílulas coloridas mantêm o fundo da classe e informam, com texto centralizado: prefeito/vereadores entregaram votos, prefeito/vereadores não entregaram votos, votação própria sem prefeito/vereadores e ausência de prefeito/vereadores e votos, sem repetir o nome da cor no texto. O mapa cruza `capital_local_0a100` com o market share municipal. Nota alta significa resultado acima de 50/100; market share alto significa resultado municipal igual ou superior à participação estadual do candidato. O hover mostra município, classe, leitura, nota, market share local e referência estadual.

À direita, quatro cards empilhados também funcionam como legenda e filtro. **🤝 Alianças de alto retorno** usa verde; **⚠️ Acordos sem entrega**, vermelho; **⭐ Votação própria**, azul; e **❄️ Zonas neutras**, cinza. Cada card recebe no fundo um gradiente translúcido da própria cor, mais luminoso no canto superior esquerdo e integrado ao azul profundo da interface; o estado selecionado intensifica esse banho de cor e ganha contorno reforçado. O ícone e o título aparecem em uma badge no topo. Abaixo, a quantidade de cidades e a participação na votação recebem peso e tamanho maiores, seguidas pela **Cidade-chave** com seus votos. A estratégia encerra o card dentro de uma pílula tonalizada pela cor da classe. Ao clicar, apenas a classe escolhida mantém sua cor no mapa e as demais ficam atenuadas; clicar novamente limpa o destaque.

Um clique em qualquer município abre a janela **Força política local**, com o nome municipal como título interno. No topo aparecem a classificação e quatro números: votos, market share local, referência estadual e capital político local. Uma frase traduz a cor em leitura estratégica. Abaixo, o layout divide-se em duas colunas: à esquerda, o polígono isolado do município conserva a cor recebida e é seguido pelos detalhes da prefeitura, Câmara, partidos aliados e base dos dados; à direita, uma lista rolável apresenta prefeito e vereadores, com nome, partido, vínculo e afinidade.

### 5.2 Mapa da atuação parlamentar de acordo com os votos

Seção de deputados estaduais, copiada de `deputados_streamlit`, depois de Força da política local, encerrando o conteúdo de Impacto político. A faixa principal usa o título **Mapa da atuação parlamentar de acordo com os votos** e o subtítulo `Índice de Retorno Parlamentar: valor total de emendas no município dividido pelos votos recebidos.`.

A coluna esquerda ocupa 70% e apresenta três KPIs — **Taxa de Reciprocidade**, **Maior Beneficiado (R$)** e **Média R$/Voto** — acima do card com mapa municipal Plotly de **720 px**. A coluna direita ocupa 30% e mostra seis cards empilhados, com gradientes, bordas coloridas, título em badge, quantidade de cidades, participação na votação e descrição: **BASE PRIORIZADA** (azul `#2563EB`), **APOSTA POLÍTICA** (verde `#16A34A`), **BASE EM RISCO** (amarelo `#FACC15`), **PRESENÇA PONTUAL** (laranja `#F97316`), **VOTAÇÃO ORGÂNICA** (cinza `#64748B`) e **TERRITÓRIO NEUTRO** (branco `#FFFFFF`). Os cards são legenda, sem filtro por clique.

O hover informa município, classe, votos e valor de emendas. Clicar no município abre **Emendas destinadas ao município**, com nome, votos, classe, total e tabela por finalidade e tipo de indicação, mostrando quantidade de indicações e valor indicado. A nota preservada esclarece que pagamento e indicação podem diferir. Fechar a janela mantém a seleção do candidato.

Sem dados, permanecem as mensagens e os KPIs de ausência da seção original. As classificações fornecidas pelo parquet têm prioridade; quando faltam, municípios com emendas usam a classe original Sem Expressão. Os critérios e a adaptação dos códigos territoriais estão documentados no README.

## 6. Interação, estados e continuidade visual

### 6.1 Escopo dos controles

| Controle | Onde atua | Persistência observável |
| --- | --- | --- |

| Candidato na barra lateral | Quatro páginas | Exibe somente deputados do prefixo configurado e preserva a seleção ao trocar de rota |
| Botões RaioX Territorial / DNA / DRE Campanha / Impacto político no sidebar | Navegação | Opção ativa destacada; preserva o candidato ao trocar de página |
| Filtro territorial Mesorregião / Município | Mapa estadual do RaioX Territorial e conteúdo da janela aberta por clique | Restrito ao primeiro mapa |

| Eleição na votação por bairros dos deputados | Mapa intramunicipal e cinco cards | 2018/2022 mostram histórico quando disponível; 2026 mostra votação atual; Projeção 2030 usa stage09b e mantém os cards em 2026 |

| Mesorregião / Município da votação por bairros | Mapa intramunicipal e cinco cards laterais do RaioX Territorial | Estado por candidato e mesorregião |
| Filtro Município da força política local | Mapa categórico dos quatro quadrantes em Minas Gerais | Única granularidade disponível nesta etapa |
| Cards da força política local | Destacam ou restauram uma classe do mapa | Card ativo recebe contorno reforçado |
| Clique em município da atuação parlamentar (deputados) | Abre o detalhamento das emendas por finalidade e tipo | Janela modal; preserva candidato |
| Clique em município da força política local | Abre o mapa isolado, os indicadores e a composição política municipal | Janela modal; fecha sem alterar o filtro dos cards |
| Município e dimensão da rosca DNA | Rosca e total do recorte | Restrito à seção de distribuição |
| Mesorregião e município do Potencial demográfico municipal | Bairros oficiais em BH; setores censitários nos demais municípios | Restrito ao bloco municipal |
| Perfil para expansão | Classes e métricas do mapa de Expansão 2030 | Restrito à seção de expansão do DNA |

### 6.2 Estado sem dados

Uma falha na listagem do bucket aparece uma vez na área principal. Se a pasta não existir, a mensagem identifica o caminho e orienta conferir `HF_VISUALIZACAO_PREFIX`; as seções não repetem a mesma mensagem.

Falta de parquet, malha ou dimensão não deve parecer valor zero. A implementação usa `st.info`, `st.warning`, captions ou cards com texto para explicar o que está ausente. Zero legítimo continua como valor ou cor mínima quando existe malha e a métrica pode ser calculada. Os mapas mantêm municípios ou setores sem votos visíveis onde a fonte geométrica está disponível. As notas analíticas permanecem próximas ao gráfico a que se referem.

### 6.3 Responsividade implementada

Os botões de navegação permanecem empilhados no sidebar, inclusive em telas menores com a barra recolhível. O hero usa toda a largura do conteúdo. A foto e os textos também se ajustam por regras CSS próprias. Os KPIs compartilhados do RaioX e de Impacto político passam de linha para uma coluna em telas até cerca de **900 px**. A faixa Top 1/5/15/20 passa para duas colunas; a lista de municípios reduz colunas novamente abaixo de **600 px**. Os quatro sub-cards do eleitor ideal passam para duas colunas abaixo de **900 px** e uma coluna abaixo de **760 px**. No card dos ICPs, o resumo e as barras demográficas empilham abaixo de **600 px**; o cabeçalho de cada perfil pode quebrar em telas estreitas. A legenda de expansão estadual mantém quatro cards em uma coluna; abaixo de **640 px**, reduz padding e remove a altura mínima dos cards.

Os pares de mapa e cards laterais do RaioX e de Impacto político e o par rosca/filtros do DNA são montados com `st.columns`; a experiência móvel também depende do empilhamento padrão do Streamlit. Nomes longos de município e persona podem quebrar linha. Tooltips complementam os rótulos que não cabem nos cards.

## 7. Critérios de fidelidade para futuras alterações

1. Preservar a diferença entre **intensidade** (gradiente azul contínuo) e **classe** (cores da força política local e da expansão).
2. Manter a leitura em camadas: hero, faixa principal, cabeçalho interno quando necessário e conteúdo analítico.
3. Manter os cards de potencial municipal vinculados às categorias e ao recorte exibido; na força política local, manter as recomendações vinculadas aos quatro quadrantes.
4. Mostrar voto observado, estimativa demográfica, custo de referência, gasto rateado e potencial em seus papéis corretos, com unidades e notas visíveis.
5. Fazer seleção e estado vazio permanecerem compreensíveis sem depender só de cor.
6. Atualizar este briefing quando mudar texto, card, escala, interação, ordem de seção ou granularidade de mapa.
7. Preservar o escopo exclusivo de deputados estaduais, a seleção de candidatos no prefixo configurado e sua continuidade entre páginas.
8. Preservar Força da política local e Mapa da atuação parlamentar exclusivamente em Impacto político, nessa ordem. Manter a concentração no encerramento do RaioX Territorial e toda a análise financeira na página DRE Campanha.

Nesta seção, áreas ponderadas servem somente ao vínculo geométrico. Toda a informação eleitoral vem de `stage01b_bairros.parquet`, com bairros identificados por `cd_bairro` do TSE. Nas áreas ponderadas, o hover lista cada bairro apenas com nome TSE e votos, sem códigos ou parênteses; a soma dos votos associados ao polígono aparece ao final. O código TSE continua sendo a chave interna de agrupamento. Nos históricos, mostra também as somas de cada ano. Cards agrupam por `cd_bairro` em todos os municípios. Nomes e códigos de área ponderada não aparecem no hover, nos cards ou na legenda. A Projeção 2030 mantém o diagnóstico por setores fora de BH, identificando-os pelo bairro TSE mais votado em 2026.

Nos municípios com menos de 8 áreas ponderadas, `cd_setor_censitario` do stage 01b serve somente para o vínculo exato com `code_tract` da malha. Nenhum nome de setor ou bairro é obtido da referência geográfica e não há associação por coordenadas/proximidade nesse modo. Em divergências, os votos são somados por `cd_bairro` dentro de cada setor e o bairro com mais votos identifica o polígono; empate usa o código TSE em ordem crescente. Nos históricos, a prioridade usa os votos do ano selecionado; na Projeção 2030, usa 2026. O tooltip informa o bairro vencedor e seus votos, enquanto o total do polígono preserva todos os votos associados. Os cards continuam calculados por bairro TSE, sem descartar bairros perdedores na disputa pela identificação do setor.

O primeiro card lateral da votação por bairros mostra o título Total de votos no Município, percentual dos votos do município na votação do candidato e badge verde Total municipal com os votos absolutos. Numerador e denominador vêm do stage01b do candidato para o ano exibido; Projeção 2030 mantém 2026. Sem denominador válido, o percentual fica indisponível.

Na seção Votação por Bairros dentro dos municípios, o mapa de intensidade usa somente o total de votos municipal para escolher a escala: linear até 1.000 (inclusive) e logarítmica acima de 1.000. Não há cor uniforme para municípios pequenos nem fator de cobertura por quantidade de bairros, áreas ou setores. O máximo de votos associado usa toda a faixa de intensidade. Os históricos comparativos e a Projeção 2030 mantêm suas cores categóricas, pois representam classes e não intensidade.


### Alinhamento do Balanço Macro

O Balanço Macro & Liquidez de Caixa mantém três cards expansíveis lado a lado, com larguras iguais e alinhamento externo ao cabeçalho da subseção: Arrecadação (Receitas), Compromissos (Despesas) e Liquidez & Saúde do Caixa. O card Volume de Lançamentos foi removido. A grade ocupa 100% da largura, com gaps de 16 px, e empilha os três cards abaixo de 900 px. Esta atualização substitui as descrições anteriores de quatro cards.

O card Composição das Receitas e sua rosca usam altura extensível para acompanhar o conjunto DRE Simplificada e Comprometimento Orçamentário na coluna direita. As bordas superiores e inferiores ficam alinhadas, eliminando a sobra externa abaixo do card esquerdo. O layout mantém duas colunas de mesma largura e o empilhamento responsivo do Streamlit.

### Subseção 4 — Contratado × Pago

Atualização vigente: os três cards são expansíveis e começam fechados, mostrando apenas título e seta. Os títulos usam a mesma fonte, padding e badge verde com largura disponível e altura mínima de 3 rem. O primeiro não reserva mais espaço vertical adicional no cabeçalho. Os indicadores aparecem somente ao expandir cada card, de forma independente.

Atualização vigente: o card Indicadores de Alerta / Distorções foi removido. Os três restantes ocupam colunas iguais, alinhadas ao topo e à largura do cabeçalho, com gaps de 16 px. Total Contratado vs. Total Pago é expansível, inicialmente fechado, com seta e foco por teclado; sua abertura mostra os totais contratado e pago. Taxa de Execução Geral e Saldo em Aberto permanecem visíveis. Abaixo de 900 px os cards empilham. Esta regra substitui a descrição anterior de quatro cards.

Após a Estrutura da Receita, o cabeçalho interno **Contratado × Pago** usa o subtítulo **A importância da análise de passivos, prazos e distorções entre contratos e pagamentos.** Quatro cards executivos aparecem lado a lado: Total Contratado vs. Total Pago, Taxa de Execução Geral, Saldo em Aberto e Indicadores de Alerta / Distorções. O último é expansível e começa fechado, mostrando ao abrir excesso pago conhecido, contratado sem pagamento e defasagem média conhecida em dias. O layout segue os cards azuis e badges verdes, passando para duas colunas abaixo de 1100 px e uma abaixo de 600 px.

O alias `execucao_resumo` lê `gastos/stage05d_execucao_resumo.parquet` da base anual selecionada. Usa exclusivamente a linha `recorte=global`, sem somar categorias e fornecedores. Campos monetários usam Decimal. O saldo prioriza `saldo_em_aberto`; o fallback `saldo_liquido` recebe identificação e explicação próprias. A taxa vem de `taxa_execucao_pct`, sem média de percentuais dos recortes nem limite em 100%. A badge indica execução não iniciada (0%), parcial (entre 0 e 100%), integral (100%) ou pagamento acima do contratado (>100%); não infere atraso por calendário. Ausências, valores inválidos e resumo global ambíguo aparecem como Indisponível. Zero válido e defasagem negativa são preservados. A subseção é da aplicação de deputados estaduais e independente dos filtros de doadores.

### Filtros de Contratado × Pago

Antes dos KPIs, **Recorte da análise** alterna Global / Geral da Campanha, Por Categoria de Despesa e Por Fornecedor. Global é o padrão e usa a linha global nos KPIs, mantendo o comparativo por categorias ou Top 10 Fornecedores no gráfico. Categoria e Fornecedor exibem um segundo selectbox para escolher o grupo; os quatro cards e o gráfico passam a usar exclusivamente esse grupo, sem somar outros recortes nem fazer médias de taxas e prazos. Os rótulos priorizam `categoria` e `nm_fornecedor` quando presentes, com fallback para `grupo_descricao` do resumo atual. A chave de seleção é `grupo_chave`, preservando fornecedores homônimos como grupos distintos. Seleções têm estado por candidato e tipo de recorte. Ausência de grupos gera mensagem e indicadores indisponíveis. Esta regra substitui a restrição anterior dos KPIs ao resumo global.

### Gráfico comparativo de Contratado × Pago

Abaixo dos quatro cards, um card de largura integral apresenta barras horizontais agrupadas: Contratado em azul e Pago em ciano, com valores em reais nas pontas. O seletor **Comparar por** alterna Categoria e Top 10 Fornecedores, usando exclusivamente o respectivo `recorte` do stage 05d. A ordem usa o maior valor entre contratado e pago; fornecedores ficam limitados aos dez primeiros, sem promover posições posteriores quando um registro tem dados inválidos. Nomes quebram em linhas e a altura acompanha os grupos. O hover informa valores e diferença, distinguindo saldo ainda não pago de pagamento acima do contratado. Zero válido aparece como zero; dados incompletos não viram zero e recebem nota de cobertura. Grupos duplicados tornam a comparação indisponível. A nota explica que diferenças de volume não comprovam atraso, retenção ou adiantamento sem datas e prazos contratuais. O seletor tem estado por candidato e não altera os KPIs globais.

### Última subseção — Da origem ao destino

Após o gráfico de Contratado × Pago, o card introdutório usa o título **DA ORIGEM AO DESTINO: O CAMINHO DOS RECURSOS** e o subtítulo **Cruze as fontes de financiamento (FEFC, Fundo Partidário e Doações) com os pagamentos efetuados por categoria e fornecedor para entender para onde foi cada real da campanha.** O componente reutiliza `section_header(..., compact=True)`, com o mesmo fundo azul, borda, cantos arredondados e hierarquia dos demais cabeçalhos internos. Integra a aplicação de deputados estaduais. Nesta etapa contém apenas a introdução, sem indicadores, filtros ou gráficos próprios.

### De onde vem? — Recursos por fonte

Na última subseção, **De onde vem?** ocupa os 50% esquerdos da página, em card azul com gráfico Plotly de barras horizontais agrupadas: Arrecadado (`receita_total`, azul) e Efetivamente pago (`despesa_paga`, ciano), por `fonte_descricao`, em ordem decrescente de arrecadação. A metade direita fica disponível para o próximo gráfico. O alias `receita_despesa_fontes` resolve `gastos/stage05e_receita_despesa_fontes.parquet` do candidato selecionado. Cada `fonte_chave` deve ser única; duplicações geram indisponibilidade.

Os rótulos das fontes mostram saldo financeiro observado e taxa de utilização financeira, também disponíveis no hover junto à receita financeira e aos valores das barras. Os indicadores vêm diretamente de `saldo_financeiro_observado` e `taxa_utilizacao_financeira_pct`: valores ausentes não viram zero, saldos negativos e taxas superiores a 100% são preservados. A nota esclarece que arrecadação total inclui receita estimável, enquanto saldo e utilização se referem à parcela financeira e não representam saldo bancário conciliado. Valores inválidos nas barras são omitidos com nota de cobertura. Não há novos KPIs ou filtros nesta etapa. Esta implementação substitui a indicação anterior de introdução sem gráficos.

### Para onde vai? — Destinação por fonte

O título **Para onde vai?** e os selectboxes **Fonte de financiamento** e **Destinação por** ficam lado a lado na linha superior do card, com alinhamento vertical central. A tabela renderizada omite CPF/CNPJ e Natureza, mostrando fonte, categoria ou fornecedor, valor pago e percentual do total pago. Esta regra substitui a descrição anterior dessas colunas.

Atualização vigente: os cards **De onde vem?** e **Para onde vai?** não exibem notas de rodapé. Os dois contêineres usam altura extensível para alinhar suas bordas inferiores. Avisos de dados indisponíveis ou fontes omitidas permanecem como mensagens de informação.

Os 50% direitos da última subseção apresentam o card **Para onde vai?**, com tabela somente para leitura baseada no alias `destinacao_fontes`, que resolve `gastos/stage05e_destinacao_fontes.parquet`. O filtro **Fonte de financiamento** oferece Todas as fontes e as fontes disponíveis no resumo ou na destinação. **Destinação por** alterna Categoria de Despesa e Fornecedor, mantendo os recortes separados para evitar dupla contagem.

A tabela ordena `valor_pago` em ordem decrescente e mostra fonte, `grupo_descricao`, `nr_cpf_cnpj_fornecedor`, natureza da despesa quando disponível, valor pago em reais e `pct_total_pago`. CPF/CNPJ permanece texto, preservando zeros iniciais; valores ausentes não viram zero. Os percentuais mantêm o total pago da campanha como referência, sem renormalização após filtrar fonte. Filtros têm estado por candidato e atuam apenas na tabela. Ausência de fonte ou recorte recebe mensagem específica, sem impedir o gráfico esquerdo. Esta composição substitui a reserva anterior da metade direita para um gráfico futuro.

### Filtros da Estrutura da Receita

O expander **Ver detalhamento dos doadores** em **Ranking do recorte** começa aberto. Os cards de doadores e ranking usam altura extensível, com larguras iguais e bordas superiores e inferiores alinhadas quando exibidos lado a lado.

A tabela Ranking do recorte omite a coluna CPF/CNPJ; mantém posição, doador, valor atribuído, percentual da receita e quantidade de receitas vinculadas.

O card Índice de Concentração da Receita foi removido. Os cards Top 10 Doadores (ou Todos os Doadores) e Ranking do recorte ficam lado a lado, com larguras iguais e bordas superiores alinhadas, sem espaço reservado para a rosca removida. Se apenas um card tiver dados, ocupa toda a largura disponível. Filtros, KPIs e expander do ranking permanecem.

Acima dos cards, três selectboxes controlam toda a subseção: **Tipo de Doador** (Imediato ou Originário), **Top 10 vs. Todos** e **Cobertura & Status da Atribuição** (todas as situações ou um status disponível). O padrão é Imediato / Top 10 / Todas as situações. O recorte se aplica aos KPIs, barras, concentração e tabela; Todos expande também as barras. `eh_top10` controla o recorte, com fallback para ranks 1 a 10 quando a coluna não existe. Ranks não são recalculados ao filtrar status. Esta regra substitui a restrição anterior a doadores imediatos.

A badge apresenta `cobertura_atribuicao_pct`, `situacao_atribuicao` e `qt_vinculos_pendentes`. Cobertura e pendências repetidas usam valores únicos válidos, sem soma; ausências ou divergências ficam indisponíveis. Status diferente de completa ou pendências positivas geram aviso. Percentuais mantêm a receita total como referência; a concentração representa os registros Top 10 presentes no recorte. A tabela se chama Ranking do recorte. Seleções são independentes por candidato e status por tipo de doador. Recorte vazio recebe mensagem explícita.
