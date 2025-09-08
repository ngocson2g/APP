# security_app/cli/main.py
from __future__ import annotations
import sys
from security_app.cli.args import build_parser
from security_app.cli.handlers import handle_cleanup, handle_run

def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Giữ alias 'query' nếu code có
    if argv and argv[0] == "query":
        from security_app.app.query import main as query_main
        return query_main(argv[1:])

    # Alias 'cleanup' → --cleanup
    if argv and argv[0] == "cleanup":
        argv = ["--cleanup"] + argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)
    return handle_cleanup(args) if args.cleanup else handle_run(args)

if __name__ == "__main__":
    raise SystemExit(main())
