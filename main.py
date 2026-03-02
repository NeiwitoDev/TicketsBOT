import discord
from discord.ext import commands
import json
import os

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("No se encontró el TOKEN en las variables de entorno.")

STAFF_ROLE_ID = 1466245030334435398

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# 📂 BASE DE DATOS JSON
# =========================

def cargar_datos():
    if not os.path.exists("tickets.json"):
        with open("tickets.json", "w") as f:
            json.dump({"contador": 0, "tickets": {}}, f)

    with open("tickets.json", "r") as f:
        return json.load(f)

def guardar_datos(data):
    with open("tickets.json", "w") as f:
        json.dump(data, f, indent=4)

# =========================
# 🎟️ SELECT MENU
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", description="Consultas generales", emoji="<:Soportegeneral:1478091664596664541>"),
            discord.SelectOption(label="Reportar Usuario", description="Reportar miembro", emoji="<:miembro:1478090498076835910>"),
            discord.SelectOption(label="Reportar Moderador", description="Reportar staff", emoji="<:staffteam:1478090615056236697>"),
            discord.SelectOption(label="Reclamar Beneficios", description="Solicitar beneficios", emoji="<:Booster:1478090731288662186>"),
            discord.SelectOption(label="Soporte Técnico", description="Problemas técnicos", emoji="<:developer:1478090349611057335>")
        ]

        super().__init__(
            placeholder="Selecciona una categoría...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        data = cargar_datos()

        # 🔒 ANTI DUPLICADO
        if str(interaction.user.id) in data["tickets"]:
            canal_id = data["tickets"][str(interaction.user.id)]["canal_id"]
            canal = interaction.guild.get_channel(canal_id)

            view = discord.ui.View()
            view.add_item(VerTicketButton(canal_id))

            return await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto.",
                view=view,
                ephemeral=True
            )

        data["contador"] += 1
        numero = data["contador"]
        ticket_id = f"{numero:03d}"
        nombre_canal = f"ticket-{ticket_id}"

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.get_role(STAFF_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        canal = await interaction.guild.create_text_channel(
            name=nombre_canal,
            overwrites=overwrites
        )

        data["tickets"][str(interaction.user.id)] = {
            "canal_id": canal.id,
            "reclamado_por": None
        }

        guardar_datos(data)

        embed = discord.Embed(
            title="🎫 Ticket Abierto",
            description=f"Bienvenido {interaction.user.mention}\n\nUn miembro del staff te atenderá pronto.",
            color=0xffffff
        )
        embed.set_footer(text="Dev Neiwito! • Tickets System")

        await canal.send(embed=embed, view=TicketButtons())

        view = discord.ui.View()
        view.add_item(VerTicketButton(canal.id))

        await interaction.response.send_message(
            "✅ Tu ticket fue creado correctamente.",
            view=view,
            ephemeral=True
        )

class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# =========================
# 🔘 BOTONES TICKET
# =========================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Reclamar Ticket", style=discord.ButtonStyle.primary)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("No tienes permiso.", ephemeral=True)

        data = cargar_datos()

        for user_id, info in data["tickets"].items():
            if info["canal_id"] == interaction.channel.id:

                if info["reclamado_por"] is not None:
                    return await interaction.response.send_message("⚠️ Este ticket ya fue reclamado.", ephemeral=True)

                info["reclamado_por"] = interaction.user.id
                guardar_datos(data)

                usuario = await bot.fetch_user(int(user_id))

                embed = discord.Embed(
                    title="🎯 Ticket Asignado",
                    description=f"Tu ticket fue asignado al staff **{interaction.user.name}**.\n\nEn breve recibirás asistencia personalizada.",
                    color=0x5865F2
                )
                embed.set_footer(text="Dev Neiwito! • Tickets System")

                try:
                    await usuario.send(embed=embed)
                except:
                    pass

                return await interaction.response.send_message(
                    f"✅ Ticket reclamado por {interaction.user.mention}"
                )

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID not in [role.id for role in interaction.user.roles]:
            return await interaction.response.send_message("No tienes permiso.", ephemeral=True)

        data = cargar_datos()

        for user_id, info in list(data["tickets"].items()):
            if info["canal_id"] == interaction.channel.id:

                usuario = await bot.fetch_user(int(user_id))

                embed = discord.Embed(
                    title="🔒 Ticket Cerrado",
                    description=f"Tu ticket fue cerrado por **{interaction.user.name}**.\n\nSi necesitas más ayuda puedes abrir uno nuevo.",
                    color=0xED4245
                )
                embed.set_footer(text="Dev Neiwito! • Tickets System")

                try:
                    await usuario.send(embed=embed)
                except:
                    pass

                del data["tickets"][user_id]
                guardar_datos(data)

                await interaction.response.send_message("🔒 Cerrando ticket...")
                return await interaction.channel.delete()

# =========================
# 🔘 BOTÓN VER TICKET
# =========================

class VerTicketButton(discord.ui.Button):
    def __init__(self, canal_id):
        super().__init__(label="Ver Ticket", style=discord.ButtonStyle.success)
        self.canal_id = canal_id

    async def callback(self, interaction: discord.Interaction):
        canal = interaction.guild.get_channel(self.canal_id)
        await interaction.response.send_message(
            f"🔗 Ir a tu ticket: {canal.mention}",
            ephemeral=True
        )

# =========================
# 📌 COMANDO PANEL
# =========================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="🎟️ Sistema de Tickets",
        description="Selecciona una categoría para abrir un ticket.\nNuestro equipo te asistirá lo antes posible.",
        color=0xffffff
    )
    embed.set_footer(text="Dev Neiwito! • Tickets System")

    await ctx.send(embed=embed, view=TicketPanel())

# =========================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

bot.run(TOKEN)
