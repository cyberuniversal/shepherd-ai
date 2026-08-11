# MultiUAV Resource Results

## Scope

These resource outcomes are secondary and exploratory. They do not support confirmatory claims, and no null-hypothesis tests were run. The three hardware repetitions are reported separately and are not pooled.

The analysis covers two immutable Qwen2.5 checkpoints, four methods, 30 source-task clusters, five dependent variants per cluster, and three repetitions. Within each repetition, model, and method, the first aggregate is the arithmetic mean across the five variants in a source-task cluster. Descriptive statistics summarize the resulting 30 cluster means.

Registered paired differences are M3 minus M1 and M3 minus M4. Each interval is a 95% percentile source-cluster bootstrap interval from 10,000 fixed-seed draws. A positive resource difference means M3 used more of the named resource; a negative difference means M3 used less.

## Boundaries

GPU-board energy is not workstation, simulator, network, or UAV energy. Peak memory is an observed process or board maximum, not a baseline-subtracted allocation. Results are specific to the admitted RTX 3090 runs. M4 is matched to M3 only by model-call count, not by tokens, latency, memory, or energy.

A post-admission diagnostic command exposed one row's nested request and raw model output before aggregate analysis. The campaign and score-blind admission were already immutable; no aggregate, paired comparison, or hidden label was exposed. The deviation is preserved in `datasets/multiuav_plat/resource_analysis_protocol_deviation_v1.json` and must be disclosed.

## Registered Contrasts

Exact descriptive results are in `outputs/tables/multiuav_resource_descriptive_v1.csv`; exact paired estimates and intervals are in `outputs/tables/multiuav_resource_contrasts_v1.csv`.

| Contrast | Repetition | Model | Metric | Difference | 95% interval |
|---|---:|---|---|---:|---:|
| M3 minus M1 | 1 | Qwen2.5-3B | Duration (s) | 9.4949 | [8.3593, 10.7066] |
| M3 minus M1 | 1 | Qwen2.5-3B | Input tokens | 3297.6800 | [2856.9302, 3778.4883] |
| M3 minus M1 | 1 | Qwen2.5-3B | Output tokens | 260.6533 | [223.5598, 299.8800] |
| M3 minus M1 | 1 | Qwen2.5-3B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 1 | Qwen2.5-3B | Process RAM peak (bytes) | 2.8157e+07 | [2.4261e+07, 3.1996e+07] |
| M3 minus M1 | 1 | Qwen2.5-3B | Board VRAM peak (bytes) | 1.9268e+09 | [1.8644e+09, 1.9866e+09] |
| M3 minus M1 | 1 | Qwen2.5-3B | Process VRAM peak (bytes) | 1.9268e+09 | [1.8644e+09, 1.9866e+09] |
| M3 minus M1 | 1 | Qwen2.5-3B | GPU-board energy (J) | 1681.2962 | [1479.8032, 1897.8546] |
| M3 minus M1 | 1 | Qwen2.5-7B | Duration (s) | -6.2278 | [-9.0561, -3.3822] |
| M3 minus M1 | 1 | Qwen2.5-7B | Input tokens | 3155.9733 | [2720.1910, 3628.0193] |
| M3 minus M1 | 1 | Qwen2.5-7B | Output tokens | -125.7000 | [-163.3475, -87.9963] |
| M3 minus M1 | 1 | Qwen2.5-7B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 1 | Qwen2.5-7B | Process RAM peak (bytes) | -2.8029e+07 | [-2.9954e+07, -2.6193e+07] |
| M3 minus M1 | 1 | Qwen2.5-7B | Board VRAM peak (bytes) | 1.7682e+09 | [1.7226e+09, 1.8094e+09] |
| M3 minus M1 | 1 | Qwen2.5-7B | Process VRAM peak (bytes) | 1.7682e+09 | [1.7226e+09, 1.8094e+09] |
| M3 minus M1 | 1 | Qwen2.5-7B | GPU-board energy (J) | -1153.2262 | [-1652.4520, -649.6979] |
| M3 minus M1 | 2 | Qwen2.5-3B | Duration (s) | 8.8561 | [7.7755, 10.0223] |
| M3 minus M1 | 2 | Qwen2.5-3B | Input tokens | 3297.6800 | [2856.9302, 3778.4883] |
| M3 minus M1 | 2 | Qwen2.5-3B | Output tokens | 260.6533 | [223.5598, 299.8800] |
| M3 minus M1 | 2 | Qwen2.5-3B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 2 | Qwen2.5-3B | Process RAM peak (bytes) | 3.7241e+06 | [1.0081e+06, 6.3966e+06] |
| M3 minus M1 | 2 | Qwen2.5-3B | Board VRAM peak (bytes) | 1.5542e+09 | [1.5070e+09, 1.6010e+09] |
| M3 minus M1 | 2 | Qwen2.5-3B | Process VRAM peak (bytes) | 1.5542e+09 | [1.5070e+09, 1.6010e+09] |
| M3 minus M1 | 2 | Qwen2.5-3B | GPU-board energy (J) | 1565.2683 | [1373.0487, 1769.1356] |
| M3 minus M1 | 2 | Qwen2.5-7B | Duration (s) | -6.7008 | [-9.4013, -4.0068] |
| M3 minus M1 | 2 | Qwen2.5-7B | Input tokens | 3155.9733 | [2720.1910, 3628.0193] |
| M3 minus M1 | 2 | Qwen2.5-7B | Output tokens | -125.7000 | [-163.3475, -87.9963] |
| M3 minus M1 | 2 | Qwen2.5-7B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 2 | Qwen2.5-7B | Process RAM peak (bytes) | -2.9659e+07 | [-3.1860e+07, -2.7390e+07] |
| M3 minus M1 | 2 | Qwen2.5-7B | Board VRAM peak (bytes) | 2.6509e+09 | [2.5498e+09, 2.7593e+09] |
| M3 minus M1 | 2 | Qwen2.5-7B | Process VRAM peak (bytes) | 2.6509e+09 | [2.5498e+09, 2.7593e+09] |
| M3 minus M1 | 2 | Qwen2.5-7B | GPU-board energy (J) | -1205.8638 | [-1689.7148, -723.9200] |
| M3 minus M1 | 3 | Qwen2.5-3B | Duration (s) | 9.0426 | [7.9764, 10.1905] |
| M3 minus M1 | 3 | Qwen2.5-3B | Input tokens | 3297.6800 | [2856.9302, 3778.4883] |
| M3 minus M1 | 3 | Qwen2.5-3B | Output tokens | 260.6533 | [223.5598, 299.8800] |
| M3 minus M1 | 3 | Qwen2.5-3B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 3 | Qwen2.5-3B | Process RAM peak (bytes) | 6.3678e+06 | [3.9475e+06, 8.7898e+06] |
| M3 minus M1 | 3 | Qwen2.5-3B | Board VRAM peak (bytes) | 4.0967e+08 | [3.6780e+08, 4.5106e+08] |
| M3 minus M1 | 3 | Qwen2.5-3B | Process VRAM peak (bytes) | 4.0967e+08 | [3.6780e+08, 4.5106e+08] |
| M3 minus M1 | 3 | Qwen2.5-3B | GPU-board energy (J) | 1598.0213 | [1393.5024, 1815.1489] |
| M3 minus M1 | 3 | Qwen2.5-7B | Duration (s) | -6.8180 | [-9.5111, -4.0391] |
| M3 minus M1 | 3 | Qwen2.5-7B | Input tokens | 3155.9733 | [2720.1910, 3628.0193] |
| M3 minus M1 | 3 | Qwen2.5-7B | Output tokens | -125.7000 | [-163.3475, -87.9963] |
| M3 minus M1 | 3 | Qwen2.5-7B | Model calls | 1.0000 | [1.0000, 1.0000] |
| M3 minus M1 | 3 | Qwen2.5-7B | Process RAM peak (bytes) | -3.5250e+06 | [-5.2392e+06, -1.9364e+06] |
| M3 minus M1 | 3 | Qwen2.5-7B | Board VRAM peak (bytes) | 1.3092e+09 | [1.2660e+09, 1.3468e+09] |
| M3 minus M1 | 3 | Qwen2.5-7B | Process VRAM peak (bytes) | 1.3092e+09 | [1.2660e+09, 1.3468e+09] |
| M3 minus M1 | 3 | Qwen2.5-7B | GPU-board energy (J) | -1244.8911 | [-1735.6559, -746.9499] |
| M3 minus M4 | 1 | Qwen2.5-3B | Duration (s) | 1.7635 | [0.4905, 3.0984] |
| M3 minus M4 | 1 | Qwen2.5-3B | Input tokens | 179.5867 | [139.4862, 218.6002] |
| M3 minus M4 | 1 | Qwen2.5-3B | Output tokens | 21.6800 | [-22.9217, 68.7735] |
| M3 minus M4 | 1 | Qwen2.5-3B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 1 | Qwen2.5-3B | Process RAM peak (bytes) | 2.2652e+07 | [2.1084e+07, 2.4167e+07] |
| M3 minus M4 | 1 | Qwen2.5-3B | Board VRAM peak (bytes) | 5.0457e+08 | [4.7218e+08, 5.3581e+08] |
| M3 minus M4 | 1 | Qwen2.5-3B | Process VRAM peak (bytes) | 5.0457e+08 | [4.7218e+08, 5.3581e+08] |
| M3 minus M4 | 1 | Qwen2.5-3B | GPU-board energy (J) | 284.7060 | [56.1538, 525.5793] |
| M3 minus M4 | 1 | Qwen2.5-7B | Duration (s) | -35.9880 | [-42.2989, -29.8736] |
| M3 minus M4 | 1 | Qwen2.5-7B | Input tokens | -72.1733 | [-116.9283, -28.8467] |
| M3 minus M4 | 1 | Qwen2.5-7B | Output tokens | -446.8067 | [-522.2037, -373.2048] |
| M3 minus M4 | 1 | Qwen2.5-7B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 1 | Qwen2.5-7B | Process RAM peak (bytes) | -5.9923e+07 | [-6.5466e+07, -5.4429e+07] |
| M3 minus M4 | 1 | Qwen2.5-7B | Board VRAM peak (bytes) | 6.1781e+08 | [5.8499e+08, 6.5115e+08] |
| M3 minus M4 | 1 | Qwen2.5-7B | Process VRAM peak (bytes) | 6.1781e+08 | [5.8499e+08, 6.5115e+08] |
| M3 minus M4 | 1 | Qwen2.5-7B | GPU-board energy (J) | -6279.0720 | [-7366.5573, -5220.6016] |
| M3 minus M4 | 2 | Qwen2.5-3B | Duration (s) | 0.0450 | [-1.2576, 1.3960] |
| M3 minus M4 | 2 | Qwen2.5-3B | Input tokens | 179.5867 | [139.4862, 218.6002] |
| M3 minus M4 | 2 | Qwen2.5-3B | Output tokens | 21.6800 | [-22.9217, 68.7735] |
| M3 minus M4 | 2 | Qwen2.5-3B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 2 | Qwen2.5-3B | Process RAM peak (bytes) | 406842.0267 | [-549590.3573, 1.4181e+06] |
| M3 minus M4 | 2 | Qwen2.5-3B | Board VRAM peak (bytes) | 1.1210e+08 | [9.0401e+07, 1.3416e+08] |
| M3 minus M4 | 2 | Qwen2.5-3B | Process VRAM peak (bytes) | 1.1210e+08 | [9.0401e+07, 1.3416e+08] |
| M3 minus M4 | 2 | Qwen2.5-3B | GPU-board energy (J) | 27.3403 | [-213.1938, 278.3841] |
| M3 minus M4 | 2 | Qwen2.5-7B | Duration (s) | -31.4094 | [-36.7287, -26.2107] |
| M3 minus M4 | 2 | Qwen2.5-7B | Input tokens | -72.1733 | [-116.9283, -28.8467] |
| M3 minus M4 | 2 | Qwen2.5-7B | Output tokens | -446.8067 | [-522.2037, -373.2048] |
| M3 minus M4 | 2 | Qwen2.5-7B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 2 | Qwen2.5-7B | Process RAM peak (bytes) | -5.3508e+07 | [-5.8715e+07, -4.8215e+07] |
| M3 minus M4 | 2 | Qwen2.5-7B | Board VRAM peak (bytes) | 1.3696e+09 | [1.2702e+09, 1.4740e+09] |
| M3 minus M4 | 2 | Qwen2.5-7B | Process VRAM peak (bytes) | 1.3696e+09 | [1.2702e+09, 1.4740e+09] |
| M3 minus M4 | 2 | Qwen2.5-7B | GPU-board energy (J) | -5669.2813 | [-6638.8212, -4726.2696] |
| M3 minus M4 | 3 | Qwen2.5-3B | Duration (s) | 0.8624 | [-0.4351, 2.2355] |
| M3 minus M4 | 3 | Qwen2.5-3B | Input tokens | 179.5867 | [139.4862, 218.6002] |
| M3 minus M4 | 3 | Qwen2.5-3B | Output tokens | 21.6800 | [-22.9217, 68.7735] |
| M3 minus M4 | 3 | Qwen2.5-3B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 3 | Qwen2.5-3B | Process RAM peak (bytes) | -1665.7067 | [-1.1001e+06, 1.1087e+06] |
| M3 minus M4 | 3 | Qwen2.5-3B | Board VRAM peak (bytes) | -3.1150e+08 | [-3.5475e+08, -2.6554e+08] |
| M3 minus M4 | 3 | Qwen2.5-3B | Process VRAM peak (bytes) | -3.1150e+08 | [-3.5475e+08, -2.6554e+08] |
| M3 minus M4 | 3 | Qwen2.5-3B | GPU-board energy (J) | 135.3187 | [-105.9926, 391.7066] |
| M3 minus M4 | 3 | Qwen2.5-7B | Duration (s) | -33.6713 | [-39.4403, -28.1236] |
| M3 minus M4 | 3 | Qwen2.5-7B | Input tokens | -72.1733 | [-116.9283, -28.8467] |
| M3 minus M4 | 3 | Qwen2.5-7B | Output tokens | -446.8067 | [-522.2037, -373.2048] |
| M3 minus M4 | 3 | Qwen2.5-7B | Model calls | 0.0000 | [0.0000, 0.0000] |
| M3 minus M4 | 3 | Qwen2.5-7B | Process RAM peak (bytes) | -4.1544e+07 | [-4.7988e+07, -3.5243e+07] |
| M3 minus M4 | 3 | Qwen2.5-7B | Board VRAM peak (bytes) | -2.8876e+08 | [-2.9820e+08, -2.7903e+08] |
| M3 minus M4 | 3 | Qwen2.5-7B | Process VRAM peak (bytes) | -2.8876e+08 | [-2.9820e+08, -2.7903e+08] |
| M3 minus M4 | 3 | Qwen2.5-7B | GPU-board energy (J) | -5995.9144 | [-7032.8299, -5007.8811] |

## Interpretation Status

The tables and figures are analysis outputs, not a causal or hardware-general performance claim. Cross-repetition consistency and practical magnitude should be discussed metric by metric in the manuscript without converting interval inclusion or exclusion of zero into an unregistered significance test.
