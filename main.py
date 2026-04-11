import argparse

from agent import Agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Local + Gemini agent CLI")
    parser.add_argument(
        "--provider",
        choices=("local", "gemini"),
        default=None,
        help="Override PRIMARY_PROVIDER for this session",
    )
    parser.add_argument(
        "--conversation-id",
        default=None,
        help="Resume a conversation UUID (also settable via CONVERSATION_ID)",
    )
    args = parser.parse_args()

    agent = Agent.from_defaults(conversation_id=args.conversation_id)
    if args.provider:
        try:
            agent.router.switch(args.provider)
        except (RuntimeError, ValueError) as e:
            print(f"Provider override failed: {e}")
    agent.run_chat_loop()


if __name__ == "__main__":
    main()
