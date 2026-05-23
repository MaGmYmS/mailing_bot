from collections import defaultdict

from db_json import get_messages


async def generate_stats():
    messages = await get_messages()

    total_messages = len(messages)

    total_views = sum(msg.get("views", 0) for msg in messages)

    average_views = 0

    if total_messages > 0:
        average_views = total_views / total_messages

    group_views = defaultdict(int)

    for msg in messages:
        group_views[msg["group_name"]] += msg.get("views", 0)

    top_groups = sorted(
        group_views.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    report = (
        f"📊 Статистика\n\n"
        f"Всего сообщений: {total_messages}\n"
        f"Всего просмотров: {total_views}\n"
        f"Среднее просмотров: {average_views:.2f}\n\n"
        f"🏆 Топ групп:\n"
    )

    for idx, (group, views) in enumerate(top_groups, start=1):
        report += f"{idx}. {group} — {views} просмотров\n"

    return report