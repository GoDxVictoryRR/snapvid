"""Tests for snapreel/history.py per AGENT_LOOP.md."""

from snapreel.history import load, save


def test_history_save_and_load(tmp_path, mocker):
    test_hist_file = tmp_path / ".history.json"
    mocker.patch("snapreel.history.HISTORY_FILE", test_hist_file)

    assert load() == []

    save("Topic 1", "/output/video1.mp4", 4)
    items = load()
    assert len(items) == 1
    assert items[0]["topic"] == "Topic 1"
    assert items[0]["path"] == "/output/video1.mp4"
    assert items[0]["scenes"] == 4

    # Add 5 more items to verify capping at 5
    for i in range(2, 7):
        save(f"Topic {i}", f"/output/video{i}.mp4", i)

    items_capped = load()
    assert len(items_capped) == 5
    assert items_capped[0]["topic"] == "Topic 6"
    assert items_capped[-1]["topic"] == "Topic 2"
