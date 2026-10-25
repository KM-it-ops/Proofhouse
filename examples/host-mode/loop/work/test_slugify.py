import unittest

from slugify import slugify


class SlugifyTests(unittest.TestCase):
    def test_lowercase_and_spaces(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_strip_accents(self) -> None:
        self.assertEqual(slugify("Café au Lait"), "cafe-au-lait")

    def test_collapse_non_alphanumerics(self) -> None:
        self.assertEqual(slugify("foo   bar!!!baz"), "foo-bar-baz")

    def test_trim_edge_dashes(self) -> None:
        self.assertEqual(slugify("---hello---"), "hello")

    def test_max_length_without_mid_word_cut(self) -> None:
        title = "one two three four five six seven eight nine ten"
        result = slugify(title, max_length=20)
        self.assertLessEqual(len(result), 20)
        self.assertFalse(result.endswith("-"))
        self.assertNotIn("--", result)
        self.assertEqual(result, "one-two-three-four")

    def test_empty_string(self) -> None:
        self.assertEqual(slugify(""), "")

    def test_digits_and_punctuation(self) -> None:
        self.assertEqual(slugify("Python 3.12 Release"), "python-3-12-release")


if __name__ == "__main__":
    unittest.main()
