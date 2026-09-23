S=<scratchpad>
cat > $S/cities_s2_links.txt <<'E'
Zürich|https://www.stadt-zuerich.ch/portal/de/index/politik_u_recht/stadtrecht/systematische_rechtssammlung.html
Genève|https://www.geneve.ch/fr/autorites-administration/conseil-municipal/reglementation-municipale
Lausanne|https://www.lausanne.ch/officiel/statut-et-reglements/reglements-municipaux.html
Bern|https://www.bern.ch/politik-und-verwaltung/stadtrecht/systematische-rechtssammlung-bsr
Lugano|https://www.lugano.ch/amministrazione-servizi/regolamenti.html
Thun|https://www.thun.ch/politik-verwaltung/rechtssammlung/systematische-rechtssammlung-srt.html
La Chaux-de-Fonds|https://www.chaux-de-fonds.ch/autorites/conseil-general/reglements-communaux
Schaffhausen|https://www.stadt-schaffhausen.ch/politik/rechtssammlung.html
Vernier|https://www.vernier.ch/politique-et-administration/reglements-et-arretes
Neuchâtel|https://www.neuchatelville.ch/autorites-et-administration/conseil-general/reglements-communaux
E
UA="Mozilla/5.0 swiss-grounding-check"
while IFS='|' read -r city url; do printf "%-18s " "$city"; curl -sL -g --max-time 25 -A "$UA" -o <scratchpad>/sgchk/city.html -w "%{http_code} %{size_download}B -> %{url_effective}" "$url"; t=$(grep -o -i '<title[^>]*>[^<]*' <scratchpad>/sgchk/city.html | head -1 | sed 's/<title[^>]*>//' | tr -s ' \n' ' ' | cut -c1-50); echo " | $t"; done < $S/cities_s2_links.txt
echo "== existing sources in the repo"
cd <repo> && for f in stadt_zuerich ge_ville; do echo "-- $f.yaml"; grep -E "^(id|name|base_url|default_extent_id|authority|fetch_strategy)|start_paths|path_allowlist|urls" -A3 src/swiss_grounding/registry/sources/$f.yaml | head -24; done
