# Briefing visual — Visualização Eleitoral

Este documento registra **a interface implementada hoje** nas duas páginas do aplicativo. Ele descreve a aparência, a ordem de leitura, os controles, as respostas às interações e os estados sem dados. O [README](README.md) concentra a arquitetura e as fontes; aqui o foco é o que o usuário vê e entende. Textos que mencionam bairros na seção Expansão 2030 do DNA descrevem rótulos atualmente presentes na interface: o mapa dessa seção é municipal.

## 1. Visão geral da experiência

O produto é um painel de inteligência eleitoral para deputados e vereadores, com duas rotas. **Raio X Eleitoral** mostra os dados do candidato selecionado, sua distribuição territorial, concentração, atuação parlamentar e custo do voto; o ano padrão do projeto é 2026 e, se não estiver disponível para uma pasta, usa o ano numérico mais recente encontrado. **DNA Eleitoral** sintetiza o eleitor predominante, os perfis estratégicos e a distribuição demográfica. **Expansão 2030** mostra oportunidades territoriais. As páginas compartilham candidato selecionado, fundo, hero, tipografia e família de cards.

O percurso é vertical. Uma capa apresenta o candidato; faixas de seção delimitam cada pergunta analítica; os cards abaixo contêm números, mapas ou gráficos. O app usa a barra lateral nativa do Streamlit para escolher uma pasta de candidato na raiz configurada do HF e navegar entre páginas. Um controle segmentado dentro da capa também alterna as duas rotas e indica qual está ativa.

### 1.1 Sistema visual compartilhado

| Elemento | Aparência atual | Função |
| --- | --- | --- |
| Fundo da página | Imagem `assets/background.png`, cobrindo a área de conteúdo, centralizada e fixa | Criar profundidade sem disputar atenção com os dados |
| Hero | Retângulo amplo com imagem escurecida, gradiente azul quase preto, borda clara fina e sombra profunda; cantos retos | Abrir a narrativa e identificar o candidato |
| Faixa principal de seção | Card de cantos arredondados, gradiente azul, brilho radial discreto e barra vertical branca/azul à esquerda | Separar os grandes capítulos da análise |
| Cabeçalho interno | Card azul mais leve, com título e subtítulo em duas linhas de hierarquia | Introduzir uma visualização dentro da seção |
| Cards de conteúdo | Azul profundo translúcido, borda azul clara fina, sombra e leve blur | Agrupar informação sem esconder o fundo |
| Gráficos Plotly | Fundo transparente, textos claros e grades discretas | Integrar gráfico e card |
| Mapas | Coropléticos Plotly nas duas páginas, sem mapa-base de ruas | Mostrar votos por intensidade, força/atuação por classe, malhas neutras ou oportunidades |
| Mensagens de ausência | Aviso ou informação textual dentro do espaço da visualização | Explicar falta de dados sem simular um resultado |

A base cromática é `#eaf2ff` para texto, `#f8fbff` para títulos e números, `#b7c7e6` para descrição e legendas. Os cards usam gradientes próximos de `rgba(11,31,77,.76)` e `rgba(7,24,54,.68)`, com bordas azuis próximas de `rgba(59,130,246,.24)`. Azul claro (`#60a5fa`), azul médio (`#2563eb`) e azul profundo (`#0b1f4d`) expressam intensidade ou seleção; verde, vermelho, amarelo, laranja e cinza têm significado específico nos mapas categóricos.

Os preenchimentos dos mapas são opacos e aparecem sobre fundo transparente, sem nomes de ruas sob os polígonos. Os tooltips usam fundo escuro e texto claro. Os 853 municípios de Minas Gerais compõem os mapas estaduais; os polígonos municipais são simplificados com tolerância pequena para preservar a leitura dos limites. O mapa detalhado usa bairros oficiais quando a malha cobre pelo menos 95% do município; caso contrário, usa áreas ponderadas quando existem duas ou mais unidades. A malha completa de setores censitários fica restrita aos municípios que possuem uma única área ponderada.

### 1.2 Hierarquia de texto e formatação

O hero usa título grande e pesado, subtítulo menor e nome/cargo/partido em maiúsculas. Quando exibido, o total de votos segue a mesma tipografia dessas linhas de identificação. Os títulos principais de seção são largos, brancos e densos; subtítulos ficam em azul claro. Labels dos KPIs gerais são compactos; no card do eleitor ideal, os títulos das dimensões têm fonte ampliada. Cards e legendas não devem exigir que a cor sozinha explique um resultado: os textos e tooltips dão o nome da categoria, a unidade e o recorte. Números de votos usam separador de milhar; percentuais e valores monetários aparecem com unidade explícita. Onde os dados são estimados ou rateados, a interface informa isso junto à visualização.

### 1.3 Capa comum às duas páginas

O hero distribui o conteúdo em duas faixas: à esquerda ficam o título da página, um subtítulo curto e uma linha com foto e dados do candidato; à direita fica a navegação vertical. A foto é vertical, com cantos levemente arredondados, borda clara e sombra; quando não há imagem remota, o espaço permanece como um bloco neutro. Os dados aparecem como `NOME:`, `CARGO:` e `PARTIDO:` em caixa alta. O partido é lido do campo `sg_partido` da base territorial do candidato. `TOTAL DE VOTOS:` aparece logo abaixo do partido nas duas páginas, com a mesma tipografia das demais linhas, sem card próprio; o valor é calculado a partir do parquet territorial selecionado. O ano integra o título do Raio X.

À direita do hero há um painel escuro arredondado com dois botões empilhados: **Raio X Eleitoral** e **DNA Eleitoral**. Cada botão ocupa toda a largura do painel; a página ativa aparece em azul e as demais opções têm fundo transparente. A navegação permanece dentro do app; a pasta selecionada na barra lateral é preservada na sessão.

| Página | Título do hero | Subtítulo |
| --- | --- | --- |
| Raio X | `RAIO X da votação 2026` (ano numérico mais recente disponível quando não há 2026) | `Análises descritivas geográficas e do perfil do eleitor na última eleição.` |
| DNA | `DNA do Eleitor` | `Quem é, onde está e como se comporta o eleitor determinante da candidatura.` |

## 2. Página 1 — Raio X Eleitoral

A página segue a ordem: **Mapa de Força Eleitoral → Como foi sua votação em Belo Horizonte → Força da política local → Concentração territorial dos votos → Mapa da atuação parlamentar → Eficiência por Custo do Voto**. A primeira parte oferece localização e volume; a segunda aproxima os votos nos bairros de Belo Horizonte; a seção de política local confronta capital político e market share; as três seguintes interpretam dependência territorial, emendas e gastos.

### 2.1 Mapa de Força Eleitoral

**Pergunta visual:** onde estão os votos e quais localidades lideram?

A faixa **Mapa de Força Eleitoral** apresenta o subtítulo `Onde estão concentrados seus votos e a força da sua votação.`. Logo abaixo, antes do mapa e dos cards laterais, o card horizontal de **Principal reduto eleitoral** destaca a mesorregião mais votada e seu volume. Uma badge verde **Maior base eleitoral** aparece no canto superior direito, e o rodapé informa `{votos} votos recebidos` com maior peso visual. O total de votos do candidato fica no hero, abaixo do partido e no mesmo padrão tipográfico das demais linhas de identificação.

O seletor **Mesorregião / Município** fica sozinho no canto superior direito, dentro do card do mapa. Ele altera o agrupamento do mapa estadual.

O card do mapa ocupa **70% da largura** disponível e tem cerca de 560 px de altura. Os 30% restantes contêm quatro cards empilhados: **Município principal (Top 1)** (nome, participação no total e votos da cidade líder, com alerta acima de 30%), **Dependência do reduto principal** (parcela dos votos no município líder, com alerta acima de 30%), **Penetração territorial** (municípios com votos sobre os municípios do estado) e **Densidade média por município** (votos divididos apenas pelos municípios com voto). No modo municipal, cada município de Minas Gerais é um polígono Plotly; o hover informa nome e votos. A intensidade progride do azul muito claro ao azul profundo, com transformação logarítmica dos votos. No modo mesorregional, cada mesorregião é um único polígono da malha oficial, colorido pelo total de seus votos; o hover informa nome e votos da mesorregião. Áreas sem votos continuam desenhadas na cor mínima. As linhas visíveis correspondem à malha selecionada.

O gráfico de barras aparece em uma janela de detalhamento após o clique no mapa. No modo mesorregional, mostra todos os municípios da mesorregião selecionada. No modo municipal, mostra todos os bairros com registros de votos do município selecionado. A altura cresce generosamente conforme a quantidade de linhas, permitindo rolar a janela até o último território sem comprimir as barras. As barras são espessas; os nomes dos municípios ou bairros e os textos de votos e participação usam tipografia ampliada. O comprimento expressa votos e a cor também varia em azul. O hover repete território, votos e percentual.

Se a malha ou os votos não puderem ser carregados, o mapa cede lugar a uma mensagem de indisponibilidade. O detalhamento também informa quando faltam dados. A interface não preenche municípios ou bairros com valores fictícios.

### 2.2 Como foi sua votação em Belo Horizonte

A seção começa com a mesma faixa principal usada em **Mapa de Força Eleitoral**: título **Como foi sua votação em Belo Horizonte** e subtítulo `Veja o histórico dos seus votos na sua Base Eleitoral`. Abaixo, usa duas colunas na proporção aproximada de 70/30: o mapa de bairros de Belo Horizonte (código IBGE `3106200`) fica à esquerda e cinco cards de indicadores ficam à direita. No topo do card do mapa, um filtro horizontal alterna **2020**, **2024**, **2026** e **Projeção 2028**, com 2026 selecionado inicialmente. A opção 2026 mantém o mapa de votos atual. As opções 2020 e 2024 leem `bh_2026/territorio/stage01b_bairros.parquet` do candidato selecionado e comparam a participação daquela eleição com 2026. **Projeção 2028** lê `bh_2026/potencial_demografico/stage08c_potencial_demografico_icp_bairro.parquet` e colore **Base Crítica (Fortaleza)** em azul, **Vulnerável/Ameaçado** em amarelo e **Oportunidade BH** em verde; as demais categorias ficam em tom neutro. Nesse filtro, os cinco cards laterais continuam mostrando os indicadores de 2026. Para 2020 e 2024, os cards acompanham o ano selecionado.

Os cinco cards mostram, nesta ordem, **Votos em Belo Horizonte (ano selecionado)**, **Bairro principal (Top 1)**, **Dependência do bairro principal**, **Penetração por bairros** e **Densidade média por bairro**. O primeiro card destaca a parcela da votação total do candidato que veio de BH; logo abaixo, uma badge verde mostra **Total municipal** e a quantidade de votos da cidade. Em 2020 e 2024, a parcela é 100%; em 2026, compara os votos de BH com o total do candidato nos municípios do estado. Concentração, penetração e densidade usam os votos por bairro do ano escolhido. A penetração mostra a quantidade de bairros com voto e sua proporção entre os bairros oficiais da malha usada pelo mapa. A badge classifica essa cobertura como **Concentração baixa** (abaixo de 1/3, vermelha), **Concentração moderada** (de 1/3 a 2/3, amarela) ou **Concentração alta** (acima de 2/3, verde). O índice só é calculado quando o mapa usa a malha oficial de bairros. O último card destaca a média de votos por bairro, com o texto **Por Bairro** abaixo do valor. Sua badge usa a média arredondada: **Concentração baixa** (menos de 100 votos, vermelha), **Concentração moderada** (100 a 300 votos, amarela) ou **Concentração alta** (mais de 300 votos, verde).

Para 2026, a geometria usa bairros oficiais quando seus polígonos cobrem pelo menos 95% do município. Se a cobertura for menor, usa áreas ponderadas quando existem duas ou mais unidades. Somente municípios com uma única área ponderada recorrem a todos os setores censitários, inclusive aqueles sem votos. Divisões internas claras distinguem as unidades e um contorno branco mais espesso preserva a silhueta municipal. Com menos de mil votos, os polígonos com votos recebem o mesmo azul médio. A partir de mil votos, a cor usa os cinco tons de azul do mapa estadual: escala linear até 5 mil votos e transformação logarítmica quando o total municipal ultrapassa esse valor. Nas malhas de bairros e áreas ponderadas, a intensidade também considera a proporção de polígonos com votos; no fallback por setores censitários, a escala ocupa toda a faixa de cores. No mapa “Como foi sua votação em Belo Horizonte”, bairros sem votos aparecem em cinza e ficam fora da escala; na escala logarítmica, gamma 0,8 suaviza a compressão para tornar diferenças entre votos baixos e médios mais visíveis.

Para 2020 e 2024, a legenda do card mostra **verde** para aumento, **azul** para estabilidade e **vermelho** para queda na participação do candidato até 2026; **cinza** identifica bairros sem comparação disponível. O hover informa os votos da eleição escolhida, os votos de 2026 e a diferença de participação em pontos percentuais. O cálculo agrega as linhas de locais correspondidos por bairro antes de comparar as participações. Os códigos das unidades geométricas não aparecem na visualização.

No filtro **Projeção 2028**, as quatro pílulas mantêm os rótulos **Base Crítica (Fortaleza)**, **Vulnerável**, **Oportunidade** e **Demais bairros**. Uma explicação logo abaixo informa o corte de base forte (mediana dos bairros com votos do candidato, com valor calculado) e o espaço demográfico (média simples ICP − população negativa, exigindo gênero, idade e escolaridade válidos). Base forte sem defasagem média fica azul; base forte com espaço fica amarela; menor votação com espaço fica verde; demais situações e comparação incompleta ficam cinza. O hover mostra votos de referência e diferença média em pontos percentuais. A nota abaixo do mapa esclarece que as dimensões são independentes e que a classificação não mede perda histórica nem prevê votos em 2028.

### 2.3 Força da política local

A faixa principal usa o título `Força da política local` e o subtítulo `Veja se vereadores e prefeitos das cidades foram decisivos na sua votação`. A estrutura repete a proporção 70/30 do Mapa de Força Eleitoral.

À esquerda há um card com o filtro territorial fixado em **Município** e a malha completa de Minas Gerais, com divisões municipais brancas e contorno estadual mais espesso. O card tem altura alinhada ao fim dos quatro cards laterais, para que o contorno do mapa termine no mesmo eixo visual do último card. Antes do mapa, uma explicação centralizada e em negrito informa que a seção avalia a eficácia de prefeitos e vereadores aliados na transferência de votos e considera votação alta quando o percentual do candidato na cidade supera sua média no estado. Abaixo, quatro pílulas coloridas mantêm o fundo da classe e informam, com texto centralizado: prefeito/vereadores entregaram votos, prefeito/vereadores não entregaram votos, votação própria sem prefeito/vereadores e ausência de prefeito/vereadores e votos, sem repetir o nome da cor no texto. O mapa cruza `capital_local_0a100` com o market share municipal. Nota alta significa resultado acima de 50/100; market share alto significa resultado municipal igual ou superior à participação estadual do candidato. O hover mostra município, classe, leitura, nota, market share local e referência estadual.

À direita, quatro cards empilhados também funcionam como legenda e filtro. **🤝 Alianças de alto retorno** usa verde; **⚠️ Acordos sem entrega**, vermelho; **⭐ Votação própria**, azul; e **❄️ Zonas neutras**, cinza. Cada card recebe no fundo um gradiente translúcido da própria cor, mais luminoso no canto superior esquerdo e integrado ao azul profundo da interface; o estado selecionado intensifica esse banho de cor e ganha contorno reforçado. O ícone e o título aparecem em uma badge no topo. Abaixo, a quantidade de cidades e a participação na votação recebem peso e tamanho maiores, seguidas pela **Cidade-chave** com seus votos. A estratégia encerra o card dentro de uma pílula tonalizada pela cor da classe. Ao clicar, apenas a classe escolhida mantém sua cor no mapa e as demais ficam atenuadas; clicar novamente limpa o destaque.

Um clique em qualquer município abre a janela **Força política local**, com o nome municipal como título interno. No topo aparecem a classificação e quatro números: votos, market share local, referência estadual e capital político local. Uma frase traduz a cor em leitura estratégica. Abaixo, o layout divide-se em duas colunas: à esquerda, o polígono isolado do município conserva a cor recebida e é seguido pelos detalhes da prefeitura, Câmara, partidos aliados e base dos dados; à direita, uma lista rolável apresenta prefeito e vereadores, com nome, partido, vínculo e afinidade.

### 2.4 Concentração territorial dos votos

**Pergunta visual:** a candidatura depende de poucos redutos ou distribui votos por muitos municípios?

Uma faixa principal apresenta o título e a frase `Quanto da votação total está concentrada nos municípios onde o candidato mais recebeu votos.`. O conteúdo está em um único card. Na parte superior há **quatro cards**: Top 1, Top 5, Top 15 e Top 20. Cada card mostra o rótulo Top em caixa alta, com fonte ampliada de 1,15 rem e texto branco dentro de uma badge verde (#15803d), com borda sutil e cantos arredondados, seguido pelo total de votos acumulados em fonte grande e negrito, com `votos` como legenda discreta. Nomes de municípios e contagem de municípios não aparecem no cabeçalho dos cards. A rosca Plotly mostra o percentual acumulado em relação a 100% dos votos em formato de gauge circular: trilho escuro e arco ativo têm a mesma espessura, as pontas do progresso são arredondadas e o tom do azul evolui sutilmente de Top 1 a Top 20, chegando a `#60a5fa`. O texto de instrução de clique não aparece abaixo delas.

Um clique na rosca abre uma janela com a composição incremental até aquele Top: Top 1, municípios 2 a 5, 6 a 15 e 16 a 20, conforme o card selecionado. Cada etapa mostra sua contribuição percentual e votos absolutos, seguida do total acumulado.

Em seguida, uma curva Plotly mostra a participação acumulada em função da posição do município até **100% da votação**. O eixo horizontal usa escala logarítmica para separar melhor os primeiros marcos de concentração. A linha azul, a área translúcida, os marcadores e as referências percentuais permitem ver a velocidade da concentração. Os marcadores da curva são **Top 1**, **Top 5**, **Top 15**, **Top 20** e **Todos**; eles servem como leitura visual e não abrem janela ao clique. Logo abaixo da curva, antes dos expansores, uma frase automática nomeia o líder e destaca o peso dos 15 municípios principais. Em seguida, os nomes completos estão em expansores `Ver municípios do Top 5`, `Top 15` e `Top 20`, com posição numérica. Sem linhas municipais válidas, o card exibe aviso e não fabrica uma curva.

### 2.5 Mapa da atuação parlamentar de acordo com os votos

**Pergunta visual:** onde os votos recebidos encontram as emendas destinadas pelo parlamentar?

A faixa principal traz o título completo. Um filtro **Recorte do mapa** alterna **Minas Gerais · municípios** e **Belo Horizonte · bairros**; Minas Gerais aparece inicialmente. No recorte estadual, antes do mapa há **três KPIs**: **Taxa de Reciprocidade** (parcela das emendas destinada aos três maiores redutos), **Maior Beneficiado (R$)** (município, valor e votos) e **Média R$/Voto** (valor estadual por voto). Os cards seguem a mesma família visual dos KPIs territoriais.

No recorte estadual, o mapa Plotly fica abaixo dos três KPIs na mesma coluna esquerda, ocupando cerca de **70% da largura** e aproximadamente **720 px** de altura; a legenda ocupa os **30%** restantes como seis cards verticais. Cada município recebe uma categoria. Os cards usam gradiente baseado na própria cor do mapa e mostram, por classe, quantidade de cidades, participação na votação total e explicação em linguagem simples: **BASE PRIORIZADA**, **APOSTA POLÍTICA**, **BASE EM RISCO**, **PRESENÇA PONTUAL**, **VOTAÇÃO ORGÂNICA** e **TERRITÓRIO NEUTRO**. A cor é **classe**, não escala monetária. O hover do mapa traz município, categoria, votos e emendas. O valor financeiro não modifica a intensidade do preenchimento.

No recorte de Belo Horizonte, o card mostra o mapa de bairros de `bh_2026/territorio/stage01b_bairros.parquet`, colorido pela votação de 2026. Ao lado, três cards mostram votos nos bairros, valor total de emendas registradas para BH e quantidade/período dos registros. O expander **Consultar emendas registradas para Belo Horizonte** lista ano, número, tipo, valor, finalidade, beneficiário e status. O parquet de emendas está no nível municipal: o total de BH não é distribuído nem atribuído aos polígonos dos bairros. A legenda do mapa permanece uma escala de votos.

O mapa estadual depende de votos e emendas do candidato. Se a combinação não estiver disponível, o card mostra `Mapa parlamentar indisponível.`. Quando não há registros de emendas, os KPIs mostram traço ou `Sem dados` com uma legenda que explica a ausência, sem apresentar a falta de registros como resultado zero. No recorte de BH, a malha e os votos usam a pasta `bh_2026`; emendas municipais sem registros aparecem como ausência de dados.

Ao clicar em um município no mapa parlamentar, uma janela mostra os votos, a categoria, o total indicado de emendas e uma tabela por finalidade e tipo de indicação. A tabela agrega os valores indicados das emendas registradas para o município; pagamentos podem ser diferentes. O card do mapa não acrescenta preenchimento lateral interno.

### 2.6 Eficiência por Custo do Voto

**Pergunta visual:** que tipos de despesa dominam os gastos e quanto foi gasto por voto na campanha?

A seção abre com a frase `Participação de cada tipo de despesa nos gastos totais da campanha.`. Logo após o título, três cards na mesma linha mostram **Custo por Voto Total**, **Total Gasto** e **Despesa Líder**. Eles reutilizam o fundo em gradiente azul, borda, cantos arredondados e sombra dos cards laterais, assim como as fontes de título, valor e nota (`raiox-insight-title`, `raiox-insight-value` e `raiox-insight-note`). Valores e nomes longos podem quebrar linha. Os indicadores são calculados de `gastos_por_tipo.parquet` e dos votos totais do candidato. Ao selecionar uma despesa no treemap, os KPIs mostram o gasto e o custo por voto desse tipo; o botão **Mostrar gasto total** restaura os totais da campanha. Se faltarem gastos ou votos, a seção informa a indisponibilidade sem apresentar zeros fictícios.

Uma margem de 1,25 rem separa os três indicadores superiores da faixa do treemap. O treemap Plotly ocupa cerca de **75% da largura** da faixa e tem **620 px** de altura. A área de cada retângulo usa a raiz quadrada de `valor_total_gasto`, reduzindo a dominância visual da maior despesa para deixar visíveis as categorias menores. Uma nota abaixo do gráfico explica esse ajuste; os percentuais, valores e custos exibidos continuam baseados nos gastos reais. As cores identificam tipos de despesa. Os nomes compactos das despesas aparecem dentro dos blocos; nos maiores, aparecem também participação e valor. Tipos que representam menos de 1% cada são agrupados depois dos quatro maiores em **OUTRAS DESPESAS**. O grupo informa seus componentes no hover e não é selecionável. A despesa selecionada recebe destaque; o hover mostra total gasto, participação e custo por voto na campanha. Os aliases e rótulos compactos são:

| Tipo de despesa nos dados | Alias geral | Rótulo compacto no treemap |
| --- | --- | --- |
| Alimentação | Alimentação | Alimentação |
| Atividades de militância e mobilização de rua | Militância | Militância |
| Cessão ou locação de veículos | Locação de Veículos | Locação de Veículos |
| Combustíveis e lubrificantes | Combustíveis | Combustíveis |
| Correspondências e despesas postais | Correios | Correios |
| Criação e inclusão de páginas na internet | Criação de Sites | Criação de Sites |
| Despesa com Impulsionamento de Conteúdos | Anúncios Online | Anúncios Online |
| Despesas com Hospedagem | Hospedagem | Hospedagem |
| Despesas com pessoal | Equipe e Pessoal | Equipe e Pessoal |
| Despesas com transporte ou deslocamento | Transporte | Transporte |
| Encargos financeiros, taxas bancárias e/ou op. cartão de crédito | Taxas Bancárias | Taxas Bancárias |
| Eventos de promoção da candidatura | Eventos | Eventos |
| Locação/cessão de bens imóveis | Locação de Imóveis | Locação de Imóveis |
| Locação/cessão de bens móveis (exceto veículos) | Locação de Bens Móveis | Locação de Bens Móveis |
| Materiais de expediente | Material de Expediente | Material de Expediente |
| Produção de jingles, vinhetas e slogans | Produção de Jingles e Áudio | Jingles e Áudio |
| Produção de programas de rádio, televisão ou vídeo | Produção Audiovisual | Produção Audiovisual |
| Publicidade por adesivos | Publicidade: Adesivos | Publicidade: Adesivos |
| Publicidade por jornais e revistas | Publicidade: Impressa (Mídia) | Publicidade Impressa |
| Publicidade por materiais impressos | Materiais Impressos | Materiais Impressos |
| Serviços advocatícios | Serviços Jurídicos | Serviços Jurídicos |
| Serviços contábeis | Serviços Contábeis | Serviços Contábeis |
| Serviços próprios prestados por terceiros | Serviços de Terceiros (Próprios) | Terceiros Próprios |
| Serviços prestados por terceiros | Serviços de Terceiros | Serviços de Terceiros |
| Taxa de Administração de Financiamento Coletivo | Taxa de Vaquinha | Taxa de Vaquinha |

À direita, três cards empilhados ocupam cerca de **25% da faixa** e usam o mesmo fundo em gradiente, borda e sombra dos cards laterais do **Mapa de Força Eleitoral**. Em telas largas, os três cards laterais ocupam os 25% restantes, crescem para acompanhar a altura do painel do treemap e mantêm 1 rem entre si. Em telas estreitas, voltam à altura natural do conteúdo. O primeiro, **Custo por voto da despesa**, mostra o valor gasto na categoria dividido pelos votos totais da campanha. Ao clicar em uma categoria no treemap, o card a acompanha; sem seleção, mostra a despesa líder. O card também informa o custo médio geral da campanha e um badge que compara a contribuição da categoria com esse custo total: **Baixo** (verde) abaixo de um terço, **Moderado** (amarelo) de um a dois terços e **Alto** (vermelho) a partir de dois terços. O texto esclarece que a razão não mede retorno isolado nem causalidade da despesa.

O segundo card, **Peso no orçamento**, mostra `valor_total_gasto` da categoria dividido pelo gasto total da campanha, em percentual com uma casa decimal. O subtexto mostra o gasto da categoria e o total em reais. O badge verde **Rubrica principal** identifica a categoria de maior gasto; as demais recebem o badge azul **Gasto secundário**. Ele acompanha o filtro do treemap e, sem seleção, mostra a rubrica líder.

O terceiro card, **Comparativo com a média**, mostra `(custo por voto da categoria - custo por voto total) / custo por voto total` como variação percentual com sinal. O subtexto mostra a diferença em reais por voto, com o mesmo sinal. O badge indica **Despesa acima** (vermelho) para variação maior que +10%, **Despesa moderada** (amarelo) entre −10% e +10%, ou **Despesa abaixo** (verde) para variação menor que −10%. Com gastos positivos, cada categoria compõe o total, então a variação acima da média total não ocorre nos dados atuais. `gastos_municipais_teoricos.parquet` ainda não alimenta a seção; o custo por voto da categoria é calculado dos totais por tipo e dos votos, com o mesmo significado de `custo_por_voto_tipo`.

## 3. Página 2 — DNA Eleitoral

Depois do hero comum, a página apresenta **três faixas principais** nesta ordem: Identidade da Base Eleitoral, Distribuição do Perfil do Eleitorado, Expansão & Oportunidades para 2030. O card Eleitor ideal do candidato aparece na primeira faixa. A seção de distribuição vem em seguida, depois o card BASE ELEITORAL DO CANDIDATO e a seção completa de expansão; o bloco Potencial demográfico municipal fecha a página. Sunburst, heatmap e composição demográfica por pontos não pertencem à interface atual.

### 3.1 Identidade da Base Eleitoral

**Pergunta visual:** quem é o eleitor predominante do candidato?

A faixa principal usa o subtítulo `Quem é o eleitor-chave e quais atributos definem o perfil do seu eleitor.`. Ela é seguida pelo card de eleitor ideal, ocupando a largura do conteúdo.

#### 3.1.1 Eleitor ideal do candidato

O card principal é um `st.container(border=True)` com a mesma borda, fundo em gradiente azul e sombra do painel **BASE ELEITORAL DO CANDIDATO**. O título `Eleitor ideal do candidato` aparece antes da descrição `Síntese do perfil demográfico predominante na base eleitoral do candidato.`. O título **👤 PERFIL PREDOMINANTE** recebe destaque maior e fica centralizado acima das badges coloridas dos atributos, que também ficam centralizadas e espaçadas. Quando o resumo agrega informação, ele aparece abaixo com emoji de fala; se apenas repete a persona, é ocultado. **A confiança do modelo não aparece no card.**

Na base do card, **quatro sub-cards com borda**, em `st.columns`, apresentam Gênero, Faixa etária, Escolaridade e Estado civil. Cada sub-card também usa `st.container(border=True)`. Títulos e categorias dominantes ficam centralizados. Cada percentual válido aparece em um gauge semicircular de 0 a 100, feito com `go.Indicator(mode="gauge+number")` dentro de `st.plotly_chart`; a cor do arco acompanha a dimensão. Os percentuais das quatro dimensões são independentes; não formam fatias de uma soma de 100%. Se o percentual não é válido ou não existe, o card não inventa o número. Os estilos desses badges e sub-cards são locais à página DNA; o hero e a navegação seguem o CSS compartilhado.

### 3.2 Distribuição do Perfil do Eleitorado

**Pergunta visual:** como se repartem as categorias demográficas e quais perfis sustentam a candidatura?

A faixa principal traz `Distribuição demográfica estimada dos votos, com recorte por município e perfil.`. Primeiro aparece a distribuição; logo abaixo, ainda nesta mesma faixa principal, vem o painel **BASE ELEITORAL DO CANDIDATO**.

#### 3.2.1 Distribuição do eleitorado

O conteúdo está em um card com a mesma borda, gradiente azul, raio, sombra e espaçamento do painel **BASE ELEITORAL DO CANDIDATO**. O cabeçalho é separado por uma linha sutil; o título menor `Distribuição do eleitorado` e uma descrição explicam que as parcelas são estimadas.

A composição usa **gráfico à esquerda e filtros à direita** (proporção aproximada 2,3:1). À direita há uma chamada `Refine a distribuição`, um seletor **MUNICÍPIO** com opção `Todos os municípios` e um seletor **PERFIL DEMOGRÁFICO** com Gênero, Faixa etária, Escolaridade e Estado civil. O município altera o universo de votos; a dimensão altera as fatias.

À esquerda, uma badge com ponto na cor da fatia indica a categoria dominante da dimensão selecionada. A **rosca Plotly** tem centro vazado amplo, total de votos em tipografia forte no miolo e subtítulo menor em azul acinzentado. Os percentuais de fatias com pelo menos 1% ficam fora da rosca, ligados às respectivas fatias por linhas; fatias menores continuam no hover e na legenda sem criar rótulos `0,0%` ao redor do gráfico. O hover mostra categoria e participação. À direita, abaixo dos seletores, a legenda mostra cor, categoria e percentual, sem votos estimados; a categoria dominante recebe realce discreto. Para gênero, feminino usa azul, masculino usa laranja e não informado usa cinza. O gráfico mostra **uma dimensão por vez**. A nota abaixo afirma que os parquets não permitem cruzar diretamente idade, gênero e escolaridade de indivíduos. Dados ausentes geram mensagem no lugar da rosca.

#### 3.2.2 BASE ELEITORAL DO CANDIDATO

O segundo bloco é um painel próprio, com título em caixa alta e pergunta `Quais perfis sustentam a candidatura e qual o peso de cada um na votação?`. Uma **barra de composição** apresenta a participação das classificações na votação do candidato: azul para Base eleitoral, ciano para Eleitor consolidado e verde para Eleitor emergente. A legenda abaixo identifica cada segmento e seu percentual. Uma classificação vazia apresenta travessão; uma parcela sem classificação aparece em cinza azulado.

A lista abaixo contém **uma linha expansível por ICP**, ordenada dentro da classificação pelo peso eleitoral. A linha fechada mostra uma badge de maturidade (`🎯 Base Principal`, `🛡️ Consolidado` ou `🚀 Emergente / Expansão`), identificador ICP, atributos demográficos dominantes em chips, percentual da votação e votos absolutos; uma seta sugere abertura. A linha aberta recebe borda mais clara e revela quatro blocos demográficos em grade de duas colunas. Cada bloco mostra dimensão, categoria dominante, percentual e uma barra azul individual. Uma nota esclarece que os percentuais descrevem categorias dominantes **dentro do perfil**. O bloco final `Leitura estratégica` traz a justificativa textual disponível. Dois ICPs com o mesmo rótulo estratégico continuam separados. Ausência de perfis gera mensagem, não um ICP fictício.

### 3.3 Expansão & Oportunidades para 2030

**Pergunta visual:** onde proteger a base existente e onde há oportunidade demográfica relativa ao ICP escolhido?

A faixa principal mantém o texto atual `Mapeamento em nível de bairro e área ponderada. Localização dos clusters táticos e visualização de manchas de potencial de crescimento.`. **A implementação exibida logo abaixo é municipal**: não há mapa de bairros nem de áreas ponderadas nesta seção. Um seletor à direita alterna **ELEITOR IDEAL** e classificações estratégicas.

Antes do mapa há uma **legenda de quatro cards**. Cada um combina amostra de cor, nome da classe e uma explicação curta: **verde** para oportunidade alta com perfil aderente, **azul** para base com muitos votos que pede proteção, **amarelo** para oportunidade com menor aderência e **cinza** para baixa similaridade ou informação insuficiente. A legenda torna o mapa categórico; cores não representam uma sequência contínua.

O mapa municipal é um **coroplético Plotly** de largura total e cerca de **640 px** de altura. Cada município recebe uma das quatro classes e a barra categórica do próprio Plotly permanece visível. O hover informa nome, classe, votos, oportunidade e similaridade. A nota inferior explicita que os limites de votos, similaridade e potencial são relativos ao perfil selecionado e que potencial demográfico **não é previsão de votos**. Se não houver dados completos de Censo/potencial ou a malha municipal falhar, a seção mostra uma informação textual no lugar do mapa.

### 3.4 Potencial demográfico municipal

O bloco usa os mesmos Parquets de potencial geral, clusters e Censo (gênero, idade e escolaridade) da expansão estadual, mantendo os resultados por **área ponderada**. A junção com a malha oficial usa diretamente `cd_area_ponderada` e `code_weighting`, sem rateio entre bairros ou setores.

O mapa ocupa 70% da largura; os quatro cards laterais ocupam 30% e apresentam as categorias da legenda: oportunidade alta (verde), proteger a base (azul), oportunidade com menor aderência (amarelo) e baixa similaridade/dados incompletos (cinza). Cada card mostra a quantidade de áreas da categoria no recorte exibido e sua explicação.

Os filtros de perfil, mesorregião, município e área ponderada são independentes da expansão estadual. Selecionar uma área restringe o mapa e as contagens dos cards. O tooltip informa código da área, categoria, votos, oportunidade, similaridade e bairros TSE de referência pelo crosswalk. Dados ausentes aparecem como indisponíveis, com polígonos neutros.

As faixas são calculadas sobre todas as áreas disponíveis para o perfil selecionado, antes dos filtros territoriais. Aplicam os mesmos critérios relativos da expansão estadual, agora na unidade de área ponderada. Os votos repetidos entre dimensões são usados uma vez por área. A nota esclarece a unidade dos resultados, o vínculo dos bairros por ponto e que potencial não é previsão de votos.

## 4. Interação, estados e continuidade visual

### 4.1 Escopo dos controles

| Controle | Onde atua | Persistência observável |
| --- | --- | --- |
| Pasta do candidato na barra lateral | Três páginas | Lista as pastas de candidatos encontradas na raiz configurada do HF e preserva a seleção ao trocar de rota |
| Painel vertical Raio X / DNA | Navegação | Opção ativa destacada no hero |
| Filtro territorial Mesorregião / Município | Mapa estadual do Raio X e conteúdo da janela aberta por clique | Restrito ao primeiro mapa |
| Eleição no mapa de Belo Horizonte | Mapa de bairros do Raio X | 2020/2024 mostram comparação com 2026; 2026 mostra votos atuais; Projeção 2028 mostra as categorias estratégicas |
| Cards de votação em Belo Horizonte | Cinco indicadores calculados para a cidade | Atualizam em 2020/2024; ficam nos dados de 2026 em 2026 e Projeção 2028 |
| Recorte do mapa parlamentar | Mapa estadual por municípios ou BH por bairros | Alterna votos/emendas municipais e votação de 2026 por bairro |
| Consultar emendas de BH | Tabela no recorte parlamentar de Belo Horizonte | Mostra registros da pasta `bh_2026`; valores permanecem no nível municipal |
| Filtro Município da força política local | Mapa categórico dos quatro quadrantes em Minas Gerais | Única granularidade disponível nesta etapa |
| Cards da força política local | Destacam ou restauram uma classe do mapa | Card ativo recebe contorno reforçado |
| Clique em município da força política local | Abre o mapa isolado, os indicadores e a composição política municipal | Janela modal; fecha sem alterar o filtro dos cards |
| Tipo de despesa no treemap | KPIs de custo e destaque no treemap | Botão restaura gasto total |
| Município e dimensão da rosca DNA | Rosca e total do recorte | Restrito à seção de distribuição |
| Mesorregião e município do Potencial demográfico municipal | Mapa categórico por área ponderada | Restrito ao bloco municipal |
| Perfil para expansão | Classes e métricas do mapa de Expansão 2030 | Restrito à seção de expansão do DNA |

### 4.2 Estado sem dados

Falta de parquet, malha ou dimensão não deve parecer valor zero. A implementação usa `st.info`, `st.warning`, captions ou cards com texto para explicar o que está ausente. Zero legítimo continua como valor ou cor mínima quando existe malha e a métrica pode ser calculada. Os mapas mantêm municípios ou setores sem votos visíveis onde a fonte geométrica está disponível. As notas analíticas permanecem próximas ao gráfico a que se referem.

### 4.3 Responsividade implementada

No hero, a navegação permanece vertical à direita em telas largas; quando as colunas do Streamlit se reorganizam, o painel passa para baixo do conteúdo mantendo os dois botões empilhados. A foto e os textos também se ajustam por regras CSS próprias. Os KPIs da página 1 passam de linha para uma coluna em telas até cerca de **900 px**. A faixa Top 1/5/15/20 passa para duas colunas; a lista de municípios reduz colunas novamente abaixo de **600 px**. Os quatro sub-cards do eleitor ideal passam para duas colunas abaixo de **900 px** e uma coluna abaixo de **760 px**. No card dos ICPs, o resumo e as barras demográficas empilham abaixo de **600 px**; o cabeçalho de cada perfil pode quebrar em telas estreitas. A legenda de expansão passa de quatro para duas colunas abaixo de **900 px** e para uma abaixo de **560 px**.

Os pares de mapa e cards laterais da página 1, o treemap com os três cards de insights ao lado e o par rosca/filtros do DNA são montados com `st.columns`; a experiência móvel também depende do empilhamento padrão do Streamlit. Nomes longos de município, persona e despesa podem quebrar linha. Tooltips complementam os rótulos que não cabem nos cards.

## 5. Critérios de fidelidade para futuras alterações

1. Preservar a diferença entre **intensidade** (gradiente azul contínuo) e **classe** (cores da atuação parlamentar e da expansão).
2. Manter a leitura em camadas: hero, faixa principal, cabeçalho interno quando necessário e conteúdo analítico.
3. Manter os cards de potencial municipal vinculados às categorias e ao recorte exibido; na força política local, manter as recomendações vinculadas aos quatro quadrantes.
4. Mostrar voto observado, estimativa demográfica, custo de referência, gasto rateado e potencial em seus papéis corretos, com unidades e notas visíveis.
5. Fazer seleção e estado vazio permanecerem compreensíveis sem depender só de cor.
6. Atualizar este briefing quando mudar texto, card, escala, interação, ordem de seção ou granularidade de mapa.
