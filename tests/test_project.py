import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class ProjectTests(unittest.TestCase):
    def test_python_files_parse(self):
        for path in ROOT.glob("*.py"):
            ast.parse(path.read_text(encoding="utf-8"))

    def test_exactly_100_slash_commands(self):
        tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        count = sum(
            1 for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef)
            and any(
                isinstance(dec, ast.Call)
                and isinstance(dec.func, ast.Attribute)
                and dec.func.attr == "command"
                for dec in node.decorator_list
            )
        )
        self.assertEqual(count, 100)

    def test_branding_is_hmb_global(self):
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("HMB GLOBAL", main)
        self.assertIn("HMB GLOBAL", readme)

if __name__ == "__main__":
    unittest.main()
