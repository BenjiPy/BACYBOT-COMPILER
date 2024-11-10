import discord
from discord import app_commands
from discord.ext import commands, tasks
import pytz
import json
from typing import Literal
import aiohttp
import sys
from executor import *
import asyncio
import time
from datetime import datetime, timedelta

def load_constants(file_path="data/constantes.json"):
    with open(file_path, 'r') as f:
        return json.load(f)

constants = load_constants()

OWNER_ID = constants["OWNER_ID"]
LOG_CHANNEL_ID = constants["LOG_CHANNEL_ID"]
STATUS_CHANNEL_ID = constants["STATUS_CHANNEL_ID"]
PYTHON_CONSOLE_CHANNEL_ID = constants["PYTHON_CONSOLE_CHANNEL_ID"]

def get_date() -> str:
    timezone = pytz.timezone("Europe/Paris")
    now = datetime.now(timezone)
    return now.strftime("%d/%m/%Y - %H:%M:%S")

async def add_to_log_file(bot, message: str, severity: str = "info") -> None:
    print(message)
    with open('data/logs.txt', 'a', encoding="utf-8") as f:
        f.write(message + "\n")

    color = 0x00ff00 if severity == "info" else 0xff0000
    embed = discord.Embed(description=message, color=color)
    embed.timestamp = datetime.now()

    channel = bot.get_channel(LOG_CHANNEL_ID)
    if channel:
        await channel.send(embed=embed)

def read_json(file_path: str) -> dict:
    with open(file_path, 'r') as f:
        return json.load(f)

def write_json(file_path: str, data: dict) -> None:
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

with open('non mon grand interdit', 'r') as f:
    return None

intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix='/', description='', intents=intents, help_command=None)
bot.remove_command('help')

async def is_owner(interaction: discord.Interaction):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message(
            "Vous n'êtes pas autorisé à utiliser cette commande.",
            ephemeral=True,
        )
        await add_to_log_file(
            bot,
            f"[  ERREUR  ] {get_date()} | Tentative non autorisée d'utilisation de la commande par {interaction.user} (ID: {interaction.user.id}).",
            "important"
        )
        return False
    return True

@bot.event
async def on_ready():
    await add_to_log_file(bot, f"\n\n[  START  ] {get_date()} | Bot démarré.", "info")
    print("-----------")
    print("R E A D Y")
    print(f'\nBot Operationnel : {sys.version}\n{get_date()}\n')
    print("-----------")
    try:
        synced = await bot.tree.sync()
        await add_to_log_file(bot, f"Synced {len(synced)} command(s)", "info")
    except Exception as e:
        await add_to_log_file(bot, f"[  ERREUR  ] {get_date()} | {e}.", "important")

    await bot.change_presence(activity=discord.Game(name="sha256"))

    reset_globals()

    channel = bot.get_channel(1305143536550809600)
    embed = discord.Embed(title="Status", description="<a:upstatus:1256566467558637568> UP", color=0x0cd424)
    embed.timestamp = datetime.now(pytz.timezone("Europe/Paris"))
    embed.set_footer(text=f"~ {sys.version}")
    await channel.purge(limit=1)
    await channel.send(embed=embed)

    hourly_log.start()


@tasks.loop(minutes=1)
async def hourly_log():
    now = datetime.now(pytz.timezone("Europe/Paris"))
    if now.minute == 9:
        await add_to_log_file(bot, f"[  SCHEDULE  ] {get_date()} | Redémarrage automatique en cours merci de ne plus utiliser les commandes intégrés.", "important")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await add_to_log_file(bot, f"[  LOGS  ] {get_date()} | {ctx.message.author} : Commande {ctx.message.content} introuvable !", "important")
    if isinstance(error, discord.errors.InteractionResponded):
        pass

@bot.tree.command(name="ping", description="Pong !")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! {round(bot.latency * 1000)} ms')


@bot.tree.command(name="execpython", description="Exécuter un fichier Python")
@app_commands.describe(file="Fichier Python à exécuter")
async def execpython(interaction: discord.Interaction, file: discord.Attachment):
    if not file.filename.endswith(".py"):
        await interaction.response.send_message("Veuillez fournir un fichier Python (.py).", ephemeral=True)
        return

    await interaction.response.defer()

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(file.url) as response:
                if response.status != 200:
                    raise Exception(f"Erreur HTTP {response.status}")
                content = await response.text()

        stdout_output, stderr_output = execute_python_code_with_timeout(content)
        result = f"```\n{stdout_output}\n```"
        await interaction.followup.send(content=f"Résultat de l'exécution du fichier {file.filename}:\n{result}")
    except Exception as e:
        await interaction.followup.send(content=f"Erreur lors de l'exécution du fichier {file.filename}: {e}", ephemeral=True)


@bot.tree.command(name="execc", description="Compiler votre code en C.")
@app_commands.describe(fichier="Votre code C. (.c accepté seulement)")
async def execc(interaction: discord.Interaction, fichier: discord.Attachment):
    if not fichier.filename.endswith('.c'):
        await interaction.response.send_message("Seuls les fichiers avec l'extension .c sont autorisés.", ephemeral=True)
        return

    await interaction.response.defer()

    fichier_content = await fichier.read()
    fichier_content_str = fichier_content.decode('utf-8')

    try:
        stdout, stderr = compile_code_c(fichier_content_str)

        stringB = "[NULL]"
        stringB2 = "[NULL]"
        if stdout:
            lignes = stdout.split('\n')
            stringB = "\n".join(line for line in lignes if line)
        if stderr:
            lignes = stderr.split('\n')
            stringB2 = "\n".join(line for line in lignes if line)

        result = f"**stdout** : \n```ansi\n[2;32m{stringB}[0m\n```\n**stderr** : \n```ansi\n[2;31m{stringB2}[0m\n```"
        await interaction.followup.send(content=result)
    except Exception as e:
        await interaction.followup.send(content=f"{str(e)}", ephemeral=True)

@bot.tree.command(name="help", description="Affiche cette aide")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Commandes disponibles",
        description="Voici une liste des commandes que vous pouvez utiliser avec ce bot.",
        color=discord.Color.blue()
    )

    for command in bot.tree.get_commands():
        args = ", ".join([f"<{param.display_name}>" for param in command.parameters])
        embed.add_field(
            name=f"/{command.name} {args}",
            value=command.description,
            inline=False
        )

    embed.set_footer(text="Bot développé par benjis")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_message(message):
    if message.channel.id == PYTHON_CONSOLE_CHANNEL_ID and not message.author.bot:
        code = message.content
        if code.strip() == "!drop":
            reset_globals()
            await message.channel.send(f"```ansi\n[2;32mMémoire de la console réinitialisée.[0m\n```")
        elif code.startswith("!install "):
            library = code.split(" ")[1]
            await message.channel.send(f"Installation de {library}...")
            result = install_library(library)
            await message.channel.send(f"Résultat de l'installation :\n```\n{result}\n```")
        elif code.startswith("#"):
            return
        else:
            stdout_output, stderr_output = execute_with_timeout(code)
            response = f"```ansi\n[2;32m{get_date()} » {stdout_output}[0m\n```" if len(stdout_output) > 0 else f"```ansi\n[2;35m{get_date()} » ~No Output[0m\n```"
            await message.channel.send(response)

def install_library(library):
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", library], capture_output=True, text=True)
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)

def reset_globals():
    global variables_globales
    variables_globales = {}

bot.run(TOKEN)
