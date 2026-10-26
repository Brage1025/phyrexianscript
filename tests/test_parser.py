import unittest

from phyx import ast
from phyx.errors import ParseError
from phyx.parser import parse


class PhraseTests(unittest.TestCase):
    def test_sov_builds_tree(self):
        (stmt,) = parse("!a-b-babg-c-tøwp.")
        self.assertIsInstance(stmt, ast.Print)
        (expr,) = stmt.exprs
        self.assertIsInstance(expr, ast.Call)
        self.assertEqual(expr.verb.word, "tøwp")
        self.assertEqual(expr.args[0].verb.word, "babg")
        self.assertEqual(expr.args[1].name, "c")

    def test_comma_is_a_barrier(self):
        (stmt,) = parse('!"x",1-2-babg.')
        self.assertEqual(len(stmt.exprs), 2)
        with self.assertRaises(ParseError):
            parse("!1,2-babg.")

    def test_missing_objects(self):
        with self.assertRaisesRegex(ParseError, "wants 2 objects"):
            parse("!1-babg.")

    def test_assignment_target_must_be_a_place(self):
        (stmt,) = parse("^xe-1-x-ţə''.")
        self.assertIsInstance(stmt.exprs[0], ast.Assign)
        (stmt,) = parse("^xe-1-l-0-tapq-ţə''.")
        self.assertIsInstance(stmt.exprs[0].target, ast.Call)
        with self.assertRaises(ParseError):
            parse("^xe-1-2-ţə''.")

    def test_list_count_must_be_literal(self):
        with self.assertRaisesRegex(ParseError, "plain numeral"):
            parse("!1-2-n-ťewn.")
        (stmt,) = parse("!1-2-2-ťewn.")
        self.assertEqual(len(stmt.exprs[0].args), 2)
        (stmt,) = parse('!"a"-1-"b"-2-2-tekt.')
        self.assertEqual(len(stmt.exprs[0].args), 4)

    def test_list_count_names_the_missing_items(self):
        with self.assertRaisesRegex(ParseError, "before the count 1"):
            parse("!1-ťewn.")
        with self.assertRaisesRegex(ParseError, r"0-ťewn"):
            parse("!1-ťewn.")
        (stmt,) = parse("!0-ťewn.")
        self.assertEqual(stmt.exprs[0].args, [])

    def test_underapplied_ability_is_a_name(self):
        (stmt,) = parse("^xe-add-fn-ţə''.", known_functions={"add": 2})
        assign = stmt.exprs[0]
        self.assertIsInstance(assign, ast.Assign)
        self.assertIsInstance(assign.value, ast.Name)
        self.assertEqual(assign.value.name, "add")
        (stmt,) = parse("!1-2-add.", known_functions={"add": 2})
        self.assertIsInstance(stmt.exprs[0], ast.UserCall)

    def test_naķm_quotes_a_zero_arity_ability(self):
        (stmt,) = parse("^xe-greet-naķm-fn-ţə''.", known_functions={"greet": 0})
        quoted = stmt.exprs[0].value
        self.assertIsInstance(quoted, ast.Call)
        self.assertEqual(quoted.verb.word, "naķm")
        self.assertIsInstance(quoted.args[0], ast.Name)
        self.assertEqual(quoted.args[0].name, "greet")

    def test_marker_mid_phrase_is_rejected(self):
        with self.assertRaisesRegex(ParseError, "mood marker"):
            parse("!1-ba-2.")


class SentenceTests(unittest.TestCase):
    def test_requires_start_symbol(self):
        with self.assertRaisesRegex(ParseError, "must begin with"):
            parse("xe-1-x-ţə''.")

    def test_missing_full_stop(self):
        with self.assertRaisesRegex(ParseError, "before the previous one ended"):
            parse("!1\n!2.")

    def test_implicit_indicative(self):
        (stmt,) = parse("^1-x-ţə''.")
        self.assertIsInstance(stmt, ast.ExprStmt)

    def test_const_requires_assignment(self):
        with self.assertRaises(ParseError):
            parse("^'u-1-2-babg.")
        (stmt,) = parse("^'u-1-x-ţə''.")
        self.assertTrue(stmt.exprs[0].const)

    def test_inline_body(self):
        (stmt,) = parse("^ba-x:lo-1.")
        self.assertIsInstance(stmt, ast.If)
        self.assertEqual(len(stmt.body), 1)
        (stmt,) = parse('^ba-x:!"y".')
        self.assertIsInstance(stmt.body[0], ast.Print)

    def test_indented_body_and_else_chain(self):
        src = "^ba-a:\n    !1.\n^qit-ba-b:\n    !2.\n^qit-bu-c:\n    !3.\n^qit:\n    !4.\n!5.\n"
        top = parse(src)
        self.assertEqual(len(top), 2)
        first = top[0]
        self.assertIsInstance(first, ast.If)
        second = first.orelse[0]
        self.assertTrue(second.chained)
        third = second.orelse[0]
        self.assertTrue(third.negate)
        self.assertIsInstance(third.orelse[0], ast.Print)

    def test_else_without_if(self):
        with self.assertRaisesRegex(ParseError, "must follow"):
            parse("!1.\n^qit:\n    !2.")

    def test_double_else(self):
        with self.assertRaisesRegex(ParseError, "already given"):
            parse("^ba-a:\n    !1.\n^qit:\n    !2.\n^qit:\n    !3.")

    def test_bad_indentation(self):
        with self.assertRaisesRegex(ParseError, "indented deeper"):
            parse("^ba-a:\n    !1.\n      !2.")
        with self.assertRaisesRegex(ParseError, "must be indented"):
            parse("^ba-a:\n!1.")

    def test_for_shape(self):
        (stmt,) = parse("^aχəw'-i-dl-5-ronɣ:!i.")
        self.assertIsInstance(stmt, ast.For)
        self.assertEqual(stmt.var, "i")
        with self.assertRaisesRegex(ParseError, "aχəw'"):
            parse("^aχəw'-i-xe-5-ronɣ:!i.")

    def test_def_registers_arity_before_use(self):
        prog = parse("!1-2-f.\n^ťe-a-b-f:\n    ^lo-a-b-babg-'iţpənn.")
        call = prog[0].exprs[0]
        self.assertIsInstance(call, ast.UserCall)
        self.assertEqual(len(call.args), 2)
        self.assertEqual(prog[1].params, ["a", "b"])

    def test_def_name_cannot_be_reserved(self):
        with self.assertRaisesRegex(ParseError, "word of the language"):
            parse("^ťe-a-babg:\n    !a.")

    def test_def_twice(self):
        with self.assertRaisesRegex(ParseError, "defined twice"):
            parse("^ťe-f:\n    !1.\n^ťe-f:\n    !2.")

    def test_seeded_ability_is_a_call(self):
        (stmt,) = parse("!1-2-f.", known_functions={"f": 2})
        self.assertIsInstance(stmt.exprs[0], ast.UserCall)

    def test_seeded_ability_may_be_redefined(self):
        (stmt,) = parse("^ťe-f:\n    !1.", known_functions={"f": 0})
        self.assertIsInstance(stmt, ast.FuncDef)

    def test_question(self):
        (stmt,) = parse('?"name?"-who.')
        self.assertIsInstance(stmt, ast.Input)
        self.assertEqual(stmt.target.name, "who")
        self.assertEqual(len(stmt.prompt), 1)
        with self.assertRaises(ParseError):
            parse("?.")

    def test_plain_sentence_takes_no_body(self):
        with self.assertRaisesRegex(ParseError, "does not take a body"):
            parse("^xe-1:\n    !1.")

    def test_assert_shape(self):
        (stmt,) = parse('^ǩaπa-1,"msg".')
        self.assertIsInstance(stmt, ast.Assert)
        self.assertIsNotNone(stmt.message)
        with self.assertRaises(ParseError):
            parse("^ǩaπa-1,2,3.")

    def test_empty_program(self):
        self.assertEqual(parse(""), [])
        self.assertEqual(parse("^rukx only a note\n"), [])


if __name__ == "__main__":
    unittest.main()
