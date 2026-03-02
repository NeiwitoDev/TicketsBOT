import discord
from discord.ext import commands, tasks
import os
import asyncio
import json
import itertools

# ===============================
# ⚙️ CONFIGURACIÓN
# ===============================

TICKET_CATEGORY_ID = 1466491475436245220

STAFF_ROLE_ID_1 = 1466244726796582964
STAFF_ROLE_ID_2 = 1466245030334435398
ALTO_MANDO_ROLE_ID = 1476595202813857857

TICKETS_FILE = "tickets.json"

# ===============================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# SISTEMA PERSISTENTE
# ===============================

def cargar_tickets():
    if not os.path.exists(TICKETS_FILE):
        return {}
    with open(TICKETS_FILE, "r") as f:
        return json.load(f)

def guardar_tickets(data):
    with open(TICKETS_FILE, "w") as f:
        json.dump(data, f, indent=4)

tickets_abiertos = cargar_tickets()

# ===============================
# READY
# ===============================

estados = itertools.cycle([
    discord.Activity(type=discord.ActivityType.watching, name="↪ Soporte Activo"),
    discord.Activity(type=discord.ActivityType.playing, name="↪ Sistema de Tickets PRO")
])

@tasks.loop(seconds=15)
async def cambiar_estado():
    await bot.change_presence(activity=next(estados))

@bot.event
async def on_ready():
    cambiar_estado.start()

    # 🔥 Views persistentes
    bot.add_view(TicketView())
    bot.add_view(TicketButtons(None, None))

    print(f"✅ Bot conectado como {bot.user}")

# ===============================
# MOTIVO CIERRE
# ===============================

class MotivoSelect(discord.ui.Select):
    def __init__(self, creador_id, tipo):
        self.creador_id = creador_id
        self.tipo = tipo

        options = [
            discord.SelectOption(label="Ticket Resuelto", emoji="✅"),
            discord.SelectOption(label="Inactividad", emoji="⏳"),
            discord.SelectOption(label="Cierre Administrativo", emoji="📁")
        ]

        super().__init__(
            placeholder="Selecciona el motivo del cierre...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        motivo = self.values[0]
        user_id = str(self.creador_id)

        if user_id in tickets_abiertos:
            if self.tipo in tickets_abiertos[user_id]:
                del tickets_abiertos[user_id][self.tipo]

            if not tickets_abiertos[user_id]:
                del tickets_abiertos[user_id]

        guardar_tickets(tickets_abiertos)

        embed = discord.Embed(
            title="🔒 Ticket Cerrado",
            description=f"**Motivo:** {motivo}\n\nEl canal se eliminará en 5 segundos.",
            color=discord.Color.red()
        )

        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(5)
        await interaction.channel.delete()

class MotivoView(discord.ui.View):
    def __init__(self, creador_id, tipo):
        super().__init__(timeout=60)
        self.add_item(MotivoSelect(creador_id, tipo))

# ===============================
# BOTONES TICKET
# ===============================

class TicketButtons(discord.ui.View):
    def __init__(self, creador_id, tipo):
        super().__init__(timeout=None)
        self.creador_id = creador_id
        self.tipo = tipo

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="cerrar_ticket")
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):

        canal = interaction.channel
        nombre = canal.name

        # detectar tipo y user del canal
        partes = nombre.split("-")
        user_id = partes[-1]
        tipo = "-".join(partes[:-1])

        await interaction.response.send_message(
            "Selecciona el motivo del cierre:",
            view=MotivoView(user_id, tipo),
            ephemeral=True
        )

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green, custom_id="reclamar_ticket")
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if STAFF_ROLE_ID_2 not in [r.id for r in interaction.user.roles]:
            await interaction.response.send_message(
                "❌ No tienes permiso para reclamar.",
                ephemeral=True
            )
            return

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
            options=options,
            custom_id="ticket_select"
        )

    async def callback(self, interaction: discord.Interaction):

        user = interaction.user
        tipo = self.values[0]
        user_id = str(user.id)

        if user_id not in tickets_abiertos:
            tickets_abiertos[user_id] = {}

        if tipo in tickets_abiertos[user_id]:
            await interaction.response.send_message(
                "❌ Ya tienes un ticket abierto en esta categoría.",
                ephemeral=True
            )
            return

        categoria = interaction.guild.get_channel(TICKET_CATEGORY_ID)

        nombre_canal = f"{tipo.replace(' ', '-').lower()}-{user.id}"

        canal = await interaction.guild.create_text_channel(
            name=nombre_canal,
            category=categoria
        )

        await canal.set_permissions(interaction.guild.default_role, read_messages=False)
        await canal.set_permissions(user, read_messages=True, send_messages=True)

        embed = discord.Embed(
            title=f"🎫 Ticket - {tipo}",
            description="Un miembro del staff te atenderá pronto.\n\n"
                        "🔒 Usa el botón para cerrar cuando el problema esté resuelto.",
            color=discord.Color.green()
        )

        await canal.send(embed=embed, view=TicketButtons(user.id, tipo))

        tickets_abiertos[user_id][tipo] = canal.id
        guardar_tickets(tickets_abiertos)

        await interaction.response.send_message(
            f"🎫 Ticket creado correctamente: {canal.mention}",
            ephemeral=True
        )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# ===============================
# PANEL MEJORADO
# ===============================

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="🎟️ 𝗖𝗘𝗡𝗧𝗥𝗢 𝗗𝗘 𝗦𝗢𝗣𝗢𝗥𝗧𝗘",
        description=(
            "━━━━━━━━━━━━━━━━━━\n\n"
            "📌 **Abre un ticket seleccionando una categoría**\n\n"
            "🛠️ Soporte General\n"
            "🎁 Reclamar Beneficios\n"
            "🚨 Reportar Usuario\n"
            "⚖️ Reportar Moderador\n\n"
            "━━━━━━━━━━━━━━━━━━"
        ),
        color=0x2F3136
    )

    embed.set_footer(text="Sistema de Tickets • RP Server")

    await ctx.send(embed=embed, view=TicketView())

# ===============================
# RUN
# ===============================

bot.run(os.getenv("TOKEN"))
