# Moto Atlas

Portal independente de cultura motociclística em **português e inglês**. Marcas e história, modalidades de corrida, rally, clubes, programas de viagem e certificação, agenda e notícias. Inclui a Iron Butt Association e seus requisitos oficiais, H.O.G. Ride 365 e passeios solidários.

## Conteúdo e idiomas

15 marcas, 18 famílias e formatos de competição, 7 redes ou associações, 4 programas e uma agenda inicial com datas oficiais e encontros aguardando confirmação. A agenda permite pesquisar encontros e rallies em 25 países e filtrar tipo e período. Idioma e favoritos ficam no navegador. A interface e o catálogo editorial são bilíngues; manchetes e nomes próprios permanecem no original, com filtros por idioma.

As datas das marcas distinguem a fundação de empresas, o início da produção de motos e mudanças históricas. Não há ranking de popularidade. Textos resumidos e independentes remetem às referências originais, sem reproduzir artigos completos. A seleção de modalidades é ampla, mas federações regionais podem adotar outros formatos.

## Rodar e verificar

Requer Python 3.11+. Sem dependências de pacote ou chaves privadas.

```sh
python -m unittest discover -s tests
python scripts/collect.py
python -m http.server 5175 --bind 127.0.0.1
```

Abra http://127.0.0.1:5175. O catálogo está em `catalog.json`; a edição automática está em `snapshot.json`. HTML, CSS e JavaScript são estáticos.

## Atualização e fontes

O GitHub Actions consulta fontes a cada **6 horas** e publica no GitHub Pages. A página busca a edição publicada a cada **15 minutos**, enquanto aberta, e oferece atualização manual. Isso não executa buscas externas a cada clique. Agendamentos do GitHub podem atrasar e dependem de Actions estar ativo.

A descoberta de notícias utiliza 12 consultas temáticas RSS em português e inglês e mais 25 consultas sobre encontros e rallies por país, com temas de mercado, competições, eventos e comunidades. O agregador aponta para veículos; as manchetes não são transformadas em eventos confirmados. A atribuição de país em notícias indica o escopo da pesquisa, não comprova a localização do evento. O portal não varre literalmente todos os sites da internet.

O coletor também verifica páginas públicas de fabricantes, clubes, programas e organizadores. Eventos novos só são extraídos de dados estruturados Event em páginas cadastradas de organizadores, com datas válidas e links no mesmo domínio. Eles são identificados separadamente; mudanças exigem conferência no organizador. Algumas páginas não fornecem dados estruturados e continuam como referências editoriais. Uma consulta bem-sucedida não significa que uma data editorial foi reconfirmada.

Falhas individuais mantêm os dados anteriores com suas datas. Notícias antigas deixam de aparecer após 180 dias; eventos passados passam à seção correspondente. Fontes que bloqueiam acesso ou exigem JavaScript podem ficar indisponíveis. Não são contornados bloqueios, autenticação ou páginas privadas. Para ampliar a cobertura, cadastre fontes e consultas públicas em `scripts/collect.py` e eventos editoriais em `catalog.json`.

## Publicar

Em Settings → Pages, escolha **GitHub Actions**. O workflow faz verificação, coleta e publicação em push, execução manual e agendamento. Só os cinco arquivos públicos do portal entram no site; nenhuma credencial é necessária.

## Participação

Moto Atlas não realiza inscrição, venda, associação ou certificação. Regras, datas, preços, acesso e adequação devem ser confirmados nas fontes oficiais. Programas de longa distância exigem descanso, respeito às leis e documentação; interrompa uma viagem diante de fadiga. O portal não é patrocinado pelas organizações citadas.

Conteúdo editorial revisado em 03/10/2026. Fontes estão visíveis no site.
