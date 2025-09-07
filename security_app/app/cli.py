# Giữ entry-point cũ
from security_app.cli.main import main
if __name__ == "__main__":
    raise SystemExit(main())
