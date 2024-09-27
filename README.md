# Nanachan

Tsundere, but useful bot (it's like wasabi!)

## Installation

Nanachan only supports python version 3.12.

You can use `pyenv` to manage multiple version of python in the same environment.

### Poetry

Nanachan project uses poetry v1.x as virtual environment manager.
You can install it either via your package manager (be sure to install version 1), or using the install script
(see the docs).

In case of using the install script, be sure to follow the instructions displayed during installation to
update your `PATH`.
If you had a previous version of poetry, just update it by running `poetry self:update` or `poetry self update`.

More info in the [installation instruction](https://poetry.eustace.io/docs/).

### Development environment

To setup your development environment, just run `poetry install`.

## Develop inside a Docker container using Visual Studio Code

### Getting started

Follow this [getting started guide](https://code.visualstudio.com/docs/remote/containers#_getting-started) to setup your [Visual Studio Code](https://code.visualstudio.com) and [Docker](https://www.docker.com/get-started) environment.
(Note: the [Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) is sufficient, no need to download the full [Remote Development extension pack](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack).)

Do not forget to correctly [setup your git credentials](https://code.visualstudio.com/docs/remote/containers#_sharing-git-credentials-with-your-container) to be able to perform git operations directly inside the container.

### Quick start

Just open the cloned repository in VS Code: a notification will appear in the bottom right corner, select the _Reopen in Container_ option.
If it is not the case, click on the green button on the left of the Status Bar and select _Remote-Containers: Reopen in Container_.

The provided `devcontainer.json` and `Dockerfile` in `.devcontainer` will tell VS Code how to build the Docker image and prepare the container.

A few minutes later your container will be ready and _Dev Container: nanachan_ will appear in the left of the Status Bar. You can now start coding inside.

### Run and Debug

To simplify these operations in VS Code, `launch.json` and `tasks.json` are provided in the `.vscode` folder.
So just go to in the _Run_ section of the Side Bar or press _F5_ to start debugging nanachan.

### Git hooks

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

### Documentation

- [Developing inside a Container](https://code.visualstudio.com/docs/remote/containers)
- [devcontainer.json reference](https://code.visualstudio.com/docs/remote/devcontainerjson-reference)
- [Debugging](https://code.visualstudio.com/docs/editor/debugging)
