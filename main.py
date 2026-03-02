import discord
from discord.ext import commands
from discord import app_commands
import os
import json

# ================= CONFIG =================

TOKEN = os.getenv("TOKEN")

TICKET_CATEGORY_ID = 1466491475436245220
STAFF_ROLE_ID = 1466245030334435398
RESET_ROLE_ID = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADO = 1466240831609638923

EMOJIS = {
    "soporte_general": "<:Soportegeneral:1478091664596664541>",
    "soporte_tecnico": "<:developer:1478090349611057335>",
    "reportar_staff": "<:staffteam:1478090615056236697>",
    "reportar_usuario": "<:miembro:1478090498076835910>",
    "reclamar_beneficios": "<:Booster:1478090731288662186>"
}

# ===========================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ================== DATA ===================

if not os.path.exists("tickets.json"):
    with open("tickets.json", "w") as f:
        json.dump({"count": 0, "open": {}}, f)

if not os.path.exists("ratings.json"):
    with open("ratings.json", "w") as f:
        json.dump({}, f)

def load_tickets():
    with open("tickets.json") as f:
        return json.load(f)

def save_tickets(data):
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)

def load_ratings():
    with open("ratings.json") as f:
        return json.load(f)

def save_ratings(data):
    with open("ratings.json", "w") as f:
        json.dump(data, f, indent=4)

# ===========================================

class CloseSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ticket Resuelto"),
            discord.SelectOption(label="Ticket abierto sin motivo"),
            discord.SelectOption(label="Ticket con inactividad")
        ]
        super().__init__(placeholder="Seleccionar motivo de cierre...", options=options)

    async def callback(self, interaction: discord.Interaction):
        motivo = self.values[0]
        data = load_tickets()

        if str(interaction.channel.id) not in data["open"]:
            return await interaction.response.send_message("Este canal no es un ticket.", ephemeral=True)

        user_id = data["open"][str(interaction.channel.id)]["user"]
        user = interaction.guild.get_member(user_id)

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"Tu ticket fue cerrado.\n\n**Motivo:** {motivo}\n\nGracias por usar nuestro sistema.",
            color=discord.Color.red()
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        try:
            await user.send(embed=embed)
        except:
            pass

        del data["open"][str(interaction.channel.id)]
        save_tickets(data)

        await interaction.response.send_message("Ticket cerrado correctamente.", ephemeral=True)
        await interaction.channel.delete()

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.success)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("No tienes permisos.", ephemeral=True)

        data = load_tickets()
        ticket = data["open"].get(str(interaction.channel.id))

        if ticket["claimed"]:
            return await interaction.response.send_message("Ya fue reclamado.", ephemeral=True)

        ticket["claimed"] = interaction.user.id
        save_tickets(data)

        user = interaction.guild.get_member(ticket["user"])

        embed = discord.Embed(
            title="📌 Ticket Reclamado",
            description=f"Tu ticket fue reclamado por {interaction.user.mention}.\nPronto te asistirá.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        try:
            await user.send(embed=embed)
        except:
            pass

        await interaction.response.send_message("Ticket reclamado.")

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("No tienes permisos.", ephemeral=True)

        view = discord.ui.View()
        view.add_item(CloseSelect())

        await interaction.response.send_message("Selecciona el motivo de cierre:", view=view, ephemeral=True)

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Selecciona una categoría",
        options=[
            discord.SelectOption(label="Soporte General", emoji="📩"),
            discord.SelectOption(label="Soporte Tecnico", emoji="🛠️"),
            discord.SelectOption(label="Reportar Usuario", emoji="👤"),
            discord.SelectOption(label="Reportar Moderador", emoji="🛡️"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="🎁")
        ]
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):

        data = load_tickets()

        for ticket in data["open"].values():
            if ticket["user"] == interaction.user.id:
                return await interaction.response.send_message("Ya tienes un ticket abierto.", ephemeral=True)

        data["count"] += 1
        ticket_number = f"{data['count']:03d}"

        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        staff_role = interaction.guild.get_role(STAFF_ROLE_ID)
        overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{ticket_number}",
            category=category,
            overwrites=overwrites
        )

        data["open"][str(channel.id)] = {
            "user": interaction.user.id,
            "claimed": None
        }

        save_tickets(data)

        embed = discord.Embed(
            title="🎫 Bienvenido a tu Ticket",
            description=f"{interaction.user.mention}, gracias por contactar soporte.\nUn staff te atenderá pronto.\n\nPor favor explica detalladamente tu situación.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        await channel.send(embed=embed, view=TicketControls())

        await interaction.response.send_message(
            f"Tu ticket fue creado: {channel.mention}",
            ephemeral=True
        )

# ================= COMMANDS =================

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎫 Sistema de Tickets",
        description=f"""
{EMOJIS['soporte_general']} **Soporte General**
{EMOJIS['soporte_tecnico']} **Soporte Técnico**
{EMOJIS['reportar_usuario']} **Reportar Usuario**
{EMOJIS['reportar_staff']} **Reportar Moderador**
{EMOJIS['reclamar_beneficios']} **Reclamar Beneficios**

Selecciona una categoría del menú desplegable.
        """,
        color=discord.Color.from_rgb(255, 255, 255)
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")

    await ctx.send(embed=embed, view=TicketPanel())

# ================= SLASH =================

@bot.tree.command(name="reset-count")
async def reset_count(interaction: discord.Interaction):
    if RESET_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("No tienes permisos.", ephemeral=True)

    data = load_tickets()
    data["count"] = 0
    save_tickets(data)

    await interaction.response.send_message("Contador reiniciado a 001.")

@bot.tree.command(name="calificar-staff")
@app_commands.describe(staff="Staff", calificacion="Número del 1 al 10", nota="Opinión")
async def calificar_staff(interaction: discord.Interaction, staff: discord.Member, calificacion: int, nota: str):

    if interaction.channel.id != CANAL_CALIFICAR:
        return await interaction.response.send_message("Este comando solo funciona en el canal designado.", ephemeral=True)

    if STAFF_ROLE_ID not in [r.id for r in staff.roles]:
        return await interaction.response.send_message("Solo puedes calificar miembros del staff.", ephemeral=True)

    if calificacion < 1 or calificacion > 10:
        return await interaction.response.send_message("La calificación debe ser del 1 al 10.", ephemeral=True)

    data = load_ratings()

    if str(staff.id) not in data:
        data[str(staff.id)] = []

    data[str(staff.id)].append(calificacion)
    save_ratings(data)

    promedio = sum(data[str(staff.id)]) / len(data[str(staff.id)])

    canal = bot.get_channel(CANAL_RESULTADO)

    embed = discord.Embed(
        title="⭐ Nueva Calificación de Staff",
        description=f"""
👤 **Staff:** {staff.mention}
📝 **Opinión:** {nota}
📊 **Calificación:** {calificacion}/10
📈 **Promedio Actual:** {promedio:.2f}
        """,
        color=discord.Color.gold()
    )

    await canal.send(embed=embed)
    await interaction.response.send_message("Calificación enviada.", ephemeral=True)

# ==========================================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Bot listo.")

bot.run(TOKEN)
