"""Foreground local server with a separate, per-launch site-edit capability."""
import argparse
import os
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description='Run the local OpsFeast Web server. '
                                     'Real Console access requires explicit interactive profile and host options.')
    parser.add_argument('--port', type=int, default=8740, help='Loopback port (default: 8740).')
    parser.add_argument('--data-root', type=Path, help='Existing external installation data root; otherwise use the checkout binding.')
    parser.add_argument('--interactive-profile', help='Explicit profile for the optional real Console service.')
    parser.add_argument('--interactive-host', action='append', default=[], help='Explicitly enable only these host IDs for real Console execution.')
    args = parser.parse_args()
    if bool(args.interactive_profile) != bool(args.interactive_host):
        parser.error('--interactive-profile and --interactive-host must be provided together')
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    try:
        import uvicorn
        from .app import create_app, WEB_ROOT
    except ImportError as exc:
        parser.exit(1, f'Missing optional Web dependency ({exc.name}). Install requirements-web.txt.\n')
    from opsfeast.storage import resolve_data_root
    from opsfeast import ConfigError
    try:
        data_root = resolve_data_root(WEB_ROOT.parent, data_root=args.data_root, required=True)
    except (ConfigError, OSError) as exc:
        parser.exit(1, f'Cannot select installation data: {exc}\n')
    token_path = data_root / f'.opsfeast-web-edit-{args.port}.token'
    token = secrets.token_urlsafe(32)
    try:
        fd = os.open(token_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    except FileExistsError:
        parser.exit(1, f'Edit token file already exists: {token_path.name}. '
                    'Check for a running server; remove this token file only if its server has stopped.\n')
    interactive_options=None
    capability_paths=[]
    try:
        console_options={}
        for role in ('writer','reader'):
            path=data_root/f'.opsfeast-console-{role}-{args.port}.token'
            token_fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            capability_paths.append(path)
            value=secrets.token_urlsafe(32)
            with os.fdopen(token_fd,'w') as stream:stream.write(value+'\n')
            console_options[role+'_token']=value
        if args.interactive_host:
            interactive_options={'targets':[(args.interactive_profile,h) for h in args.interactive_host]}
            for role in ('operator','agent'):
                path=data_root/f'.opsfeast-interactive-{role}-{args.port}.token'
                token_fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
                capability_paths.append(path)
                value=secrets.token_urlsafe(32)
                with os.fdopen(token_fd,'w') as stream:stream.write(value+'\n')
                interactive_options[role+'_token']=value
            print(f'Interactive Console: http://127.0.0.1:{args.port}/interactive (operator/agent tokens in installation data)',flush=True)
        with os.fdopen(fd, 'w') as stream:
            stream.write(token + '\n')
        print(f'Site settings: http://127.0.0.1:{args.port}/settings/site', flush=True)
        print(f'Installation data: {data_root}', flush=True)
        print(f'Local edit token: read {token_path.name} from the installation data directory. '
              'This token edits site presentation and can bootstrap the first administrator; it is not a user login or profile-management credential.', flush=True)
        app=create_app(data_root=data_root, edit_token=token,interactive_options=interactive_options,console_options=console_options)
        uvicorn.run(app, host='127.0.0.1', port=args.port, access_log=False,timeout_graceful_shutdown=5)
    finally:
        if 'app' in locals() and app.state.interactive:app.state.interactive.shutdown()
        for path in capability_paths:path.unlink(missing_ok=True)
        token_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
