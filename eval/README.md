# Evaluation Harness

This directory is dedicated to the offline evaluation harness and standalone testing scripts for DocuMind. 

Offline evaluation is a core requirement of this production system to ensure that modifications to search configurations, chunking strategies, embeddings, or prompts do not degrade retrieval and response quality.

## Directory Structure

```
eval/
  README.md
  dataset/               # Ground truth Q&A test datasets (JSON/CSV)
  run_eval.py            # Entry point script to run evaluations
  metrics/               # Metric computation helper modules (hit-rate, MRR, ROUGE, LLM-as-a-judge)
```

## Setup & Running Evaluations

Evaluation scripts share backend configuration and should be executed within the backend virtual environment:

1. Active the Poetry environment:
   ```bash
   cd ../backend
   poetry shell
   ```
2. Run the evaluation script:
   ```bash
   cd ../eval
   python run_eval.py --dataset dataset/ground_truth_v1.json
   ```

## Metrics Tracked

1. **Retrieval Metrics**:
   *   **Hit Rate @ K**: Did the ground truth chunk appear in the top K retrieved documents?
   *   **Mean Reciprocal Rank (MRR)**: Evaluates the rank of the first correct retrieved document.
2. **Generation Metrics**:
   *   **Faithfulness / Groundedness**: Is the answer derived *only* from the context?
   *   **Answer Relevance**: Does the generated answer address the question?
   *   **ROUGE / BLEU**: Syntactic similarity checks against target human answers (optional baseline).
