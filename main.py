import discord
from discord.ext import commands
import os
import asyncio

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================

TICKET_CATEGORY_ID = 1466491475436245220

STAFF_ROLE_ID_1 = 1466244726796582964
STAFF_ROLE_ID_2 = 1466245030334435398

ALTO_MANDO_ROLE_ID = 1476595202813857857  

# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# READY
# ===============================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔁 Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        print(e)

# ===============================
# VER TICKET
# ===============================

class VerTicketView(discord.ui.View):
    def __init__(self, canal):
        super().__init__(timeout=60)
        self.add_item(
            discord.ui.Button(
                label="🔎 Ver Ticket",
                style=discord.ButtonStyle.link,
                url=canal.jump_url
            )
        )

# ===============================
# CIERRE CON MOTIVO
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
            description=f"Motivo: **{motivo}**\n\nEl canal se eliminará en 5 segundos.",
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
# BOTONES DEL TICKET
# ===============================

class TicketButtons(discord.ui.View):
    def __init__(self, creador):
        super().__init__(timeout=None)
        self.creador = creador
        self.claimed_by = None

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Selecciona el motivo del cierre:",
            view=MotivoView(),
            ephemeral=True
        )

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.claimed_by:
            await interaction.response.send_message(
                f"⚠️ Este ticket ya fue reclamado por {self.claimed_by.mention}",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user
        guild = interaction.guild

        alto_mando = guild.get_role(ALTO_MANDO_ROLE_ID)

        # Quitar permisos de escritura a staff
        staff1 = guild.get_role(STAFF_ROLE_ID_1)
        staff2 = guild.get_role(STAFF_ROLE_ID_2)

        if staff1:
            await interaction.channel.set_permissions(staff1, send_messages=False)

        if staff2:
            await interaction.channel.set_permissions(staff2, send_messages=False)

        # Permitir escribir solo al que reclamó
        await interaction.channel.set_permissions(interaction.user, send_messages=True)

        # Permitir altos mandos escribir
        if alto_mando:
            await interaction.channel.set_permissions(alto_mando, send_messages=True)

        embed = discord.Embed(
            description=f"📌 Ticket reclamado por {interaction.user.mention}",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)

# ===============================
# MENÚ CREAR TICKET
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

        categoria = guild.get_channel(TICKET_CATEGORY_ID)

        nombre_canal = f"{tipo.lower().replace(' ', '-')}-{user.name}"

        canal = await guild.create_text_channel(
            name=nombre_canal,
            category=categoria
        )

        await canal.set_permissions(guild.default_role, read_messages=False)
        await canal.set_permissions(user, read_messages=True, send_messages=True)

        staff_role_1 = guild.get_role(STAFF_ROLE_ID_1)
        staff_role_2 = guild.get_role(STAFF_ROLE_ID_2)

        embed = discord.Embed(
            title=f"🎫 Ticket - {tipo}",
            description="Un miembro del staff te atenderá pronto.",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Usuario", value=user.mention)

        botones = TicketButtons(user)

        await canal.send(
            content=f"{staff_role_1.mention if staff_role_1 else ''} {staff_role_2.mention if staff_role_2 else ''}",
            embed=embed,
            view=botones
        )

        view = VerTicketView(canal)

        await interaction.response.send_message(
            "🎫 Ticket creado correctamente!\nPresiona el botón para ir al ticket.",
            view=view,
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
        description="Selecciona una categoría para abrir un ticket, Recuerda no  abrir sin motivo.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())

# ===============================
# RUN
# ===============================

bot.run(os.getenv("TOKEN"))
