# Briefing visual — Visualização Eleitoral

Este documento registra **a interface implementada hoje** nas duas páginas do aplicativo. Ele descreve a aparência, a ordem de leitura, os controles, as respostas às interações e os estados sem dados. A proposta compartilha a mesma experiência entre vereadores e deputados estaduais, com seções adaptadas ao cargo; funcionalidades planejadas são identificadas separadamente. O [README](README.md) concentra a arquitetura e as fontes; aqui o foco é o que o usuário vê e entende. A expansão para 2030 é municipal; o bloco final de potencial usa bairros oficiais em BH e setores censitários nos demais municípios.

Revisado em 13 de outubro de 2026 a partir dos componentes chamados pelas páginas atuais.

A implementação mantém uma entrada única em `app.py` e as duas páginas compartilhadas. As seções exclusivas de vereadores ficam em `src/eleitoral/vereadores/`; `src/eleitoral/deputados/` contém a seção de emendas desse cargo. Essa organização não altera a ordem, os controles ou a aparência descritos neste documento.

## 1. Visão geral da experiência

O produto é um painel de inteligência eleitoral para deputados e vereadores, com duas rotas. **Raio X Eleitoral** mostra os dados do candidato selecionado, sua distribuição territorial, concentração e custo do voto; o ano padrão do projeto é 2026 e, se não estiver disponível para uma pasta, usa o ano numérico mais recente encontrado. **DNA Eleitoral** sintetiza o eleitor predominante, os perfis estratégicos e a distribuição demográfica. **Expansão 2030** mostra oportunidades territoriais. As páginas compartilham candidato selecionado, fundo, hero, tipografia e família de cards.

O percurso é vertical. Uma capa apresenta o candidato; faixas de seção delimitam cada pergunta analítica; os cards abaixo contêm números, mapas ou gráficos. A barra lateral seleciona cargo e candidato. A navegação nativa de páginas fica oculta: os dois botões verticais do hero fazem a troca entre Raio X Eleitoral e DNA do Eleitor e destacam a página ativa.

### Barra lateral e variações por cargo

A barra lateral começa pelo título **Cargo Atual**, seguido de um selectbox com **Vereadores** e **Deputados Estaduais**. Abaixo aparece **Candidato**, com o botão **Atualizar candidatos** e o selectbox **Candidato**. As opções exibem somente o nome, como Marcela Trópia ou Fernando Breno, sem nome de pasta. Não há legenda inferior com cargo, ano ou slug.

Vereadores lista candidatos de `vereadores/`; Deputados Estaduais lista candidatos de `dep_estaduais/`. Ambos exigem uma pasta anual como `2026`. Bruno e Pablo aparecerão quando seus dados anuais forem gerados; `bh_2026` não substitui essa base. Trocar cargo reinicia os estados da candidatura e das visualizações. Trocar página pelos botões preserva cargo e candidato.

| Seção | Vereadores | Deputados Estaduais |
| --- | --- | --- |
| Como foi sua votação em Belo Horizonte — Raio X | Visível | Oculta |
| Eleitor de BH x Eleitor do Interior — DNA | Visível | Oculta |
| Demais seções atuais | Compartilhadas | Compartilhadas |
| Emendas legislativas | Sem seção atual | Implementada entre concentração e seção financeira |

A seção de emendas dos deputados replica o componente de `deputados_streamlit`: mapa, três indicadores, seis cards de legenda e diálogo por município, com dados do bucket deste projeto.

### 1.1 Sistema visual compartilhado

| Elemento | Aparência atual | Função |
| --- | --- | --- |
| Fundo da página | Imagem `assets/background.png`, cobrindo a área de conteúdo, centralizada e fixa | Criar profundidade sem disputar atenção com os dados |
| Hero | Retângulo amplo com imagem escurecida, gradiente azul quase preto, borda clara fina e sombra profunda; cantos retos | Abrir a narrativa e identificar o candidato |
| Faixa principal de seção | Card de cantos arredondados, gradiente azul, brilho radial discreto e barra vertical branca/azul à esquerda | Separar os grandes capítulos da análise |
| Cabeçalho interno | Card azul mais leve, com título e subtítulo em duas linhas de hierarquia | Introduzir uma visualização dentro da seção |
| Cards de conteúdo | Azul profundo translúcido, borda azul clara fina, sombra e leve blur | Agrupar informação sem esconder o fundo |
| Gráficos Plotly | Fundo transparente, textos claros e grades discretas | Integrar gráfico e card |
| Mapas | Coropléticos Plotly nas duas páginas, sem mapa-base de ruas | Mostrar votos por intensidade, força política por classe, malhas neutras ou oportunidades |
| Mensagens de ausência | Aviso ou informação textual dentro do espaço da visualização | Explicar falta de dados sem simular um resultado |

A base cromática é `#eaf2ff` para texto, `#f8fbff` para títulos e números, `#b7c7e6` para descrição e legendas. Os cards usam gradientes próximos de `rgba(11,31,77,.76)` e `rgba(7,24,54,.68)`, com bordas azuis próximas de `rgba(59,130,246,.24)`. Azul claro (`#60a5fa`), azul médio (`#2563eb`) e azul profundo (`#0b1f4d`) expressam intensidade ou seleção; verde, vermelho, amarelo, laranja e cinza têm significado específico nos mapas categóricos.

Os preenchimentos dos mapas são opacos e aparecem sobre fundo transparente, sem nomes de ruas sob os polígonos. Os tooltips usam fundo escuro e texto claro. Os 853 municípios de Minas Gerais compõem os mapas estaduais; os polígonos municipais são simplificados com tolerância pequena para preservar a leitura dos limites. O mapa detalhado de votação usa bairros oficiais quando a malha cobre pelo menos 95% do município; caso contrário, usa áreas ponderadas quando existem duas ou mais unidades. A malha completa de setores censitários fica restrita aos municípios que possuem uma única área ponderada.

### 1.2 Hierarquia de texto e formatação

O hero usa título grande e pesado, subtítulo menor e nome/cargo/partido em maiúsculas. Quando exibido, o total de votos segue a mesma tipografia dessas linhas de identificação. Os títulos principais de seção são largos, brancos e densos; subtítulos ficam em azul claro. Labels dos KPIs gerais são compactos; no card do eleitor ideal, os títulos das dimensões têm fonte ampliada. Cards e legendas não devem exigir que a cor sozinha explique um resultado: os textos e tooltips dão o nome da categoria, a unidade e o recorte. Números de votos usam separador de milhar; percentuais e valores monetários aparecem com unidade explícita. Onde os dados são estimados ou rateados, a interface informa isso junto à visualização.

### 1.3 Capa comum às duas páginas

O hero distribui o conteúdo em duas faixas: à esquerda ficam o título da página, um subtítulo curto e uma linha com foto e dados do candidato; à direita fica a navegação vertical. A foto é vertical, com cantos levemente arredondados, borda clara e sombra; quando não há imagem remota, o espaço permanece como um bloco neutro. Os dados aparecem como `NOME:`, `CARGO:` e `PARTIDO:` em caixa alta. O partido é lido do campo `sg_partido` da base territorial do candidato. `TOTAL DE VOTOS:` aparece logo abaixo do partido nas duas páginas, com a mesma tipografia das demais linhas, sem card próprio; o valor é calculado a partir do parquet territorial selecionado. O ano integra o título do Raio X.

À direita do hero há dois botões empilhados diretamente sobre a capa, sem painel interno: **Raio X Eleitoral** e **DNA do Eleitor**. O conjunto fica centralizado verticalmente na coluna do cabeçalho. Cada botão ocupa toda a largura da coluna, com altura mínima de 5 rem, fonte responsiva de 1,05 a 1,3 rem, borda azul clara, cantos de 14 px, texto branco em negrito, gradiente e sombra. A página ativa recebe azul mais intenso; a outra mantém fundo azul escuro. Ao passar o mouse, o botão fica mais claro e sobe discretamente; o foco por teclado recebe contorno visível. A navegação permanece dentro do app; a pasta selecionada na barra lateral é preservada na sessão.

| Página | Título do hero | Subtítulo |
| --- | --- | --- |
| Raio X | `RAIO X da votação 2026` (ano numérico mais recente disponível quando não há 2026) | `Análises descritivas geográficas e do perfil do eleitor na última eleição.` |
| DNA | `DNA do Eleitor` | `Quem é, onde está e como se comporta o eleitor determinante da candidatura.` |

## 2. Página 1 — Raio X Eleitoral

Para **vereadores**, a ordem é: **Mapa de Força Eleitoral → Como foi sua votação em Belo Horizonte → Votação por Bairros dentro dos municípios → Força da política local → Concentração territorial dos votos → Eficiência Financeira & Custo do Voto**. Para **deputados estaduais**, a ordem é: **Mapa de Força Eleitoral → Votação por Bairros dentro dos municípios → Força da política local → Concentração territorial dos votos → Mapa da atuação parlamentar de acordo com os votos → Eficiência Financeira & Custo do Voto**. A seção financeira contém o cabeçalho principal e o cabeçalho interno de Balanço Macro & Liquidez de Caixa, ainda sem indicadores ou gráficos. A seção de emendas é exclusiva dos deputados.

### 2.1 Mapa de Força Eleitoral

**Pergunta visual:** onde estão os votos e quais localidades lideram?

A faixa **Mapa de Força Eleitoral** apresenta o subtítulo `Onde estão concentrados seus votos e a força da sua votação.`. Logo abaixo, antes do mapa e dos cards laterais, o card horizontal de **Principal reduto eleitoral** destaca a mesorregião mais votada e seu volume. Uma badge verde **Maior base eleitoral** aparece no canto superior direito, e o rodapé informa `{votos} votos recebidos` com maior peso visual. O total de votos do candidato fica no hero, abaixo do partido e no mesmo padrão tipográfico das demais linhas de identificação.

O seletor **Mesorregião / Município** fica sozinho no canto superior direito, dentro do card do mapa. Ele altera o agrupamento do mapa estadual.

O card do mapa ocupa **70% da largura** disponível e tem cerca de 560 px de altura. Os 30% restantes contêm quatro cards empilhados: **Município principal (Top 1)** (nome, participação no total e votos da cidade líder, com alerta acima de 30%), **Dependência do reduto principal** (parcela dos votos no município líder, com alerta acima de 30%), **Penetração territorial** (municípios com votos sobre os municípios do estado) e **Densidade média por município** (votos divididos apenas pelos municípios com voto). No modo municipal, cada município de Minas Gerais é um polígono Plotly; o hover informa nome e votos. A intensidade progride do azul muito claro ao azul profundo, com transformação logarítmica dos votos. No modo mesorregional, cada mesorregião é um único polígono da malha oficial, colorido pelo total de seus votos; o hover informa nome e votos da mesorregião. Áreas sem votos continuam desenhadas na cor mínima. As linhas visíveis correspondem à malha selecionada.

O gráfico de barras aparece em uma janela de detalhamento após o clique no mapa. No modo mesorregional, mostra todos os municípios da mesorregião selecionada. No modo municipal, mostra todos os bairros com registros de votos do município selecionado. A altura cresce generosamente conforme a quantidade de linhas, permitindo rolar a janela até o último território sem comprimir as barras. As barras são espessas; os nomes dos municípios ou bairros e os textos de votos e participação usam tipografia ampliada. O comprimento expressa votos e a cor também varia em azul. O hover repete território, votos e percentual.

Se a malha ou os votos não puderem ser carregados, o mapa cede lugar a uma mensagem de indisponibilidade. O detalhamento também informa quando faltam dados. A interface não preenche municípios ou bairros com valores fictícios.

### 2.2 Como foi sua votação em Belo Horizonte

**Exclusiva de vereadores.** Para deputados estaduais, toda a seção é omitida, sem reservar espaço vazio.

A seção começa com a mesma faixa principal usada em **Mapa de Força Eleitoral**: título **Como foi sua votação em Belo Horizonte** e subtítulo `Veja o histórico dos seus votos na sua Base Eleitoral`. Abaixo, usa duas colunas na proporção aproximada de 70/30: o mapa de bairros de Belo Horizonte (código IBGE `3106200`) fica à esquerda e cinco cards de indicadores ficam à direita. No topo do card do mapa, um filtro horizontal alterna **2020**, **2024**, **2026** e **Projeção 2028**, com 2026 selecionado inicialmente. A opção 2026 mantém o mapa de votos atual. As opções 2020 e 2024 leem `bh_2026/territorio/stage01b_bairros.parquet` do candidato selecionado e comparam a participação daquela eleição com 2026. **Projeção 2028** lê `bh_2026/potencial_demografico/stage08c_potencial_demografico_icp_bairro.parquet` e colore **Base Crítica (Fortaleza)** em azul, **Vulnerável/Ameaçado** em amarelo e **Oportunidade BH** em verde; as demais categorias ficam em tom neutro. Nesse filtro, os cinco cards laterais continuam mostrando os indicadores de 2026. Para 2020 e 2024, os cards acompanham o ano selecionado.

Os cinco cards mostram, nesta ordem, **Votos em Belo Horizonte (ano selecionado)**, **Bairro principal (Top 1)**, **Dependência do bairro principal**, **Penetração por bairros** e **Densidade média por bairro**. O primeiro card destaca a parcela da votação total do candidato que veio de BH; logo abaixo, uma badge verde mostra **Total municipal** e a quantidade de votos da cidade. Em 2020 e 2024, a parcela é 100%; em 2026, compara os votos de BH com o total do candidato nos municípios do estado. Concentração, penetração e densidade usam os votos por bairro do ano escolhido. A penetração mostra a quantidade de bairros com voto e sua proporção entre os bairros oficiais da malha usada pelo mapa. A badge classifica essa cobertura como **Concentração baixa** (abaixo de 1/3, vermelha), **Concentração moderada** (de 1/3 a 2/3, amarela) ou **Concentração alta** (acima de 2/3, verde). O índice só é calculado quando o mapa usa a malha oficial de bairros. O último card destaca a média de votos por bairro, com o texto **Por Bairro** abaixo do valor. Sua badge usa a média arredondada: **Concentração baixa** (menos de 100 votos, vermelha), **Concentração moderada** (100 a 300 votos, amarela) ou **Concentração alta** (mais de 300 votos, verde).

Para 2026, a geometria usa bairros oficiais quando seus polígonos cobrem pelo menos 95% do município. Se a cobertura for menor, usa áreas ponderadas quando existem duas ou mais unidades. Somente municípios com uma única área ponderada recorrem a todos os setores censitários, inclusive aqueles sem votos. Divisões internas claras distinguem as unidades e um contorno branco mais espesso preserva a silhueta municipal. Com menos de mil votos, os polígonos com votos recebem o mesmo azul médio. A partir de mil votos, a cor usa os cinco tons de azul do mapa estadual: escala linear até 5 mil votos e transformação logarítmica quando o total municipal ultrapassa esse valor. Nas malhas de bairros e áreas ponderadas, a intensidade também considera a proporção de polígonos com votos; no fallback por setores censitários, a escala ocupa toda a faixa de cores. No mapa “Como foi sua votação em Belo Horizonte”, bairros sem votos aparecem em cinza e ficam fora da escala; na escala logarítmica, gamma 0,8 suaviza a compressão para tornar diferenças entre votos baixos e médios mais visíveis.

Para 2020 e 2024, a legenda do card mostra **verde** para aumento, **azul** para estabilidade e **vermelho** para queda na participação do candidato até 2026; **cinza** identifica bairros sem comparação disponível. O hover informa os votos da eleição escolhida, os votos de 2026 e a diferença de participação em pontos percentuais. O cálculo agrega as linhas de locais correspondidos por bairro antes de comparar as participações. Os códigos das unidades geométricas não aparecem na visualização.

No filtro **Projeção 2028**, as quatro pílulas mantêm os rótulos **Base Crítica (Fortaleza)**, **Vulnerável**, **Oportunidade** e **Demais bairros**, sem o parágrafo de critérios abaixo da legenda. Base forte sem defasagem média fica azul; base forte com espaço fica amarela; menor votação com espaço fica verde; demais situações e comparação incompleta ficam cinza. O hover mostra votos de referência e diferença média em pontos percentuais. A nota abaixo do mapa esclarece que as dimensões são independentes e que a classificação não mede perda histórica nem prevê votos em 2028.

### 2.3 Votação por Bairros dentro dos municípios

**Compartilhada entre vereadores e deputados**, copiada da mesma seção de `deputados_streamlit`. Para vereadores aparece logo após **Como foi sua votação em Belo Horizonte**; para deputados, logo após **Mapa de Força Eleitoral**. Nos dois casos antecede **Força da política local**.

A faixa principal segue o mesmo padrão de Mapa de Força Eleitoral, com gradiente azul, barra vertical à esquerda, cantos arredondados e tipografia ampliada, e mantém o título **Votação por Bairros dentro dos municípios** e o subtítulo `Votos por bairro no município selecionado.`. O card do mapa fica à esquerda (70%), com os filtros **Mesorregião → Município** e mapa Plotly de **560 px**. A seleção inicial destaca o município mais votado do candidato e sua mesorregião. Os controles têm chaves próprias por candidato; o controle municipal também é separado por mesorregião.

À direita (30%), cinco cards empilhados mostram **Total de votos no Município** com a participação percentual e badge verde do total municipal, **Bairro principal (Top 1)**, **Dependência do bairro principal**, **Penetração por bairros** e **Densidade média por bairro**. O visual, as badges e os critérios seguem a seção original. Penetração informa a quantidade de bairros com voto; não calcula uma proporção sem conhecer o total de bairros.

Nesta seção, somente Belo Horizonte usa malha de bairros. Nos demais municípios, as votações usam áreas ponderadas somente quando existem 8 ou mais unidades; abaixo desse corte, usam-se setores censitários com identificação pelo bairro TSE de maior votação. Essa regra também vale para os históricos de 2018 e 2022 dos deputados. A Projeção 2030 mantém bairros apenas em BH e setores nos demais municípios. A intensidade usa escala linear até 1.000 votos municipais e logarítmica acima de 1.000, sem azul uniforme nem ajuste pela quantidade ou proporção de polígonos com votos. O tooltip e a nota inferior mantêm a identificação territorial e a explicação da escala. Falta de dados, malha ou opções de município apresenta a mensagem específica da seção original.

**Somente para BH neste bloco**, todos os bairros são desenhados a partir de `IBGE/MG/dadosterritorio/MG_bairros_CD2022.parquet`, com vínculo exato por código IBGE de bairro ao stage 01b do candidato. Não há fallback para outras malhas ou associação por coordenadas. O hover usa nomes e votos do candidato, sem nomes vindos da malha; bairros sem registro mostram informação indisponível em cinza. Os cards de BH agrupam pelo `cd_bairro` do TSE, e o hover detalha os votos desses bairros eleitorais mesmo quando compartilham um polígono IBGE. A nota explica a origem da geometria e dos valores e informa registros sem correspondência. Essa exceção não altera o histórico de Belo Horizonte nem os demais municípios.

Somente para **deputados**, o topo do card inclui **Eleição exibida no mapa**, com botões **2018**, **2022**, **2026** e **Projeção 2030**, no mesmo padrão do histórico de BH; 2026 é o padrão. A troca preserva os filtros territoriais. Em 2018/2022, os cards acompanham os votos conhecidos do ano e o mapa mostra aumento (verde), estabilidade (azul), queda (vermelho) ou ausência de comparação (cinza) em relação a 2026. O hover detalha os bairros TSE, os votos dos dois anos e a diferença média ponderada de participação. Anos sem valores no candidato/município apresentam indisponibilidade, sem tratar ausência como zero. Cobertura histórica parcial recebe nota.

Em **Projeção 2030**, a legenda usa **Proteger a base** (azul), **Oportunidade alta** (verde), **Potencial a desenvolver** (amarelo) e **Sem potencial ou dados incompletos** (cinza), com diagnóstico stage09b do eleitor ideal e os mesmos critérios do DNA. BH preserva bairros oficiais vinculados pelo código IBGE e nomes/votos TSE do candidato; os outros municípios mostram setores censitários. As estimativas demográficas são identificadas como diagnóstico. Os cinco cards continuam em 2026. A nota explica a cobertura e que potencial não prevê votos. Para vereadores, este seletor não aparece e a seção permanece em sua votação atual.

### 2.4 Força da política local


A faixa principal usa o título `Força da política local` e o subtítulo `Veja se vereadores e prefeitos das cidades foram decisivos na sua votação`. A estrutura repete a proporção 70/30 do Mapa de Força Eleitoral.

À esquerda há um card com o filtro territorial fixado em **Município** e a malha completa de Minas Gerais, com divisões municipais brancas e contorno estadual mais espesso. O card tem altura alinhada ao fim dos quatro cards laterais, para que o contorno do mapa termine no mesmo eixo visual do último card. Antes do mapa, uma explicação centralizada e em negrito informa que a seção avalia a eficácia de prefeitos e vereadores aliados na transferência de votos e considera votação alta quando o percentual do candidato na cidade supera sua média no estado. Abaixo, quatro pílulas coloridas mantêm o fundo da classe e informam, com texto centralizado: prefeito/vereadores entregaram votos, prefeito/vereadores não entregaram votos, votação própria sem prefeito/vereadores e ausência de prefeito/vereadores e votos, sem repetir o nome da cor no texto. O mapa cruza `capital_local_0a100` com o market share municipal. Nota alta significa resultado acima de 50/100; market share alto significa resultado municipal igual ou superior à participação estadual do candidato. O hover mostra município, classe, leitura, nota, market share local e referência estadual.

À direita, quatro cards empilhados também funcionam como legenda e filtro. **🤝 Alianças de alto retorno** usa verde; **⚠️ Acordos sem entrega**, vermelho; **⭐ Votação própria**, azul; e **❄️ Zonas neutras**, cinza. Cada card recebe no fundo um gradiente translúcido da própria cor, mais luminoso no canto superior esquerdo e integrado ao azul profundo da interface; o estado selecionado intensifica esse banho de cor e ganha contorno reforçado. O ícone e o título aparecem em uma badge no topo. Abaixo, a quantidade de cidades e a participação na votação recebem peso e tamanho maiores, seguidas pela **Cidade-chave** com seus votos. A estratégia encerra o card dentro de uma pílula tonalizada pela cor da classe. Ao clicar, apenas a classe escolhida mantém sua cor no mapa e as demais ficam atenuadas; clicar novamente limpa o destaque.

Um clique em qualquer município abre a janela **Força política local**, com o nome municipal como título interno. No topo aparecem a classificação e quatro números: votos, market share local, referência estadual e capital político local. Uma frase traduz a cor em leitura estratégica. Abaixo, o layout divide-se em duas colunas: à esquerda, o polígono isolado do município conserva a cor recebida e é seguido pelos detalhes da prefeitura, Câmara, partidos aliados e base dos dados; à direita, uma lista rolável apresenta prefeito e vereadores, com nome, partido, vínculo e afinidade.

### 2.5 Concentração territorial dos votos

**Pergunta visual:** a candidatura depende de poucos redutos ou distribui votos por muitos municípios?

Uma faixa principal apresenta o título e a frase `Quanto da votação total está concentrada nos municípios onde o candidato mais recebeu votos.`. O conteúdo está em um único card. Na parte superior há **quatro cards**: Top 1, Top 5, Top 15 e Top 20. Cada card mostra o rótulo Top em caixa alta, com fonte ampliada de 1,15 rem e texto branco dentro de uma badge verde (#15803d), com borda sutil e cantos arredondados, seguido pelo total de votos acumulados em fonte grande e negrito, com `votos` como legenda discreta. Nomes de municípios e contagem de municípios não aparecem no cabeçalho dos cards. A rosca Plotly mostra o percentual acumulado em relação a 100% dos votos em formato de gauge circular: trilho escuro e arco ativo têm a mesma espessura, as pontas do progresso são arredondadas e o tom do azul evolui sutilmente de Top 1 a Top 20, chegando a `#60a5fa`. O texto de instrução de clique não aparece abaixo delas.

Um clique na rosca abre uma janela com a composição incremental até aquele Top: Top 1, municípios 2 a 5, 6 a 15 e 16 a 20, conforme o card selecionado. Cada etapa mostra sua contribuição percentual e votos absolutos, seguida do total acumulado.

Antes da curva, uma frase automática nomeia o líder e destaca o peso dos 15 municípios principais. Os expansores `Ver municípios do Top 5`, `Top 15` e `Top 20` aparecem em seguida, ainda antes da curva. As listas preenchem cada coluna de cima para baixo e continuam na coluna seguinte à direita, com três colunas em telas largas, duas até 900 px e uma até 600 px. Em seguida, uma curva Plotly mostra a participação acumulada em função da posição do município até **100% da votação**. O eixo horizontal usa escala logarítmica para separar melhor os primeiros marcos de concentração. A linha azul, a área translúcida, os marcadores e as referências percentuais permitem ver a velocidade da concentração. Os marcadores da curva são **Top 1**, **Top 5**, **Top 15**, **Top 20** e **Todos**; eles servem como leitura visual e não abrem janela ao clique. Sem linhas municipais válidas, o card exibe aviso e não fabrica uma curva.

### 2.6 Mapa da atuação parlamentar de acordo com os votos

**Exclusiva de deputados estaduais**, copiada de `deputados_streamlit`, depois da concentração e antes da seção financeira. A faixa principal usa o título **Mapa da atuação parlamentar de acordo com os votos** e o subtítulo `Índice de Retorno Parlamentar: valor total de emendas no município dividido pelos votos recebidos.`.

A coluna esquerda ocupa 70% e apresenta três KPIs — **Taxa de Reciprocidade**, **Maior Beneficiado (R$)** e **Média R$/Voto** — acima do card com mapa municipal Plotly de **720 px**. A coluna direita ocupa 30% e mostra seis cards empilhados, com gradientes, bordas coloridas, título em badge, quantidade de cidades, participação na votação e descrição: **BASE PRIORIZADA** (azul `#2563EB`), **APOSTA POLÍTICA** (verde `#16A34A`), **BASE EM RISCO** (amarelo `#FACC15`), **PRESENÇA PONTUAL** (laranja `#F97316`), **VOTAÇÃO ORGÂNICA** (cinza `#64748B`) e **TERRITÓRIO NEUTRO** (branco `#FFFFFF`). Os cards são legenda, sem filtro por clique.

O hover informa município, classe, votos e valor de emendas. Clicar no município abre **Emendas destinadas ao município**, com nome, votos, classe, total e tabela por finalidade e tipo de indicação, mostrando quantidade de indicações e valor indicado. A nota preservada esclarece que pagamento e indicação podem diferir. Fechar a janela mantém a seleção do candidato.

Sem dados, permanecem as mensagens e os KPIs de ausência da seção original. As classificações fornecidas pelo parquet têm prioridade; quando faltam, municípios com emendas usam a classe original Sem Expressão. Os critérios e a adaptação dos códigos territoriais estão documentados no README.

### 2.7 EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO

Na subseção 1, o arranjo atual segue a mesma composição da subseção 2: uma coluna de 50% à esquerda com o card da rosca; à direita, os outros 50% contêm dois cards empilhados, DRE Simplificada da Campanha e Comprometimento Orçamentário. O gauge permanece centralizado dentro de seu próprio card, logo abaixo do funil. Este arranjo substitui a linha independente anterior do gauge. Em telas estreitas, as colunas seguem o empilhamento do Streamlit.

Os 50% à direita do Top 10 recebem dois cards empilhados. **Índice de Concentração da Receita** apresenta rosca de 340 px com abertura 60%, percentual do Top 10 centralizado, legenda inferior e cores azul (Top 10), ciano (demais identificados) e cinza (sem atribuição, quando conhecida). **Ranking Completo** traz um expander inicialmente fechado com tabela de auditoria somente para leitura: posição, doador, CPF/CNPJ, valor atribuído, percentual da receita com barra de progresso e receitas vinculadas. Documentos preservam zeros iniciais e valores usam reais. Os cards mantêm fundo, borda e tipografia do dashboard; ausência de dados oculta o card correspondente.

O primeiro gráfico da Estrutura da Receita é **Top 10 Doadores**, abaixo dos KPIs, na metade esquerda de uma linha 50%/50%. Seu card mantém borda e fundo padrão. Barras horizontais azuis mostram valores em reais nas pontas; os maiores doadores aparecem no topo, seguindo o ranking. Nomes completos quebram em linhas no eixo, sem reticências; a altura acompanha os rótulos e o tooltip preserva nome e valor. Fundo transparente, textos claros e grade discreta integram o Plotly ao dashboard. Registros ausentes ficam ocultos.

Na Estrutura da Receita, cards de KPIs sem dados são ocultos, e os disponíveis dividem a largura da linha. Sem dados para nenhum KPI, a linha não aparece. O ranking exibido é o de doadores imediatos, separado dos originários; esta regra substitui a exibição anterior de Indisponível nesses cards.

Sob o subtítulo de **ESTRUTURA DA RECEITA**, quatro cards de KPIs apresentam **Maior Doador (Top 1)**, **Concentração no Top 10**, **Cobertura da Atribuição** e **Total de Doadores Unificados**. Usam títulos em badges verdes, valores brancos destacados e descrições em azul claro, com fundo azul em gradiente, borda fina, sombra e cantos de 14 px. O Top 1 mostra valor em reais e nome completo do doador, com quebra de linha. Os dois percentuais têm uma casa decimal e a contagem usa separador de milhar. Quatro colunas passam para duas abaixo de 1100 px e uma abaixo de 600 px. Dados insuficientes mostram Indisponível. Esta implementação substitui a indicação anterior de subseção sem conteúdo analítico.

A subseção 2, **ESTRUTURA DA RECEITA**, começa após o gauge de comprometimento, com subtítulo **Origem e concentração dos recursos da campanha**. Seu card usa `_section_header()`, com o mesmo fundo azul translúcido, borda fina, cantos arredondados e hierarquia dos cabeçalhos internos. Nesta etapa exibe título e subtítulo, sem conteúdo analítico. É comum aos dois cargos.

Logo abaixo da linha de rosca e funil, **Comprometimento Orçamentário** ocupa um card centralizado de meia largura (colunas 1:2:1), com título centralizado e gauge semicircular idêntico ao DNA: `go.Indicator(mode="gauge+number")`, 170 px, arco azul claro de espessura 0,48, trilho translúcido, fundo transparente e número branco de 25 px com uma casa decimal. O cálculo é despesas contratadas / receita total × 100, com valores de referência e fórmula abaixo. Percentuais acima de 100% são preservados e ampliam a escala, com nota explicativa. Receita zero, dados ausentes ou inválidos geram mensagem. O card acompanha o empilhamento responsivo do Streamlit.

Layout atualizado das visualizações: dois cards lado a lado, cada um com 50% da largura disponível. **Composição das Receitas** fica à esquerda com a rosca e, abaixo, duas colunas de legenda. **DRE Simplificada da Campanha** fica à direita com funil Plotly de 400 px, fundo transparente, texto claro e barras azul, ciano, índigo e verde. As etapas são Receita Total → Receita Financeira → Despesa Contratada → Despesa Paga, com valores em reais nas barras e no hover. A nota explica que são totais de cada etapa, sem subtração, e que compromissos podem superar receitas. Dados incompletos, negativos ou todos zerados geram mensagem. Em telas estreitas, o Streamlit empilha as colunas. Esta composição substitui o layout anterior de legenda à esquerda da rosca.

Logo abaixo dos quatro cards fica **Composição das Receitas**, em contêiner nativo com borda, seguindo o fundo azul e a tipografia do Raio X. À esquerda (40%), a legenda mostra títulos, valores em reais e percentuais com marcas azuis; à direita (60%), a rosca Plotly de 400 px usa abertura de 60%, fundo transparente, azul #2563eb para Entrada Financeira (Dinheiro) e ciano #38bdf8 para Bens e Serviços (Estimável). O total das duas receitas aparece no centro. Fatias de pelo menos 1% mostram o percentual externo; todas têm valor e percentual no hover e na legenda. A nota esclarece que receita estimável não é dinheiro em caixa. Ausências, valores negativos e soma zero mostram mensagem, sem fabricar proporções. As colunas seguem o empilhamento do Streamlit em telas estreitas.

Atualização dos indicadores: os três primeiros cards agora usam `gastos/stage05a_resumo_financeiro.parquet` da base anual selecionada. Arrecadação apresenta Dinheiro / Espécie e Bens e Serviços Doados; Compromissos apresenta Despesas Contratadas e Despesas Pagas; Liquidez apresenta Saldo Líquido / Resultado e Saldo a Pagar. Cada indicador ocupa um bloco com título, valor em reais destacado e descrição; uma linha discreta separa os blocos. Resultado = receita financeira − despesas pagas; saldo a pagar = despesas contratadas − despesas pagas. O resultado recebe badge verde para caixa positivo, vermelha para déficit temporário de liquidez ou neutra para caixa equilibrado. Dados ausentes aparecem como Indisponível. Somente o quarto card permanece vazio. Esta atualização substitui as referências abaixo aos interiores vazios e à ausência de indicadores.

Após o subtítulo de **BALANÇO MACRO & LIQUIDEZ DE CAIXA**, aparecem quatro cards expansíveis compartilhados entre vereadores e deputados: **Arrecadação (Receitas)**, **Compromissos (Despesas)**, **Liquidez & Saúde do Caixa** e **Volume de Lançamentos**. São quatro colunas de mesma largura em telas largas, duas abaixo de 1100 px e uma abaixo de 600 px. Cada card mantém fundo azul em gradiente, borda clara e cantos arredondados; o título usa badge verde (#15803d), texto branco em negrito e fonte de 1,1 a 1,5 rem. Uma seta gira quando o card se expande. Clique ou teclado abre e recolhe cada card independentemente. Todos começam fechados; o interior permanece vazio nesta etapa, aguardando os indicadores do stage 05a de `2026/gastos`. As referências abaixo à ausência de conteúdo analítico continuam válidas; os cards já estão implementados.

A seção abre com o card de cabeçalho com o título **EFICIÊNCIA FINANCEIRA & CUSTO DO VOTO** e o subtítulo `Análise do retorno do investimento eleitoral: veja onde o orçamento foi alocado e quanto custou a conquista de cada voto.`, no mesmo padrão visual das faixas principais.

Logo abaixo, um card de subseção apresenta **BALANÇO MACRO & LIQUIDEZ DE CAIXA** e o subtítulo `Raio-x executivo da arrecadação e dos compromissos financeiros: monitore o saldo real de caixa, o volume contratado e a saúde orçamentária da campanha.`. Ele reutiliza o cabeçalho interno (`mapa-section-card`), com fundo azul translúcido mais suave, borda fina de 1 px, cantos arredondados e tipografia menor que a faixa principal. Não há indicadores, gráficos, filtros, notas ou mensagens de ausência abaixo dele.

## 3. Página 2 — DNA Eleitoral

Para **vereadores**, o DNA segue: **Identidade da Base Eleitoral → Eleitor de BH x Eleitor do Interior → Distribuição do Perfil do Eleitorado → BASE ELEITORAL DO CANDIDATO → Expansão & Oportunidades para 2030 → Potencial demográfico municipal**. Para **deputados estaduais**, a comparação BH/interior é omitida, mantendo as outras cinco seções na mesma ordem. Sunburst, heatmap e composição demográfica por pontos não integram a interface atual.

### 3.1 Identidade da Base Eleitoral

**Pergunta visual:** quem é o eleitor predominante do candidato?

A faixa principal usa o subtítulo `Quem é o eleitor-chave e quais atributos definem o perfil do seu eleitor.`. Ela é seguida pelo card de eleitor ideal, ocupando a largura do conteúdo.

#### 3.1.1 Eleitor ideal do candidato

O card principal é um `st.container(border=True)` com borda, fundo em gradiente azul e sombra. O título `Eleitor ideal do candidato` fica centralizado, com tipografia ampliada, forte e responsiva. Os badges coloridos dos atributos aparecem centralizados logo abaixo, com fonte ampliada e responsiva (1,15 a 1,35 rem), altura mínima de 3,2 rem, espaçamento interno generoso, bordas suaves e sombra discreta. Não há subtítulo, linha divisória nem rótulo PERFIL PREDOMINANTE. Quando o resumo agrega informação, aparece abaixo com emoji de fala; se apenas repete a persona, é ocultado. **A confiança do modelo não aparece no card.**

Na base do card, **quatro sub-cards com borda**, em `st.columns`, apresentam Gênero, Faixa etária, Escolaridade e Estado civil. Cada sub-card também usa `st.container(border=True)`. Títulos e categorias dominantes ficam centralizados. Cada percentual válido aparece em um gauge semicircular de 0 a 100, feito com `go.Indicator(mode="gauge+number")` dentro de `st.plotly_chart`; a cor do arco acompanha a dimensão. Os percentuais das quatro dimensões são independentes; não formam fatias de uma soma de 100%. Se o percentual não é válido ou não existe, o card não inventa o número. Os estilos desses badges e sub-cards são locais à página DNA; o hero e a navegação seguem o CSS compartilhado.

#### 3.1.2 Eleitor de BH x Eleitor do Interior

**Exclusiva de vereadores.** Para deputados estaduais, o fluxo segue do eleitor ideal diretamente para a distribuição demográfica.

Em cada card, as categorias predominantes aparecem logo abaixo do título e antes do gráfico, em badges centralizados com rótulo da dimensão em negrito. As badges usam fonte compacta, quebra de linha e fundo/borda tonalizados pela mesma cor da barra correspondente: verde para gênero, azul para idade, roxo para escolaridade e amarelo para estado civil. Os valores continuam dinâmicos conforme o candidato e o recorte.

Os cards não exibem rodapés de metodologia ou fonte. Os critérios de cálculo permanecem documentados no README; avisos de indisponibilidade continuam visíveis quando necessários.

Logo após o card do eleitor ideal e antes de Distribuição do Perfil do Eleitorado, uma nova faixa usa o mesmo padrão visual das faixas principais: título **Eleitor de BH x Eleitor do Interior** e subtítulo `Será que você tem o mesmo perfil de eleitor na capital e no interior?`.

Abaixo, dois cards dividem igualmente a largura, com o mesmo gradiente e borda do eleitor ideal e títulos centralizados: **Eleitor da capital** à esquerda e **Eleitor do Interior** à direita. Cada gráfico apresenta barras horizontais de 0 a 100% para gênero, idade, escolaridade e estado civil, com cores por dimensão, percentuais e categorias predominantes. A capital consolida bairros com ICP calculado e votos; o interior exclui BH e usa perfis locais ou distribuições stage 02, conforme a fonte disponível. A categoria predominante reúne o maior peso em votos dos territórios onde lidera; a barra mostra a média de seu percentual nesses territórios, ponderada pelos votos. Os cards não exibem nota metodológica. O interior usa distribuições stage 02 quando o perfil geral replica a persona estadual; o cálculo e suas limitações estão descritos no README. Dimensões são independentes; ausência de fonte ou percentual gera mensagem. Em telas estreitas os cards seguem o empilhamento do Streamlit.

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

**Pergunta visual:** onde proteger a base existente e onde há oportunidade demográfica relativa ao ICP escolhido?

O diagnóstico municipal stage 09b tem prioridade. Quando essa fonte não é lida, o componente usa o cálculo legado stage 08c com Censo, mantendo o mapa agregado por município.

A faixa principal apresenta `Mapeamento municipal de oportunidades demográficas e da base eleitoral para orientar a expansão territorial.`. **A implementação exibida logo abaixo é municipal**: não há mapa de bairros nem de áreas ponderadas nesta seção. Um seletor à direita alterna **ELEITOR IDEAL** e classificações estratégicas.

O conteúdo usa **mapa em card à esquerda (70%) e quatro cards de legenda empilhados à direita (30%)**, no padrão do Mapa de Força Eleitoral do Raio X. O seletor de ICP fica no canto superior direito, dentro do card do mapa. Os cards laterais têm borda tonalizada, sombra, gradiente com iluminação na cor da classe, badge de cor e títulos destacados: **Oportunidade de expansão** (verde), **Proteger a base** (azul), **Potencial a desenvolver** (amarelo) e **Baixa similaridade** (cinza). Cada um mantém a explicação da legenda original. A legenda torna o mapa categórico; cores não representam uma sequência contínua.

O mapa municipal é um **coroplético Plotly** com cerca de **560 px** de altura, dentro do card azul com borda e cantos arredondados. Cada município recebe uma das quatro classes; a barra categórica do Plotly fica oculta porque os cards laterais apresentam a legenda. No diagnóstico stage 09b, o hover informa município, leitura da classe, votos nos setores associados, população estimada do ICP e sua parcela na população de referência. No fallback stage 08c, informa votos, oportunidade e similaridade. A nota inferior explica a cobertura dos setores associados, os cortes relativos, os votos probabilísticos dos clusters e que potencial **não é previsão de votos**. No stage 09b, azul identifica o quartil superior de votos; verde exige população estimada no quartil superior e parcela na referência igual ou superior à mediana; amarelo identifica população estimada positiva fora desses critérios. Azul tem prioridade. A legenda cinza passa a **Sem potencial ou dados incompletos**. No fallback stage 08c, permanecem as explicações de oportunidade e similaridade. Se não houver dados completos de Censo/potencial ou a malha municipal falhar, o card mostra uma informação textual no lugar do mapa, mantendo as explicações laterais. Em telas estreitas as colunas seguem o empilhamento do Streamlit.

### 3.5 Potencial demográfico municipal

Uma faixa principal no mesmo padrão de Identidade da Base Eleitoral e Distribuição do Perfil do Eleitorado abre o bloco, com título **Potencial demográfico municipal** e subtítulo `Explore as oportunidades demográficas e a aderência ao perfil do eleitor em cada município.`.

O bloco usa os diagnósticos **stage 09b por setor**, com filtros **Mesorregião → Município → Perfil para expansão**, independentes da expansão estadual. Não há seletor de unidade intramunicipal nem fallback para áreas ponderadas.

O mapa ocupa 70% da largura e tem **640 px** de altura; quatro cards empilhados ocupam os 30% restantes. Em **Belo Horizonte**, a malha é de bairros oficiais IBGE, com diagnósticos setoriais agregados por código exato de bairro e cortes relativos recalculados entre bairros. Nos demais municípios, todos os setores censitários da malha municipal são desenhados; os nomes de bairros identificam as unidades no hover, sem mudar sua geometria setorial.

Os cards apresentam **Oportunidade alta** (verde), **Proteger a base** (azul), **Potencial a desenvolver** (amarelo) e **Sem potencial ou dados incompletos** (cinza). Os títulos ficam em badges arredondados na cor da classe, com texto branco em negrito e quebra de linha. Abaixo, a contagem usa o rótulo **Bairros** em BH e **Áreas** nos demais municípios, seguida da explicação. Fundo azul em gradiente, borda clara, raio de 16 px, padding de 20 px e sombra integram mapa e cards. Os cards acompanham o conteúdo; não há regra específica que force sua altura a preencher a coluna do mapa.

O tooltip mostra **Bairro: nome**, classe, votos associados, população estimada do ICP e parcela do ICP na população de referência. Não mostra código de setor ou bairro. Sem vínculo de bairro, usa **Bairro: Sem bairro vinculado**. Valores ausentes aparecem como **Indisponível**, e polígonos sem diagnóstico permanecem cinza.

As classes seguem os critérios relativos stage 09b da expansão estadual; fora de BH, os cortes são calculados antes do filtro municipal. A nota abaixo do mapa explica a agregação de BH, os vínculos exatos, as áreas sem diagnóstico e que votos associados a locais de votação não representam residência dos eleitores. Potencial demográfico não é previsão de votos. Falta de malha, diagnóstico ou vínculos recebe mensagem específica.

## 4. Interação, estados e continuidade visual

### 4.1 Escopo dos controles

| Controle | Onde atua | Persistência observável |
| --- | --- | --- |
| Cargo Atual na barra lateral | Duas páginas e fonte no HF | Alterna Vereadores/Deputados Estaduais, filtra candidatos pelo grupo e reinicia estados ao mudar |
| Candidato na barra lateral | Duas páginas | Exibe somente nomes do cargo ativo e preserva a seleção ao trocar de rota |
| Painel vertical Raio X / DNA | Navegação | Opção ativa destacada no hero |
| Filtro territorial Mesorregião / Município | Mapa estadual do Raio X e conteúdo da janela aberta por clique | Restrito ao primeiro mapa |
| Eleição no mapa de Belo Horizonte | Mapa de bairros do Raio X, somente para vereadores | 2020/2024 mostram comparação com 2026; 2026 mostra votos atuais; Projeção 2028 mostra as categorias estratégicas |
| Eleição na votação por bairros dos deputados | Mapa intramunicipal e cinco cards | 2018/2022 mostram histórico quando disponível; 2026 mostra votação atual; Projeção 2030 usa stage09b e mantém os cards em 2026 |
| Cards de votação em Belo Horizonte | Cinco indicadores calculados para a cidade | Atualizam em 2020/2024; ficam nos dados de 2026 em 2026 e Projeção 2028 |
| Mesorregião / Município da votação por bairros | Mapa intramunicipal e cinco cards laterais do Raio X | Independente do histórico de BH; estado por candidato e mesorregião |
| Filtro Município da força política local | Mapa categórico dos quatro quadrantes em Minas Gerais | Única granularidade disponível nesta etapa |
| Cards da força política local | Destacam ou restauram uma classe do mapa | Card ativo recebe contorno reforçado |
| Clique em município da atuação parlamentar (deputados) | Abre o detalhamento das emendas por finalidade e tipo | Janela modal; preserva candidato |
| Clique em município da força política local | Abre o mapa isolado, os indicadores e a composição política municipal | Janela modal; fecha sem alterar o filtro dos cards |
| Município e dimensão da rosca DNA | Rosca e total do recorte | Restrito à seção de distribuição |
| Mesorregião e município do Potencial demográfico municipal | Bairros oficiais em BH; setores censitários nos demais municípios | Restrito ao bloco municipal |
| Perfil para expansão | Classes e métricas do mapa de Expansão 2030 | Restrito à seção de expansão do DNA |

### 4.2 Estado sem dados

Falta de parquet, malha ou dimensão não deve parecer valor zero. A implementação usa `st.info`, `st.warning`, captions ou cards com texto para explicar o que está ausente. Zero legítimo continua como valor ou cor mínima quando existe malha e a métrica pode ser calculada. Os mapas mantêm municípios ou setores sem votos visíveis onde a fonte geométrica está disponível. As notas analíticas permanecem próximas ao gráfico a que se referem.

### 4.3 Responsividade implementada

No hero, a navegação permanece vertical à direita em telas largas; quando as colunas do Streamlit se reorganizam, o painel passa para baixo do conteúdo mantendo os dois botões empilhados. A foto e os textos também se ajustam por regras CSS próprias. Os KPIs da página 1 passam de linha para uma coluna em telas até cerca de **900 px**. A faixa Top 1/5/15/20 passa para duas colunas; a lista de municípios reduz colunas novamente abaixo de **600 px**. Os quatro sub-cards do eleitor ideal passam para duas colunas abaixo de **900 px** e uma coluna abaixo de **760 px**. No card dos ICPs, o resumo e as barras demográficas empilham abaixo de **600 px**; o cabeçalho de cada perfil pode quebrar em telas estreitas. A legenda de expansão estadual mantém quatro cards em uma coluna; abaixo de **640 px**, reduz padding e remove a altura mínima dos cards.

Os pares de mapa e cards laterais da página 1 e o par rosca/filtros do DNA são montados com `st.columns`; a experiência móvel também depende do empilhamento padrão do Streamlit. Nomes longos de município e persona podem quebrar linha. Tooltips complementam os rótulos que não cabem nos cards.

## 5. Critérios de fidelidade para futuras alterações

1. Preservar a diferença entre **intensidade** (gradiente azul contínuo) e **classe** (cores da força política local e da expansão).
2. Manter a leitura em camadas: hero, faixa principal, cabeçalho interno quando necessário e conteúdo analítico.
3. Manter os cards de potencial municipal vinculados às categorias e ao recorte exibido; na força política local, manter as recomendações vinculadas aos quatro quadrantes.
4. Mostrar voto observado, estimativa demográfica, custo de referência, gasto rateado e potencial em seus papéis corretos, com unidades e notas visíveis.
5. Fazer seleção e estado vazio permanecerem compreensíveis sem depender só de cor.
6. Atualizar este briefing quando mudar texto, card, escala, interação, ordem de seção ou granularidade de mapa.
7. Preservar o filtro de candidatos por cargo e as diferenças entre as seções dos vereadores e dos deputados.
8. Preservar a seção de emendas como exclusiva de deputados e manter seu posicionamento entre concentração territorial e seção financeira.

Nesta seção, áreas ponderadas servem somente ao vínculo geométrico. Toda a informação eleitoral vem de `stage01b_bairros.parquet`, com bairros identificados por `cd_bairro` do TSE. Nas áreas ponderadas, o hover lista cada bairro apenas com nome TSE e votos, sem códigos ou parênteses; a soma dos votos associados ao polígono aparece ao final. O código TSE continua sendo a chave interna de agrupamento. Nos históricos, mostra também as somas de cada ano. Cards agrupam por `cd_bairro` em todos os municípios. Nomes e códigos de área ponderada não aparecem no hover, nos cards ou na legenda. A Projeção 2030 mantém o diagnóstico por setores fora de BH, identificando-os pelo bairro TSE mais votado em 2026.

Nos municípios com menos de 8 áreas ponderadas, `cd_setor_censitario` do stage 01b serve somente para o vínculo exato com `code_tract` da malha. Nenhum nome de setor ou bairro é obtido da referência geográfica e não há associação por coordenadas/proximidade nesse modo. Em divergências, os votos são somados por `cd_bairro` dentro de cada setor e o bairro com mais votos identifica o polígono; empate usa o código TSE em ordem crescente. Nos históricos, a prioridade usa os votos do ano selecionado; na Projeção 2030, usa 2026. O tooltip informa o bairro vencedor e seus votos, enquanto o total do polígono preserva todos os votos associados. Os cards continuam calculados por bairro TSE, sem descartar bairros perdedores na disputa pela identificação do setor.

O primeiro card lateral da votação por bairros segue o padrão do histórico de BH: título Total de votos no Município, percentual dos votos do município na votação do candidato e badge verde Total municipal com os votos absolutos. Numerador e denominador vêm do stage01b do candidato para o ano exibido; Projeção 2030 mantém 2026. Sem denominador válido, o percentual fica indisponível.

Na seção Votação por Bairros dentro dos municípios, o mapa de intensidade usa somente o total de votos municipal para escolher a escala: linear até 1.000 (inclusive) e logarítmica acima de 1.000. Não há cor uniforme para municípios pequenos nem fator de cobertura por quantidade de bairros, áreas ou setores. O máximo de votos associado usa toda a faixa de intensidade. Os históricos comparativos e a Projeção 2030 mantêm suas cores categóricas, pois representam classes e não intensidade.
