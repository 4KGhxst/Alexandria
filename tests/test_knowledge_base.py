from alexandria.knowledge.knowledge_base import Fact, KnowledgeBase


def test_load_seed_data_populates_facts():
    kb = KnowledgeBase()
    loaded = kb.load_seed_data()
    assert loaded > 0
    assert kb.count() == loaded


def test_load_seed_data_is_idempotent():
    kb = KnowledgeBase()
    kb.load_seed_data()
    count_after_first = kb.count()
    second_load = kb.load_seed_data()
    assert second_load == 0
    assert kb.count() == count_after_first


def test_search_finds_relevant_fact():
    kb = KnowledgeBase()
    kb.load_seed_data()
    results = kb.search("when should I change my oil")
    assert any("oil" in fact.topic.lower() for fact in results)


def test_search_with_no_matches_returns_empty():
    kb = KnowledgeBase()
    kb.load_seed_data()
    results = kb.search("xyzabc nonsense query")
    assert results == []


def test_get_dtc_explanation():
    kb = KnowledgeBase()
    kb.load_seed_data()
    explanation = kb.get_dtc_explanation("P0128")
    assert explanation is not None
    assert "thermostat" in explanation.lower()


def test_add_fact_and_search():
    kb = KnowledgeBase()
    kb.add_fact(Fact(topic="Test Topic", category="test", content="unique needle content", tags=["needle"]))
    results = kb.search("needle")
    assert len(results) == 1
    assert results[0].topic == "Test Topic"
