from alexandria.diagnostics.obd_interface import Snapshot
from alexandria.llm.cloud_client import CloudClient
from alexandria.llm.local_client import LocalAnswerer
from alexandria.llm.manual_rag import ManualAnswerer
from alexandria.llm.router import HybridRouter
from alexandria.manuals.manual_library import ManualLibrary
from alexandria.manuals.vehicle import Vehicle

CIVIC = Vehicle(2015, "Honda", "Civic")


def _router(with_manual: bool):
    cloud = CloudClient(api_key=None, model="claude-sonnet-5")
    manual, vehicle = None, None
    if with_manual:
        library = ManualLibrary()
        library.add_pages(["Oil drain plug torque: 29 ft-lb."], CIVIC, "Test Manual")
        manual = ManualAnswerer(library, cloud)
        vehicle = CIVIC
    return HybridRouter(local=LocalAnswerer(), cloud=cloud, manual=manual, vehicle=vehicle)


def test_local_sensor_answer_wins_over_everything():
    router = _router(with_manual=True)
    snapshot = Snapshot(coolant_temp_f=200.0)
    answer = router.answer("what's my coolant temperature", snapshot, system_prompt="irrelevant")
    assert answer == "200.0°F"


def test_technical_query_routes_to_manual_when_configured():
    # With a manual hit found, the manual tier hands off to the cloud LLM for
    # synthesis (grounded in the excerpt) rather than refusing outright — so
    # with no API key configured we still expect the cloud fallback message,
    # not the manual's "nothing found" refusal.
    router = _router(with_manual=True)
    answer = router.answer("what's the torque spec for the oil drain plug", None, system_prompt="irrelevant")
    assert "don't have anything on that" not in answer.lower()
    assert "ANTHROPIC_API_KEY" in answer


def test_technical_query_falls_back_to_cloud_without_manual_configured():
    router = _router(with_manual=False)
    answer = router.answer("what's the torque spec for the oil drain plug", None, system_prompt="irrelevant")
    assert "ANTHROPIC_API_KEY" in answer  # CloudClient's no-key fallback message


def test_chitchat_query_goes_to_cloud_even_with_manual_configured():
    router = _router(with_manual=True)
    answer = router.answer("how are you feeling today", None, system_prompt="irrelevant")
    assert "ANTHROPIC_API_KEY" in answer
