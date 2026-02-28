import discord 
from discord.ext import commands
import os
import asyncio
import json
from discord.ext import tasks
import itertools
from discord import app_commands

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================

TICKET_CATEGORY_ID = 1466491475436245220

STAFF_ROLE_ID_1 = 1466244726796582964
STAFF_ROLE_ID_2 = 1466245030334435398

ALTO_MANDO_ROLE_ID = 1476595202813857857

CANAL_COMANDO_ID = 1466231866041307187
CANAL_CALIFICACIONES_ID = 1466240831609638923
ROL_STAFF_CALIFICABLE = 1466245030334435398

DATA_FILE = "calificaciones.json"

# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

tickets_abiertos = {}

# ===============================
# SISTEMA CALIFICACIONES
# ===============================

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===============================
# READY
# ===============================

estados = itertools.cycle([
    discord.Activity(type=discord.ActivityType.watching, name="↪ developer: neiwito."),
    discord.Activity(type=discord.ActivityType.playing, name="↪ Villa Carlos Paz RP")
])

@tasks.loop(seconds=15)
async def cambiar_estado():
    await bot.change_presence(activity=next(estados))

@bot.event
async def on_ready():
    cambiar_estado.start()
    await bot.tree.sync()
    print(f"✅ Bot conectado como {bot.user}")

# ===============================
# SISTEMA TICKETS COMPLETO
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
# MOTIVO CIERRE
# ===============================

class MotivoSelect(discord.ui.Select):
    def __init__(self, creador, tipo, claimed_by):
        self.creador = creador
        self.tipo = tipo
        self.claimed_by = claimed_by

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
        staff = interaction.user

        mensajes = []
        async for msg in interaction.channel.history(limit=None, oldest_first=True):
            mensajes.append(f"[{msg.created_at.strftime('%H:%M')}] {msg.author}: {msg.content}")

        transcripcion = "\n".join(mensajes)

        embed_dm = discord.Embed(
            title="📩 Tu Ticket Fue Cerrado",
            description=f"**Categoría:** {self.tipo}\n"
                        f"**Motivo:** {motivo}\n"
                        f"**Staff Responsable:** {staff.mention}",
            color=0xFFFFFF
        )

        embed_dm.add_field(
            name="📜 Transcripción",
            value=transcripcion[:1000] if transcripcion else "Sin mensajes.",
            inline=False
        )

        try:
            await self.creador.send(embed=embed_dm)
        except:
            pass

        if self.creador.id in tickets_abiertos:
            if self.tipo in tickets_abiertos[self.creador.id]:
                tickets_abiertos[self.creador.id].remove(self.tipo)

        embed_close = discord.Embed(
            description=f"🔒 Ticket cerrado por {staff.mention}\nMotivo: **{motivo}**\n\nEl canal se eliminará en 5 segundos.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed_close)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class MotivoView(discord.ui.View):
    def __init__(self, creador, tipo, claimed_by):
        super().__init__(timeout=60)
        self.add_item(MotivoSelect(creador, tipo, claimed_by))

# ===============================
# BOTONES TICKET
# ===============================

class TicketButtons(discord.ui.View):
    def __init__(self, creador, tipo):
        super().__init__(timeout=None)
        self.creador = creador
        self.tipo = tipo
        self.claimed_by = None

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Selecciona el motivo del cierre:",
            view=MotivoView(self.creador, self.tipo, self.claimed_by),
            ephemeral=True
        )

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        # 🔒 SOLO ROL 1466245030334435398 PUEDE RECLAMAR
        if STAFF_ROLE_ID_2 not in [role.id for role in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ No tienes permiso para reclamar este ticket.",
                ephemeral=True
            )
            return

        if self.claimed_by:
            await interaction.response.send_message(
                f"⚠️ Ya fue reclamado por {self.claimed_by.mention}",
                ephemeral=True
            )
            return

        self.claimed_by = interaction.user
        guild = interaction.guild

        alto_mando = guild.get_role(ALTO_MANDO_ROLE_ID)
        staff1 = guild.get_role(STAFF_ROLE_ID_1)
        staff2 = guild.get_role(STAFF_ROLE_ID_2)

        if staff1:
            await interaction.channel.set_permissions(staff1, send_messages=False)

        if staff2:
            await interaction.channel.set_permissions(staff2, send_messages=False)

        await interaction.channel.set_permissions(interaction.user, send_messages=True)

        if alto_mando:
            await interaction.channel.set_permissions(alto_mando, send_messages=True)

        embed = discord.Embed(
            description=f"📌 Ticket reclamado por {interaction.user.mention}",
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)

# ===============================
# SELECT TICKET
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

        if user.id not in tickets_abiertos:
            tickets_abiertos[user.id] = []

        if tipo in tickets_abiertos[user.id]:
            await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto en esta categoría.",
                ephemeral=True
            )
            return

        tickets_abiertos[user.id].append(tipo)

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

        botones = TicketButtons(user, tipo)

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
        description="Selecciona una categoría para abrir un ticket.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())

# ===============================
# RUN
# ===============================

bot.run(os.getenv("TOKEN"))
