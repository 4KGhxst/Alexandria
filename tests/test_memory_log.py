from alexandria.personality.memory_log import MemoryLog


def test_no_summaries_returns_empty():
    log = MemoryLog()
    assert log.recent_summaries() == []


def test_save_and_retrieve_summary():
    log = MemoryLog()
    log.save_summary("2026-01-01", "Discussed an oil change coming up soon.")
    assert log.recent_summaries() == [("2026-01-01", "Discussed an oil change coming up soon.")]


def test_recent_summaries_ordered_most_recent_first():
    log = MemoryLog()
    log.save_summary("2026-01-01", "day one")
    log.save_summary("2026-01-03", "day three")
    log.save_summary("2026-01-02", "day two")

    dates = [date for date, _ in log.recent_summaries(limit=10)]
    assert dates == ["2026-01-03", "2026-01-02", "2026-01-01"]


def test_recent_summaries_respects_limit():
    log = MemoryLog()
    for day in range(1, 6):
        log.save_summary(f"2026-01-0{day}", f"day {day}")
    assert len(log.recent_summaries(limit=2)) == 2


def test_before_date_excludes_todays_own_entry():
    log = MemoryLog()
    log.save_summary("2026-01-01", "yesterday")
    log.save_summary("2026-01-02", "today, still in progress")

    results = log.recent_summaries(before_date="2026-01-02")
    assert results == [("2026-01-01", "yesterday")]


def test_saving_same_date_twice_overwrites():
    log = MemoryLog()
    log.save_summary("2026-01-01", "first draft")
    log.save_summary("2026-01-01", "revised summary")
    assert log.recent_summaries() == [("2026-01-01", "revised summary")]
