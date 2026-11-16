"""Loopback Web server with an optional memory-only agent owner controller."""
import argparse
from pathlib import Path
import secrets


def main():
    parser = argparse.ArgumentParser(description='Run the local OpsFeast Web server. '
                                     'Real Console access requires explicit interactive profile and host options.')
    parser.add_argument('--port', type=int, help='Persist this Web port in installation-data (1024-65535); default: saved port or automatic first allocation.')
    parser.add_argument('--agent-control', action='store_true', help='Memory-only agent owner capability and JSON-lines control on private stdin/stdout.')
    parser.add_argument('--data-root', type=Path, help='Existing external installation data root; otherwise use the checkout binding.')
    parser.add_argument('--interactive-profile', help='Explicit profile for the optional real Console service.')
    parser.add_argument('--interactive-host', action='append', default=[], help='Explicitly enable only these host IDs for real Console execution.')
    args = parser.parse_args()
    if bool(args.interactive_profile) != bool(args.interactive_host):
        parser.error('--interactive-profile and --interactive-host must be provided together')
    if args.port is not None and not 1024 <= args.port <= 65535:
        parser.error('--port must be between 1024 and 65535')
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
    from .process import claim, ProcessMarkerError
    try:
        with claim(data_root):
            serve(args, data_root, parser, uvicorn, create_app, WEB_ROOT)
    except ProcessMarkerError as exc:
        parser.exit(exc.exit_code, str(exc) + '\n')
    except OSError as exc:
        parser.exit(1, f'Cannot start Web: {exc}\n')


def serve(args, data_root, parser, uvicorn, create_app, WEB_ROOT):
    from opsfeast import ConfigError
    from opsfeast.web_settings import bind_server
    try:
        listener=bind_server(WEB_ROOT.parent,args.port,data_root=data_root)
    except (ConfigError,OSError) as exc:
        parser.exit(1,f'Cannot reserve installation Web port: {exc}\n')
    port=listener.getsockname()[1]
    token = secrets.token_urlsafe(32)
    interactive_options = ({'targets':[(args.interactive_profile,h) for h in args.interactive_host]}
                           if args.interactive_host else None)
    app=None
    try:
        app=create_app(data_root=data_root,agent_token=token if args.agent_control else None,interactive_options=interactive_options)
        if args.agent_control:
            from .agent_control import run
            run(app,token,port=port,listener=listener)
        else:
            # Browser-only service for an already configured administrator.
            del token
            print(f'Web workspace: http://127.0.0.1:{port}',flush=True)
            server=uvicorn.Server(uvicorn.Config(app,host='127.0.0.1',port=port,access_log=False,timeout_graceful_shutdown=5))
            server.run(sockets=[listener])
    finally:
        listener.close()
        if app is not None and app.state.interactive:app.state.interactive.shutdown()



if __name__ == '__main__':
    main()
