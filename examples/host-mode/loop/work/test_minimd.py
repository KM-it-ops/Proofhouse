import unittest

from escape import escape_html
from inline import render_inline
from blocks import split_blocks, render_block
from markdown import convert


class EscapeTests(unittest.TestCase):
    def test_escapes_the_five_characters(self):
        self.assertEqual(escape_html("<a href=\"x\">T&C's</a>"), "&lt;a href=&quot;x&quot;&gt;T&amp;C&#39;s&lt;/a&gt;")

    def test_ampersand_is_escaped_once(self):
        self.assertEqual(escape_html("a &amp; b"), "a &amp;amp; b")

    def test_plain_text_is_unchanged(self):
        self.assertEqual(escape_html("hello world"), "hello world")


class InlineTests(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(render_inline("hello"), "hello")

    def test_strong(self):
        self.assertEqual(render_inline("a **bold** word"), "a <strong>bold</strong> word")

    def test_emphasis(self):
        self.assertEqual(render_inline("an *italic* word"), "an <em>italic</em> word")

    def test_strong_and_emphasis_together(self):
        self.assertEqual(render_inline("**a** and *b*"), "<strong>a</strong> and <em>b</em>")

    def test_code_span(self):
        self.assertEqual(render_inline("use `x < y` here"), "use <code>x &lt; y</code> here")

    def test_code_span_is_not_formatted(self):
        self.assertEqual(render_inline("`*not em*`"), "<code>*not em*</code>")

    def test_link(self):
        self.assertEqual(render_inline("see [docs](https://example.com/a?b=1&c=2)"), 'see <a href="https://example.com/a?b=1&amp;c=2">docs</a>')

    def test_link_text_can_be_formatted(self):
        self.assertEqual(render_inline("[**go**](/x)"), '<a href="/x"><strong>go</strong></a>')

    def test_html_in_text_is_escaped(self):
        self.assertEqual(render_inline("<script>x</script>"), "&lt;script&gt;x&lt;/script&gt;")

    def test_unclosed_markers_stay_literal(self):
        self.assertEqual(render_inline("2 * 3 and **open"), "2 * 3 and **open")

    def test_javascript_links_are_not_made(self):
        self.assertEqual(render_inline("[x](javascript:alert(1))"), "[x](javascript:alert(1))")

    def test_backslash_escapes_a_marker(self):
        self.assertEqual(render_inline(r"\*not em\*"), "*not em*")


class BlockTests(unittest.TestCase):
    def test_split_on_blank_lines(self):
        self.assertEqual(split_blocks("one\ntwo\n\nthree\n"), ["one\ntwo", "three"])

    def test_split_ignores_extra_blank_lines(self):
        self.assertEqual(split_blocks("\n\na\n\n\n\nb\n\n"), ["a", "b"])

    def test_split_keeps_fenced_code_together(self):
        text = "intro\n\n```\na\n\nb\n```\n\nafter"
        self.assertEqual(split_blocks(text), ["intro", "```\na\n\nb\n```", "after"])

    def test_heading_levels(self):
        self.assertEqual(render_block("# Title"), "<h1>Title</h1>")
        self.assertEqual(render_block("### Deep"), "<h3>Deep</h3>")
        self.assertEqual(render_block("###### Six"), "<h6>Six</h6>")

    def test_seven_hashes_is_a_paragraph(self):
        self.assertEqual(render_block("####### Seven"), "<p>####### Seven</p>")

    def test_heading_needs_a_space(self):
        self.assertEqual(render_block("#nospace"), "<p>#nospace</p>")

    def test_heading_text_is_inline_formatted(self):
        self.assertEqual(render_block("## A *b* c"), "<h2>A <em>b</em> c</h2>")

    def test_paragraph_joins_lines_with_a_space(self):
        self.assertEqual(render_block("one\ntwo"), "<p>one two</p>")

    def test_unordered_list(self):
        self.assertEqual(render_block("- a\n- b"), "<ul><li>a</li><li>b</li></ul>")

    def test_list_accepts_star_and_plus(self):
        self.assertEqual(render_block("* a\n+ b"), "<ul><li>a</li><li>b</li></ul>")

    def test_list_items_are_inline_formatted(self):
        self.assertEqual(render_block("- **a**"), "<ul><li><strong>a</strong></li></ul>")

    def test_ordered_list(self):
        self.assertEqual(render_block("1. a\n2. b"), "<ol><li>a</li><li>b</li></ol>")

    def test_fenced_code_block_is_escaped_and_not_formatted(self):
        self.assertEqual(render_block("```\n<b>*x*</b>\n```"), "<pre><code>&lt;b&gt;*x*&lt;/b&gt;</code></pre>")

    def test_fenced_code_block_keeps_language_class(self):
        self.assertEqual(render_block("```py\nx = 1\n```"), '<pre><code class="language-py">x = 1</code></pre>')

    def test_blockquote(self):
        self.assertEqual(render_block("> hi\n> there"), "<blockquote><p>hi there</p></blockquote>")

    def test_horizontal_rule(self):
        self.assertEqual(render_block("---"), "<hr>")
        self.assertEqual(render_block("***"), "<hr>")


class ConvertTests(unittest.TestCase):
    def test_empty_input(self):
        self.assertEqual(convert(""), "")

    def test_whitespace_only_input(self):
        self.assertEqual(convert("  \n\n \n"), "")

    def test_document(self):
        text = "# Hi\n\nA *small* doc.\n\n- one\n- two\n"
        self.assertEqual(convert(text), "<h1>Hi</h1>\n<p>A <em>small</em> doc.</p>\n<ul><li>one</li><li>two</li></ul>")

    def test_windows_line_endings(self):
        self.assertEqual(convert("a\r\nb\r\n\r\nc"), "<p>a b</p>\n<p>c</p>")

    def test_tabs_are_not_special_in_paragraphs(self):
        self.assertEqual(convert("a\tb"), "<p>a\tb</p>")

    def test_code_fence_with_blank_line_inside_survives_convert(self):
        self.assertEqual(convert("```\na\n\nb\n```"), "<pre><code>a\n\nb</code></pre>")

    def test_unterminated_fence_runs_to_the_end(self):
        self.assertEqual(convert("```\na\nb"), "<pre><code>a\nb</code></pre>")

    def test_raw_html_never_passes_through(self):
        self.assertEqual(convert("<div onclick=\"x()\">hi</div>"), "<p>&lt;div onclick=&quot;x()&quot;&gt;hi&lt;/div&gt;</p>")

    def test_idempotent_escape_of_entities_in_text(self):
        self.assertEqual(convert("Tom &amp; Jerry"), "<p>Tom &amp;amp; Jerry</p>")


if __name__ == "__main__":
    unittest.main()
