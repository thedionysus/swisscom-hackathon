# Re-test: Jev topic question on a fresh sample

Chunks 75; labelled by both 75; structured answers 75; plain answers 75; baseline no

- Labeller agreement: junk κ = 1.00; primary topics κ = 0.78
- Gold: 11 positive pairs, 704 negative, 35 excluded; chunks with >= 2 gold topics: 0; agreed junk 35 of 75

Scored chunks (answered by every design): 75

| prediction | subset | TP | FP | FN | precision (95% CI) | recall (95% CI) |
|---|---|---|---|---|---|---|
| structured | all (n=75) | 10 | 1 | 1 | 0.91 (0.62–0.98) | 0.91 (0.62–0.98) |
| structured | agreed content (n=40) | 10 | 0 | 1 | 1.00 (0.72–1.00) | 0.91 (0.62–0.98) |
| structured | agreed junk (n=35) | 0 | 1 | 0 | 0.00 (0.00–0.79) | — |
| structured | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| structured | language de (n=49) | 4 | 1 | 1 | 0.80 (0.38–0.96) | 0.80 (0.38–0.96) |
| structured | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |
| structured-floor | all (n=75) | 9 | 1 | 2 | 0.90 (0.60–0.98) | 0.82 (0.52–0.95) |
| structured-floor | agreed content (n=40) | 9 | 0 | 2 | 1.00 (0.70–1.00) | 0.82 (0.52–0.95) |
| structured-floor | agreed junk (n=35) | 0 | 1 | 0 | 0.00 (0.00–0.79) | — |
| structured-floor | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| structured-floor | language de (n=49) | 3 | 1 | 2 | 0.75 (0.30–0.95) | 0.60 (0.23–0.88) |
| structured-floor | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |
| structured-tie | all (n=75) | 10 | 1 | 1 | 0.91 (0.62–0.98) | 0.91 (0.62–0.98) |
| structured-tie | agreed content (n=40) | 10 | 0 | 1 | 1.00 (0.72–1.00) | 0.91 (0.62–0.98) |
| structured-tie | agreed junk (n=35) | 0 | 1 | 0 | 0.00 (0.00–0.79) | — |
| structured-tie | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| structured-tie | language de (n=49) | 4 | 1 | 1 | 0.80 (0.38–0.96) | 0.80 (0.38–0.96) |
| structured-tie | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |
| plain | all (n=75) | 10 | 3 | 1 | 0.77 (0.50–0.92) | 0.91 (0.62–0.98) |
| plain | agreed content (n=40) | 10 | 0 | 1 | 1.00 (0.72–1.00) | 0.91 (0.62–0.98) |
| plain | agreed junk (n=35) | 0 | 3 | 0 | 0.00 (0.00–0.56) | — |
| plain | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| plain | language de (n=49) | 4 | 3 | 1 | 0.57 (0.25–0.84) | 0.80 (0.38–0.96) |
| plain | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |
| plain-floor | all (n=75) | 8 | 1 | 3 | 0.89 (0.56–0.98) | 0.73 (0.43–0.90) |
| plain-floor | agreed content (n=40) | 8 | 0 | 3 | 1.00 (0.68–1.00) | 0.73 (0.43–0.90) |
| plain-floor | agreed junk (n=35) | 0 | 1 | 0 | 0.00 (0.00–0.79) | — |
| plain-floor | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| plain-floor | language de (n=49) | 2 | 1 | 3 | 0.67 (0.21–0.94) | 0.40 (0.12–0.77) |
| plain-floor | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |
| plain-tie | all (n=75) | 10 | 3 | 1 | 0.77 (0.50–0.92) | 0.91 (0.62–0.98) |
| plain-tie | agreed content (n=40) | 10 | 0 | 1 | 1.00 (0.72–1.00) | 0.91 (0.62–0.98) |
| plain-tie | agreed junk (n=35) | 0 | 3 | 0 | 0.00 (0.00–0.56) | — |
| plain-tie | >= 2 gold topics (n=0) | 0 | 0 | 0 | — | — |
| plain-tie | language de (n=49) | 4 | 3 | 1 | 0.57 (0.25–0.84) | 0.80 (0.38–0.96) |
| plain-tie | language fr (n=26) | 6 | 0 | 0 | 1.00 (0.61–1.00) | 1.00 (0.61–1.00) |

- structured: none_of_these on agreed junk 25/35; AUC 0.999 (11 positive, 704 negative pairs)
- plain: none_of_these on agreed junk 23/35; AUC 0.998 (11 positive, 704 negative pairs)
- structured vs plain per chunk: fewer errors 2, more 0, equal 73; sign test p = 0.5000