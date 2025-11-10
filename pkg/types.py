from typing import AsyncContextManager, Callable

from sqlalchemy.ext.asyncio import AsyncSession

SessionProvider = Callable[..., AsyncContextManager[AsyncSession]]
