import discord
from discord.ext import commands
from discord import app_commands
import os
import json

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No se encontró el TOKEN en variables de entorno.")

# ================= CONFIG =================

STAFF_ROLE_ID = 1466245030334435398
ADMIN_RESET_ROLE = 1466440467204800597

CANAL_CALIFICAR = 1466231866041307187
CANAL_RESULTADOS = 1466240831609638923

TICKET_CATEGORY_ID = 1466491475436245220
DATA_FILE = "tickets_data.json"

# ================= BOT =================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ================= DATA =================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"count": 0, "open_tickets": {}, "staff_ratings": {}, "claimed": {}}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

data = load_data()

# ================= PANEL =================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", emoji="<:Soportegeneral:1478091664596664541>", description="Consultas generales."),
            discord.SelectOption(label="Reportar Usuario", emoji="<:miembro:1478090498076835910>", description="Reportar miembro."),
            discord.SelectOption(label="Reportar Moderador", emoji="<:staffteam:1478090615056236697>", description="Reportar staff."),
            discord.SelectOption(label="Reclamar Beneficios", emoji="<:Booster:1478090731288662186>", description="Reclamar recompensas."),
            discord.SelectOption(label="Soporte Técnico", emoji="<:developer:1478090349611057335>", description="Errores técnicos.")
        ]
        super().__init__(placeholder="Selecciona una categoría...", options=options)

    async def callback(self, interaction: discord.Interaction):

        if str(interaction.user.id) in data["open_tickets"]:
            return await interaction.response.send_message("❌ Ya tienes un ticket abierto.", ephemeral=True)

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
            title="🎫 Ticket Creado Correctamente",
            description=(
                f"Hola {interaction.user.mention} 👋\n\n"
                "Gracias por contactar con el equipo.\n"
                "🔹 Explica detalladamente tu situación.\n"
                "🔹 Un miembro del staff responderá pronto.\n\n"
                "Por favor evita spam."
            ),
            color=0x2b2d31
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        await channel.send(embed=embed, view=TicketButtons())

        await interaction.response.send_message(f"✅ Ticket creado: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Sistema Oficial de Tickets",
        description=(
            "<:Soportegeneral:1478091664596664541> Soporte General\n"
            "<:miembro:1478090498076835910> Reportar Usuario\n"
            "<:staffteam:1478090615056236697> Reportar Moderador\n"
            "<:Booster:1478090731288662186> Reclamar Beneficios\n"
            "<:developer:1478090349611057335> Soporte Técnico\n\n"
            "Selecciona una categoría abajo."
        ),
        color=0x2b2d31
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")
    await ctx.send(embed=embed, view=TicketView())

# ================= BOTONES =================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("❌ No eres staff.", ephemeral=True)

        data["claimed"][str(interaction.channel.id)] = interaction.user.id
        save_data(data)

        embed = discord.Embed(
            title="📌 Ticket Reclamado",
            description=f"Este ticket ahora está siendo gestionado por {interaction.user.mention}",
            color=0x5865F2
        )

        await interaction.channel.send(embed=embed)

        # DM usuario
        try:
            user_id = [k for k,v in data["open_tickets"].items() if v == interaction.channel.id][0]
            user = await bot.fetch_user(int(user_id))
            dm = discord.Embed(
                title="📌 Tu ticket fue reclamado",
                description=f"El staff {interaction.user.mention} tomó tu caso.",
                color=0x5865F2
            )
            await user.send(embed=dm)
        except:
            pass

        await interaction.response.defer()

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [r.id for r in interaction.user.roles]:
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
            title="🔒 Ticket Resuelto",
            description=f"**Staff:** {interaction.user.mention}\n**Motivo:** {motivo}",
            color=0xED4245
        )

        await interaction.channel.send(embed=embed)

        # DM usuario
        try:
            user_id = [k for k,v in data["open_tickets"].items() if v == interaction.channel.id][0]
            user = await bot.fetch_user(int(user_id))
            dm = discord.Embed(
                title="🔒 Tu ticket fue cerrado",
                description=f"Staff: {interaction.user.mention}\nMotivo: {motivo}",
                color=0xED4245
            )
            await user.send(embed=dm)
            del data["open_tickets"][user_id]
            save_data(data)
        except:
            pass

        await interaction.channel.delete(delay=5)

# ================= UNCLAIM =================

@tree.command(name="unclaim", description="Quitar claim del ticket")
async def unclaim(interaction: discord.Interaction):

    if interaction.channel.category_id != TICKET_CATEGORY_ID:
        return await interaction.response.send_message("❌ Este comando solo funciona en tickets.", ephemeral=True)

    if str(interaction.channel.id) not in data["claimed"]:
        return await interaction.response.send_message("❌ Este ticket no está reclamado.", ephemeral=True)

    del data["claimed"][str(interaction.channel.id)]
    save_data(data)

    await interaction.response.send_message("✅ Ticket liberado.", ephemeral=True)

# ================= ADD USER =================

@tree.command(name="add-user", description="Añadir usuario al ticket")
async def add_user(interaction: discord.Interaction, usuario: discord.Member):

    if interaction.channel.category_id != TICKET_CATEGORY_ID:
        return await interaction.response.send_message("❌ Solo funciona en tickets.", ephemeral=True)

    await interaction.channel.set_permissions(usuario, read_messages=True, send_messages=True)

    await interaction.response.send_message(f"✅ {usuario.mention} fue añadido al ticket.", ephemeral=True)

# ================= CALIFICAR STAFF =================

@tree.command(name="calificar-staff", description="Calificar atención del staff")
async def calificar_staff(interaction: discord.Interaction, staff: discord.Member, calificacion: app_commands.Range[int, 1, 10], nota: str):

    if interaction.channel.id != CANAL_CALIFICAR:
        return await interaction.response.send_message("❌ Usa el canal correcto.", ephemeral=True)

    if STAFF_ROLE_ID not in [r.id for r in staff.roles]:
        return await interaction.response.send_message("❌ Solo puedes calificar staff.", ephemeral=True)

    staff_id = str(staff.id)

    if staff_id not in data["staff_ratings"]:
        data["staff_ratings"][staff_id] = []

    data["staff_ratings"][staff_id].append(calificacion)
    ratings = data["staff_ratings"][staff_id]
    promedio = sum(ratings) / len(ratings)

    save_data(data)

    canal = bot.get_channel(CANAL_RESULTADOS)

    embed = discord.Embed(title="📊 Nueva Evaluación", color=0x5865F2)
    embed.add_field(name="Staff", value=staff.mention, inline=False)
    embed.add_field(name="Calificación", value=f"{calificacion}/10", inline=True)
    embed.add_field(name="Promedio", value=f"{promedio:.2f}/10", inline=True)
    embed.add_field(name="Opinión", value=nota, inline=False)
    embed.set_footer(text=f"Total evaluaciones: {len(ratings)}")

    await canal.send(embed=embed)
    await interaction.response.send_message("✅ Evaluación enviada.", ephemeral=True)

# ================= RESET =================

@tree.command(name="reset-count", description="Resetear contador de tickets")
async def reset_count(interaction: discord.Interaction):

    if ADMIN_RESET_ROLE not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)

    data["count"] = 0
    save_data(data)

    await interaction.response.send_message("✅ Contador reiniciado a Ticket-001.", ephemeral=True)

# ================= READY =================

@bot.event
async def on_ready():
    await tree.sync()
    bot.add_view(TicketView())
    bot.add_view(TicketButtons())
    print(f"Bot conectado como {bot.user}")

bot.run(TOKEN)
