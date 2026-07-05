# Week 2 Status Summary

Week 2 status summary from existing raw artifacts. This is not a final benchmark; the audio set is small, local-GPU ASR is not Colab/T4, and the current audio split is retrospective.

## Headline Metrics

| Question | Current Answer |
| --- | --- |
| ASR exact transcript accuracy | 90.00% on 10 recordings |
| ASR mean word error rate | 1.00% |
| Human-transcript intent exact accuracy | 100.00% with `trained_nb_human_curated_v2` |
| Whisper-transcript intent exact accuracy | 90.00% with `trained_nb_human_curated_v2` |
| Canonical constraint changes from ASR | 0 records |
| Audio-matched human-transcript span F1 | 73.24% with `span_nb_v1` |
| ASR semantic span-prediction changes | 0 records |
| Colab/T4 DistilBERT text span F1 | 78.57% |
| Colab/T4 DistilBERT text span precision/recall | 75.00% / 82.50% |

## Interpretation

- ASR is currently strong on the small recorded sample, but the evidence is not benchmark-grade.
- The observed ASR word substitution affects raw constraint strings, but canonical altitude constraints remain unchanged.
- Audio-linked intent extraction is perfect on human transcripts and drops to 0.90 exact-record accuracy on Whisper transcripts because of one raw constraint mismatch.
- The strongest text span extractor is the expanded 85-record Colab/T4 DistilBERT run, with entity F1 around 0.79 on the current 10-record test split.
- The remaining transformer span errors still cluster around count/constraint confusion and target boundary mistakes.
- The next research-useful improvement is a pre-registered larger audio batch or a restored Colab checkpoint for direct transformer inference on ASR text.

## Remaining Errors

- False negatives by entity: `{"action": 1, "constraint": 1, "count": 2, "location": 1, "target": 2}`
- False positives by entity: `{"action": 1, "constraint": 3, "count": 2, "location": 1, "target": 4}`
- Worst held-out record ids: `human_cmd_030, human_cmd_050, human_cmd_045, human_cmd_049, human_cmd_048, human_cmd_047`

## Limitations

- The current audio set has only 10 recordings.
- The current audio split was assigned retrospectively after the first pooled ASR run.
- The recorded ASR run used a local GTX GPU, not Colab/T4.
- Audio-linked intent labels are reused from matching text-command records; they are not newly collected audio-specific gold labels.
- ASR transcript span rows compare predictions only; no human gold spans exist for Whisper transcript text.
- The strongest transformer result is text-command span extraction, not speech-to-mission performance.

## Source Artifacts

- `audio_evaluation`: `outputs\evaluations\whisper_base_audio_evaluation_local_gtx1650.json`
- `intent_accuracy`: `outputs\evaluations\whisper_base_intent_accuracy_local_gtx1650.json`
- `intent_impact`: `outputs\evaluations\whisper_base_intent_impact_local_gtx1650.json`
- `span_impact`: `outputs\evaluations\whisper_base_span_impact_local_gtx1650.json`
- `hf_token_metrics`: `outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_metrics.json`
- `hf_token_error_analysis`: `outputs\evaluations\hf_token_classifier_distilbert_colab_t4_expanded85_test_error_analysis.json`
