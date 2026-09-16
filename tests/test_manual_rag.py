from alexandria.llm.manual_rag import ManualAnswerer, looks_technical
from alexandria.llm.cloud_client import CloudClient
from alexandria.manuals.manual_library import ManualLibrary
from alexandria.manuals.vehicle import Vehicle

CIVIC = Vehicle(2015, "Honda", "Civic")


def test_looks_technical_true_for_spec_questions():
    assert looks_technical("what's the torque spec for the oil drain plug")
    assert looks_technical("how do I replace the cabin air filter")
    assert looks_technical("what's the part number for the front brake pads")


def test_looks_technical_false_for_chitchat():
    assert not looks_technical("how are you feeling today")
    assert not looks_technical("thanks for the help")
    assert not looks_technical("tell me a joke")


def test_refuses_when_manual_has_no_relevant_excerpt():
    library = ManualLibrary()
    library.add_pages(["Spark plug gap: 0.041 inches."], CIVIC, "Test Manual")
    cloud = CloudClient(api_key=None, model="claude-sonnet-5")
    answerer = ManualAnswerer(library, cloud)

    answer = answerer.answer("what is the transmission fluid capacity", CIVIC)
    assert "don't have anything on that" in answer.lower()
    assert "2015 Honda Civic" in answer


def test_refuses_without_calling_cloud_when_no_manual_ingested():
    library = ManualLibrary()
    cloud = CloudClient(api_key=None, model="claude-sonnet-5")
    answerer = ManualAnswerer(library, cloud)

    answer = answerer.answer("what is the oil capacity", CIVIC)
    assert "don't have anything on that" in answer.lower()
