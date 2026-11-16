"""Per-installation Web PID marker; no automatic stale-file repair or signaling."""
from contextlib import contextmanager
import os
from pathlib import Path
import signal
import stat

FILENAME = 'web-server.pid'


class ProcessMarkerError(ValueError):
    def __init__(self, message, *, exit_code=1):
        super().__init__(message)
        self.exit_code = exit_code


def existing_marker(path):
    """Conservatively refuse all existing markers, including stale/invalid ones."""
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 32:
            raise ValueError()
        value = path.read_text(encoding='ascii').strip()
        if not value.isascii() or not value.isdecimal() or int(value) < 1:
            raise ValueError()
        pid = int(value)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            raise ProcessMarkerError(f'Stale Web PID file: {path} (PID {pid} is not running). Ask your agent to inspect it; no file was removed and no server was started.') from None
        except PermissionError:
            raise ProcessMarkerError(f'Web PID {pid} exists but cannot be inspected. Refusing to start; preserve {path} for agent inspection.', exit_code=2) from None
        raise ProcessMarkerError(f'Warning: Web PID {pid} is still running. Refusing to start another server. PID file: {path}', exit_code=2)
    except (OSError, UnicodeError, ValueError, OverflowError) as error:
        if isinstance(error, ProcessMarkerError):
            raise
        raise ProcessMarkerError(f'Cannot validate Web PID file: {path}. Ask your agent to inspect it; no automatic repair was attempted.') from None


@contextmanager
def claim(data_root):
    """Reserve the actual process PID, removing only our marker on orderly exit."""
    path = Path(data_root) / FILENAME
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        existing_marker(path)
        raise AssertionError('existing_marker must refuse startup')
    pid = str(os.getpid()) + '\n'
    owned = os.fstat(fd)
    previous = {}
    def terminate(signum, frame):
        raise SystemExit(128 + signum)
    try:
        # Cover signals before Uvicorn installs its own orderly-shutdown handlers.
        for signum in (signal.SIGTERM, signal.SIGHUP):
            if signum == signal.SIGHUP and signal.getsignal(signum) == signal.SIG_IGN:
                continue  # Preserve an explicitly selected nohup lifetime.
            previous[signum] = signal.signal(signum, terminate)
        with os.fdopen(fd, 'w', encoding='ascii') as stream:
            stream.write(pid)
            stream.flush()
            os.fsync(stream.fileno())
        yield path
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        try:
            current = path.lstat()
            if (current.st_dev, current.st_ino) == (owned.st_dev, owned.st_ino) and path.read_text(encoding='ascii') == pid:
                path.unlink()
        except (FileNotFoundError, UnicodeError):
            pass
