# Nanachan

Tsundere, but useful bot (it's like wasabi!)

## Quickstart

```sh
git clone https://github.com/Japan7/nanachan.git
cd nanachan/
uv run --frozen -m nanachan
```

Create your discord app at https://discord.com/developers/applications.
On the “Bot” page enable the server member intent and message content intent, generate your bot token.

Then copy `nanachan/example.local_settings.py` to `nanachan/local_settings.py` and edit it appropriately.

You can invite your bot to a server with a link similar to this (using the client ID of your application):
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=0&scope=bot+applications.commands


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
