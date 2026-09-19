from alexandria.core.conversation import ConversationMemory


def test_empty_memory_has_no_messages():
    memory = ConversationMemory()
    assert memory.as_messages() == []


def test_records_turns_in_order():
    memory = ConversationMemory()
    memory.add_user("hi")
    memory.add_assistant("hey there")
    memory.add_user("how are you")
    assert memory.as_messages() == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hey there"},
        {"role": "user", "content": "how are you"},
    ]


def test_bounds_history_to_max_exchanges():
    memory = ConversationMemory(max_exchanges=2)
    for i in range(5):
        memory.add_user(f"user {i}")
        memory.add_assistant(f"assistant {i}")
    messages = memory.as_messages()
    assert len(messages) == 4  # 2 exchanges = 4 messages
    assert messages[0] == {"role": "user", "content": "user 3"}


def test_clear_empties_history():
    memory = ConversationMemory()
    memory.add_user("hi")
    memory.clear()
    assert memory.as_messages() == []
