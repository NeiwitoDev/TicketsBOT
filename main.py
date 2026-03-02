import discord
from discord.ext import commands
from discord.ui import View, Button
import json
import os

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------------
# SISTEMA PERSISTENTE
# ------------------------

def get_ticket_number():
    with open("ticket_counter.json", "r") as f:
        data = json.load(f)

    data["last_ticket"] += 1

    with open("ticket_counter.json", "w") as f:
        json.dump(data, f, indent=4)

    return data["last_ticket"]

# ------------------------
# BOTÓN CREAR TICKET
# ------------------------

class TicketPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="ver-ticket", style=discord.ButtonStyle.green, emoji="🎫", custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):

        ticket_number = get_ticket_number()
        ticket_name = f"TICKET-{ticket_number:03d}"

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=ticket_name,
            overwrites=overwrites,
            category=interaction.channel.category
        )

        embed = discord.Embed(
            title="📩 Ticket Creado Correctamente",
            description=f"{interaction.user.mention}, tu ticket fue abierto con éxito.\n\nUn miembro del staff te atenderá pronto.",
            color=0x2ecc71
        )

        embed.add_field(name="🆔 Número", value=f"`{ticket_name}`", inline=True)
        embed.set_footer(text="Sistema de Tickets • Stars Solutions Studios")

        await channel.send(embed=embed, view=CloseTicket())

        await interaction.response.send_message(
            f"✅ Tu ticket fue creado: {channel.mention}",
            ephemeral=True
        )

# ------------------------
# BOTÓN CERRAR TICKET
# ------------------------

class CloseTicket(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):

        user = interaction.user
        channel = interaction.channel

        try:
            await user.send(f"🔒 Tu ticket `{channel.name}` fue cerrado por el staff.")
        except:
            pass

        await interaction.response.send_message("🗑 Cerrando ticket...", ephemeral=True)
        await channel.delete()

# ------------------------
# COMANDO PARA ENVIAR PANEL
# ------------------------

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):

    embed = discord.Embed(
        title="🎟 Sistema de Tickets",
        description=(
            "¿Necesitas ayuda?\n\n"
            "Presiona el botón **ver-ticket** para abrir un ticket privado.\n\n"
            "📌 Nuestro equipo responderá lo antes posible."
        ),
        color=0x3498db
    )

    embed.add_field(name="⏱ Tiempo de Respuesta", value="Entre 5 a 30 minutos.", inline=False)
    embed.add_field(name="📜 Reglas", value="No abuses del sistema o será sancionado.", inline=False)
    embed.set_footer(text="Stars Solutions Studios • Soporte Oficial")

    await ctx.send(embed=embed, view=TicketPanel())

# ------------------------
# PERSISTENCIA AL REINICIAR
# ------------------------

@bot.event
async def on_ready():
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicket())
    print(f"Bot conectado como {bot.user}")

bot.run("TU_TOKEN_AQUI")
