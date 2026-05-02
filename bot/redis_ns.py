import os

NS = "icarus:dev" if os.environ.get("ICARUS_ENV") == "dev" else "icarus"
