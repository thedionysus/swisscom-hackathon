UA="Mozilla/5.0 swiss-grounding-check"; B=https://mcp.opencaselaw.ch/api
curl -sL -A "$UA" "$B/openapi.json" -o <scratchpad>/sgchk/ocl.json -w "openapi %{http_code} %{size_download}B\n"
python3 -c "
import json;d=json.load(open('<scratchpad>/sgchk/ocl.json'));p=[k for k in d.get('paths',{}) if 'court' in k.lower()];print('court paths:',p)"
curl -sL -A "$UA" "$B/courts" -o <scratchpad>/sgchk/courts.json -w "courts %{http_code} %{content_type} %{size_download}B\n"; head -c 600 <scratchpad>/sgchk/courts.json; echo
