import logging
from pathlib import Path
from typing import TYPE_CHECKING

from discord.ext.commands import ExtensionError

from nanachan.settings import DISABLED_EXTENSIONS
from nanachan.utils.misc import get_traceback, get_traceback_str

if TYPE_CHECKING:
    from nanachan.discord.bot import Bot


log = logging.getLogger(__name__)

init_file = Path(__file__)
extensions_dir = Path(init_file).parent


async def load_extensions(bot: 'Bot'):
    errors = []
    for extension_file in extensions_dir.iterdir():
        extension = extension_file.stem

        if any(
            (
                extension_file.is_dir(),
                extension.startswith('_'),
                extension.startswith('.'),
                extension in DISABLED_EXTENSIONS,
            )
        ):
            continue

        try:
            module_name = f'nanachan.extensions.{extension}'
            await bot.load_extension(module_name)
            log.info(f"Extension '{module_name}' loaded")
        except ExtensionError as e:
            log.exception(e)

            trace = get_traceback(e)
            errors.append(bot.send_error(get_traceback_str(trace)))

    return errors
