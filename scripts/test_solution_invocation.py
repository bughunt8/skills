import unittest

from check_solutions import invocation_error


class SolutionInvocation(unittest.TestCase):
    def test_implicit_user_only_call_is_refused(self):
        self.assertTrue(invocation_error({}, {"disable-model-invocation": True}))

    def test_explicit_model_user_only_call_is_refused(self):
        self.assertTrue(invocation_error({"invocation": "model"}, {"disable-model-invocation": True}))

    def test_human_boundary_is_accepted(self):
        self.assertEqual(invocation_error({"invocation": "user"}, {"disable-model-invocation": True}), "")

    def test_legacy_nested_flag_remains_conservative(self):
        self.assertTrue(invocation_error({}, {"metadata": {"disable-model-invocation": True}}))

    def test_model_provider_is_accepted(self):
        self.assertEqual(invocation_error({}, {"name": "tdd"}), "")

    def test_unknown_mode_is_refused(self):
        self.assertTrue(invocation_error({"invocation": "automatic"}, {}))


if __name__ == "__main__":
    unittest.main()
