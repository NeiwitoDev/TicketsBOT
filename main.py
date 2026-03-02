import discord
from discord.ext import commands
from discord import app_commands
import os
import json

# =========================
# TOKEN (VARIABLE DE ENTORNO)
# =========================

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No se encontró el TOKEN en las variables de entorno.")

# =========================
# CONFIG
# =========================

STAFF_ROLE_ID = 1466245030334435398
ADMIN_RESET_ROLE = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADOS = 1466240831609638923

TICKET_CATEGORY_ID = 1466491475436245220

DATA_FILE = "tickets_data.json"

# =========================
# BOT
# =========================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# =========================
# DATA
# =========================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "count": 0,
            "open_tickets": {},
            "staff_ratings": {}
        }
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# =========================
# PANEL TICKETS
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", description="Consultas generales."),
            discord.SelectOption(label="Reportar Usuario", description="Reportar un miembro."),
            discord.SelectOption(label="Reportar Moderador", description="Reportar un staff."),
            discord.SelectOption(label="Reclamar Beneficios", description="Reclamar recompensas."),
            discord.SelectOption(label="Soporte Técnico", description="Errores o bugs técnicos.")
        ]
        super().__init__(placeholder="Selecciona una categoría...", options=options)

    async def callback(self, interaction: discord.Interaction):

        if str(interaction.user.id) in data["open_tickets"]:
            return await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto.",
                ephemeral=True
            )

        data["count"] += 1
        ticket_number = f"{data['count']:03}"
        channel_name = f"ticket-{ticket_number}"

        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)

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

        data["open_tickets"][str(interaction.user.id)] = channel.id
        save_data(data)

        embed = discord.Embed(
            title="🎫 Ticket Abierto",
            description=f"Bienvenido {interaction.user.mention}\n\nUn staff te atenderá pronto.",
            color=0x2b2d31
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        await channel.send(embed=embed, view=TicketButtons())

        await interaction.response.send_message(
            f"✅ Ticket creado: {channel.mention}",
            ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Sistema de Tickets",
        description="Selecciona una categoría para abrir un ticket.\n\nNuestro equipo responderá lo antes posible.",
        color=0x2b2d31
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")

    await ctx.send(embed=embed, view=TicketView())

# =========================
# BOTONES TICKET
# =========================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("❌ No eres staff.", ephemeral=True)

        embed = discord.Embed(
            title="📌 Ticket Reclamado",
            description=f"Reclamado por {interaction.user.mention}",
            color=0x5865F2
        )
        await interaction.channel.send(embed=embed)

        await interaction.response.defer()

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("❌ No eres staff.", ephemeral=True)

        await interaction.response.send_message("✏️ Escribe el motivo de cierre:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", timeout=60, check=check)
            motivo = msg.content
        except:
            return await interaction.channel.send("❌ Tiempo agotado.")

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"**Cerrado por:** {interaction.user.mention}\n**Motivo:** {motivo}",
            color=0xED4245
        )
        await interaction.channel.send(embed=embed)

        try:
            user_id = [k for k,v in data["open_tickets"].items() if v == interaction.channel.id][0]
            del data["open_tickets"][user_id]
            save_data(data)
        except:
            pass

        await interaction.channel.delete(delay=5)

# =========================
# SLASH: CALIFICAR STAFF
# =========================

@tree.command(name="calificar-staff", description="Calificar atención del staff")
async def calificar_staff(
    interaction: discord.Interaction,
    staff: discord.Member,
    calificacion: app_commands.Range[int, 1, 10],
    nota: str
):

    if interaction.channel.id != CANAL_CALIFICAR:
        return await interaction.response.send_message(
            "❌ Usa este comando en el canal correspondiente.",
            ephemeral=True
        )

    if STAFF_ROLE_ID not in [r.id for r in staff.roles]:
        return await interaction.response.send_message(
            "❌ Solo puedes calificar miembros del Staff.",
            ephemeral=True
        )

    staff_id = str(staff.id)

    if staff_id not in data["staff_ratings"]:
        data["staff_ratings"][staff_id] = []

    data["staff_ratings"][staff_id].append(calificacion)

    ratings = data["staff_ratings"][staff_id]
    promedio = sum(ratings) / len(ratings)

    save_data(data)

    canal = bot.get_channel(CANAL_RESULTADOS)

    embed = discord.Embed(
        title="📊 Nueva Evaluación",
        color=0x5865F2
    )

    embed.add_field(name="👮 Staff", value=staff.mention, inline=False)
    embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
    embed.add_field(name="⭐ Calificación", value=f"{calificacion}/10", inline=True)
    embed.add_field(name="📈 Promedio Actual", value=f"{promedio:.2f}/10", inline=True)
    embed.add_field(name="📝 Opinión", value=nota, inline=False)
    embed.set_footer(text=f"Total de evaluaciones: {len(ratings)} • Dev Neiwito!")

    await canal.send(embed=embed)

    await interaction.response.send_message(
        "✅ Evaluación enviada.",
        ephemeral=True
    )

# =========================
# SLASH: RESET COUNT
# =========================

@tree.command(name="reset-count", description="Resetear contador de tickets")
async def reset_count(interaction: discord.Interaction):

    if ADMIN_RESET_ROLE not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message(
            "❌ No tienes permiso.",
            ephemeral=True
        )

    data["count"] = 0
    save_data(data)

    await interaction.response.send_message(
        "✅ Contador reiniciado a Ticket-001.",
        ephemeral=True
    )

# =========================
# READY
# =========================

@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(TicketView())
    bot.add_view(TicketButtons())
    print(f"Bot conectado como {bot.user}")

bot.run(TOKEN)
