import tempfile
import unittest
from pathlib import Path

from phyx.cli import main
from phyx.scaffold import create
from phyx.testing import run_test_file


class NewTests(unittest.TestCase):
    def test_writes_program_and_test(self):
        folder = Path(tempfile.mkdtemp())
        program, test = create("greet", directory=folder)
        self.assertEqual(program.name, "greet.phyx")
        self.assertEqual(test.name, "test_greet.phyx")
        prog = program.read_text(encoding="utf-8")
        self.assertTrue(prog.startswith("#! /usr/bin/env phyx\n"))
        self.assertIn("^ťe-n-greet:", prog)
        self.assertIn("'iţpənn", prog)
        self.assertIn('^lo-"greet.phyx"-bukð.', test.read_text(encoding="utf-8"))
        result = run_test_file(test)
        self.assertTrue(result.ok, result.detail)

    def test_ascii_scaffold(self):
        folder = Path(tempfile.mkdtemp())
        program, test = create("greet", directory=folder, ascii_mode=True)
        prog = program.read_text(encoding="utf-8")
        self.assertIn("^Te-n-greet:", prog)
        self.assertNotIn("ťe", prog)
        result = run_test_file(test, ascii_mode=True)
        self.assertTrue(result.ok, result.detail)

    def test_refuse_overwrite_and_reserved(self):
        folder = Path(tempfile.mkdtemp())
        create("greet", directory=folder)
        with self.assertRaises(FileExistsError):
            create("greet", directory=folder)
        with self.assertRaises(ValueError):
            create("babg", directory=folder)
        with self.assertRaises(ValueError):
            create("../x", directory=folder)

    def test_cli_new(self):
        folder = Path(tempfile.mkdtemp())
        code = main(["new", "greet", "-d", str(folder)])
        self.assertEqual(code, 0)
        self.assertTrue((folder / "greet.phyx").is_file())
        self.assertTrue((folder / "test_greet.phyx").is_file())
        code = main(["new", "greet", "-d", str(folder)])
        self.assertEqual(code, 1)
