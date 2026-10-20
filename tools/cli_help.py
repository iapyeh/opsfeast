"""Task grouping for top-level CLI discovery; command parsing stays in argparse."""
import argparse


COMMAND_GROUPS = (
    ('Profiles and setup', ('init', 'profiles', 'use', 'attach', 'detach', 'instance')),
    ('Hosts and access (hosts.yaml)',
     ('check', 'dump', 'test-connection', 'host-init', 'test-host', 'test-su', 'test-sudo', 'check-access')),
    ('Recipes and reports', ('inspect-recipe', 'recipes', 'inventory')),
    ('Retained data and consumers', ('retention', 'consumers')),
    ('Vault content', ('vault',)),
)


class TaskHelpFormatter(argparse.HelpFormatter):
    """Render one subparser action as labeled groups using its real command summaries."""

    def add_argument(self, action):
        super().add_argument(action)
        if getattr(action, 'help_groups', None) is not None:
            # Include the extra heading indentation in column sizing on every Python.
            widths = [len(self._format_action_invocation(entry)) + self._current_indent + self._indent_increment
                      for entry in action._get_subactions()]
            self._action_max_length = max([self._action_max_length, *widths])

    def _format_action(self, action):
        groups = getattr(action, 'help_groups', None)
        if groups is None:
            return super()._format_action(action)
        # argparse's own pseudo-actions preserve summary wrapping, aliases and alignment.
        entries = {entry.dest: entry for entry in action._get_subactions()}
        rendered = []
        shown = set()

        def section(title, names):
            selected = [name for name in names if name in entries and name not in shown]
            if not selected:
                return
            if rendered:
                rendered.append('\n')
            rendered.append(' ' * self._current_indent + title + ':\n')
            self._indent()
            try:
                for name in selected:
                    rendered.append(super(TaskHelpFormatter, self)._format_action(entries[name]))
                    shown.add(name)
            finally:
                self._dedent()

        for title, names in groups:
            section(title, names)
        # A later command must remain discoverable even before its group is assigned.
        section('Other commands', [name for name in entries if name not in shown])
        return ''.join(rendered)
