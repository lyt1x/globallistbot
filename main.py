import discord
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import json
import aiohttp
from colorama import init, Fore, Back, Style
from discord import Activity, ActivityType, app_commands

init(convert=True)
intents = discord.Intents.default()
intents.message_content = True
intents.presences = True
intents.members = True
Bot = commands.Bot(command_prefix='.', intents=intents)
Bot.remove_command('help')

with open('token.txt', 'r') as g:
    token = g.read()

@Bot.event
async def on_ready():
    print('')
    print('[=========================================================================================]')
    print('')
    print(f'[{Fore.LIGHTGREEN_EX}+{Fore.RESET}] Successfully logged in account [{Fore.LIGHTMAGENTA_EX}{Bot.user}{Fore.RESET}]')
    print('')
    print('[=========================================================================================]')
    print('')
    await load_and_mirror_json()
    synced = await Bot.tree.sync()
    print(f'synced {synced} commands')

original_json = {}
reverse_json = {}

async def load_and_mirror_json():
    global original_json, reverse_json
    with open('accounts.json', 'r') as f:
        original_json = json.load(f)
        
    reverse_json = {value: key for key, value in original_json.items()}
    print("loaded both jsons")


@Bot.tree.command(name="pingall",description="pings all victors of a selected level")
async def self(interaction: discord.Interaction, level: str):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.demonlist.org/levels/classic?search={level}&levels_type=all&offset=0&limit=150',timeout=10) as response:
                text = json.loads(await response.text())
                level_id = text["data"][0]["level_id"]
        offset = 0
        ping = ""; level_name = ""; placement = 0
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.demonlist.org/records?level_id={level_id}&status=1&without_verifiers=false&offset={offset}&move_info=true',timeout=10) as response:
                    data = json.loads(await response.text())["data"]["records"]
                    if len(data) == 0:
                        break
                    level_name = data[0]["level_name"]
                    placement = data[0]["place"]
                    for i in data:
                        try:
                            if interaction.guild.get_member(int(original_json[str(i["user_id"])])) != None and int(i["percent"]) == 100:
                                ping += f"<@{original_json[str(i["user_id"])]}>"
                        except Exception:
                            pass
                    offset += 50
        await interaction.followup.send(f"All victors of [{level_name} - #{placement}](https://demonlist.org/classic/{placement}) in the server: {ping}",suppress_embeds=True)

    except asyncio.TimeoutError:
        error_msg = "❌ Сервер не ответил"
        print(error_msg)
        await interaction.followup.send(error_msg)
    except Exception as e:
        error_msg = f"❌ Ошибка: {e}"
        print(error_msg)
        await interaction.followup.send(error_msg)

@Bot.tree.command(name="profile",description="shows your linked account")
async def self(interaction: discord.Interaction):
    await interaction.response.defer()
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://api.demonlist.org/records?user_id={reverse_json[interaction.user.id]}&order_by_newest=true&offset=0',timeout=10) as response:
            text = json.loads(await response.text())
            await interaction.followup.send(f'[{text["data"]["records"][0]["username"]}](https://demonlist.org/profile/{reverse_json[interaction.user.id]}), {reverse_json[interaction.user.id]}', suppress_embeds=True)
Bot.run(token)