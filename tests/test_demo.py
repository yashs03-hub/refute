"""The demo harness.

Five commands typed live, with flags, while talking, is five chances to mistype
or scroll past the number that matters. `refute demo` fixes the order and the
words. These tests exist because a demo that breaks silently is worse than no
demo - the failure happens in front of an audience.
"""

from __future__ import annotations

import pytest

from refute.demo import BEATS, run_demo


def test_beats_are_numbered_in_order():
    assert [b.n for b in BEATS] == list(range(1, len(BEATS) + 1))


def test_every_beat_has_something_to_say():
    for b in BEATS:
        assert b.title, f"beat {b.n} has no title"
        assert b.say.strip(), f"beat {b.n} has no line to deliver"
        assert b.seconds > 0


def test_the_whole_thing_fits_a_pitch_slot():
    budget = sum(b.seconds for b in BEATS)
    assert 180 <= budget <= 420, f"{budget}s of material is the wrong shape for a pitch"


def test_the_ceiling_comes_before_the_agent():
    """Order is load-bearing.

    If the agent's refusal (beat 6) is shown before the one-plate ceiling
    (beat 3), the refusal reads as the model failing rather than as the model
    agreeing with the simulator.
    """
    titles = {b.n: b.title.lower() for b in BEATS}
    ceiling = next(n for n, t in titles.items() if "apparatus" in t)
    agent = next(n for n, t in titles.items() if "frontier model" in t)
    assert ceiling < agent


def test_it_opens_on_the_real_data_not_a_claim():
    assert "failed" in BEATS[0].title.lower()


def test_it_ends_on_the_refusal():
    assert "frontier model" in BEATS[-1].title.lower()


def test_no_beat_says_something_the_tool_cannot_show():
    """The spoken line must not promise a number the beat does not print.

    Cheap proxy: the closing line about the refusal must not claim a power
    figure for it, since a declined design has none.
    """
    agent_beat = BEATS[-1]
    assert "declined" in agent_beat.say.lower()
    assert "%" not in agent_beat.say.split("declined")[1], (
        "do not quote a percentage after the refusal - there is none"
    )


def test_the_demo_runs_end_to_end_without_a_credential(monkeypatch, capsys):
    """The whole point: nothing here may touch a provider."""
    import refute.providers as providers

    monkeypatch.setattr(
        providers,
        "get_provider",
        lambda *_a, **_k: pytest.fail("the demo called a model provider"),
    )

    code = run_demo(sims=50, pause=False)
    out = capsys.readouterr().out

    assert code == 0
    # Each beat must have produced a header.
    for b in BEATS:
        assert b.title in out, f"beat {b.n} produced no output"
    # And the headline numbers must appear.
    assert "6/6" in out, "the lysis split is the opening hook"
    assert "DECLINED" in out or "No recorded run" in out


def test_a_single_beat_can_be_run():
    assert run_demo(sims=50, pause=False, only=3) == 0


def test_an_unknown_beat_is_refused():
    assert run_demo(sims=50, pause=False, only=99) == 2


def test_the_agent_beat_degrades_rather_than_crashing(monkeypatch, capsys):
    """If the recorded run is missing it must explain, not raise mid-demo."""
    import refute.demo as demo_mod
    from pathlib import Path

    monkeypatch.setattr(demo_mod, "RECORDED_RUN", Path("does/not/exist.json"))
    assert run_demo(sims=50, pause=False, only=len(BEATS)) == 0
    out = capsys.readouterr().out
    assert "No recorded run" in out
    # It must warn against the obvious wrong move.
    assert "Do NOT run the agent live" in out


def test_the_data_beat_degrades_when_the_csv_is_missing(monkeypatch, capsys):
    import refute.demo as demo_mod
    from pathlib import Path

    monkeypatch.setattr(demo_mod, "DATA_CSV", Path("does/not/exist.csv"))
    assert run_demo(sims=50, pause=False, only=1) == 0
    assert "missing" in capsys.readouterr().out
