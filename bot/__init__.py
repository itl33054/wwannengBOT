"""
Compatibility shims for older Python versions.

This module is imported before other modules in the package (via `from bot import ...`).
We provide a small shim for `asyncio.to_thread` which was added in Python 3.9,
so the codebase can call `asyncio.to_thread` even when running under Python 3.8.
"""
import asyncio
import functools


if not hasattr(asyncio, 'to_thread'):
	async def _to_thread(func, /, *args, **kwargs):
		"""Run *func* in default ThreadPoolExecutor.

		This mirrors asyncio.to_thread available in Python 3.9+.
		"""
		loop = asyncio.get_event_loop()
		pfunc = functools.partial(func, *args, **kwargs)
		return await loop.run_in_executor(None, pfunc)

	asyncio.to_thread = _to_thread
