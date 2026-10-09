"""Texto da versão pessoal de leitura (português). Números = {chave} do registro de afirmações do artigo.

Blocos: ("title"|"subtitle"|"h1"|"h2"|"h3"|"p"|"box", texto), ("ul"|"ol", [itens]),
("table", cabeçalho, linhas[, larguras Typst]), ("figure", caminho, legenda), ("eq", typst, texto_docx),
("pagebreak",). **negrito** é o único realce.
"""

EXTRA: dict = {}

BLOCKS = [
    ("title", "Como escolhas de análise e a amostragem dos satélites mudam o mapa da Anomalia do Atlântico Sul"),
    ("subtitle", "Versão em português simples do artigo e do suplemento (dados de janeiro de 2024, satélites NOAA e MetOp). "
                 "Fellipe Gonçalves Leite."),
    ("box", "**Versão pessoal de leitura — não é para publicação.** Este texto reescreve o artigo em português comum para "
            "você entender o seu próprio trabalho. Ele tem as mesmas conclusões e os mesmos números do manuscrito: cada número "
            "aqui sai do mesmo registro de afirmações (claims register) que alimenta o PDF do artigo. Não é uma tradução "
            "oficial, não substitui o artigo e não deve ser citado. Depois do texto principal há uma seção final, "
            "“Depois do artigo: o que eu preciso entender”, com conceitos, glossário e perguntas prováveis."),

    ("h1", "O artigo em uma página"),
    ("table", ["Pergunta", "O que os dados mostram", "O que isso NÃO quer dizer"], [
        ["Limiar de “alto fluxo” (top 20% até top 1%)",
         "O centróide do mapa anda {thr_shift_min}–{thr_shift_max} km, dependendo da grade e da estatística. A área encolhe "
         "{thr_area_ratio_5_mean} vezes, mas quase tudo isso é imposto pela própria regra do percentil.",
         "Que a Anomalia se moveu essa distância. Quem mudou foi a definição do objeto."],
        ["Canal de energia (p1 = 25 MeV, p3 = 100 MeV)",
         "No top 10%, o centróide de p3 fica {ch_d_p3p1} km ao sul e a leste do de p1, e essa direção se manteve quando os "
         "dias foram reamostrados.",
         "Que prótons mais energéticos ficam fisicamente em outro lugar. O estudo não separa física de efeitos do ajuste "
         "espectral e da resposta dos detectores."],
        ["Janela de tempo (3 dias contra o mês)",
         "Comparação direta: Jaccard {tw_d3_Je} e {tw_d3_De} km. Só nas células que os dois mapas conseguem avaliar: "
         "{tw_d3_Jc} e {tw_d3_Dc} km. Com 1 dia ainda sobra diferença ({tw_d1_Dc} km).",
         "Que a diferença foi “causada” só pela cobertura, ou que existe um tempo de acumulação universal."],
        ["Cinco satélites",
         "Com a regra de qualidade QC-1, no caso de referência, a maior distância entre os centróides é {sat_max_prim} km "
         "({sat_max_median_prim} km com medianas). Sem a regra, {sat_max_unf} km.",
         "Que os satélites estão calibrados entre si, ou que sabemos a causa do registro excluído."],
        ["Campo magnético",
         "{mag_q25_min}% das amostras dentro do mapa ficam abaixo do primeiro quartil regional da intensidade do campo "
         "modelado.",
         "Que o campo magnético define ou valida uma fronteira “verdadeira” da Anomalia."],
    ], ["1fr", "1.6fr", "1.4fr"]),

    ("h1", "A pergunta do artigo"),
    ("p", "A Anomalia do Atlântico Sul (em inglês, SAA) é a região, sobre a América do Sul e o Atlântico Sul, onde o "
          "cinturão interno de prótons chega mais perto da Terra. Satélites em órbita baixa que passam por ali encontram "
          "muito mais partículas energéticas do que no resto do caminho. Por isso a região costuma ser desenhada a partir "
          "de medidas de partículas."),
    ("p", "Só que um satélite não entrega um mapa pronto. Ele entrega medidas soltas, uma a cada 2 segundos, em pontos "
          "diferentes da órbita. Para transformar isso em mapa é preciso decidir várias coisas: o tamanho das células do "
          "mapa, quantas medidas uma célula precisa ter, se a célula é resumida pela média ou pela mediana, o que conta "
          "como “alto fluxo”, quantos dias juntar, qual canal de energia usar e qual satélite usar. Normalmente essas "
          "escolhas são feitas uma vez e quase não são comentadas."),
    ("p", "O artigo pergunta: **para um mês de dados públicos (janeiro de 2024), quanto a posição e o tamanho de uma região "
          "de alto fluxo definida por percentil mudam quando cada uma dessas escolhas muda de forma controlada, e quanto "
          "dessa mudança vem da cobertura dos dados ou de medidas individuais, e não do campo de partículas?**"),
    ("p", "O artigo não tenta descobrir a Anomalia, não define a sua fronteira “verdadeira”, não mede dose de radiação nem "
          "risco, e não mostra que ela se moveu. Todos os deslocamentos do artigo são deslocamentos de um resultado de "
          "análise, não da Anomalia."),

    ("h1", "Os dados"),
    ("p", "Os dados são os arquivos diários processados do instrumento SEM-2, distribuídos pelo NCEI (o arquivo de dados "
          "ambientais da NOAA), para os 31 dias de janeiro de 2024 e cinco satélites: NOAA-15, NOAA-18, NOAA-19, MetOp-01 "
          "e MetOp-03. São 155 arquivos, e cada um tem a sua impressão digital (SHA-256) registrada no suplemento."),
    ("p", "As variáveis usadas são p1, p2 e p3: o fluxo diferencial de prótons em 25, 50 e 100 MeV medido pelos detectores "
          "omnidirecionais (OMNI) do instrumento MEPED. Um ponto importante: p1, p2 e p3 **não** são três instrumentos "
          "independentes. Os detectores contam partículas em quatro faixas de energia que se sobrepõem; o processamento da "
          "NOAA converte essas contagens em faixas separadas, ajusta uma curva (uma lei de potência) e lê essa curva em 25, 50 "
          "e 100 MeV. Os três canais vêm das mesmas contagens e do mesmo modelo."),
    ("p", "O fluxo é dado em partículas por cm² por segundo por esterradiano por MeV. O artigo nunca compara valores "
          "absolutos entre canais ou entre satélites; compara só posição e forma. Nenhuma calibração cruzada entre satélites "
          "foi aplicada. Os próprios arquivos avisam que os dados têm problemas conhecidos de contaminação."),

    ("h1", "Como o mapa é construído"),
    ("ol", [
        "**Recorte da região.** Ficam só as medidas entre as latitudes −70° e 20° e as longitudes −100° e 20°.",
        "**Células.** A região é dividida em células de 5° × 5° (432 células) e, numa segunda versão, de 2° × 2° (2.700 "
        "células). Cada medida cai na célula da posição do satélite.",
        "**Resumo da célula.** Para cada célula calculam-se o número de medidas, a média e a mediana do fluxo.",
        "**Célula elegível.** Uma célula só entra no mapa mensal se tiver pelo menos 30 medidas válidas. Para janelas mais "
        "curtas, o mínimo diminui na proporção dos dias (com piso de 3). Célula não elegível fica em branco, não vira zero.",
        "**Percentil.** Ordenam-se as células elegíveis pelo valor (média ou mediana) e calcula-se, por exemplo, o 90º "
        "percentil. “Top 10%” quer dizer: as células com valor maior ou igual a esse corte.",
        "**Footprint.** O conjunto dessas células é o “footprint”, a pegada de alto fluxo. É uma construção da análise, "
        "não uma fronteira física.",
        "**Área.** A área de cada célula é calculada na esfera: células perto do equador são maiores que células perto do "
        "polo, mesmo tendo os mesmos 5°.",
        "**Centróide.** É o “centro de massa” do footprint, em latitude e longitude, onde cada célula pesa o seu fluxo "
        "vezes a sua área.",
    ]),
    ("eq", "overline(phi) = (sum_i F_i A_i phi_i) / (sum_i F_i A_i)",
     "latitude do centróide = soma(fluxo × área × latitude) ÷ soma(fluxo × área)   (igual para a longitude)"),
    ("p", "O peso fluxo × área veio de uma observação do François Ginisty: uma célula grande (perto do equador) cobre mais "
          "território que uma pequena e deve pesar mais. Antes, o centróide pesava só o fluxo. (Agradecer a ele no artigo "
          "ainda depende de você pedir permissão.)"),
    ("p", "Para comparar dois mapas o artigo usa duas medidas. A **distância entre centróides**, em km, medida sobre a "
          "superfície da Terra. E o **índice de Jaccard ponderado por área**: a área que está nos dois footprints dividida "
          "pela área que está em pelo menos um deles. Vale 1 se forem idênticos e 0 se não tiverem nada em comum."),
    ("eq", "J(X, Y) = A(X inter Y) / A(X union Y)",
     "Jaccard = área em comum ÷ área total ocupada pelos dois"),
    ("p", "Cada família de testes muda uma coisa só (limiar, canal, janela ou satélite) e repete a mudança em 20 "
          "combinações de grade (5° ou 2°), estatística (média ou mediana) e limiar (top 20, 10, 5, 2 ou 1%). São {cfg_total} "
          "configurações, mas só {cfg_distinct} são realmente diferentes, porque o mapa de referência aparece nas quatro "
          "famílias e a primeira semana é igual à janela de 7 dias. Não são {cfg_total} experimentos independentes."),

    ("h1", "Limpeza dos dados e a regra de qualidade QC-1"),
    ("h2", "O que é retirado antes de tudo"),
    ("ul", [
        "Medidas feitas durante a calibração a bordo (marcador mep_IFC_on igual a 1): sai {ifc_on_noaa15} registro do NOAA-15.",
        "O valor −1 desse marcador aparece na maioria dos registros, mas a documentação não diz o que ele significa. Esses "
        "registros ficam, sem interpretação.",
        "Fluxos negativos (o mínimo documentado é zero) ou sem ajuste (marcador de ajuste igual a −1) viram “ausentes”: "
        "{invalid_p1_total} valores de p1 na região. Zeros válidos ficam. Nada é interpolado nem trocado por zero.",
    ]),
    ("h2", "O registro do NOAA-15"),
    ("p", "Ao comparar os satélites, um único registro do NOAA-15 apareceu com peso enorme: 19 de janeiro de 2024, "
          "09:14:30 UTC, perto de 12,5° S e 29,3° W, arquivo poes_n15_20240119_proc.nc, posição {ev_index}. O valor de p1 "
          "era {ev_p1}, enquanto os 20 registros vizinhos (20 segundos antes e depois) têm mediana {ev_nb_p1_median}. Sozinho, "
          "ele respondia por {ev_frac_sum}% de toda a soma de fluxo da sua célula de 5°."),
    ("p", "Um pesquisador da área, ao ver os detalhes, achou provável que fosse uma anomalia e sugeriu duas verificações: "
          "entender o marcador de ajuste e ver se a subida é gradual ou um pico isolado. Opinião de especialista não basta "
          "para apagar dado, então as verificações foram feitas, e foram um pouco além:"),
    ("ul", [
        "**O tipo de ajuste.** O registro tem marcador de ajuste 1, enquanto os 20 vizinhos têm 0. O tipo 0 é o ajuste "
        "normal, com quatro trechos. O tipo 1 é o “plano B” do algoritmo da NOAA: quando o ajuste normal falha, ele usa um "
        "único ponto e uma inclinação padrão (−2,9). Isso não torna o dado inválido por si só, porque o plano B é comum e "
        "documentado.",
        "**Os três canais são um número só.** No registro, p1/p2 = p2/p3 = {ev_spectral_ratio}, exatamente 2 elevado a 2,9. "
        "Ou seja, p2 e p3 são o mesmo valor esticado pela inclinação padrão. “Os três canais subiram juntos” não são três "
        "confirmações, é uma só.",
        "**É um pico de um único registro.** O valor sobe e volta ao nível anterior no registro seguinte; não há subida "
        "nem descida gradual.",
        "**Os detectores direcionais leem zero.** No mesmo registro, os telescópios direcionais do MEPED (canal P6, de 0° e "
        "90°), que nos vizinhos marcam pelo menos {ev_dir_p6_nb_min}, marcam exatamente zero.",
        "**As contagens brutas não fecham.** A NOAA tem, para o mesmo dia, um arquivo de nível 1a com as contagens de cada "
        "detector (baixado só para esta verificação). Nesse registro, o canal acima de 35 MeV contou {rc_p7} partículas por "
        "segundo; nos vizinhos, entre {rc_p7_nb_min} e {rc_p7_nb_max}, e em nenhum outro momento do dia passou de "
        "{rc_p7_second}. Ao mesmo tempo, o canal acima de 16 MeV marcou {rc_p6}, normal. Todo próton acima de 35 MeV também "
        "está acima de 16 MeV, então essas duas contagens não podem descrever as mesmas partículas. Com isso o ajuste "
        "normal fica impossível, sobra o plano B, e o plano B estica o canal inflado até virar o fluxo enorme que está no "
        "arquivo.",
    ]),
    ("p", "Conclusão desta parte: o valor de fluxo desse registro não vem de uma medida coerente; ele não segue da própria "
          "contagem acima de 16 MeV feita no mesmo instante. O que **não** sabemos é a causa: erro de transmissão, da "
          "eletrônica ou outra coisa. O artigo não afirma nenhuma delas."),
    ("h2", "Por que uma regra, e não simplesmente apagar"),
    ("p", "Apagar um ponto porque ele atrapalha, ou porque alguém achou estranho, seria escolher o resultado. Por isso a "
          "exclusão foi feita por uma regra escrita, que vale para todos os registros de todos os satélites, que pode ser "
          "repetida por qualquer pessoa e que não cita o NOAA-15 nem a data. A regra, chamada QC-1, exclui os valores de um "
          "registro quando as três condições abaixo valem ao mesmo tempo."),
    ("ol", [
        "O registro usou o ajuste plano B (marcador 1 ou 2).",
        "Os {qc_k} registros antes e os {qc_k} depois são contínuos no tempo (nenhum buraco maior que {qc_step} s) e todos "
        "usaram o ajuste normal.",
        "O valor é mais de {qc_ratio} vezes maior que a mediana dos vizinhos de antes **e** mais de {qc_ratio} vezes maior "
        "que a mediana dos vizinhos de depois.",
    ]),
    ("p", "Por que cada condição. A segunda garante que estamos num trecho com contagens altas o bastante para o ajuste "
          "normal; ali um salto de cem vezes não pode ser acaso estatístico. Nos dados, nenhum registro de ajuste normal "
          "passa de {qc_regular_max} vezes os seus vizinhos. A terceira precisa de um limite alto porque o próprio plano B "
          "costuma ficar acima dos vizinhos (a inclinação padrão não acompanha o espectro real): nos {qc_iso_fallback} casos "
          "isolados de plano B, a mediana fica entre {qc_fallback_median_min} e {qc_fallback_median_max} vezes, conforme o satélite, e o máximo é {qc_fallback_max} vezes. O limite de "
          "{qc_ratio} fica {qc_ratio_margin} vezes acima desse máximo, para não punir o plano B normal. E “dos dois lados” "
          "separa um pico isolado de uma subida gradual, como a entrada do satélite na Anomalia."),
    ("p", "Os três valores (p1, p2, p3) do registro marcado saem juntos, porque vêm do mesmo ajuste. Nada é cortado, "
          "arredondado ou substituído; o arquivo original continua igual."),
    ("h2", "“Post hoc”: a regra veio depois"),
    ("p", "A regra foi escrita depois de o registro ter sido encontrado. Isso se chama decisão post hoc, e o artigo diz "
          "isso com todas as letras. O risco de uma regra post hoc é ela ter sido ajustada para pegar exatamente o caso "
          "desejado. Para testar isso, a regra foi rodada com {qc_pert_n} variações dos parâmetros. Em {qc_pert_same} delas "
          "o resultado é idêntico: o mesmo único registro. Qualquer limite entre {qc_ratio_lo} e {qc_ratio_hi} vezes dá o "
          "mesmo resultado. O conjunto só muda quando o limite cai para dentro da faixa normal do plano B (com 15 vezes "
          "saem {qc_ratio_15_n} registros, com 10 vezes, {qc_ratio_10_n}) ou quando se tira a exigência de vizinhos com "
          "ajuste normal ({qc_nonb_n} registros, quase todos valores pequenos ao lado de vizinhos quase zero, longe da "
          "Anomalia). As duas fronteiras têm explicação e não dependem do registro do NOAA-15."),
    ("p", "Resultado: entre {qc_records} registros dos cinco satélites, a QC-1 exclui **um**, o do NOAA-15. Todos os outros "
          "valores de plano B ficam."),
    ("h2", "Por que o resultado sem filtro continua aparecendo"),
    ("p", "O artigo mostra sempre as duas versões: com a QC-1 (a principal) e sem filtro (a de sensibilidade). Assim quem "
          "discordar da regra vê o que muda, a decisão fica visível, e a história de como o resultado foi construído "
          "continua rastreável. Uma verificação extra: a exclusão pela regra dá exatamente o mesmo resultado, número por "
          "número, que a omissão daquele registro feita antes à mão, pelo seu identificador."),
    ("p", "A regra também tem limites. Ela só consegue olhar onde os vizinhos tiveram ajuste normal, o que vale para "
          "{qc_region_regular}% dos registros da região. Em regiões de fluxo baixo, perto de buracos nos dados e nas bordas "
          "dos arquivos, um pico isolado não seria detectado, e problemas que duram vários registros estão fora do alcance "
          "dela."),

    ("h1", "Resultados"),
    ("h2", "O mapa de referência"),
    ("p", "A configuração de referência é NOAA-19, canal p1, células de 5°, média, top 10%. O corte fica em {p_cut} (unidades "
          "de fluxo). O footprint tem {p_cells} das {eligible_5} células elegíveis ({p_area} milhões de km²) e o centróide fica "
          "em {p_lat}° de latitude e {p_lon}° de longitude. Todas as células de 5° têm medidas suficientes. Em todas as "
          "variações testadas, a região de alto fluxo continua sobre a América do Sul e o Atlântico Sul; o que muda é o "
          "tamanho e a posição do resumo."),
    ("figure", "paper/figures/fig1_reference.png",
     "Figura 1. (a) Média de p1 em cada célula de 5°, em escala logarítmica; em laranja, as células do top 10%; a cruz é o "
     "centróide. (b) Quantas medidas cada célula tem. (c) O mesmo mapa em células de 2°; as hachuradas têm medidas, mas "
     "menos de 30."),
    ("h2", "O limiar"),
    ("p", "Passar do top 20% para o top 1% move o centróide {thr_shift_5_mean} km (5°, média), principalmente para o sul; "
          "conforme grade e estatística, entre {thr_shift_min} e {thr_shift_max} km. O caminho não é reto: os passos "
          "sucessivos são {thr_step_top20_top10}, {thr_step_top10_top5}, {thr_step_top5_top2} e {thr_step_top2_top1} km, e o "
          "top 1% tem só cinco células."),
    ("p", "A área encolhe {thr_area_ratio_5_mean} vezes. Mas isso não é descoberta: escolher 20% das células e depois 1% "
          "já obriga uma razão de 20 no número de células (a realizada foi {thr_count_ratio_5_mean}); a área só se afasta "
          "disso porque as células têm tamanhos diferentes. O que o limiar ensina é **para onde** as células mais altas "
          "vão, não quanto a área encolhe."),
    ("figure", "paper/figures/fig2_threshold.png",
     "Figura 2. (a) Centróides para cada limiar, em 5° e 2°, com média (cheio) e mediana (vazado). (b) Área selecionada "
     "contra a fração nominal; a linha pontilhada é a área que a própria regra do percentil já impõe."),
    ("h2", "O canal de energia"),
    ("p", "No top 10% (5°, média), p2 e p3 ficam ao sul e a leste de p1: p3 está a {ch_d_p3p1} km de p1, p2 a {ch_d_p2p1} "
          "km, e p3 a {ch_d_p3p2} km de p2. Os footprints se sobrepõem bastante (Jaccard {ch_jac_p3p1} entre p1 e p3). "
          "Considerando as duas grades e as duas estatísticas, a distância entre canais no top 10% vai de {ch_pd_min} a "
          "{ch_pd_max} km; esse intervalo é do top 10%, não o máximo de todos os limiares."),
    ("p", "Para saber se essa diferença é estável, os dias do mês foram reamostrados: sorteiam-se blocos de 1, 3 ou 7 "
          "dias seguidos, com reposição, até completar 31 dias, e o mapa é refeito, 1.000 vezes para cada tamanho de bloco "
          "e com os mesmos dias sorteados para os três canais. O protocolo foi fixado antes das rodadas de produção. A "
          "diferença de latitude entre p3 e p1 manteve o sinal em 95% das rodadas, para os três tamanhos de bloco. Já a "
          "diferença de latitude entre p3 e p2 às vezes troca de sinal. Isso mede estabilidade diante da reamostragem de "
          "dias deste mês; não é um intervalo de confiança da posição física nem prova de significância."),
    ("p", "Olhando o campo inteiro, sem limiar, e normalizando cada canal, a sobreposição entre p1 e p3 é {ch_ov_p3p1} (entre "
          "{ch_ov_min} e {ch_ov_max} nos vários casos), e os centros desses campos inteiros ficam a {ch_cd_p3p1} km. Essa "
          "sobreposição de massa e o Jaccard dos footprints medem coisas diferentes e não devem ser comparados como se "
          "fossem a mesma régua. A lição é que a escolha do resumo importa: o limiar dá peso à cauda alta, e neste caso é ali "
          "que os canais mais diferem."),
    ("figure", "paper/figures/fig3_channel.png",
     "Figura 3. (a, b) Diferenças de latitude e longitude entre canais (segundo menos primeiro); a linha preta é o valor "
     "observado e as barras mostram onde caíram 95% das reamostragens, para blocos de 1, 3 e 7 dias. (c) Distância entre "
     "canais para o footprint (cheio) e para o campo inteiro normalizado (vazado)."),
    ("h2", "A janela de tempo"),
    ("p", "Mapas de um dia são esparsos: em 1º de janeiro, o NOAA-19 tem {tw_d1_covN} células elegíveis de 5° "
          "({tw_d1_covA}% da área). Com três dias, {tw_d3_covA}%; com sete, {tw_d7_covA}%."),
    ("p", "Comparando direto com o mês, o mapa de três dias parece bem diferente: Jaccard {tw_d3_Je} e centróide a "
          "{tw_d3_De} km. Só {tw_d3_Obs}% da área do footprint mensal sequer é elegível no mapa de três dias. Fazendo a "
          "comparação só nas {tw_d3_Sn} células que os dois mapas conseguem avaliar (o “suporte compartilhado”), com o "
          "percentil de cada mapa recalculado ali, eles concordam em {tw_d3_Jc} e {tw_d3_Dc} km. Para um dia a história é "
          "outra: {tw_d1_Je} e {tw_d1_De} km direto, {tw_d1_Jc} e {tw_d1_Dc} km no suporte compartilhado; sobra uma "
          "diferença real. Para sete dias já está tudo próximo ({tw_d7_Je}, {tw_d7_De} km)."),
    ("p", "Na grade de 2°, o Jaccard de três dias é só {tw2_d3_Je}, e o mapa de um dia tem Jaccard {tw2_d1_Je} com "
          "centróide a apenas {tw2_d1_De} km do mensal: distância pequena não garante footprints parecidos. As quatro "
          "semanas ficam a {tw_week_min}–{tw_week_max} km uma da outra."),
    ("p", "O mês contém cada janela, então a concordância com ele é descritiva, não uma validação independente. E a "
          "comparação no suporte compartilhado remove só a diferença de elegibilidade; ela não separa amostragem de "
          "mudança real de um dia para o outro."),
    ("figure", "paper/figures/fig4_temporal.png",
     "Figura 4. (a) Fração da área com células elegíveis em cada janela. (b) Jaccard com o mês: direto (cheio) e no "
     "suporte compartilhado (vazado). (c) Distância de centróides nas mesmas duas comparações."),
    ("h2", "Os satélites"),
    ("p", "Com a QC-1 aplicada, os cinco satélites dão centróides a poucos graus um do outro. A maior distância é "
          "{sat_max_prim} km ({sat_max_pair_prim}); NOAA-18 e NOAA-19 ficam a {sat_n18n19} km; entre os quatro satélites "
          "sem o NOAA-15, o máximo é {sat_max_excl15} km. Com medianas, o máximo é {sat_max_median_prim} km. Nos cinco "
          "limiares, com médias, o máximo fica entre {sat_thr_prim_min} e {sat_thr_prim_max} km; com medianas ele chega a "
          "{sat_med_thr_prim_max} km no top {sat_med_thr_prim_argmax}%."),
    ("p", "Sem o filtro, aquele registro faz a média da sua célula passar de {ev_mean_prim} para {ev_mean_unf}, enquanto a "
          "mediana ({ev_median_unf}) não muda. A célula passa a carregar {ev_weight}% do peso do centróide do NOAA-15, o "
          "centróide do NOAA-15 vai {n15_shift} km para leste e a maior distância entre satélites sobe para {sat_max_unf} km "
          "({sat_max_pair_unf}). Sem o filtro, a distância também cresce quando o limiar aperta, de {sat_thr_unf_min} até "
          "{sat_thr_unf_max} km, porque a célula pesa mais quanto menor o footprint. A participação no footprint muda para "
          "{ev_members_top10_5} registros do NOAA-15. Com medianas, na grade de 5°, os resultados são idênticos com e sem o "
          "filtro em todos os limiares; na grade de 2°, a diferença é de no máximo {sat_median2_maxdiff} km."),
    ("p", "Nenhum desses números é uma diferença calibrada entre satélites. Eles diferem em horário de passagem e histórico "
          "dos detectores. Um fator constante de calibração não moveria um footprint de percentil nem um centróide "
          "normalizado; diferenças de resposta que dependem da energia, sim. As calibrações cruzadas publicadas tratam de "
          "outro canal (fluxo integral acima de 16 MeV), por isso nenhuma foi aplicada."),
    ("figure", "paper/figures/fig5_satellite.png",
     "Figura 5. (a) Centróides dos cinco satélites com a QC-1; a seta leva ao centróide do NOAA-15 sem o filtro. (b) Maior "
     "distância entre os cinco centróides para cada limiar: média com QC-1 (principal), média sem filtro e mediana com "
     "QC-1, em escala logarítmica."),
    ("h2", "O contexto magnético"),
    ("p", "Os arquivos trazem valores do campo magnético calculados por modelo (IGRF), não medidos. No caso principal, "
          "{mag_q25_min}% das amostras dentro do footprint de cada satélite estão abaixo do primeiro quartil regional da "
          "intensidade do campo, e 90% delas cabem nos {mag_cap90_min}–{mag_cap90_max}% mais fracos da região. Isso mostra "
          "que esses footprints ficam onde o campo é fraco; não testa nenhuma fronteira e não prova causa. Uma "
          "classificação antiga que usava hora magnética local foi aposentada, porque o resultado dela mudava conforme a "
          "origem do relógio."),

    ("h1", "O que os dados mostram e o que não podemos concluir"),
    ("h3", "O que os dados mostram"),
    ("ul", [
        "A região de alto fluxo aparece no mesmo setor em todas as configurações testadas.",
        "O limiar move o centróide algumas centenas de km porque redefine o objeto; a queda de área é imposta pela regra.",
        "O canal de energia muda a posição no top 10%, e a direção p3 versus p1 é estável na reamostragem de dias.",
        "Janelas curtas veem menos células; em três dias quase toda a diferença some no suporte compartilhado, em um dia não.",
        "Com a QC-1, no caso de referência, os cinco satélites concordam em {sat_max_prim} km; sem ela, um único registro "
        "leva isso a {sat_max_unf} km.",
        "O registro excluído tem contagens internamente incoerentes, verificadas no arquivo de nível 1a da NOAA.",
    ]),
    ("h3", "O que não podemos concluir"),
    ("ul", [
        "Que a Anomalia se moveu, ou qual é a sua fronteira ou centro “verdadeiros”.",
        "Que um fator é “mais importante” que outro: as faixas testadas de cada fator não são comparáveis.",
        "Que existe um tempo de acumulação ideal e universal.",
        "Que as diferenças entre canais são física da energia, e não efeito do ajuste e dos detectores.",
        "Que os satélites estão calibrados entre si.",
        "Por que o registro do NOAA-15 saiu errado; e que os dados estão livres de outros artefatos.",
        "Qualquer coisa sobre outros meses, estações ou o ciclo solar.",
    ]),

    ("h1", "Limitações"),
    ("ul", [
        "Um mês só, num contexto solar e geomagnético só.",
        "O mês de referência contém cada janela curta; a reamostragem usa só 31 dias e não há estacionariedade garantida.",
        "p1, p2 e p3 vêm das mesmas contagens e do mesmo modelo de ajuste.",
        "O marcador mep_IFC_on = −1 fica sem significado conhecido.",
        "A QC-1 é post hoc e só consegue olhar onde há ajuste normal ({qc_region_regular}% dos registros da região).",
        "Sem calibração cruzada; diferenças de resposta dependentes da energia podem contribuir para diferenças entre satélites.",
        "Os bytes originais de parte dos arquivos usados em etapas antigas não foram registrados; os valores foram "
        "reproduzidos exatamente, os bytes antigos não.",
    ]),

    ("h1", "Conclusão"),
    ("p", "Para os dados de janeiro de 2024, a região de alto fluxo definida por percentil é persistente, mas a sua posição "
          "resumida e o seu tamanho dependem das escolhas de análise em quantidades parecidas com as distâncias que alguém "
          "poderia ser tentado a interpretar fisicamente. O limiar move o centróide {thr_shift_min}–{thr_shift_max} km, o "
          "canal até cerca de {ch_pd_max} km no top 10%, a janela curta muda o que pode ser selecionado, e um único registro "
          "excluído por uma regra declarada separa {sat_max_prim} km de {sat_max_unf} km entre satélites. Relatar a "
          "população do percentil, o suporte elegível, a estatística e as medidas influentes junto com qualquer “posição da "
          "Anomalia” tornaria esses mapas comparáveis entre estudos."),

    ("pagebreak",),
    ("h1", "Depois do artigo: o que eu preciso entender"),
    ("h2", "Os conceitos que importam"),
    ("ol", [
        "**Fluxo diferencial.** Quantas partículas, por segundo, atravessam cada cm², vindas de cada direção (esterradiano), "
        "por unidade de energia (MeV). É uma taxa, não uma contagem total.",
        "**p1, p2, p3 são saídas de um ajuste.** Os detectores contam partículas em faixas largas; a NOAA ajusta uma curva e "
        "lê a curva em 25, 50 e 100 MeV. Por isso os canais não são independentes.",
        "**Célula elegível.** Célula com medidas suficientes (30 no mês). Célula com poucas medidas fica em branco: não é "
        "zero, é “não sei”.",
        "**Percentil.** Ordenando as células elegíveis, o 90º percentil é o valor abaixo do qual estão 90% delas. Top 10% = "
        "o que está acima disso. O percentil é sobre células, não sobre área nem sobre medidas.",
        "**Footprint.** As células acima do corte. É uma construção da análise, não a Anomalia.",
        "**Área esférica.** Uma célula de 5° perto do equador é maior que uma perto do polo; a área vem da geometria da esfera.",
        "**Centróide ponderado por fluxo × área.** O centro de massa do footprint, onde cada célula pesa o fluxo vezes a área. "
        "É um resumo, não o centro físico da Anomalia.",
        "**Jaccard ponderado por área.** Área em comum dividida pela área ocupada pelos dois. 1 = iguais, 0 = nada em comum.",
        "**Comparação direta versus suporte compartilhado.** Direta: os footprints originais. Suporte compartilhado: só as "
        "células que os dois mapas conseguem avaliar, com o percentil refeito ali. A diferença entre as duas mostra quanto "
        "da discordância acompanha a falta de cobertura, sem provar causa.",
        "**Reamostragem em blocos.** Sortear blocos de dias seguidos, com reposição, refazer o mapa muitas vezes e ver o "
        "quanto o resultado varia. Mede estabilidade diante da escolha de dias, não incerteza física.",
        "**Sensibilidade.** Refazer a análise com uma escolha diferente e mostrar o resultado ao lado do principal, sem "
        "escondê-lo.",
        "**Marcador de ajuste e plano B.** 0 = ajuste normal; 1 e 2 = ajustes simplificados quando o normal falha. Plano B "
        "não é dado inválido.",
        "**Regra post hoc.** Regra criada depois de ver o problema. É aceitável se for declarada como tal, geral, testada "
        "contra variações e acompanhada do resultado sem a regra.",
        "**Média versus mediana.** A média sente um único valor gigante; a mediana quase não sente. Foi por isso que só a "
        "média mudou com o registro do NOAA-15.",
        "**Calibração cruzada.** Ajustar a escala de um satélite para bater com outro. Não foi feita; por isso só posição e "
        "forma são comparadas.",
    ]),
    ("h2", "O raciocínio por trás de cada figura"),
    ("ul", [
        "**Figura 1 (referência).** Mostra o objeto: o mapa de média, o footprint do top 10%, o centróide e quantas medidas "
        "cada célula tem. Serve para ver que o footprint é uma construção sobre células elegíveis e que em 2° aparecem "
        "buracos de cobertura.",
        "**Figura 2 (limiar).** Painel (a): o centróide vai para o sul quando o limiar aperta, e não em linha reta. Painel (b): "
        "a área segue a linha que a regra do percentil impõe; por isso a queda de área não é resultado empírico.",
        "**Figura 3 (canal).** Painéis (a, b): a diferença p3 menos p1 tem o mesmo sinal em quase todas as reamostragens. "
        "Painel (c): o resumo muda a resposta; footprint e campo inteiro dão distâncias diferentes.",
        "**Figura 4 (tempo).** Mostra, lado a lado, quanto da área é elegível e como a concordância com o mês muda entre a "
        "comparação direta e a do suporte compartilhado.",
        "**Figura 5 (satélites).** Painel (a): com a QC-1 os centróides se agrupam; a seta mostra para onde o NOAA-15 iria sem "
        "o filtro. Painel (b): sem o filtro, a distância entre satélites dispara quando o limiar aperta; com o filtro, a "
        "média fica entre {sat_thr_prim_min} e {sat_thr_prim_max} km, e a mediana sobe para {sat_med_thr_prim_max} km no top "
        "{sat_med_thr_prim_argmax}%: nenhuma das duas estatísticas dá sempre a menor distância.",
    ]),
    ("h2", "Cada número principal: o que é e o que não é"),
    ("table", ["Número", "O que é", "O que NÃO é"], [
        ["{p_lat}°, {p_lon}°", "Centróide de referência (NOAA-19, p1, 5°, média, top 10%).", "O centro da Anomalia."],
        ["{thr_shift_min}–{thr_shift_max} km", "Quanto o centróide anda do top 20% ao top 1%.", "Movimento da Anomalia."],
        ["{thr_area_ratio_5_mean}×", "Quanto a área encolhe do top 20% ao top 1% (5°, média).", "Descoberta: é quase toda imposta pela regra."],
        ["{ch_d_p3p1} km", "Distância entre os centróides de p3 e p1 no caso de referência.", "Distância física entre populações de prótons."],
        ["{ch_pd_min}–{ch_pd_max} km", "Faixa entre canais no top 10%, nas duas grades e estatísticas.", "O máximo em todos os limiares."],
        ["{tw_d3_De} km e {tw_d3_Dc} km", "Três dias contra o mês: direto e no suporte compartilhado.", "Prova de que a falta de cobertura causou a diferença entre os dois."],
        ["{tw_d1_Dc} km", "Diferença de um dia que sobra no suporte compartilhado.", "Movimento diário da Anomalia."],
        ["{sat_max_prim} km", "Maior distância entre os 5 satélites com a QC-1 (resultado principal).", "Diferença calibrada entre satélites."],
        ["{sat_max_unf} km", "O mesmo sem a QC-1 (sensibilidade).", "O resultado “certo” que foi escondido."],
        ["{sat_max_median_prim} km", "O mesmo com medianas (5°, top 10%); igual com e sem filtro.", "Uma terceira estimativa independente."],
        ["{qc_records} e {qc_excl_global}", "Registros examinados pela QC-1 e registros excluídos.", "Garantia de que os dados não têm outros erros."],
        ["{rc_p7} /s", "Contagem acima de 35 MeV no registro excluído.", "Um fluxo físico de prótons."],
        ["{mag_q25_min}%", "Amostras do footprint abaixo do 1º quartil regional do campo modelado.", "Validação de fronteira."],
    ], ["1.1fr", "1.8fr", "1.5fr"]),
    ("h2", "Glossário curto"),
    ("table", ["Termo", "Significado"], [
        ["SAA / Anomalia do Atlântico Sul", "Região onde o cinturão interno de prótons chega mais baixo."],
        ["SEM-2, MEPED, OMNI", "Instrumento de partículas dos satélites; o MEPED tem telescópios direcionais e detectores omnidirecionais (OMNI)."],
        ["NCEI", "Centro da NOAA que arquiva e distribui os dados."],
        ["Nível 1a / processado", "Contagens brutas por detector / fluxos já convertidos e ajustados."],
        ["Footprint", "Conjunto de células acima do corte de percentil."],
        ["Célula elegível", "Célula com medidas suficientes para entrar no mapa."],
        ["Centróide", "Centro de massa do footprint (peso fluxo × área)."],
        ["Jaccard", "Área em comum ÷ área ocupada pelos dois."],
        ["Suporte compartilhado", "Células que os dois mapas conseguem avaliar."],
        ["Reamostragem em blocos", "Sorteio repetido de blocos de dias para medir estabilidade."],
        ["Plano B (ajuste 1 ou 2)", "Ajuste simplificado quando o normal falha; documentado e válido."],
        ["QC-1", "A regra de qualidade post hoc deste artigo."],
        ["Sem filtro", "A análise sem a QC-1, mostrada como sensibilidade."],
        ["IGRF, Btot", "Modelo do campo magnético da Terra e a intensidade calculada por ele."],
        ["Calibração cruzada", "Ajuste de escala entre instrumentos; não aplicada aqui."],
    ], ["1fr", "2.6fr"]),
    ("h2", "O projeto em 60 segundos"),
    ("p", "Quando se desenha a Anomalia do Atlântico Sul com dados de satélite, a gente escolhe um monte de coisas: tamanho "
          "das células, quantas medidas exigir, média ou mediana, o que é “alto fluxo”, quantos dias juntar, qual energia e "
          "qual satélite. Eu peguei um mês de dados públicos da NOAA, de cinco satélites, e mudei uma escolha de cada vez, "
          "sempre do mesmo jeito. O limiar mexe o centro do mapa em algumas centenas de quilômetros, porque muda o próprio "
          "objeto. A energia mexe até uns {ch_pd_max} km no top 10%. Janelas curtas parecem diferentes em parte porque veem "
          "menos lugares, mas um dia só ainda difere de verdade. Entre satélites, com uma regra de qualidade declarada que "
          "tira um único registro com contagens incoerentes, os cinco concordam em cerca de {sat_max_prim} km no caso de "
          "referência; sem a regra "
          "seriam {sat_max_unf} km, e eu mostro os dois. Tudo é reproduzível por um comando, a partir dos arquivos originais. "
          "O trabalho não descobre a física da Anomalia: ele mostra o quanto o mapa depende de como ele é feito."),
    ("h2", "Perguntas que um professor ou revisor pode fazer"),
    ("ul", [
        "**Por que só um mês?** Porque o objetivo era medir a sensibilidade às escolhas com tudo controlado e reproduzível. "
        "Generalizar para outros meses é trabalho futuro, e o artigo diz isso.",
        "**Por que percentil e não um valor fixo de fluxo?** Um valor fixo dependeria da escala absoluta de cada satélite e "
        "canal, que não está calibrada. O percentil compara forma e posição. O preço é que a área fica imposta pela regra, "
        "e o artigo trata isso explicitamente.",
        "**Vocês não estão só removendo o ponto que estragava o resultado?** A regra foi declarada como post hoc, vale para "
        "todos os registros, foi testada em {qc_pert_n} variações e o resultado sem ela continua publicado ao lado. Além "
        "disso, as contagens brutas do registro são internamente incoerentes, o que não depende de opinião.",
        "**E se houver outros pontos ruins?** Pode haver. A QC-1 só olha onde os vizinhos têm ajuste normal "
        "({qc_region_regular}% dos registros da região) e só pega picos de um registro. Com medianas (grade de 5°), o resultado "
        "entre satélites já era o mesmo, o que ajuda.",
        "**Por que não calibrar os satélites?** As calibrações publicadas são de outro canal (integral acima de 16 MeV). "
        "Para posição e forma de um footprint de percentil, um fator constante não muda nada; por isso só posição e forma "
        "são comparadas.",
        "**A diferença entre canais é física?** Não dá para dizer. Os canais vêm do mesmo ajuste e de detectores com "
        "respostas diferentes; o estudo mostra a diferença e a sua estabilidade, não a causa.",
        "**A reamostragem dá um intervalo de confiança?** Não. Ela mostra a estabilidade diante da escolha de dias deste "
        "mês. Com 31 dias não dá para garantir as condições que um intervalo de confiança exigiria.",
        "**Por que o centróide pesa fluxo × área?** Porque células de 5° têm áreas diferentes conforme a latitude; sem o "
        "peso da área, células pequenas pesariam demais.",
        "**O que é o “suporte compartilhado”?** As células que os dois mapas conseguem avaliar. Comparar ali mostra quanto "
        "da diferença acompanha a falta de cobertura, sem afirmar causa.",
        "**Por que 30 medidas por célula?** É o critério de cobertura usado em todo o projeto desde o início; janelas curtas "
        "usam o mínimo proporcional. Células abaixo disso ficam em branco.",
        "**O campo magnético confirma a Anomalia?** Ele mostra que os footprints ficam onde o campo modelado é fraco. Isso é "
        "descrição, não validação de fronteira.",
        "**Dá para reproduzir?** Sim: um comando refaz tudo a partir dos 155 arquivos, conferindo os hashes, e compara os "
        "resultados byte a byte.",
    ]),
]
