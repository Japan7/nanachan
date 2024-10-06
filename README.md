# Nanachan

Tsundere, but useful bot (it's like wasabi!)

## Quickstart

```sh
git clone https://github.com/Japan7/nanachan.git
cd nanachan/
uv run --frozen -m nanachan
```

## Git hooks

To check your changes before committing you can use the provided pre-commit hook:

```sh
git config core.hookspath hooks
```

or

```sh
cp hooks/pre-commit .git/hooks
```

By default it will run `ruff check` on the codebase and `pyright` if the
`HOOKS_PYRIGHT_CHECK` environment variable is set (because pyright is very
slow).
In any case the CI will run the same commands and report the errors just the same.
