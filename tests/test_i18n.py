"""Every interface string that goes through the translator has a Spanish entry."""
import ast
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intrinsic.ui.i18n import ES, GLOSSARY_ES  # noqa: E402

UI_FILES = ('app.py', 'intrinsic/dashboard_panel.py', 'intrinsic/bank_panel.py', 'intrinsic/ui/components.py')


def _const(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def translated_literals():
    """String literals the UI passes to t(), _chart(), line(), plus the sidebar field tables."""
    found = set()
    for rel in UI_FILES:
        with open(os.path.join(ROOT, rel)) as fh:
            tree = ast.parse(fh.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                name, args = node.func.id, node.args
                if name == 't' and args and _const(args[0]):
                    found.add(_const(args[0]))
                elif name == '_chart':
                    found |= {_const(a) for a in args[1:3] if _const(a)}
                elif name == 'line' and args and _const(args[0]):
                    found.add(_const(args[0]))
            if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id in ('fields', 'names', 'BETA_BODY', 'BETA_NOTE')
                                                    for x in node.targets):
                for sub in ast.walk(node.value):
                    s = _const(sub)
                    if s and (' ' in s or s.endswith('(%)')):
                        found.add(s)
    return found


class I18nTests(unittest.TestCase):
    def test_every_ui_string_has_spanish(self):
        missing = sorted(s for s in translated_literals() if s not in ES)
        self.assertEqual(missing, [], f'{len(missing)} UI strings have no Spanish translation')

    def test_placeholders_match(self):
        import string
        fields = lambda s: {f for _, f, _, _ in string.Formatter().parse(s) if f}
        bad = [k for k, v in ES.items() if '{' in k and fields(k) != fields(v)]
        self.assertEqual(bad, [])

    def test_glossary_covers_english_terms(self):
        from intrinsic.dashboard_panel import GLOSSARY
        self.assertEqual(set(GLOSSARY) - set(GLOSSARY_ES), set())


if __name__ == '__main__':
    unittest.main()
