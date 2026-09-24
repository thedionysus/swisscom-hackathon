# typesafe-mcp (evaluate v0.4.4) live test

## E1 equivalence (single calls, state identical to M1)

- ge_ville#314 (fr, content): tool isError=None, direct HTTP 200; max|dp| tool vs direct-now 0.010000000000000002; direct-now vs M1 0.009999999999999998; tool vs M1 0.019999999999999997
  - tool response keys: ['answers', 'model', 'provider_metadata', 'usage']; model typesafe-ai/jev
- zh_ch#814 (de, content): tool isError=None, direct HTTP 200; max|dp| tool vs direct-now 0.030000000000000006; direct-now vs M1 0.01999999999999999; tool vs M1 0.030000000000000006
  - tool response keys: ['answers', 'model', 'provider_metadata', 'usage']; model typesafe-ai/jev
- zh_ch#843 (de, junk): tool isError=None, direct HTTP 200; max|dp| tool vs direct-now 0.01; direct-now vs M1 0.020000000000000018; tool vs M1 0.020000000000000018
  - tool response keys: ['answers', 'model', 'provider_metadata', 'usage']; model typesafe-ai/jev
- E1 HTTP (tool + direct): 6 HTTP requests for 6 distinct bodies; statuses {200: 6}; peak concurrency 1; bodies re-sent 0 (waits before re-send, s: []); bodies whose last attempt failed 0; median upstream latency of 200s 371.0 ms; retry-after values seen []
  - paths ['/typesafe/v1/systemone']; request header names ['accept', 'accept-encoding', 'authorization', 'connection', 'content-length', 'content-type', 'host', 'user-agent', 'x-test']; user-agents ['Go-http-client/1.1', 'python-httpx/0.28.1']

## E2 items batch (75 chunks, M1 questions verbatim)

- tool isError None; results 36; errors 39; wall 45.7 s; meta null
- error messages (first 5): {"ge_ville#122": "evaluate: 429 Too Many Requests: {\"error\":{\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"param\":{\"error\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"statusCode\":429,\"name\":\"RateLimitExceededError\",\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\"}},\"providerMetadata\":{\"gateway\":{\"routing\":{\"originalModelId\":\"typesafe-ai/jev\",\"resolvedProvider\":\"typesafe-ai\",\"fallbacksAvailable\":[],\"canonicalSlug\":\"typesafe-ai/jev\",\"modelAttemptCount\":1,\"modelAttempts\":[{\"canonicalSlug\":\"typesafe-ai/jev\",\"success\":false,\"providerAttemptCount\":0,\"providerAttempts\":[]}],\"totalProviderAttemptCount\":0},\"generationId\":\"gen_01M37K1100EB5N6D17HMZTNNVH\"}}}", "ge_ville#124": "evaluate: 429 Too Many Requests: {\"error\":{\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"param\":{\"error\":\"The upstream provider is currently experiencing high demand
- E2 HTTP: 214 HTTP requests for 75 distinct bodies; statuses {200: 36, 503: 1, 429: 177}; peak concurrency 8; bodies re-sent 49 (waits before re-send, s: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]…); bodies whose last attempt failed 39; median upstream latency of 200s 388.5 ms; retry-after values seen ['2', '4', '42', '43', '47', '49', '5', '51', '55', '57', '58', '6', '60']
  - paths ['/typesafe/v1/systemone']; request header names ['accept-encoding', 'authorization', 'content-length', 'content-type', 'host', 'user-agent']; user-agents ['Go-http-client/1.1']
- |dp| vs M1 over 396 values: mean 0.004, max 0.13, share > 0.10: 0.00
  - R1 all (n=36): TP 4 FP 9 FN 1 | precision 0.31 recall 0.80
  - R1 random (n=28): TP 3 FP 6 FN 0 | precision 0.33 recall 1.00
  - R1 targeted (n=8): TP 1 FP 3 FN 1 | precision 0.25 recall 0.50
  - R1 German (n=24): TP 2 FP 9 FN 1 | precision 0.18 recall 0.67
  - R1 French (n=12): TP 2 FP 0 FN 0 | precision 1.00 recall 1.00
  - R1 agreed content (exploratory) (n=21): TP 4 FP 3 FN 1 | precision 0.57 recall 0.80
  - R1 agreed junk (exploratory) (n=15): TP 0 FP 6 FN 0 | precision 0.00 recall —
  - R2 all (n=36): TP 5 FP 12 FN 0 | precision 0.29 recall 1.00
  - R2 random (n=28): TP 3 FP 8 FN 0 | precision 0.27 recall 1.00
  - R2 targeted (n=8): TP 2 FP 4 FN 0 | precision 0.33 recall 1.00
  - R2 German (n=24): TP 3 FP 12 FN 0 | precision 0.20 recall 1.00
  - R2 French (n=12): TP 2 FP 0 FN 0 | precision 1.00 recall 1.00
  - R2 agreed content (exploratory) (n=21): TP 5 FP 4 FN 0 | precision 0.56 recall 1.00
  - R2 agreed junk (exploratory) (n=15): TP 0 FP 8 FN 0 | precision 0.00 recall —
  - M1 on the same 36 chunks, R1 all: TP 3 FP 7 FN 2 | precision 0.30 recall 0.60

## E3 guidance design (one choice with none_of_these)

- tool isError None; results 27; errors 48; wall 52.6 s; meta null
- error messages (first 5): {"ge_ville#114": "evaluate: 429 Too Many Requests: {\"error\":{\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"param\":{\"error\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"statusCode\":429,\"name\":\"RateLimitExceededError\",\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\"}},\"providerMetadata\":{\"gateway\":{\"routing\":{\"originalModelId\":\"typesafe-ai/jev\",\"resolvedProvider\":\"typesafe-ai\",\"fallbacksAvailable\":[],\"canonicalSlug\":\"typesafe-ai/jev\",\"modelAttemptCount\":1,\"modelAttempts\":[{\"canonicalSlug\":\"typesafe-ai/jev\",\"success\":false,\"providerAttemptCount\":0,\"providerAttempts\":[]}],\"totalProviderAttemptCount\":0},\"generationId\":\"gen_01M37K2M19BYAD5J0TEWT54RJP\"}}}", "ge_ville#122": "evaluate: 429 Too Many Requests: {\"error\":{\"message\":\"The upstream provider is currently experiencing high demand. Please retry shortly.\",\"type\":\"rate_limit_exceeded\",\"param\":{\"error\":\"The upstream provider is currently experiencing high demand
- E3 HTTP: 240 HTTP requests for 75 distinct bodies; statuses {429: 211, 200: 27, 503: 2}; peak concurrency 7; bodies re-sent 61 (waits before re-send, s: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]…); bodies whose last attempt failed 48; median upstream latency of 200s 369 ms; retry-after values seen ['10', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30', '31', '32', '33', '34', '35', '36', '38', '39', '40', '41', '42', '43', '44', '45', '46', '47', '48', '49', '50', '51', '52', '53', '54', '55', '56', '57', '60']
  - paths ['/typesafe/v1/systemone']; request header names ['accept-encoding', 'authorization', 'content-length', 'content-type', 'host', 'user-agent']; user-agents ['Go-http-client/1.1']
  - all (n=27): TP 3 FP 2 FN 0 | precision 0.60 recall 1.00
  - random (n=23): TP 3 FP 2 FN 0 | precision 0.60 recall 1.00
  - targeted (n=4): TP 0 FP 0 FN 0 | precision — recall —
  - German (n=17): TP 0 FP 2 FN 0 | precision 0.00 recall —
  - French (n=10): TP 3 FP 0 FN 0 | precision 1.00 recall 1.00
  - agreed content (exploratory) (n=14): TP 3 FP 0 FN 0 | precision 1.00 recall 1.00
  - agreed junk (exploratory) (n=13): TP 0 FP 2 FN 0 | precision 0.00 recall —
- agreed-junk chunks answered none_of_these: 9/13; agreed-content chunks answered none_of_these: 10/14
- descriptive, drop predictions with confidence < 0.3: all TP 3 FP 2 FN 0 | precision 0.60 recall 1.00
- descriptive, drop predictions with confidence < 0.5: all TP 3 FP 2 FN 0 | precision 0.60 recall 1.00
- choices: {'none_of_these': 19, 'housing': 1, 'waste': 2, 'transport': 1, 'schools': 1, 'parking': 1, 'dogs': 1, 'hiking': 1}