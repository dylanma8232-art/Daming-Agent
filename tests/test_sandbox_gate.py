import unittest
import ast

class TestSandboxGateAndRuntimeIntegration(unittest.TestCase):
    def test_ast_validation_syntax_error(self):
        invalid_code = "def foo(:\n    pass"
        with self.assertRaises(SyntaxError):
            ast.parse(invalid_code)

    def test_ast_validation_valid_code(self):
        valid_code = "def add(a, b):\n    return a + b"
        tree = ast.parse(valid_code)
        self.assertIsNotNone(tree)

if __name__ == "__main__":
    unittest.main()

