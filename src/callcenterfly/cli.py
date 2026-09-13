"""Command-line interface for data, training, evaluation and inference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .artifacts import load_artifact, save_artifact
from .connectome.mock import MockConnectomeBackend
from .connectome.registry import verify_registry
from .data import (
    find_decision,
    load_action_catalog,
    load_decision_points,
    validate_release,
)
from .encoding import EncoderConfig, StructuredStimulusEncoder
from .evaluation import evaluate_policy
from .inference import InferenceEngine
from .responses import ResponseCatalog
from .training import TrainingConfig, train_policy
from .version import __version__

DEFAULT_DATASET = Path("data/synthetic/v0.1.0")
DEFAULT_RESPONSES = Path("data/scripts/response_catalog.csv")
DEFAULT_MODEL = Path("models/mock-baseline-v0")


def emit(payload: Any) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def components_from_metadata(model_dir: Path):
    policy, metadata = load_artifact(model_dir)
    encoder_meta = metadata["encoder"]
    backend_meta = metadata["backend"]
    if backend_meta["type"] != "mock":
        raise ValueError("this baseline CLI only instantiates explicit mock artifacts")
    encoder = StructuredStimulusEncoder(
        EncoderConfig(
            dimension=int(encoder_meta["dimension"]),
            seed=int(encoder_meta["seed"]),
            text_weight=float(encoder_meta["text_weight"]),
        )
    )
    backend = MockConnectomeBackend(
        input_dimension=int(backend_meta["input_dimension"]),
        readout_dimension=int(backend_meta["readout_dimension"]),
        seed=int(backend_meta["seed"]),
    )
    return policy, metadata, encoder, backend


def command_validate(args: argparse.Namespace) -> int:
    report = validate_release(args.dataset)
    actions = load_action_catalog(args.dataset)
    responses = ResponseCatalog.from_csv(args.responses)
    missing_responses = sorted(set(actions) - responses.action_families)
    payload = report.to_dict()
    payload["response_catalog_complete"] = not missing_responses
    payload["missing_response_actions"] = missing_responses
    payload["passed"] = report.passed and not missing_responses
    emit(payload)
    return 0 if payload["passed"] else 1


def command_train(args: argparse.Namespace) -> int:
    actions = list(load_action_catalog(args.dataset))
    train_rows = load_decision_points(args.dataset, "train")
    validation_rows = load_decision_points(args.dataset, "validation")
    test_rows = load_decision_points(args.dataset, "test")
    encoder_config = EncoderConfig(
        dimension=args.encoder_dimension,
        seed=args.seed,
        text_weight=args.text_weight,
    )
    encoder = StructuredStimulusEncoder(encoder_config)
    backend = MockConnectomeBackend(
        input_dimension=args.encoder_dimension,
        readout_dimension=args.readout_dimension,
        seed=args.backend_seed,
    )
    training_config = TrainingConfig(
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        l2=args.l2,
        settle_steps=args.settle_steps,
        seed=args.seed,
    )
    policy, history = train_policy(
        train_rows,
        validation_rows,
        encoder,
        backend,
        actions,
        training_config,
    )
    test_report = evaluate_policy(test_rows, encoder, backend, policy, training_config.settle_steps)
    metadata = {
        "model_name": args.output.name,
        "package_version": __version__,
        "dataset_version": "0.1.0",
        "dataset_path_at_training": args.dataset.as_posix(),
        "backend": {
            "type": "mock",
            "name": backend.name,
            "input_dimension": backend.input_dimension,
            "readout_dimension": backend.readout_dimension,
            "seed": backend.seed,
            "connectome_used": False,
            "scientific_interpretation": "software mock; not biological evidence",
        },
        "encoder": {
            "dimension": encoder_config.dimension,
            "seed": encoder_config.seed,
            "text_weight": encoder_config.text_weight,
            "mapping_status": "engineered and unvalidated",
        },
        "training": {
            "objective": "full-information contextual bandit expected reward",
            "epochs": training_config.epochs,
            "learning_rate": training_config.learning_rate,
            "l2": training_config.l2,
            "settle_steps": training_config.settle_steps,
            "seed": training_config.seed,
            "train_examples": len(train_rows),
            "validation_examples": len(validation_rows),
        },
        "history": [entry.to_dict() for entry in history],
        "test_metrics": test_report.to_dict(),
        "limitations": [
            "No MaleCNS connectome was loaded.",
            "Synthetic templated data only.",
            "Response templates require institutional review.",
            "Not approved for production member servicing.",
        ],
    }
    save_artifact(args.output, policy, metadata)
    (args.output / "evaluation_test.json").write_text(
        json.dumps(test_report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    emit(
        {
            "model_dir": args.output.as_posix(),
            "backend": backend.name,
            "connectome_used": False,
            "last_validation": history[-1].validation.to_dict(),
            "test": test_report.to_dict(),
        }
    )
    return 0


def command_evaluate(args: argparse.Namespace) -> int:
    policy, metadata, encoder, backend = components_from_metadata(args.model)
    rows = load_decision_points(args.dataset, args.split)
    report = evaluate_policy(
        rows,
        encoder,
        backend,
        policy,
        int(metadata["training"]["settle_steps"]),
    )
    emit(report.to_dict())
    return 0


def command_infer(args: argparse.Namespace) -> int:
    decision = find_decision(args.dataset, args.decision_id)
    engine = InferenceEngine(args.model, args.responses)
    prediction = engine.predict(decision)
    emit(
        {
            **prediction.to_dict(),
            "candidate_actions": list(decision.candidate_actions),
            "preferred_action_for_offline_evaluation": decision.preferred_action_family,
            "human_review_required": True,
            "production_ready": False,
        }
    )
    return 0


def command_verify_connectome(args: argparse.Namespace) -> int:
    results = verify_registry(args.registry, args.data_dir)
    payload = {
        "passed": all(result.passed for result in results),
        "connectome_loaded": False,
        "files": [
            {
                "filename": result.filename,
                "present": result.present,
                "bytes_match": result.bytes_match,
                "sha256_match": result.sha256_match,
                "observed_bytes": result.observed_bytes,
                "observed_sha256": result.observed_sha256,
            }
            for result in results
        ],
    }
    emit(payload)
    return 0 if payload["passed"] else 1


def command_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError as exc:
        raise RuntimeError("install serving extras with: pip install -e '.[serve]'") from exc
    from .service import create_app

    app = create_app(args.model, args.responses, args.audit_path)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="callcenterfly")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate-data", help="validate the synthetic release")
    validate.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    validate.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    validate.set_defaults(handler=command_validate)

    train = subparsers.add_parser("train", help="train the mock contextual-bandit adapter")
    train.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    train.add_argument("--output", type=Path, default=Path("artifacts/mock-run"))
    train.add_argument("--epochs", type=int, default=4)
    train.add_argument("--learning-rate", type=float, default=0.04)
    train.add_argument("--l2", type=float, default=1e-5)
    train.add_argument("--settle-steps", type=int, default=6)
    train.add_argument("--encoder-dimension", type=int, default=128)
    train.add_argument("--readout-dimension", type=int, default=64)
    train.add_argument("--text-weight", type=float, default=0.16)
    train.add_argument("--backend-seed", type=int, default=7)
    train.add_argument("--seed", type=int, default=20260913)
    train.set_defaults(handler=command_train)

    evaluate = subparsers.add_parser("evaluate", help="evaluate a frozen adapter")
    evaluate.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    evaluate.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    evaluate.add_argument("--split", choices=("validation", "test"), default="test")
    evaluate.set_defaults(handler=command_evaluate)

    infer = subparsers.add_parser("infer", help="run one synthetic decision")
    infer.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    infer.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    infer.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    infer.add_argument("--decision-id", required=True)
    infer.set_defaults(handler=command_infer)

    verify = subparsers.add_parser("verify-connectome", help="verify external MaleCNS files")
    verify.add_argument("--registry", type=Path, default=Path("config/datasets/malecns_v1.json"))
    verify.add_argument("--data-dir", type=Path, default=Path("connectome_data/malecns_v1"))
    verify.set_defaults(handler=command_verify_connectome)

    serve = subparsers.add_parser("serve", help="serve the experimental HTTP boundary")
    serve.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    serve.add_argument("--responses", type=Path, default=DEFAULT_RESPONSES)
    serve.add_argument("--audit-path", type=Path, default=Path("logs/decisions.jsonl"))
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(handler=command_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (FileNotFoundError, KeyError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
