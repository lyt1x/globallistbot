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
        error_msg = "The server did not respond"
        print(error_msg)
        await interaction.followup.send(error_msg)
    except Exception as e:
        error_msg = f"Error: {e}"
        print(error_msg)
        await interaction.followup.send(error_msg)

@Bot.tree.command(name="profile",description="shows your linked account")
async def self(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.demonlist.org/records?user_id={reverse_json[interaction.user.id]}&order_by_newest=true&offset=0',timeout=10) as response:
                text = json.loads(await response.text())
                await interaction.followup.send(f'Linked profile: [{text["data"]["records"][0]["username"]}](https://demonlist.org/profile/{reverse_json[interaction.user.id]}), ID: {reverse_json[interaction.user.id]}', suppress_embeds=True)
    except asyncio.TimeoutError:
        error_msg = "The server did not respond"
        print(error_msg)
        await interaction.followup.send(error_msg)
    except Exception as e:
        error_msg = f"Error: {e}"
        print(error_msg)
        await interaction.followup.send(error_msg)

@Bot.tree.command(name="link",description="links a global list account to the discord account")
async def self(interaction: discord.Interaction, name: str, user: discord.Member = None):
    await interaction.response.defer()
    await load_and_mirror_json()
    if user is None:
        user = interaction.user
    else:
        admins = [722772182320545793, 378602408424767498] #поменять для использования
        if interaction.user.id not in admins:
            mentions = [f"<@{user_id}>" for user_id in admins]
            await interaction.followup.send(f"Only these users can modify others profiles: " + " ".join(mentions))
            return
        if user.id in reverse_json:
            existing_player_id = reverse_json[user.id]
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://api.demonlist.org/records?user_id={existing_player_id}&order_by_newest=true&offset=0',timeout=10) as response:
                    textt = json.loads(await response.text())
            await interaction.followup.send(f"User {user.mention} is already linked to {textt["data"]["records"][0]["username"]}, ID: {existing_player_id}")
            return
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f'https://api.demonlist.org/users/top?username_search={name}', timeout=10) as response:
                data = await response.json()
            if not data.get('success', False) or not data.get('data'):
                await interaction.followup.send("❌ No players found with this name!")
                return
            players = data['data']
            embed = discord.Embed(title="🔍 Found players", description=f"Found {len(players)} players for `{name}`:", color=discord.Color.blue())
            for i, player in enumerate(players, 1):
                embed.add_field(name=f"#{i} - {player['username']}", value=f"**Place:** #{player['place']}\n**Score:** {player['score']}\n**Country:** {player['country']}\n**ID:** {player['id']}", inline=False)
            view = discord.ui.View(timeout=60)
            for player in players:
                button = discord.ui.Button(style=discord.ButtonStyle.primary, label=player['username'])
                async def button_callback(interaction: discord.Interaction, p=player):
                    if str(p['id']) in original_json:
                        existing_discord_id = original_json[str(p['id'])]
                        await interaction.response.send_message(f"❌ Player {p['username']} is already linked to <@{existing_discord_id}>!")
                        return
                    original_json[str(p['id'])] = user.id
                    with open('accounts.json', 'w') as f:
                        json.dump(original_json, f, indent=4)
                    await interaction.response.send_message(f"✅ Player {p['username']} (ID: {p['id']}) linked to {user.mention}!")
                button.callback = button_callback
                view.add_item(button)
            cancel_button = discord.ui.Button(style=discord.ButtonStyle.danger, label="❌ Cancel")
            async def cancel_callback(interaction: discord.Interaction):
                await interaction.response.send_message("❌ Linking cancelled", ephemeral=True)
            cancel_button.callback = cancel_callback
            view.add_item(cancel_button)
            await interaction.followup.send(embed=embed, view=view)
        except aiohttp.ClientTimeout:
            await interaction.followup.send("The server did not respond")
        except Exception as e:
            await interaction.followup.send(f"Error: {str(e)}")

Bot.run(token)