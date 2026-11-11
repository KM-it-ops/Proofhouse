"""A figure the facts never give must be caught when the narration spells it out in words."""

from proofhouse import studio

FACTS = {"product": "Demo", "summary": "A tool that makes prompts.", "facts": ["Works with 4 providers."]}


def test_a_spelled_out_invented_figure_in_the_narration_is_caught():
    digits = [{"say": "It is 10 times faster with 12 providers.", "base": {"kind": "living"}}]
    words = [{"say": "It is ten times faster with twelve providers.", "base": {"kind": "living"}}]

    assert studio._invented(digits, "Make a film about Demo", FACTS), "the digit form is caught (control)"
    assert studio._invented(words, "Make a film about Demo", FACTS), \
        "The same invented figures, written as words, pass the check."
