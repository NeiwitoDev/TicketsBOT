import os
import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# 🔐 TOKEN desde Railway
TOKEN = os.getenv("TOKEN")

CATEGORIA_TICKETS = 1466491475436245220
ROL_STAFF_1 = 1466244726796582964
ROL_STAFF_2 = 1466245030334435398


# =========================
# PANEL DE TICKETS
# =========================

class TicketSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Soporte General"),
            discord.SelectOption(label="Reclamar Beneficios"),
            discord.SelectOption(label="Reportar Usuario"),
            discord.SelectOption(label="Reportar Moderador"),
        ]
        super().__init__(
            placeholder="Selecciona una categoría...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        categoria_nombre = self.values[0]
        nombre_canal = f"{categoria_nombre.lower().replace(' ', '-')}-{interaction.user.id}"

        # 🔒 Anti doble ticket por categoría
        for canal in interaction.guild.channels:
            if canal.category and canal.category.id == CATEGORIA_TICKETS:
                if canal.name == nombre_canal:
                    await interaction.response.send_message(
                        "❌ Ya tienes un ticket de esta categoría creado.",
                        ephemeral=True
                    )
                    return

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(ROL_STAFF_1): discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(ROL_STAFF_2): discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        categoria = interaction.guild.get_channel(CATEGORIA_TICKETS)

        canal = await interaction.guild.create_text_channel(
            name=nombre_canal,
            category=categoria,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Creado",
            description=f"Categoría: **{categoria_nombre}**\n\nUn miembro del staff te atenderá pronto.",
            color=0xFFFFFF
        )

        view = TicketButtons(interaction.user)

        await canal.send(
            content=f"<@&{ROL_STAFF_1}> <@&{ROL_STAFF_2}>",
            embed=embed,
            view=view
        )

        view_link = VerTicketView(canal)

        await interaction.response.send_message(
            "🎫 Ticket creado correctamente.",
            view=view_link,
            ephemeral=True
        )


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


class VerTicketView(discord.ui.View):
    def __init__(self, canal):
        super().__init__(timeout=60)
        self.add_item(discord.ui.Button(
            label="🔎 Ver Ticket",
            url=canal.jump_url
        ))


# =========================
# BOTONES DEL TICKET
# =========================

class TicketButtons(discord.ui.View):
    def __init__(self, usuario):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.staff_reclamador = None

    @discord.ui.button(label="🛡 Reclamar Ticket", style=discord.ButtonStyle.primary)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.staff_reclamador:
            await interaction.response.send_message(
                "❌ Este ticket ya fue reclamado.",
                ephemeral=True
            )
            return

        self.staff_reclamador = interaction.user

        # Bloquear escritura a no-staff
        for member in interaction.channel.members:
            if ROL_STAFF_1 not in [r.id for r in member.roles] and \
               ROL_STAFF_2 not in [r.id for r in member.roles]:
                await interaction.channel.set_permissions(member, send_messages=False)

        await interaction.response.send_message(
            f"✅ Ticket reclamado por {interaction.user.mention}"
        )

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "🔒 Cerrando ticket...",
            ephemeral=True
        )

        await interaction.channel.delete()


# =========================
# COMANDO PANEL
# =========================

@bot.command(name="panel-send")
@commands.has_permissions(administrator=True)
async def panel_send(ctx):

    embed = discord.Embed(
        title="🎟️ Centro de Soporte",
        description="Selecciona una categoría para abrir un ticket.",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())


# =========================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")


# 🔥 INICIO
bot.run(TOKEN)
