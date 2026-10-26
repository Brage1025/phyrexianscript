import unittest

from phyx.errors import LexError
from phyx.lexer import tokenize, transliterate, untransliterate
from phyx.numerals import BASILICA_TO_ASCII, hex_digit, is_numeral_start


def kinds(src):
    return [(t.kind, t.value) for t in tokenize(src) if t.kind != "EOF"]


class LexerTests(unittest.TestCase):
    def test_punctuation_and_words(self):
        self.assertEqual(
            kinds("^xe-5-x-ţə''."),
            [
                ("START", "^"),
                ("WORD", "xe"),
                ("SEP", "-"),
                ("NUMBER", 5),
                ("SEP", "-"),
                ("WORD", "x"),
                ("SEP", "-"),
                ("WORD", "ţə''"),
                ("END", "."),
            ],
        )

    def test_numbers_are_hexadecimal(self):
        self.assertEqual(
            kinds("!10-0ff-əx1a."),
            [
                ("START", "!"),
                ("NUMBER", 16),
                ("SEP", "-"),
                ("NUMBER", 255),
                ("SEP", "-"),
                ("NUMBER", -26),
                ("END", "."),
            ],
        )

    def test_number_glued_to_word_is_an_error(self):
        with self.assertRaises(LexError):
            tokenize("^xe-5x.")
        with self.assertRaises(LexError):
            tokenize("^xe-x5.")

    def test_strings_with_escapes(self):
        toks = kinds(r'!"a \"b\" c\n".')
        self.assertEqual(toks[1], ("STRING", 'a "b" c\n'))

    def test_unterminated_string(self):
        with self.assertRaises(LexError):
            tokenize('!"open.')

    def test_comment_is_dropped(self):
        self.assertEqual(kinds("^rukx anything. goes: here\n!1."), [("START", "!"), ("NUMBER", 1), ("END", ".")])

    def test_shebang_is_dropped_and_line_numbers_hold(self):
        toks = tokenize("#!/usr/bin/env phyx\n!1.")
        meaningful = [(t.kind, t.value, t.line) for t in toks if t.kind != "EOF"]
        self.assertEqual(meaningful, [("START", "!", 2), ("NUMBER", 1, 2), ("END", ".", 2)])

    def test_indent_recorded_on_tokens(self):
        toks = tokenize("^ba-x:\n    !x.\n\t!y.")
        starts = [t for t in toks if t.kind == "START"]
        self.assertEqual([t.indent for t in starts], [0, 4, 4])

    def test_bom_and_nfc(self):
        # decomposed s + caron must normalise to š
        self.assertEqual(kinds("\ufeff!s\u030c."), [("START", "!"), ("WORD", "š"), ("END", ".")])

    def test_unknown_symbol(self):
        with self.assertRaises(LexError):
            tokenize("^xe-a-b-babg;")

    def test_transliteration(self):
        self.assertEqual(transliterate("TTE''"), "ţə''")
        self.assertEqual(transliterate("THuqx"), "θuqx")
        self.assertEqual(transliterate("PHyrx GGx GHy Gz"), "φyrx ǧx ǥy ɣz")
        self.assertEqual(transliterate("aXEw' KHi LZiww NNe"), "aχəw' ķi ɮiww ɴe")
        # strings are untouched
        self.assertEqual(transliterate('!"THE END"-TTE.'), '!"THE END"-ţə.')
        self.assertEqual(untransliterate("ţə'' θuqx"), "TTE'' THuqx")

    def test_ascii_mode_in_tokenizer(self):
        toks = tokenize("^xe-5-x-TTE''.", ascii_mode=True)
        self.assertEqual(toks[7].value, "ţə''")

    def test_basilica_digits_are_the_same_hex(self):
        # Mathematical Monospace 0-9 A-F: same numerals as Arabic hex.
        mono0 = "\N{MATHEMATICAL MONOSPACE DIGIT ZERO}"
        mono1 = "\N{MATHEMATICAL MONOSPACE DIGIT ONE}"
        mono_a = "\N{MATHEMATICAL MONOSPACE CAPITAL A}"
        mono_f = "\N{MATHEMATICAL MONOSPACE CAPITAL F}"
        self.assertTrue(is_numeral_start(mono0))
        self.assertTrue(is_numeral_start(mono_a))
        self.assertEqual(hex_digit(mono_a), "A")
        self.assertEqual(kinds(f"!{mono1}{mono0}."), [("START", "!"), ("NUMBER", 16), ("END", ".")])
        self.assertEqual(kinds(f"!{mono0}{mono_a}."), [("START", "!"), ("NUMBER", 10), ("END", ".")])
        self.assertEqual(
            kinds(f"!əx{mono1}{mono_a}."),
            [("START", "!"), ("NUMBER", -26), ("END", ".")],
        )
        self.assertEqual(kinds(f"!{mono_f}{mono_f}."), [("START", "!"), ("NUMBER", 255), ("END", ".")])
        mixed = kinds(f"!0{mono_a}-10.")
        self.assertEqual(mixed[1], ("NUMBER", 10))
        self.assertEqual(mixed[3], ("NUMBER", 16))
        self.assertGreaterEqual(len(BASILICA_TO_ASCII), 16)

    def test_ascii_letter_a_is_still_a_name(self):
        self.assertEqual(
            kinds("!a."),
            [("START", "!"), ("WORD", "a"), ("END", ".")],
        )


if __name__ == "__main__":
    unittest.main()
