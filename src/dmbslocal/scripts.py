def run_backend() -> None:
    # Lazy import to keep the wrapper thin and avoid tooling/type-checker issues.
    from .local_backend import run_backend as impl

    impl()


def run_frontend() -> None:
    # Lazy import to keep the wrapper thin and avoid tooling/type-checker issues.
    from .local_frontend import run_frontend as impl

    impl()


__all__ = ["run_backend", "run_frontend"]

