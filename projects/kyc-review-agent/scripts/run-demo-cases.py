import argparse
from pathlib import Path

from kyc_review_agent.demo import run_demo_suite
from kyc_review_agent.generation import generator_from_environment


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the five KYC PoC demonstration cases.")
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help="Use the configured LLM for cases 1-4; case 5 always injects a safe failure.",
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    generator = generator_from_environment() if args.live_llm else None
    report = run_demo_suite(project_root, normal_generator=generator)
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
