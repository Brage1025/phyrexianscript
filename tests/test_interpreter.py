import io
import os
import unittest

from phyx.errors import ParseError, RuntimeFault, UserMistake
from phyx.interpreter import run_source


def run(src, stdin="", **kw):
    out = io.StringIO()
    run_source(src, stdout=out, stdin=io.StringIO(stdin), **kw)
    return out.getvalue()


class ArithmeticTests(unittest.TestCase):
    def test_hex_in_hex_out(self):
        self.assertEqual(run("!0a-0a-babg,10-1-mɒɣg,3-4-tøwp,0ff."), "14 0f 0c 0ff\n")

    def test_negative_and_division(self):
        self.assertEqual(run("!əx1a,7-2-χɬkevk,7-2-geft,əx7-2-χɬkevk."), "əx1a 3 1 əx4\n")

    def test_number_words(self):
        self.assertEqual(run("!'ii-ķu-babg-ķi-tøwp."), "9\n")

    def test_division_by_zero(self):
        with self.assertRaisesRegex(RuntimeFault, "zero"):
            run("!1-0-χɬkevk.")

    def test_type_errors_name_the_kinds(self):
        with self.assertRaisesRegex(RuntimeFault, "cannot add"):
            run('!1-"a"-babg.')

    def test_twice_half_random(self):
        self.assertEqual(run("!5-ķus'ər,5-əxķus'ər."), "0a 2\n")
        out = run("!0a-'uɬč.", seed=1)
        self.assertTrue(0 <= int(out.strip(), 16) < 10)

    def test_integer_power(self):
        self.assertEqual(run("!2-8-lu'f,5-0-lu'f."), "100 1\n")
        with self.assertRaisesRegex(RuntimeFault, "negative"):
            run("!2-əx1-lu'f.")


class LogicTests(unittest.TestCase):
    def test_comparisons(self):
        self.assertEqual(run("!1-2-grmɒɣg,2-1-korxgr,1-1-ǆ'ynpp,1-əxbytp-ǆ'ynpp."),
                         "əxbytp əxbytp əxbytp bytp\n")

    def test_logic(self):
        self.assertEqual(run("!əxbytp-bytp-xə,əxbytp-bytp-ðə,bytp-əx,0-əx,\"\"-əx."),
                         "bytp əxbytp əxbytp əxbytp əxbytp\n")

    def test_choose(self):
        self.assertEqual(run('!1-"a"-"b"-ʁšθakɴ,0-"a"-"b"-ʁšθakɴ.'), "a b\n")

    def test_string_ordering(self):
        self.assertEqual(run('!"a"-"b"-grmɒɣg.'), "əxbytp\n")
        with self.assertRaises(RuntimeFault):
            run('!"a"-1-grmɒɣg.')


class VariableTests(unittest.TestCase):
    def test_assign_and_update(self):
        self.assertEqual(run("^xe-1-x-ţə''.\n^xe-x-1-babg-x-ţə''.\n!x."), "2\n")

    def test_unknown_word(self):
        with self.assertRaisesRegex(RuntimeFault, "unknown word 'y'"):
            run("!y.")

    def test_constants_cannot_change(self):
        with self.assertRaisesRegex(RuntimeFault, "fixed in the past"):
            run("^'u-1-x-ţə''.\n^xe-2-x-ţə''.")
        with self.assertRaisesRegex(RuntimeFault, "already has a value"):
            run("^xe-1-x-ţə''.\n^'u-2-x-ţə''.")

    def test_assignment_is_an_expression(self):
        self.assertEqual(run("!5-x-ţə''-x-babg."), "0a\n")

    def test_for_cannot_overwrite_a_constant(self):
        with self.assertRaisesRegex(RuntimeFault, "fixed in the past"):
            run("^'u-0-i-ţə''.\n^aχəw'-i-dl-3-ronɣ:!i.")


class ControlFlowTests(unittest.TestCase):
    def test_if_chain(self):
        src = (
            "^ťe-n-sign:\n"
            "    ^ba-n-0-grmɒɣg:lo-\"neg\"-'iţpənn.\n"
            "    ^qit-ba-n-0-ǆ'ynpp:lo-\"zero\"-'iţpənn.\n"
            "    ^qit:lo-\"pos\"-'iţpənn.\n"
            "!əx1-sign,0-sign,1-sign.\n"
        )
        self.assertEqual(run(src), "neg zero pos\n")

    def test_unless(self):
        self.assertEqual(run('^bu-bytp:!"a".\n^əx-əxbytp:!"b".\n^bu-əxbytp:!"c".'), "a\n")

    def test_while_break_continue(self):
        src = (
            "^xe-0-i-ţə''.\n"
            "^baxuφ-əxbytp:\n"
            "    ^xe-i-1-babg-i-ţə''.\n"
            "    ^ba-i-3-ǆ'ynpp:lo-ɢnagɮ.\n"
            "    ^ba-i-5-korxgr:lo-lups.\n"
            "    !i.\n"
        )
        self.assertEqual(run(src), "1\n2\n4\n5\n")

    def test_for_over_list_text_book(self):
        self.assertEqual(run("^aχəw'-x-dl-3-ronɣ:!x."), "0\n1\n2\n")
        self.assertEqual(run("^aχəw'-c-dl-\"ab\":!c."), "a\nb\n")
        self.assertEqual(run("^aχəw'-k-dl-\"x\"-1-\"y\"-2-2-tekt:!k."), "x\ny\n")

    def test_for_over_number_fails(self):
        with self.assertRaisesRegex(RuntimeFault, "cannot walk"):
            run("^aχəw'-x-dl-3:!x.")

    def test_control_words_outside_context(self):
        with self.assertRaises(ParseError) as stopped:
            run("^lo-lups.")
        self.assertIn("outside of a loop", stopped.exception.message)
        self.assertEqual(stopped.exception.line, 1)
        self.assertTrue(stopped.exception.hint)
        with self.assertRaises(ParseError) as returned:
            run("^lo-1-'iţpənn.")
        self.assertIn("outside of an ability", returned.exception.message)
        self.assertEqual(returned.exception.line, 1)
        self.assertTrue(returned.exception.hint)


class AbilityTests(unittest.TestCase):
    def test_recursion_and_hoisting(self):
        src = (
            "!5-fact.\n"
            "^ťe-n-fact:\n"
            "    ^ba-n-2-grmɒɣg:lo-1-'iţpənn.\n"
            "    ^lo-n-n-1-mɒɣg-fact-tøwp-'iţpənn.\n"
        )
        self.assertEqual(run(src), "78\n")  # 120

    def test_return_without_value_is_void(self):
        self.assertEqual(run("^ťe-f:\n    ^lo-'iţpənn.\n!f."), "əixiww\n")

    def test_locals_do_not_leak_but_globals_are_visible(self):
        src = (
            "^xe-1-g-ţə''.\n"
            "^ťe-f:\n"
            "    ^xe-5-local-ţə''.\n"
            "    ^xe-g-1-babg-g-ţə''.\n"
            "    ^lo-local-'iţpənn.\n"
            "!f,g.\n"
            "!local.\n"
        )
        with self.assertRaisesRegex(RuntimeFault, "unknown word 'local'"):
            run(src)
        self.assertEqual(run(src.rsplit("\n!local.", 1)[0]), "5 2\n")

    def test_nested_abilities_close_over_scope(self):
        src = (
            "^ťe-n-outer:\n"
            "    ^ťe-inner:\n"
            "        ^lo-n-ķus'ər-'iţpənn.\n"
            "    ^lo-inner-'iţpənn.\n"
            "!4-outer.\n"
        )
        self.assertEqual(run(src), "8\n")

    def test_too_deep(self):
        with self.assertRaisesRegex(RuntimeFault, "too deeply"):
            run("^ťe-f:\n    ^lo-f-'iţpənn.\n!f.")

    def test_compiled_recursion_of_8000_returns(self):
        # 1f40 is 8000. The compiled engine uses one host frame per call.
        src = (
            "^ťe-n-cnt:\n"
            "    ^ba-n-0-grmɒɣg:lo-0-'iţpənn.\n"
            "    ^lo-n-1-mɒɣg-cnt-'iţpənn.\n"
            "!1f40-cnt.\n"
        )
        self.assertEqual(run(src, treewalk=False), "0\n")

    def test_phyx_recursion_sets_the_ceiling(self):
        deep = (
            "^ťe-n-cnt:\n"
            "    ^ba-n-0-grmɒɣg:lo-0-'iţpənn.\n"
            "    ^lo-n-1-mɒɣg-cnt-'iţpənn.\n"
            "!100-cnt.\n"
        )
        shallow = deep.replace("!100-cnt.", "!20-cnt.")
        previous = os.environ.get("PHYX_RECURSION")
        os.environ["PHYX_RECURSION"] = "200"
        try:
            self.assertEqual(run(shallow, treewalk=False), "0\n")
            with self.assertRaisesRegex(RuntimeFault, "too deeply"):
                run(deep, treewalk=False)
            os.environ["PHYX_RECURSION"] = "nope"
            with self.assertRaisesRegex(RuntimeFault, "PHYX_RECURSION"):
                run("!1.", treewalk=False)
            os.environ["PHYX_RECURSION"] = "1000000"
            with self.assertRaisesRegex(RuntimeFault, "does not fit"):
                run("!1.", treewalk=False)
        finally:
            if previous is None:
                os.environ.pop("PHYX_RECURSION", None)
            else:
                os.environ["PHYX_RECURSION"] = previous

    def test_ability_is_truthy_and_can_be_activated(self):
        src = (
            "^ťe-a-b-add:\n"
            "    ^lo-a-b-babg-'iţpənn.\n"
            "^xe-add-fn-ţə''.\n"
            '^ba-fn:!"yes".\n'
            "!3-4-2-ťewn-fn-čtəčpliɣn.\n"
        )
        self.assertEqual(run(src), "yes\n7\n")

    def test_activate_arity_mismatch(self):
        with self.assertRaisesRegex(RuntimeFault, "wants 2"):
            run("^ťe-a-b-add:\n    ^lo-a-b-babg-'iţpənn.\n^xe-add-fn-ţə''.\n!1-1-ťewn-fn-čtəčpliɣn.")

    def test_quote_zero_arity_and_activate(self):
        src = (
            "^ťe-greet:\n"
            '    !"hi".\n'
            "^xe-greet-naķm-fn-ţə''.\n"
            "^lo-0-ťewn-fn-čtəčpliɣn.\n"
        )
        self.assertEqual(run(src), "hi\n")

    def test_command_args(self):
        self.assertEqual(run("!'uxq.", argv=["red", "blue"]), '"red"-"blue"-2-ťewn\n')
        self.assertEqual(run("!'uxq-samk."), "0\n")


class CollectionTests(unittest.TestCase):
    def test_list_ops(self):
        src = (
            "^xe-1-2-3-3-ťewn-l-ţə''.\n"
            "^xe-l-4-bɬølπ.\n"
            "^xe-9-l-0-tapq-ţə''.\n"
            "!l,l-samk,l-'iixtfu'q,l-ǩeǆylqitsodrm,l-əx1-tapq,2-l-dl,7-l-dl.\n"
            "!l-1-čxət',l.\n"
            "!l-1-3-ɣɒzɢ,l-əixiww-2-ɣɒzɢ,l-tluxt-l-ǆ'ynpp.\n"
        )
        self.assertEqual(
            run(src),
            "9-2-3-4-4-ťewn 4 9 4 4 əxbytp bytp\n"
            "2 9-3-4-3-ťewn\n"
            "3-4-2-ťewn 9-3-2-ťewn əxbytp\n",
        )

    def test_index_errors(self):
        with self.assertRaisesRegex(RuntimeFault, "no item"):
            run("!1-1-ťewn-5-tapq.")
        with self.assertRaisesRegex(RuntimeFault, "has no beginning"):
            run("!0-ťewn-'iixtfu'q.")

    def test_book_ops(self):
        src = (
            '^xe-"a"-1-"b"-2-2-tekt-b-ţə\'\'.\n'
            '^xe-3-b-"c"-tapq-ţə\'\'.\n'
            '!b-"c"-tapq,b-samk,"a"-b-dl,"z"-b-dl,b-rukxtekt.\n'
            '!b-"a"-čxət\',b.\n'
        )
        self.assertEqual(
            run(src),
            '3 3 əxbytp bytp "a"-"b"-"c"-3-ťewn\n'
            '1 "b"-2-"c"-3-2-tekt\n',
        )
        with self.assertRaisesRegex(RuntimeFault, "no entry"):
            run('!0-tekt-"k"-tapq.')

    def test_text_ops(self):
        src = (
            '!"a,b"-","-pən\'g,"abc"-""-pən\'g-"|"-raφoj,"hello"-1-3-ɣɒzɢ,"hello"-samk,"ell"-"hello"-dl.\n'
            '!"ab"-3-tøwp,"a"-"b"-babg,"abc"-əx1-tapq.\n'
        )
        self.assertEqual(run(src), '"a"-"b"-2-ťewn a|b|c el 5 əxbytp\nababab ab c\n')

    def test_conversion_and_types(self):
        self.assertEqual(run('!"ff"-asərθ,"əx10"-asərθ,əxbytp-asərθ,0a-xušv-"!"-babg.'), "0ff əx10 1 0a!\n")
        mono_a = "\N{MATHEMATICAL MONOSPACE CAPITAL A}"
        self.assertEqual(run(f'!"{mono_a}"-asərθ.'), "0a\n")
        self.assertEqual(run("!1-πøkk,\"\"-πøkk,bytp-πøkk,əixiww-πøkk,0-ťewn-πøkk,0-tekt-πøkk."),
                         "asərθ rukx wija'x əixiww ťewn tekt\n")
        with self.assertRaises(RuntimeFault):
            run('!"xyz"-asərθ.')


class IOTests(unittest.TestCase):
    def test_question_reads_a_line(self):
        self.assertEqual(run('?"name: "-n.\n!"hi",n.', stdin="norn\n"), "name: hi norn\n")

    def test_question_at_eof_gives_void(self):
        self.assertEqual(run("?n.\n!n.", stdin=""), "əixiww\n")

    def test_speak_passes_through(self):
        self.assertEqual(run("!1-2-babg-pihš-2-tøwp."), "3\n6\n")

    def test_reveal_uses_source_form(self):
        self.assertEqual(run('^xe-"a"-krepg.'), '"a"\n')

    def test_ask_verb(self):
        self.assertEqual(run('!"q "-\'ətsxn.', stdin="42\n"), "q 42\n")


class ErrorTests(unittest.TestCase):
    def test_mistake_is_caught_with_blame(self):
        src = (
            "^baqilx:\n"
            '    ^xe-"bad"-ɬšeɴazv.\n'
            '    !"no".\n'
            "^qit:\n"
            "    !dekp.\n"
        )
        self.assertEqual(run(src), "bad\n")

    def test_runtime_fault_is_caught(self):
        self.assertEqual(run("^baqilx:\n    !1-0-χɬkevk.\n^qit:\n    !\"caught\".\n"), "caught\n")

    def test_try_without_handler_swallows(self):
        self.assertEqual(run("^baqilx:\n    !1-0-χɬkevk.\n!\"after\".\n"), "after\n")

    def test_uncaught_mistake_carries_value_and_line(self):
        with self.assertRaises(UserMistake) as cm:
            run("!1.\n^xe-7-ɬšeɴazv.")
        self.assertEqual(cm.exception.value, 7)
        self.assertEqual(cm.exception.line, 2)

    def test_assert(self):
        self.assertEqual(run("^ǩaπa-1-1-ǆ'ynpp.\n!\"ok\"."), "ok\n")
        with self.assertRaisesRegex(RuntimeFault, "must.*: nope"):
            run('^ǩaπa-bytp,"nope".')

    def test_control_flow_passes_through_try(self):
        src = (
            "^aχəw'-i-dl-5-ronɣ:\n"
            "    ^baqilx:\n"
            "        ^ba-i-2-ǆ'ynpp:lo-lups.\n"
            "    !i.\n"
        )
        self.assertEqual(run(src), "0\n1\n")


class AsciiModeTests(unittest.TestCase):
    def test_ascii_program(self):
        self.assertEqual(run("^xe-5-x-TTE''.\n!x-KHus'Er.", ascii_mode=True), "0a\n")


class IncludeTests(unittest.TestCase):
    def test_cast_library(self):
        from pathlib import Path

        libdir = Path(__file__).resolve().parent.parent / "examples"
        out = io.StringIO()
        run_source(
            '^lo-"lib_asərθ.phyx"-bukð.\n!əx0a-abs,30-12-ǩeznasərθ.',
            stdout=out,
            base_dir=libdir,
        )
        self.assertEqual(out.getvalue(), "0a 6\n")

    def test_cast_missing_file(self):
        with self.assertRaisesRegex(RuntimeFault, "no such text"):
            run('^lo-"nope.phyx"-bukð.')

    def test_research_and_spread_a_note(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as td:
            out = io.StringIO()
            run_source(
                '^lo-"hi"-"n.rukx"-mɴyrx.\n!"n.rukx"-brøtjt.',
                stdout=out,
                base_dir=td,
            )
            self.assertEqual(out.getvalue(), "hi\n")
            self.assertEqual((Path(td) / "n.rukx").read_text(encoding="utf-8"), "hi")
        with self.assertRaisesRegex(RuntimeFault, "cannot read"):
            run('!"missing.rukx"-brøtjt.')

    def test_cast_cycle(self):
        import tempfile
        from pathlib import Path

        from phyx.errors import ParseError

        with tempfile.TemporaryDirectory() as td:
            a = Path(td) / "a.phyx"
            b = Path(td) / "b.phyx"
            a.write_text('^lo-"b.phyx"-bukð.\n', encoding="utf-8")
            b.write_text('^lo-"a.phyx"-bukð.\n', encoding="utf-8")
            with self.assertRaisesRegex(ParseError, "cycle"):
                run_source('^lo-"a.phyx"-bukð.', base_dir=td)


if __name__ == "__main__":
    unittest.main()
