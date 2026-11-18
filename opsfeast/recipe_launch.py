"""Recipe launch guidance 0.1.0: direct runner or explicit agent conversation."""
from . import ConfigError


def describe(metadata):
    value = metadata.get('launch', {'mode': 'direct'})
    if not isinstance(value, dict) or set(value) - {'mode', 'prompt', 'river'}:
        raise ConfigError('recipe launch must contain mode and optional prompt')
    if value.get('mode') not in ('direct', 'agent'):
        raise ConfigError('recipe launch.mode must be direct or agent')
    prompt = value.get('prompt', '')
    if not isinstance(prompt, str) or len(prompt) > 8000 or '\x00' in prompt:
        raise ConfigError('recipe launch.prompt must be text up to 8000 characters without NUL')
    if value['mode'] == 'agent' and not prompt.strip():
        raise ConfigError('agent launch requires a nonempty suggested prompt')
    if type(value.get('river', False)) is not bool:
        raise ConfigError('recipe launch.river must be boolean')
    if value.get('river'):
        runner = metadata.get('runner') or {}
        if not isinstance(runner, dict) or runner.get('contract') not in (None, '', 'python-workflow'):
            raise ConfigError('recipe launch.river requires python-workflow')
    from .staged_execution import stages
    stages(metadata)
    return {'mode': value['mode'], 'prompt': prompt, 'river': value.get('river', False)}
