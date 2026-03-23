import discord
from discord.ext import tasks

def setup_status(bot):
    statuses = [
        discord.Activity(type=discord.ActivityType.watching, name="↪ developer neiwito."),
        discord.Game(name="↪ VCPRP")
    ]

    current_status = 0

    @tasks.loop(seconds=5)
    async def change_status():
        nonlocal current_status
        await bot.change_presence(activity=statuses[current_status])
        current_status = (current_status + 1) % len(statuses)

    change_status.start()
