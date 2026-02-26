import discord
from discord.ext import commands

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


CATEGORIA_TICKETS = 1466491475436245220
ROL_STAFF_1 = 1466244726796582964
ROL_STAFF_2 = 1466245030334435398
CANAL_COMANDO_CALIFICAR = 1466231866041307187
CANAL_LOGS_CALIFICACIONES = 1466240831609638923


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
        super().__init__(placeholder="Selecciona una categoría...", options=options)

    async def callback(self, interaction: discord.Interaction):
        categoria_nombre = self.values[0]

        # Anti doble ticket por categoría
        for canal in interaction.guild.channels:
            if canal.category and canal.category.id == CATEGORIA_TICKETS:
                if canal.name == f"{categoria_nombre.lower().replace(' ', '-')}-{interaction.user.id}":
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
            name=f"{categoria_nombre.lower().replace(' ', '-')}-{interaction.user.id}",
            category=categoria,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Ticket Creado",
            description=f"Categoría: **{categoria_nombre}**\n\nUn staff te atenderá pronto.",
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
        self.add_item(discord.ui.Button(label="🔎 Ver Ticket", url=canal.jump_url))


# =========================
# BOTONES DENTRO DEL TICKET
# =========================

class TicketButtons(discord.ui.View):
    def __init__(self, usuario):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.staff_reclamador = None

    @discord.ui.button(label="🛡 Reclamar Ticket", style=discord.ButtonStyle.primary)
    async def reclamar(self, interaction: discord.Interaction, button: discord.ui.Button):

        if self.staff_reclamador:
            await interaction.response.send_message("❌ Ya fue reclamado.", ephemeral=True)
            return

        self.staff_reclamador = interaction.user

        for member in interaction.channel.members:
            if ROL_STAFF_1 not in [r.id for r in member.roles] and ROL_STAFF_2 not in [r.id for r in member.roles]:
                await interaction.channel.set_permissions(member, send_messages=False)

        await interaction.response.send_message(
            f"✅ Ticket reclamado por {interaction.user.mention}"
        )

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.danger)
    async def cerrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CerrarModal(self.usuario, self.staff_reclamador))


class CerrarModal(discord.ui.Modal, title="Cerrar Ticket"):
    motivo = discord.ui.TextInput(label="Motivo del cierre", required=True)

    def __init__(self, usuario, staff):
        super().__init__()
        self.usuario = usuario
        self.staff = staff

    async def on_submit(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🎫 Tu ticket fue cerrado",
            color=0xFFFFFF
        )
        embed.add_field(name="👮 Staff", value=self.staff.mention if self.staff else "No reclamado", inline=False)
        embed.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
        embed.add_field(name="⭐ ¿Deseas calificar al staff?", value="Presiona el botón abajo.", inline=False)

        view = CalificarView(self.usuario, self.staff)

        try:
            await self.usuario.send(embed=embed, view=view)
        except:
            pass

        await interaction.channel.delete()


# =========================
# CALIFICACIÓN
# =========================

class CalificarView(discord.ui.View):
    def __init__(self, usuario, staff):
        super().__init__(timeout=None)
        self.usuario = usuario
        self.staff = staff

    @discord.ui.button(label="⭐ Calificar Staff", style=discord.ButtonStyle.success)
    async def calificar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CalificacionModal(self.usuario, self.staff))


class CalificacionModal(discord.ui.Modal, title="Calificar Staff"):
    estrellas = discord.ui.TextInput(label="Calificación (1-5)", max_length=1)
    nota = discord.ui.TextInput(label="¿Por qué esa calificación?", style=discord.TextStyle.paragraph)

    def __init__(self, usuario, staff):
        super().__init__()
        self.usuario = usuario
        self.staff = staff

    async def on_submit(self, interaction: discord.Interaction):

        guild = bot.get_guild(interaction.user.mutual_guilds[0].id)
        canal_logs = guild.get_channel(CANAL_LOGS_CALIFICACIONES)

        estrellas_num = int(self.estrellas.value)
        estrellas_visual = "⭐" * estrellas_num

        embed = discord.Embed(
            title="📊 Nueva Calificación",
            color=0xFFFFFF
        )
        embed.add_field(name="👤 Usuario", value=self.usuario.mention, inline=False)
        embed.add_field(name="🛡 Staff", value=self.staff.mention if self.staff else "No reclamado", inline=False)
        embed.add_field(name="⭐ Calificación", value=estrellas_visual, inline=False)
        embed.add_field(name="📝 Nota", value=self.nota.value, inline=False)

        await canal_logs.send(embed=embed)
        await interaction.response.send_message("✅ Calificación enviada.", ephemeral=True)


# =========================
# COMANDOS
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


@bot.command(name="calificar-staff")
async def calificar_staff(ctx, staff: discord.Member, calificacion: int, *, nota):

    if ctx.channel.id != CANAL_COMANDO_CALIFICAR:
        return

    canal_logs = ctx.guild.get_channel(CANAL_LOGS_CALIFICACIONES)

    estrellas_visual = "⭐" * calificacion

    embed = discord.Embed(
        title="📊 Nueva Calificación Manual",
        color=0xFFFFFF
    )
    embed.add_field(name="👤 Usuario", value=ctx.author.mention, inline=False)
    embed.add_field(name="🛡 Staff", value=staff.mention, inline=False)
    embed.add_field(name="⭐ Calificación", value=estrellas_visual, inline=False)
    embed.add_field(name="📝 Nota", value=nota, inline=False)

    await canal_logs.send(embed=embed)
    await ctx.send("✅ Calificación enviada.")


# =========================

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

bot.run(os.getenv("TOKEN"))
