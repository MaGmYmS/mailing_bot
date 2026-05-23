import aiofiles
import json
import os
from datetime import datetime

from config import GROUPS_FILE, MESSAGES_FILE, SETTINGS_FILE


async def ensure_files():
    files = {
        GROUPS_FILE: [],
        MESSAGES_FILE: [],
        SETTINGS_FILE: {}
    }

    for file_name, default_data in files.items():
        if not os.path.exists(file_name):
            async with aiofiles.open(file_name, "w", encoding="utf-8") as f:
                await f.write(json.dumps(default_data, ensure_ascii=False, indent=4))


async def read_json(file_name):
    async with aiofiles.open(file_name, "r", encoding="utf-8") as f:
        content = await f.read()

        if not content.strip():
            return []

        return json.loads(content)


async def write_json(file_name, data):
    async with aiofiles.open(file_name, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=4))


# GROUPS

async def get_groups():
    return await read_json(GROUPS_FILE)


async def add_group(group_data):
    groups = await get_groups()

    exists = any(g["chat_id"] == group_data["chat_id"] for g in groups)

    if not exists:
        groups.append(group_data)
        await write_json(GROUPS_FILE, groups)


async def remove_group(chat_id):
    groups = await get_groups()

    groups = [g for g in groups if g["chat_id"] != chat_id]

    await write_json(GROUPS_FILE, groups)


# MESSAGES

async def get_messages():
    return await read_json(MESSAGES_FILE)


async def add_message(message_data):
    messages = await get_messages()

    messages.append(message_data)

    await write_json(MESSAGES_FILE, messages)


async def update_message_views(message_id, views):
    messages = await get_messages()

    for msg in messages:
        if msg["internal_id"] == message_id:
            msg["views"] = views
            msg["last_view_update"] = datetime.utcnow().isoformat()

    await write_json(MESSAGES_FILE, messages)