"""Tutorial chapter 3: person on the verb, not English tense."""

from __future__ import annotations

import io
import unittest

from phyx.conjugation import CONJUGATIONS, inflect, lemma_of, split_root
from phyx.errors import ParseError
from phyx.hints import explain_word
from phyx.interpreter import run_source
from phyx.parser import parse


class TutorialTableTests(unittest.TestCase):
    """The published zept (defile) table must come out of inflect() exactly."""

    def test_zept_cells(self):
        expected = {
            (1, 1): "zepot",
            (2, 1): "zepaat",
            (3, 1): "zepať",
            (4, 1): "zepat",
            (1, 2): "zøpat",
            (2, 2): "zøput",
            (3, 2): "zøpt",
            (4, 2): "zøpet",
            (1, 3): "zeπat",
            (2, 3): "zeπut",
            (3, 3): "zept",
            (4, 3): "zepyt",
            (1, 4): "zøpat",
            (2, 4): "zepøt",
            (3, 4): "zepet",
            (4, 4): "zepeet",
        }
        for persons, form in expected.items():
            with self.subTest(persons=persons):
                self.assertEqual(inflect("zept", *persons), form)

    def test_kill_third_to_fourth_is_qabe(self):
        # tutorial example: qab' + e before last consonant → qabe'
        self.assertEqual(inflect("qab'", 3, 4), "qabe'")
        self.assertEqual(lemma_of("qabe'"), "qab'")

    def test_lemma_is_third_to_third(self):
        self.assertEqual(inflect("babg", 3, 3), "babg")
        self.assertEqual(lemma_of("babg"), "babg")

    def test_split_root(self):
        self.assertEqual(split_root("zept"), ("zep", "t"))
        self.assertEqual(split_root("qab'"), ("qab", "'"))
        self.assertEqual(split_root("babg"), ("bab", "g"))
        self.assertIsNone(split_root("xe"))
        self.assertIsNone(split_root("ba"))


class RuntimeTests(unittest.TestCase):
    def test_conjugated_add_is_add(self):
        # 3→4 they → one: insert e before last consonant
        self.assertEqual(inflect("babg", 3, 4), "babeg")
        out = io.StringIO()
        run_source("!1-2-babeg.", stdout=out)
        self.assertEqual(out.getvalue(), "3\n")
        run_source("!1-2-babg.", stdout=out)

    def test_lemma_and_inflection_agree(self):
        out_a, out_b = io.StringIO(), io.StringIO()
        run_source("!0a-5-mɒɣg.", stdout=out_a)
        inflected = inflect("mɒɣg", 3, 4)
        self.assertEqual(inflected, "mɒɣeg")
        run_source(f"!0a-5-{inflected}.", stdout=out_b)
        self.assertEqual(out_a.getvalue(), out_b.getvalue())

    def test_conjugated_put(self):
        form = inflect("ţə''", 3, 4)
        self.assertIsNotNone(form)
        out = io.StringIO()
        run_source(f"^xe-5-x-{form}.\n!x.", stdout=out)
        self.assertEqual(out.getvalue(), "5\n")

    def test_cannot_name_an_ability_after_a_conjugation(self):
        with self.assertRaises(ParseError):
            parse("^ťe-n-babeg:\n    ^lo-n-'iţpənn.")

    def test_explain_names_persons_not_tense(self):
        text = explain_word("babeg")
        self.assertIsNotNone(text)
        self.assertIn("babg", text)
        self.assertIn("they", text)
        self.assertIn("one", text)
        self.assertIn("mood marker", text)
        self.assertNotIn("past tense", text.lower())


class MapIntegrityTests(unittest.TestCase):
    def test_every_listed_form_stems_to_a_verb(self):
        self.assertGreater(len(CONJUGATIONS), 100)
        for form, conj in CONJUGATIONS.items():
            self.assertEqual(lemma_of(form), conj.lemma)
            self.assertEqual(inflect(conj.lemma, conj.doing, conj.receiving), form)


if __name__ == "__main__":
    unittest.main()
