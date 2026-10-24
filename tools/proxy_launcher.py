"""Private child-process entrypoint for process_environment.proxy_options."""
import json
import os
import sys


def main():
    try:
        path = sys.argv[1]
        with open(path, encoding='utf-8') as stream:
            payload = json.load(stream)
        os.unlink(path)
        environment = os.environ.copy()
        for name, value in payload['environment'].items():
            if value is None:
                environment.pop(name, None)
            else:
                environment[name] = value
        argv = payload['argv']
        os.execvpe(argv[0], argv, environment)
    except Exception:
        # Neither exception messages nor payload/argv may enter the SSH stream.
        print('OpsFeast proxy launch failed', file=sys.stderr)
        return 126


if __name__ == '__main__':
    sys.exit(main())
