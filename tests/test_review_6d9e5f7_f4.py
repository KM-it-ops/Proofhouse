"""With no fixes left, a film must not go ahead still saying a figure the facts never give."""

from proofhouse import studio

FACTS = {"product": "Demo", "summary": "A tool that makes prompts.", "facts": ["Works with 4 providers."]}
BRIEF = "Make a film about Demo"


def test_settling_does_not_leave_an_invented_figure_in_the_narration():
    board = [
        {"say": "Meet Demo.", "base": {"kind": "living"}},
        {"say": "It handles 500 requests a second.", "base": {"kind": "living"}},
        {"say": "Try Demo today.", "base": {"kind": "living"}},
    ]
    try:
        studio.settle_gaps(board, brief=BRIEF, seconds=12, facts=FACTS, footage=[], voiced=True, pictures=False)
    except studio.StudioError:
        return  # refusing the film is a fair answer
    left = [figures for _beat, layer, figures in studio._invented(board, BRIEF, FACTS) if layer is None]
    assert not left, f"The settled script still says {left}, which the facts never give, and the film goes ahead."
