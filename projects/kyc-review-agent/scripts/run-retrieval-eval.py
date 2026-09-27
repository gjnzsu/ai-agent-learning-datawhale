import argparse
from pathlib import Path

from kyc_review_agent.evaluation import (
    evaluate_retrieval,
    load_retrieval_evaluation_cases,
)
from kyc_review_agent.ingestion import build_policy_retriever


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Evaluate policy retrieval precision and recall.")
    parser.add_argument("--top-k", type=int, default=1)
    parser.add_argument(
        "--cases",
        type=Path,
        default=project_root / "data" / "evaluation" / "retrieval-cases.json",
    )
    args = parser.parse_args()

    retriever = build_policy_retriever(project_root / "data" / "policies")
    cases = load_retrieval_evaluation_cases(args.cases)
    report = evaluate_retrieval(retriever, cases, top_k=args.top_k)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
