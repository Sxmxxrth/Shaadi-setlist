import argparse

from src.app import main


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ShaadiSetlist REPL.")
    parser.add_argument(
        "--enable-live-search",
        action="store_true",
        help="Enable live YouTube search fallback when no dataset matches are found.",
    )
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the Gradio browser UI instead of the terminal REPL.",
    )
    parser.add_argument(
        "--workflow",
        action="store_true",
        help="Run local demo checks, validate Ollama, then launch the Gradio UI.",
    )
    parser.add_argument(
        "--workflow-check",
        action="store_true",
        help="Run local demo checks without launching the Gradio UI.",
    )
    args = parser.parse_args()
    if args.workflow_check:
        from src.workflow import run_workflow

        raise SystemExit(run_workflow(launch_ui=False))
    if args.workflow:
        from src.workflow import run_workflow

        raise SystemExit(run_workflow())
    if args.ui:
        from src.gradio_ui import main as gradio_main

        gradio_main()
        raise SystemExit(0)
    raise SystemExit(main(enable_live_search=args.enable_live_search))
