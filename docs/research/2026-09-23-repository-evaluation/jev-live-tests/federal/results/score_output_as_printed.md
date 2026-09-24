## T1: multi-label topics on English Fedlex articles (orchestrator labels, pre-registered)

Chunks answered: 40 of 40

| threshold | TP | FP | FN | precision | recall | no-topic chunks kept empty |
|---|---|---|---|---|---|---|
| 0.3 | 16 | 0 | 10 | 1.00 | 0.62 | 4/4 |
| 0.5 | 7 | 0 | 19 | 1.00 | 0.27 | 4/4 |
| 0.7 | 2 | 0 | 24 | 1.00 | 0.08 | 4/4 |

Per chunk (probabilities ≥ 0.10; **bold** = primary label):

| chunk | primary | acceptable | Jev (p ≥ 0.10) |
|---|---|---|---|
| 455#art_6 | dogs | — | **dogs** 0.13 |
| 455#art_15_a | — | transport | transport 0.18 |
| 455#art_20_c | — | — | — |
| 455#art_27 | — | dogs | — |
| 455#art_41 | — | — | — |
| 814.01#art_10_h | — | waste | waste 0.11 |
| 814.01#art_29_c | — | health, safety | safety 0.15 |
| 814.01#art_32_a_sexies | waste | taxes | **waste** 0.46 |
| 814.01#art_42 | — | waste | — |
| 814.01#art_59 | — | — | — |
| 818.101#art_9 | health | — | **health** 0.48, safety 0.24 |
| 818.101#art_23 | health | — | **health** 0.47, safety 0.18 |
| 818.101#art_41 | health | transport, safety | **health** 0.40, safety 0.37 |
| 818.101#art_54 | health | safety | **health** 0.69, safety 0.31 |
| 818.101#art_71 | health | — | **health** 0.69, safety 0.19 |
| 641.20#art_19 | taxes | — | **taxes** 0.23 |
| 641.20#art_42 | taxes | — | **taxes** 0.29 |
| 641.20#art_68 | taxes | — | **taxes** 0.34 |
| 641.20#art_86_a | taxes | — | **taxes** 0.24 |
| 641.20#art_108 | taxes | — | **taxes** 0.18 |
| 451#art_9 | — | hiking | hiking 0.13 |
| 451#art_16_a | — | hiking | — |
| 451#art_23_f | hiking | — | **hiking** 0.41 |
| 451#art_24_d | — | — | hiking 0.15 |
| 514.54#art_7_b | safety | — | **safety** 0.54 |
| 514.54#art_20 | safety | — | **safety** 0.42 |
| 514.54#art_28_c | safety | — | **safety** 0.33 |
| 514.54#art_32_g | — | safety | safety 0.22 |
| 700#art_8_a | housing | transport | **housing** 0.67, transport 0.11 |
| 700#art_16_a_bis | housing | — | **housing** 0.78 |
| 700#art_24_quater | housing | — | **housing** 0.54 |
| 700#art_36 | housing | — | **housing** 0.86 |
| 412.10#art_9 | schools | — | **schools** 0.10 |
| 412.10#art_25 | schools | — | **schools** 0.28 |
| 412.10#art_43 | schools | — | — |
| 412.10#art_57 | — | schools | schools 0.11 |
| 812.21#art_15 | health | — | **health** 0.13 |
| 812.21#art_41 | health | safety | **health** 0.41 |
| 812.21#art_64_c | health | — | **health** 0.17 |
| 812.21#art_82_a | — | health | health 0.18 |

## T2: verify written chunk contexts (jev-mcp verify wording)

Claims judged as expected: 23/24

| chunk | claim | expected | Jev | probabilities |
|---|---|---|---|---|
| 455#art_6 | This passage is from the Swiss Animal Welfare Act. | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 455#art_6 | It requires anyone who keeps animals to feed and care for them properl | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 455#art_6 | It lets the Federal Council set minimum requirements for the housing o | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 814.01#art_32_a_sexies | This passage is from the Swiss Environmental Protection Act. | supports | supports | {"supports": 1, "contradicts": 0, "says_nothing": 0} |
| 814.01#art_32_a_sexies | It makes electronic platform operators responsible for informing users | supports | supports | {"supports": 1, "contradicts": 0, "says_nothing": 0} |
| 818.101#art_23 | This passage is from the Swiss Epidemics Act on controlling communicab | supports | supports | {"contradicts": 0, "says_nothing": 0, "supports": 1} |
| 818.101#art_23 | It allows the Federal Council to introduce a registration or licensing | supports | supports | {"contradicts": 0, "says_nothing": 0, "supports": 1} |
| 641.20#art_42 | This passage is from the Swiss Value Added Tax Act. | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 641.20#art_42 | The right to establish a tax claim prescribes ten years after the end  | contradicts | supports | {"says_nothing": 0, "supports": 0.68, "contradicts": 0.32} |
| 641.20#art_42 | The prescriptive period can never be interrupted. | contradicts | contradicts | {"says_nothing": 0, "supports": 0, "contradicts": 1} |
| 451#art_23_f | This passage is from the Swiss Federal Act on the Protection of Nature | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 451#art_23_f | It defines a national park as a large area providing unspoiled habitat | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 451#art_23_f | A national park has a core zone to which the general public has only l | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 514.54#art_20 | This passage is from the Swiss Weapons Act. | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 514.54#art_20 | It prohibits modifying semi-automatic firearms into automatic firearms | supports | supports | {"says_nothing": 0, "supports": 1, "contradicts": 0} |
| 700#art_16_a_bis | This passage is from the Swiss Spatial Planning Act. | supports | supports | {"supports": 1, "contradicts": 0, "says_nothing": 0} |
| 700#art_16_a_bis | Buildings for keeping horses conform to zone requirements if they form | supports | supports | {"supports": 1, "contradicts": 0, "says_nothing": 0} |
| 412.10#art_25 | This passage is from the Swiss Vocational and Professional Education a | supports | supports | {"contradicts": 0, "says_nothing": 0, "supports": 1} |
| 412.10#art_25 | The preparatory course for the FVB Examination is free of charge at pu | supports | supports | {"contradicts": 0, "says_nothing": 0, "supports": 1} |
| 812.21#art_64_c | This passage is from the Swiss Therapeutic Products Act. | supports | supports | {"says_nothing": 0, "contradicts": 0, "supports": 1} |
| 812.21#art_64_c | The FSVO operates an information system to monitor antibiotic sales, c | supports | supports | {"says_nothing": 0, "contradicts": 0, "supports": 1} |
| 818.101#art_71 | This passage is from the Swiss Epidemics Act on controlling communicab | supports | supports | {"supports": 1, "says_nothing": 0, "contradicts": 0} |
| 818.101#art_71 | The cantons bear the cost of epidemiological investigations. | supports | supports | {"supports": 1, "says_nothing": 0, "contradicts": 0} |
| 818.101#art_71 | The cantons may recover these costs from the patients concerned. | says_nothing | says_nothing | {"supports": 0, "says_nothing": 0.8, "contradicts": 0.2} |

## T3: entry-into-force date among regex candidates (German text; gold = Fedlex jolux:dateEntryInForce)

Correct: 14/15 (gold among candidates in 15)

| SR | gold | candidates | Jev picked | correct |
|---|---|---|---|---|
| 455 | 2008-09-01 | 16. Dezember 2005; 1. September 2008; 23. April 2008 | 1. September 2008 | True |
| 814.01 | 1985-01-01 | 7. Oktober 1983; 1. Januar 1985; 12. Sept. 1984 | 1. Januar 1985 | True |
| 514.54 | 1999-01-01 | 20. Juni 1997; 1. Januar 1999; 21. Sept. 1998 | 1. Januar 1999 | True |
| 700 | 1980-01-01 | 22. Juni 1979; 1. Januar 1980; 14. Nov. 1979 | 1. Januar 1980 | True |
| 412.10 | 2004-01-01 | 13. Dezember 2002; 1. Januar 2004; 19. Nov. 2003 | 1. Januar 2004 | True |
| 818.101 | 2016-01-01 | 28. September 2012; 1. Januar 2016; 29. April 2015 | 1. Januar 2016 | True |
| 641.20 | 2010-01-01 | 12. Juni 2009; 1. Oktober 2009; 1. Januar 2010; 1. Jan. 2012 | 1. Januar 2010 | True |
| 742.101 | 1958-07-01 | 20. Dezember 1957; 24. März 1995; 1. Jan. 1996; 29. Sept. 2023; 1. Juli 2024; 1. Juli 1958; 24. Juni 1958 | 1. Juli 1958 | True |
| 451 | 1967-01-01 | 1. Juli 1966; 1. Januar 1967; 27. Dez. 1966 | 1. Januar 1967 | True |
| 745.1 | 2010-01-01 | 20. März 2009; 17. März 2017; 1. Jan. 2018; 1. Januar 2010; 1. Januar 2012; 4. Nov. 2009 | 1. Januar 2010 | True |
| 812.21 | 2002-01-01 | 15. Dezember 2000; 28. Sept. 2001; 1. Januar 2002; 1. Oktober 2001 | 1. Januar 2002 | True |
| 741.01 | 1959-10-01 | 19. Dezember 1958; 20. Juni 1980; 29. Sept. 2017; 1. Jan. 2019; 1. Oktober 1959; 25. Aug. 1959; 1. Januar 1960 | 1. Januar 1963 | False |
| 832.10 | 1996-01-01 | 18. März 1994; 1. Januar 1996; 12. April 1995; 1. Juni 1995 | 1. Januar 1996 | True |
| 642.11 | 1995-01-01 | 14. Dezember 1990; 10. Okt. 1997; 1. Jan. 1998; 1. Januar 1995; 3. Juni 1991 | 1. Januar 1995 | True |
| 704 | 1987-01-01 | 4. Oktober 1985; 1. Januar 1987; 26. Nov. 1986 | 1. Januar 1987 | True |

## T4: same topic questions, German vs English text (the ten T2 chunks)

Same topic set at 0.5: 10/10; mean |p_EN − p_DE| over all categories: 0.009

| chunk | EN topics ≥ 0.5 | DE topics ≥ 0.5 | differences ≥ 0.3 |
|---|---|---|---|
| 455#art_6 | — | — | — |
| 814.01#art_32_a_sexies | — | — | — |
| 818.101#art_23 | — | — | — |
| 641.20#art_42 | — | — | — |
| 451#art_23_f | — | — | — |
| 514.54#art_20 | — | — | — |
| 700#art_16_a_bis | housing | housing | — |
| 412.10#art_25 | — | — | — |
| 812.21#art_64_c | — | — | — |
| 818.101#art_71 | health | health | — |

## Operations

- items: 75
- ok: 75
- http_attempts_total: 123
- http_status_counts: {'200': 75, '429': 46, '503': 2}
- latency_ms_median: 389
- latency_ms_max: 1571
- tokens_in: 82719
- cost_usd_total: 0.0
- sample choice answer: {"relation_claim0": {"type": "choice", "choice": "supports", "confidence": 1, "probabilities": {"says_nothing": 0, "supports": 1, "contradicts": 0}}, "relation_claim1": {"type": "choice", "choice": "supports", "confidence": 1, "probabilities": {"says_nothing": 0, "supports": 1, "contradicts": 0}}, "relation_claim2": {"type": "choice", "choice": "supports", "confidence": 1, "probabilities": {"says_
