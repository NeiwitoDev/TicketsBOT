import discord
from discord.ext import commands
import os
import asyncio

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================

TICKET_CATEGORY_ID = 1466491475436245220  # 🔥 CAMBIA SOLO ESTE ID SI QUIERES OTRA CATEGORÍA

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# BOT READY
# ===============================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# ===============================
# BOTÓN VER TICKET
# ===============================

class VerTicketView(discord.ui.View):
    def __init__(self, canal):
        super().__init__(timeout=None)
        self.add_item(
            discord.ui.Button(
                label="🔎 Ver Ticket",
                style=discord.ButtonStyle.link,
                url=canal.jump_url
            )
        )

# ===============================
# MENÚ MOTIVO CIERRE
# ===============================

class MotivoSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Ticket Resuelto", emoji="✅"),
            discord.SelectOption(label="Ticket Cerrado Sin Motivo", emoji="⚠️")
        ]

        super().__init__(
            placeholder="Selecciona el motivo del cierre...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        motivo = self.values[0]

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"**Motivo:** {motivo}\n\nEl canal se eliminará en 5 segundos.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)

        await asyncio.sleep(5)
        await interaction.channel.delete()

class MotivoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(MotivoSelect())

# ===============================
# BOTÓN CERRAR
# ===============================

class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Selecciona el motivo del cierre:",
            view=MotivoView(),
            ephemeral=True
        )

# ===============================
# MENÚ CREACIÓN TICKET
# ===============================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General", emoji="🛠️"),
            discord.SelectOption(label="Reclamar Beneficios", emoji="🎁"),
            discord.SelectOption(label="Reportar Usuario", emoji="🚨"),
            discord.SelectOption(label="Reportar Moderador", emoji="⚖️")
        ]

        super().__init__(
            placeholder="🎟️ Selecciona el tipo de ticket...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        guild = interaction.guild
        user = interaction.user
        tipo = self.values[0]

        # 🔥 Obtener categoría por ID
        categoria = guild.get_channel(TICKET_CATEGORY_ID)

        if categoria is None:
            await interaction.response.send_message(
                "❌ Error: La categoría configurada no existe.",
                ephemeral=True
            )
            return

        nombre_canal = f"{tipo.lower().replace(' ', '-')}-{user.name}"

        canal = await guild.create_text_channel(
            name=nombre_canal,
            category=categoria
        )

        await canal.set_permissions(guild.default_role, read_messages=False)
        await canal.set_permissions(user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"🎫 Ticket - {tipo}",
            description="Describe tu problema con el mayor detalle posible.\nUn staff responderá pronto.",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Usuario", value=user.mention)
        embed.set_footer(text="Sistema de tickets • NeiwitoDev")

        await canal.send(user.mention, embed=embed, view=CloseTicketView())

        await interaction.response.send_message(
            "✅ Ticket creado correctamente!",
            view=VerTicketView(canal),
            ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ===============================
# COMANDO PANEL
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Centro de Soporte",
        description=(
            "Selecciona una categoría en el menú desplegable para abrir un ticket.\n"
            "Nuestro equipo te atenderá lo antes posible."
        ),
        color=discord.Color.blue()
    )

    embed.set_footer(text="Sistema Avanzado de Tickets • NeiwitoDev")

    await ctx.send(embed=embed, view=TicketView())

bot.run(os.getenv("TOKEN"))