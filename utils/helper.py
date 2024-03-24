def is_google_message_valid(messages):
    user_messages = []
    assistant_messages = []
    system_messages = []
    for message in messages:
        if message['role'] == 'user':
            user_messages.append(message)
        elif message['role'] == 'assistant':
            assistant_messages.append(message)
        elif message['role'] == 'system':
            system_messages.append(message)
    if len(user_messages) == 0:
        return False
    if user_messages[-1] != messages[-1]:
        return False
    if len(user_messages) > 1 and len(assistant_messages) == 0:
        return False
