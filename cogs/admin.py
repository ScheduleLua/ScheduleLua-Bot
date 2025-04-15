import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
import traceback
from typing import Optional

class Admin(commands.Cog):
    """Admin commands for bot management (owner only)"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check if the user is the bot owner"""
        return await self.bot.is_owner(ctx.author)
    
    @app_commands.command(name="sync", description="Sync application commands")
    @app_commands.guilds(int(os.getenv('GUILD_ID')))  # Restrict to specific guild
    @app_commands.default_permissions(administrator=True)
    async def sync(self, interaction: discord.Interaction):
        """Sync application commands to Discord"""
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
        
        try:
            guild = discord.Object(id=interaction.guild_id)
            self.bot.tree.copy_global_to(guild=guild)
            await self.bot.tree.sync(guild=guild)
            await interaction.response.send_message("Commands synced successfully!", ephemeral=True)
            self.bot.logger.info(f"Commands synced by {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"Error syncing commands: {e}", ephemeral=True)
            self.bot.logger.error(f"Command sync error: {e}")
    
    @app_commands.command(name="reload", description="Reload a cog")
    @app_commands.guilds(int(os.getenv('GUILD_ID')))  # Restrict to specific guild
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(cog="The cog to reload")
    async def reload(self, interaction: discord.Interaction, cog: str):
        """Reload a specific cog"""
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
        
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await interaction.response.send_message(f"Cog `{cog}` reloaded successfully!", ephemeral=True)
            self.bot.logger.info(f"Cog {cog} reloaded by {interaction.user}")
        except Exception as e:
            await interaction.response.send_message(f"Error reloading cog `{cog}`: {e}", ephemeral=True)
            self.bot.logger.error(f"Cog reload error: {e}")
    
    @app_commands.command(name="shutdown", description="Shut down the bot")
    @app_commands.guilds(int(os.getenv('GUILD_ID')))  # Restrict to specific guild
    @app_commands.default_permissions(administrator=True)
    async def shutdown(self, interaction: discord.Interaction):
        """Shut down the bot"""
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("Only the bot owner can use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message("Shutting down...", ephemeral=True)
        self.bot.logger.info(f"Bot shutdown requested by {interaction.user}")
        await self.bot.close()

async def setup(bot):
    await bot.add_cog(Admin(bot)) 