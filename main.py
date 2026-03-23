from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo"

def run():
    port = int(os.environ.get("PORT", 10000))  # 👈 ESTO ES LO IMPORTANTE
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
    
import discord
from discord.ext import commands
from discord import app_commands
import os
import json

TOKEN = os.getenv("TOKEN")

CATEGORY_ID = 1466491475436245220
STAFF_ROLE_ID = 1466245030334435398
ADMIN_RESET_ROLE = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADOS = 1466240831609638923

DATA_FILE = "data.json"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"count": 0, "open": {}, "claims": {}, "ratings": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=4)

data = load_data()

# ================= PANEL =================

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Selecciona una categoría",
        options=[
            discord.SelectOption(label="Soporte General", emoji="<:Soportegeneral:1478091664596664541>"),
            discord.SelectOption(label="Soporte Tecnico", emoji="<:developer:1478090349611057335>"),
            discord.SelectOption(label="Reportar Usuario", emoji="<:miembro:1478090498076835910>"),
            discord.SelectOption(label="Reportar Moderador", emoji="<:staffteam:1478090615056236697>"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="<:Booster:1478090731288662186>")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        user_id = str(interaction.user.id)

        if user_id in data["open"]:
            return await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto.",
                ephemeral=True
            )

        data["count"] += 1
        ticket_number = f"{data['count']:03d}"
        channel_name = f"ticket-{ticket_number}"

        category = interaction.guild.get_channel(CATEGORY_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category
        )

        data["open"][user_id] = channel.id
        save_data(data)

        embed = discord.Embed(
            title="🎟 Ticket Abierto",
            description=f"""
Bienvenido {interaction.user.mention}

Un miembro del staff atenderá tu solicitud pronto.

📌 Categoría: **{select.values[0]}**
            """,
            color=0x2b2d31
        )

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)

        await channel.send(
            content=staff_role.mention,
            embed=embed,
            view=TicketButtons()
        )

        await interaction.response.send_message(
            f"✅ Tu ticket fue creado: {channel.mention}",
            ephemeral=True
        )

# ================= BOTONES =================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.green)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Solo staff.", ephemeral=True)

        channel_id = str(interaction.channel.id)

        if channel_id in data["claims"]:

            if data["claims"][channel_id] == interaction.user.id:
                return await interaction.response.send_message(
                    "⚠️ Ya reclamaste este ticket.",
                    ephemeral=True
                )
            else:
                return await interaction.response.send_message(
                    "❌ Este ticket ya está reclamado por otro staff.",
                    ephemeral=True
                )

        data["claims"][channel_id] = interaction.user.id
        save_data(data)

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        for member in staff_role.members:
            if member.id != interaction.user.id:
                await interaction.channel.set_permissions(member, read_messages=False)

        embed = discord.Embed(
            title="🎯 Ticket Reclamado",
            description=f"<:staffteam:1478090615056236697> Staff asignado: {interaction.user.mention}",
            color=0x57F287
        )

        await interaction.channel.send(embed=embed)

        user_id = next((u for u, c in data["open"].items() if c == interaction.channel.id), None)
        if user_id:
            user = await bot.fetch_user(int(user_id))
            await user.send(embed=discord.Embed(
                title="📩 Tu ticket fue asignado",
                description=f"El staff {interaction.user} está atendiendo tu caso.",
                color=0x57F287
            ))

        await interaction.response.defer()

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ Solo staff.", ephemeral=True)

        await interaction.response.send_message(
            "Selecciona el motivo de cierre:",
            view=CloseReason(),
            ephemeral=True
        )

# ================= MOTIVO =================

class CloseReason(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.select(
        placeholder="Selecciona motivo",
        options=[
            discord.SelectOption(label="Ticket Resuelto"),
            discord.SelectOption(label="Ticket abierto sin motivo"),
            discord.SelectOption(label="Ticket con inactividad")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        motivo = select.values[0]

        user_id = next((u for u, c in data["open"].items() if c == interaction.channel.id), None)

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"Motivo: **{motivo}**\nCerrado por: {interaction.user.mention}",
            color=0xED4245
        )

        await interaction.channel.send(embed=embed)

        if user_id:
            user = await bot.fetch_user(int(user_id))
            await user.send(embed=embed)
            del data["open"][user_id]

        if str(interaction.channel.id) in data["claims"]:
            del data["claims"][str(interaction.channel.id)]

        save_data(data)

        await interaction.channel.delete()

# ================= COMANDOS =================

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 Sistema Oficial de Tickets",
        description="""
<:Soportegeneral:1478091664596664541> **Soporte General**
<:developer:1478090349611057335> **Soporte Tecnico**
<:miembro:1478090498076835910> **Reportar Usuario**
<:staffteam:1478090615056236697> **Reportar Moderador**
<:Booster:1478090731288662186> **Reclamar Beneficios**

Selecciona una categoría.
        """,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")
    await ctx.send(embed=embed, view=TicketPanel())

@tree.command(name="unclaim", description="Libera el ticket reclamado.")
async def unclaim(interaction: discord.Interaction):

    channel_id = str(interaction.channel.id)

    if channel_id not in data["claims"]:
        return await interaction.response.send_message("❌ No está reclamado.", ephemeral=True)

    del data["claims"][channel_id]
    save_data(data)

    staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
    for member in staff_role.members:
        await interaction.channel.set_permissions(member, read_messages=True, send_messages=True)

    await interaction.response.send_message("🔓 Ticket liberado.")

@tree.command(name="add-user", description="Añade un usuario al ticket actual.")
async def add_user(interaction: discord.Interaction, usuario: discord.Member):
    await interaction.channel.set_permissions(usuario, read_messages=True, send_messages=True)
    await interaction.response.send_message(f"✅ {usuario.mention} añadido.")

@tree.command(name="reset-count", description="Reinicia el contador de tickets.")
async def reset_count(interaction: discord.Interaction):

    if ADMIN_RESET_ROLE not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ Sin permisos.", ephemeral=True)

    data["count"] = 0
    save_data(data)

    await interaction.response.send_message("✅ Contador reiniciado.", ephemeral=True)

@tree.command(name="calificar-staff", description="Califica la atención de un staff.")
async def calificar_staff(
    interaction: discord.Interaction,
    staff: discord.Member,
    calificacion: app_commands.Range[int, 1, 10],
    nota: str
):

    if interaction.channel.id != CANAL_CALIFICAR:
        return await interaction.response.send_message("❌ Canal incorrecto.", ephemeral=True)

    if STAFF_ROLE_ID not in [r.id for r in staff.roles]:
        return await interaction.response.send_message("❌ Solo staff.", ephemeral=True)

    staff_id = str(staff.id)

    if staff_id not in data["ratings"]:
        data["ratings"][staff_id] = []

    data["ratings"][staff_id].append(calificacion)
    promedio = sum(data["ratings"][staff_id]) / len(data["ratings"][staff_id])
    total = len(data["ratings"][staff_id])

    save_data(data)

    canal = bot.get_channel(CANAL_RESULTADOS)

    embed = discord.Embed(
        title="📊 Nueva Evaluación de Staff",
        color=0x5865F2
    )

    embed.add_field(name="<:staffteam:1478090615056236697> Staff", value=staff.mention, inline=False)
    embed.add_field(name="<:miembro:1478090498076835910> Usuario", value=interaction.user.mention, inline=True)
    embed.add_field(name="⭐ Calificación", value=f"{calificacion}/10", inline=True)
    embed.add_field(name="<:Soportegeneral:1478091664596664541> Promedio", value=f"{promedio:.2f}/10 ({total})", inline=False)
    embed.add_field(name="📝 Opinión", value=nota, inline=False)

    embed.set_footer(text="Dev Neiwito! • Sistema de Evaluaciones")

    await canal.send(embed=embed)

    await interaction.response.send_message("✅ Evaluación enviada.", ephemeral=True)

@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(TicketPanel())
    bot.add_view(TicketButtons())
    print("Bot listo.")

keep_alive()
bot.run(TOKEN)
