# Strategy B alarm-threshold sensitivity (test, D23)

Drops 0.03, 0.05, 0.1; everything else from configs/strategies.toml. Random-label conditions pooled (9 conditions x 200 streams per scenario). Drop 0.05 reproduces the D14 run: DIFFERENT in 10355 of 60000 rows: {('B', 'd0_p100'): 180, ('B', 'd0_p20'): 494, ('B', 'd0_p50'): 257, ('B', 'd10_p100'): 180, ('B', 'd10_p20'): 522, ('B', 'd10_p50'): 231, ('B', 'd5_alert_first'): 1430, ('B', 'd5_p100'): 180, ('B', 'd5_p20'): 486, ('B', 'd5_p50'): 227, ('B_F1', 'd0_p100'): 185, ('B_F1', 'd0_p20'): 489, ('B_F1', 'd0_p50'): 251, ('B_F1', 'd10_p100'): 185, ('B_F1', 'd10_p20'): 518, ('B_F1', 'd10_p50'): 233, ('B_F1', 'd5_alert_first'): 239, ('B_F1', 'd5_p100'): 185, ('B_F1', 'd5_p20'): 481, ('B_F1', 'd5_p50'): 230, ('B_ipw', 'd0_p100'): 180, ('B_ipw', 'd0_p20'): 494, ('B_ipw', 'd0_p50'): 257, ('B_ipw', 'd10_p100'): 180, ('B_ipw', 'd10_p20'): 522, ('B_ipw', 'd10_p50'): 231, ('B_ipw', 'd5_alert_first'): 415, ('B_ipw', 'd5_p100'): 180, ('B_ipw', 'd5_p20'): 486, ('B_ipw', 'd5_p50'): 227}.

| Strategy | Drop | Scenario | Detection | False alerts | Median delay |
|---|---:|---|---:|---:|---:|
| B | 0.03 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.03 | H2_benign_mix |  | 0.0% |  |
| B | 0.03 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.03 | S0_stable |  | 0.0% |  |
| B | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 9.0 |
| B | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B | 0.05 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.05 | H2_benign_mix |  | 0.0% |  |
| B | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.05 | S0_stable |  | 0.0% |  |
| B | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 11.0 |
| B | 0.05 | X1_hard_attack_mix_rare | 99.8% | 0.0% | 8.0 |
| B | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 10.0 |
| B | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B | 0.1 | H1_fewer_attacks |  | 0.0% |  |
| B | 0.1 | H2_benign_mix |  | 0.0% |  |
| B | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B | 0.1 | S0_stable |  | 0.0% |  |
| B | 0.1 | X1_hard_attack_mix | 99.9% | 0.0% | 8.0 |
| B | 0.1 | X1_hard_attack_mix_gradual | 97.6% | 0.0% | 16.0 |
| B | 0.1 | X1_hard_attack_mix_rare | 85.3% | 0.0% | 12.0 |
| B | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B | 0.1 | X2_false_positive_burst_gradual | 99.8% | 0.0% | 15.0 |
| B | 0.1 | X2_false_positive_burst_rare | 96.5% | 0.0% | 11.0 |
| B_F1 | 0.03 | H1_fewer_attacks |  | 100.0% |  |
| B_F1 | 0.03 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.03 | H3_easy_attack_mix |  | 0.0% |  |
| B_F1 | 0.03 | S0_stable |  | 0.0% |  |
| B_F1 | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 9.0 |
| B_F1 | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.05 | H1_fewer_attacks |  | 99.8% |  |
| B_F1 | 0.05 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B_F1 | 0.05 | S0_stable |  | 0.0% |  |
| B_F1 | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 11.0 |
| B_F1 | 0.05 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_F1 | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 10.0 |
| B_F1 | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.1 | H1_fewer_attacks |  | 54.5% |  |
| B_F1 | 0.1 | H2_benign_mix |  | 0.0% |  |
| B_F1 | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B_F1 | 0.1 | S0_stable |  | 0.0% |  |
| B_F1 | 0.1 | X1_hard_attack_mix | 99.9% | 0.0% | 8.0 |
| B_F1 | 0.1 | X1_hard_attack_mix_gradual | 97.0% | 0.0% | 16.0 |
| B_F1 | 0.1 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_F1 | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 7.0 |
| B_F1 | 0.1 | X2_false_positive_burst_gradual | 99.0% | 0.0% | 15.0 |
| B_F1 | 0.1 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.03 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.03 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.03 | S0_stable |  | 0.0% |  |
| B_ipw | 0.03 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.03 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 9.0 |
| B_ipw | 0.03 | X1_hard_attack_mix_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.03 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.03 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.05 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.05 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.05 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.05 | S0_stable |  | 0.0% |  |
| B_ipw | 0.05 | X1_hard_attack_mix | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.05 | X1_hard_attack_mix_gradual | 100.0% | 0.0% | 11.0 |
| B_ipw | 0.05 | X1_hard_attack_mix_rare | 99.8% | 0.0% | 8.0 |
| B_ipw | 0.05 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.05 | X2_false_positive_burst_gradual | 100.0% | 0.0% | 10.0 |
| B_ipw | 0.05 | X2_false_positive_burst_rare | 100.0% | 0.0% | 8.0 |
| B_ipw | 0.1 | H1_fewer_attacks |  | 0.0% |  |
| B_ipw | 0.1 | H2_benign_mix |  | 0.0% |  |
| B_ipw | 0.1 | H3_easy_attack_mix |  | 0.0% |  |
| B_ipw | 0.1 | S0_stable |  | 0.0% |  |
| B_ipw | 0.1 | X1_hard_attack_mix | 99.9% | 0.0% | 8.0 |
| B_ipw | 0.1 | X1_hard_attack_mix_gradual | 97.6% | 0.0% | 16.0 |
| B_ipw | 0.1 | X1_hard_attack_mix_rare | 85.3% | 0.0% | 12.0 |
| B_ipw | 0.1 | X2_false_positive_burst | 100.0% | 0.0% | 6.0 |
| B_ipw | 0.1 | X2_false_positive_burst_gradual | 99.8% | 0.0% | 15.0 |
| B_ipw | 0.1 | X2_false_positive_burst_rare | 96.5% | 0.0% | 11.0 |

## Real windows in time order

| Strategy | Drop | Condition | Alarm windows |
|---|---:|---|---|
| B_F1 | 0.03 | d0_p100 | 6 34 45 54 |
| B | 0.03 | d0_p100 | 45 54 |
| B_ipw | 0.03 | d0_p100 | 45 54 |
| B_F1 | 0.03 | d0_p50 | 6 45 54 |
| B | 0.03 | d0_p50 | 45 54 |
| B_ipw | 0.03 | d0_p50 | 45 54 |
| B_F1 | 0.03 | d0_p20 | 45 |
| B | 0.03 | d0_p20 | 45 |
| B_ipw | 0.03 | d0_p20 | 45 |
| B_F1 | 0.03 | d5_p100 | 6 34 45 54 |
| B | 0.03 | d5_p100 | 45 54 |
| B_ipw | 0.03 | d5_p100 | 45 54 |
| B_F1 | 0.03 | d5_p50 | 6 34 45 54 |
| B | 0.03 | d5_p50 | 34 45 54 |
| B_ipw | 0.03 | d5_p50 | 34 45 54 |
| B_F1 | 0.03 | d5_p20 | 33 45 |
| B | 0.03 | d5_p20 | 33 45 |
| B_ipw | 0.03 | d5_p20 | 33 45 |
| B_F1 | 0.03 | d10_p100 | 6 34 45 54 |
| B | 0.03 | d10_p100 | 45 54 |
| B_ipw | 0.03 | d10_p100 | 45 54 |
| B_F1 | 0.03 | d10_p50 | 3 45 54 |
| B | 0.03 | d10_p50 | 45 54 |
| B_ipw | 0.03 | d10_p50 | 45 54 |
| B_F1 | 0.03 | d10_p20 | 34 45 |
| B | 0.03 | d10_p20 | 34 45 |
| B_ipw | 0.03 | d10_p20 | 34 45 |
| B_F1 | 0.03 | d5_alert_first | 6 48 |
| B | 0.03 | d5_alert_first | 6 30 46 58 69 85 |
| B_ipw | 0.03 | d5_alert_first | 46 |
| B_F1 | 0.05 | d0_p100 | 45 54 |
| B | 0.05 | d0_p100 | 49 54 |
| B_ipw | 0.05 | d0_p100 | 49 54 |
| B_F1 | 0.05 | d0_p50 | 45 54 |
| B | 0.05 | d0_p50 | 45 54 |
| B_ipw | 0.05 | d0_p50 | 45 54 |
| B_F1 | 0.05 | d0_p20 | 45 |
| B | 0.05 | d0_p20 | 48 |
| B_ipw | 0.05 | d0_p20 | 48 |
| B_F1 | 0.05 | d5_p100 | 45 54 |
| B | 0.05 | d5_p100 | 49 54 |
| B_ipw | 0.05 | d5_p100 | 49 54 |
| B_F1 | 0.05 | d5_p50 | 45 54 |
| B | 0.05 | d5_p50 | 49 |
| B_ipw | 0.05 | d5_p50 | 49 |
| B_F1 | 0.05 | d5_p20 | 45 |
| B | 0.05 | d5_p20 | 48 |
| B_ipw | 0.05 | d5_p20 | 48 |
| B_F1 | 0.05 | d10_p100 | 45 54 |
| B | 0.05 | d10_p100 | 49 54 |
| B_ipw | 0.05 | d10_p100 | 49 54 |
| B_F1 | 0.05 | d10_p50 | 6 45 54 |
| B | 0.05 | d10_p50 | 49 54 |
| B_ipw | 0.05 | d10_p50 | 49 54 |
| B_F1 | 0.05 | d10_p20 | 45 |
| B | 0.05 | d10_p20 | 49 |
| B_ipw | 0.05 | d10_p20 | 49 |
| B_F1 | 0.05 | d5_alert_first | 48 |
| B | 0.05 | d5_alert_first | 6 46 58 |
| B_ipw | 0.05 | d5_alert_first | 46 |
| B_F1 | 0.1 | d0_p100 | 49 |
| B | 0.1 | d0_p100 |  |
| B_ipw | 0.1 | d0_p100 |  |
| B_F1 | 0.1 | d0_p50 | 49 54 |
| B | 0.1 | d0_p50 |  |
| B_ipw | 0.1 | d0_p50 |  |
| B_F1 | 0.1 | d0_p20 | 48 |
| B | 0.1 | d0_p20 | 50 |
| B_ipw | 0.1 | d0_p20 | 50 |
| B_F1 | 0.1 | d5_p100 | 49 |
| B | 0.1 | d5_p100 |  |
| B_ipw | 0.1 | d5_p100 |  |
| B_F1 | 0.1 | d5_p50 | 49 |
| B | 0.1 | d5_p50 | 49 |
| B_ipw | 0.1 | d5_p50 | 49 |
| B_F1 | 0.1 | d5_p20 | 48 |
| B | 0.1 | d5_p20 | 49 |
| B_ipw | 0.1 | d5_p20 | 49 |
| B_F1 | 0.1 | d10_p100 | 49 |
| B | 0.1 | d10_p100 |  |
| B_ipw | 0.1 | d10_p100 |  |
| B_F1 | 0.1 | d10_p50 | 49 |
| B | 0.1 | d10_p50 | 49 |
| B_ipw | 0.1 | d10_p50 | 49 |
| B_F1 | 0.1 | d10_p20 | 49 |
| B | 0.1 | d10_p20 | 50 |
| B_ipw | 0.1 | d10_p20 | 50 |
| B_F1 | 0.1 | d5_alert_first |  |
| B | 0.1 | d5_alert_first | 48 |
| B_ipw | 0.1 | d5_alert_first |  |
