# Strategy B alarm-threshold sensitivity (validation, D23)

Drops 0.03, 0.05, 0.1; everything else from configs/strategies.toml. Random-label conditions pooled (9 conditions x 200 streams per scenario). Drop 0.05 reproduces the D14 run: DIFFERENT in 9006 of 60000 rows: {('B', 'd0_p100'): 156, ('B', 'd0_p20'): 462, ('B', 'd0_p50'): 239, ('B', 'd10_p100'): 156, ('B', 'd10_p20'): 490, ('B', 'd10_p50'): 221, ('B', 'd5_alert_first'): 714, ('B', 'd5_p100'): 156, ('B', 'd5_p20'): 470, ('B', 'd5_p50'): 233, ('B_F1', 'd0_p100'): 158, ('B_F1', 'd0_p20'): 467, ('B_F1', 'd0_p50'): 225, ('B_F1', 'd10_p100'): 158, ('B_F1', 'd10_p20'): 489, ('B_F1', 'd10_p50'): 216, ('B_F1', 'd5_alert_first'): 179, ('B_F1', 'd5_p100'): 158, ('B_F1', 'd5_p20'): 457, ('B_F1', 'd5_p50'): 230, ('B_ipw', 'd0_p100'): 156, ('B_ipw', 'd0_p20'): 462, ('B_ipw', 'd0_p50'): 239, ('B_ipw', 'd10_p100'): 156, ('B_ipw', 'd10_p20'): 490, ('B_ipw', 'd10_p50'): 221, ('B_ipw', 'd5_alert_first'): 389, ('B_ipw', 'd5_p100'): 156, ('B_ipw', 'd5_p20'): 470, ('B_ipw', 'd5_p50'): 233}.

| Strategy | Drop | Scenario | Detection | False alerts | Median delay |
|---|---:|---|---:|---:|---:|
| B | 0.03 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.03 | H2_benign_mix |  | 0.0% |  |
| B | 0.03 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.03 | S0_stable |  | 0.0% |  |
| B | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 8.0 |
| B | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B | 0.05 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.05 | H2_benign_mix |  | 0.0% |  |
| B | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.05 | S0_stable |  | 0.0% |  |
| B | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 10.0 |
| B | 0.05 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 9.0 |
| B | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B | 0.1 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.1 | H2_benign_mix |  | 0.0% |  |
| B | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.1 | S0_stable |  | 0.0% |  |
| B | 0.1 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B | 0.1 | X1_hard_attack_mix_gradual | 99.8% | 0.0% | 15.0 |
| B | 0.1 | X1_hard_attack_mix_rare | 94.3% | 0.0% | 11.0 |
| B | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.1 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 13.0 |
| B | 0.1 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | H1_fewer_attacks |  | 100.0% |  |
| B_F1 | 0.03 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.03 | H3_easy_attack_mix |  | 0.1% |  |
| B_F1 | 0.03 | S0_stable |  | 0.0% |  |
| B_F1 | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.05 | H1_fewer_attacks |  | 100.0% |  |
| B_F1 | 0.05 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B_F1 | 0.05 | S0_stable |  | 0.0% |  |
| B_F1 | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 10.0 |
| B_F1 | 0.05 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 9.0 |
| B_F1 | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.1 | H1_fewer_attacks |  | 89.5% |  |
| B_F1 | 0.1 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B_F1 | 0.1 | S0_stable |  | 0.0% |  |
| B_F1 | 0.1 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.1 | X1_hard_attack_mix_gradual | 99.8% | 0.0% | 15.0 |
| B_F1 | 0.1 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.1 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 13.0 |
| B_F1 | 0.1 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.03 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.03 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.03 | S0_stable |  | 0.0% |  |
| B_ipw | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.05 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.05 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.05 | S0_stable |  | 0.0% |  |
| B_ipw | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 10.0 |
| B_ipw | 0.05 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 9.0 |
| B_ipw | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.1 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.1 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.1 | S0_stable |  | 0.0% |  |
| B_ipw | 0.1 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.1 | X1_hard_attack_mix_gradual | 99.8% | 0.0% | 15.0 |
| B_ipw | 0.1 | X1_hard_attack_mix_rare | 94.3% | 0.0% | 11.0 |
| B_ipw | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.1 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 13.0 |
| B_ipw | 0.1 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |

## Real windows in time order

| Strategy | Drop | Condition | Alarm windows |
|---|---:|---|---|
| B_F1 | 0.03 | d0_p100 | 2 51 |
| B | 0.03 | d0_p100 | 2 10 52 |
| B_ipw | 0.03 | d0_p100 | 2 10 52 |
| B_F1 | 0.03 | d0_p50 | 2 51 |
| B | 0.03 | d0_p50 | 2 10 54 |
| B_ipw | 0.03 | d0_p50 | 2 10 54 |
| B_F1 | 0.03 | d0_p20 | 2 54 |
| B | 0.03 | d0_p20 | 2 55 |
| B_ipw | 0.03 | d0_p20 | 2 55 |
| B_F1 | 0.03 | d5_p100 | 2 51 |
| B | 0.03 | d5_p100 | 2 10 52 |
| B_ipw | 0.03 | d5_p100 | 2 10 52 |
| B_F1 | 0.03 | d5_p50 | 2 51 |
| B | 0.03 | d5_p50 | 2 7 53 |
| B_ipw | 0.03 | d5_p50 | 2 7 53 |
| B_F1 | 0.03 | d5_p20 | 4 52 |
| B | 0.03 | d5_p20 | 4 54 |
| B_ipw | 0.03 | d5_p20 | 4 54 |
| B_F1 | 0.03 | d10_p100 | 2 51 |
| B | 0.03 | d10_p100 | 2 10 52 |
| B_ipw | 0.03 | d10_p100 | 2 10 52 |
| B_F1 | 0.03 | d10_p50 | 2 52 |
| B | 0.03 | d10_p50 | 2 10 54 |
| B_ipw | 0.03 | d10_p50 | 2 10 54 |
| B_F1 | 0.03 | d10_p20 | 2 52 |
| B | 0.03 | d10_p20 | 2 54 |
| B_ipw | 0.03 | d10_p20 | 2 54 |
| B_F1 | 0.03 | d5_alert_first | 2 55 |
| B | 0.03 | d5_alert_first | 2 11 36 |
| B_ipw | 0.03 | d5_alert_first | 2 9 |
| B_F1 | 0.05 | d0_p100 | 2 7 53 |
| B | 0.05 | d0_p100 | 2 56 |
| B_ipw | 0.05 | d0_p100 | 2 56 |
| B_F1 | 0.05 | d0_p50 | 2 10 52 |
| B | 0.05 | d0_p50 | 2 56 |
| B_ipw | 0.05 | d0_p50 | 2 56 |
| B_F1 | 0.05 | d0_p20 | 2 55 |
| B | 0.05 | d0_p20 | 2 55 |
| B_ipw | 0.05 | d0_p20 | 2 55 |
| B_F1 | 0.05 | d5_p100 | 2 7 53 |
| B | 0.05 | d5_p100 | 2 56 |
| B_ipw | 0.05 | d5_p100 | 2 56 |
| B_F1 | 0.05 | d5_p50 | 2 7 53 |
| B | 0.05 | d5_p50 | 2 56 |
| B_ipw | 0.05 | d5_p50 | 2 56 |
| B_F1 | 0.05 | d5_p20 | 4 54 |
| B | 0.05 | d5_p20 | 4 56 |
| B_ipw | 0.05 | d5_p20 | 4 56 |
| B_F1 | 0.05 | d10_p100 | 2 7 53 |
| B | 0.05 | d10_p100 | 2 56 |
| B_ipw | 0.05 | d10_p100 | 2 56 |
| B_F1 | 0.05 | d10_p50 | 2 10 52 |
| B | 0.05 | d10_p50 | 2 10 56 |
| B_ipw | 0.05 | d10_p50 | 2 10 56 |
| B_F1 | 0.05 | d10_p20 | 2 52 |
| B | 0.05 | d10_p20 | 2 54 |
| B_ipw | 0.05 | d10_p20 | 2 54 |
| B_F1 | 0.05 | d5_alert_first | 2 |
| B | 0.05 | d5_alert_first | 2 22 38 54 |
| B_ipw | 0.05 | d5_alert_first | 2 |
| B_F1 | 0.1 | d0_p100 | 2 56 |
| B | 0.1 | d0_p100 | 2 57 |
| B_ipw | 0.1 | d0_p100 | 2 57 |
| B_F1 | 0.1 | d0_p50 | 2 56 |
| B | 0.1 | d0_p50 | 2 57 |
| B_ipw | 0.1 | d0_p50 | 2 57 |
| B_F1 | 0.1 | d0_p20 | 2 56 |
| B | 0.1 | d0_p20 | 2 57 |
| B_ipw | 0.1 | d0_p20 | 2 57 |
| B_F1 | 0.1 | d5_p100 | 2 56 |
| B | 0.1 | d5_p100 | 2 57 |
| B_ipw | 0.1 | d5_p100 | 2 57 |
| B_F1 | 0.1 | d5_p50 | 2 56 |
| B | 0.1 | d5_p50 | 3 57 |
| B_ipw | 0.1 | d5_p50 | 3 57 |
| B_F1 | 0.1 | d5_p20 | 4 56 |
| B | 0.1 | d5_p20 | 57 |
| B_ipw | 0.1 | d5_p20 | 57 |
| B_F1 | 0.1 | d10_p100 | 2 56 |
| B | 0.1 | d10_p100 | 2 57 |
| B_ipw | 0.1 | d10_p100 | 2 57 |
| B_F1 | 0.1 | d10_p50 | 2 56 |
| B | 0.1 | d10_p50 | 2 57 |
| B_ipw | 0.1 | d10_p50 | 2 57 |
| B_F1 | 0.1 | d10_p20 | 2 57 |
| B | 0.1 | d10_p20 | 2 57 |
| B_ipw | 0.1 | d10_p20 | 2 57 |
| B_F1 | 0.1 | d5_alert_first |  |
| B | 0.1 | d5_alert_first | 2 57 |
| B_ipw | 0.1 | d5_alert_first | 2 |
