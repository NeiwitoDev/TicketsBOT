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

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

# ===============================
# VISTA BOTONES TICKET
# ===============================

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando ticket en 5 segundos...")
        await asyncio.sleep(5)
        await interaction.channel.delete()

    @discord.ui.button(label="📌 Reclamar Ticket", style=discord.ButtonStyle.green)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        canal = interaction.channel
        user = interaction.user

        staff_role_1 = guild.get_role(STAFF_ROLE_ID_1)
        staff_role_2 = guild.get_role(STAFF_ROLE_ID_2)
        alto_mando_role = guild.get_role(ALTO_MANDO_ROLE_ID)

        # Verificar que sea staff
        if not (
            staff_role_1 in user.roles or
            staff_role_2 in user.roles or
            alto_mando_role in user.roles
        ):
            await interaction.response.send_message(
                "❌ Solo el staff puede reclamar tickets.",
                ephemeral=True
            )
            return

        # Bloquear escritura a staff normal
        if staff_role_1:
            await canal.set_permissions(staff_role_1, send_messages=False)
        if staff_role_2:
            await canal.set_permissions(staff_role_2, send_messages=False)

        # Permitir escribir al que reclama
        await canal.set_permissions(user, send_messages=True)

        # Alto mando siempre puede escribir
        if alto_mando_role:
            await canal.set_permissions(alto_mando_role, send_messages=True)

        embed = discord.Embed(
            title="📌 Ticket Reclamado",
            description=f"Este ticket fue reclamado por {user.mention}",
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=embed)

# ===============================
# CREACIÓN TICKET
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

        if not categoria:
            await interaction.response.send_message(
                "❌ Error: categoría no encontrada.",
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
            description="Describe tu problema. Un miembro del staff te responderá pronto.",
            color=discord.Color.green()
        )

        embed.add_field(name="👤 Usuario", value=user.mention)

        staff_role_1 = guild.get_role(STAFF_ROLE_ID_1)
        staff_role_2 = guild.get_role(STAFF_ROLE_ID_2)

        await canal.send(
            content=f"{staff_role_1.mention if staff_role_1 else ''} {staff_role_2.mention if staff_role_2 else ''}",
            embed=embed,
            view=TicketButtons()
        )

        await interaction.response.send_message(
            "✅ Ticket creado correctamente.",
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
        description="¡Bienvenido al Panel de tickets! Aqui Puedes abrir 1 ticket si tienes un problema... Recuerda no abrir sin motivo.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())

bot.run(os.getenv("TOKEN"))
