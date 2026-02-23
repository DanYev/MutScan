from __future__ import annotations

import os
import shutil
import sys
from functools import wraps
from pathlib import Path
from typing import Callable, Optional, TypeVar, Union


T = TypeVar("T")


def cleanup_failure(
	_func: Optional[Callable[..., T]] = None,
	*,
	mdruns_dirname: str = "mdruns",
	log_glob: str = "*.log",
	remove_system_on_failure: bool = False,
) -> Union[Callable[[Callable[..., T]], Callable[..., T]], Callable[..., T]]:
	"""Decorator to clean up generated directories on failure.

	If the wrapped function raises an exception, this decorator will:
	1) Determine a target directory from the wrapped function's args:
	   - If args look like (sysdir, sysname, runname, ...): delete
	     Path(sysdir)/sysname/mdruns/<runname>
	   - If args look like (sysdir, sysname, ...): delete Path(sysdir)/sysname
	   - If remove_system_on_failure=True: always delete Path(sysdir)/sysname
	2) Before deleting, find all matching log files (default: '*.log') under the
	   target directory and move them into the *execution directory* (the current
	   working directory at the moment the wrapped function is entered).

	Usage:
		@cleanup_failure
		def md_npt(sysdir, sysname, runname): ...

		@cleanup_failure(remove_system_on_failure=True)
		def setup_martini(sysdir, sysname): ...
	"""

	def decorator(func: Callable[..., T]) -> Callable[..., T]:
		@wraps(func)
		def wrapper(*args, **kwargs):
			exec_dir = Path.cwd()
			script_dir = Path(__file__).parent
			try:
				return func(*args, **kwargs)
			except Exception:
				try:
					target_dir = _infer_target_dir(
						args,
						mdruns_dirname=mdruns_dirname,
						remove_system_on_failure=remove_system_on_failure,
					)
					if target_dir is not None and target_dir.exists():
						_dest = script_dir
						_move_logs(target_dir, _dest, log_glob=log_glob)
						shutil.rmtree(target_dir, ignore_errors=True)
				except Exception as cleanup_exc:
					print(f"cleanup_failure: cleanup error: {cleanup_exc}", file=sys.stderr)
				raise

		return wrapper

	# Support both @cleanup_failure and @cleanup_failure(...)
	if _func is not None:
		return decorator(_func)
	return decorator


def _infer_target_dir(
	args: tuple,
	*,
	mdruns_dirname: str,
	remove_system_on_failure: bool,
) -> Optional[Path]:
	if len(args) < 2:
		return None

	sysdir = args[0]
	sysname = args[1]
	if not isinstance(sysdir, (str, os.PathLike)) or not isinstance(sysname, (str, os.PathLike)):
		return None

	sys_root = Path(sysdir) / Path(sysname)
	if remove_system_on_failure:
		return sys_root

	# If runname is provided, default to cleaning only that run directory.
	if len(args) >= 3:
		runname = args[2]
		if isinstance(runname, (str, os.PathLike)):
			return sys_root / mdruns_dirname / Path(runname)

	return sys_root


def _safe_dest_dir(exec_dir: Path, target_dir: Path) -> Path:
	"""Ensure destination for moved logs is outside the directory being removed."""
	try:
		exec_dir_r = exec_dir.resolve()
		target_dir_r = target_dir.resolve()
		try:
			exec_dir_r.relative_to(target_dir_r)
		except Exception:
			return exec_dir_r
		return target_dir_r.parent
	except Exception:
		return exec_dir


def _move_logs(target_dir: Path, dest_dir: Path, *, log_glob: str) -> None:
	if not dest_dir.exists():
		dest_dir.mkdir(parents=True, exist_ok=True)

	try:
		target_dir_r = target_dir.resolve()
	except Exception:
		target_dir_r = target_dir

	for log_path in target_dir_r.rglob(log_glob):
		if not log_path.is_file():
			continue
		dest_path = dest_dir / log_path.name
		try:
			if dest_path.exists():
				dest_path.unlink()
			shutil.move(str(log_path), str(dest_path))
		except Exception:
			# Fall back to copy if move fails (permissions / cross-device / etc.)
			try:
				if dest_path.exists():
					dest_path.unlink()
				shutil.copy2(str(log_path), str(dest_path))
			except Exception:
				pass


