import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List, Optional
import datetime
import random

from utils.helpers import create_embed, load_json, save_json

class Info(commands.Cog):
    """Commands for providing information about ScheduleLua"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="about", description="Get information about ScheduleLua")
    async def about(self, interaction: discord.Interaction):
        """Provides information about ScheduleLua"""
        embed = create_embed(
            title="About ScheduleLua",
            description="ScheduleLua is a Lua modding framework for Schedule 1, allowing you to create custom scripts and mods using Lua.",
            color=discord.Color.blue(),
            fields=[
                {
                    "name": "Documentation",
                    "value": "[ScheduleLua Docs](https://schedulelua.github.io/ScheduleLua-Docs/)",
                    "inline": True
                },
                {
                    "name": "GitHub Repository",
                    "value": "[GitHub](https://github.com/ScheduleLua/ScheduleLua-Framework)",
                    "inline": True
                },
                {
                    "name": "Report Bugs",
                    "value": "[GitHub Issues](https://github.com/ScheduleLua/ScheduleLua-Framework/issues)",
                    "inline": True
                }
            ],
            footer="ScheduleLua - Enhancing Schedule 1 with Lua scripting",
            thumbnail="https://github.com/ScheduleLua/ScheduleLua-Framework/raw/main/logo.png"
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="docs", description="Get links to ScheduleLua documentation")
    async def docs(self, interaction: discord.Interaction):
        """Provides links to ScheduleLua documentation"""
        base_url = "https://schedulelua.github.io/ScheduleLua-Docs"
        
        embed = create_embed(
            title="ScheduleLua Documentation",
            description="Here are the main documentation resources for ScheduleLua:",
            color=discord.Color.blue(),
            fields=[
                {
                    "name": "Getting Started",
                    "value": f"[Installation Guide]({base_url}/guide/installation.html)\n[Getting Started]({base_url}/guide/getting-started.html)",
                    "inline": False
                },
                {
                    "name": "API Reference",
                    "value": f"[API Documentation]({base_url}/api/)",
                    "inline": False
                },
                {
                    "name": "Examples",
                    "value": f"[Example Scripts]({base_url}/examples/)",
                    "inline": False
                },
                {
                    "name": "Contributing",
                    "value": f"[Contributing Guide]({base_url}/guide/contributing.html)",
                    "inline": False
                }
            ]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="report", description="Get information on how to report bugs or request features")
    async def report(self, interaction: discord.Interaction):
        """Provides information on how to report bugs or request features"""
        embed = create_embed(
            title="Report Bugs & Request Features",
            description="Help improve ScheduleLua by reporting bugs and requesting new features:",
            color=discord.Color.blue(),
            fields=[
                {
                    "name": "Report Bugs",
                    "value": "1. Go to [GitHub Issues](https://github.com/ScheduleLua/ScheduleLua-Framework/issues)\n2. Click 'New Issue'\n3. Select 'Bug Report'\n4. Fill in the template with details about the bug\n5. Submit the issue",
                    "inline": False
                },
                {
                    "name": "Request Features",
                    "value": "1. Go to [GitHub Issues](https://github.com/ScheduleLua/ScheduleLua-Framework/issues)\n2. Click 'New Issue'\n3. Select 'Feature Request'\n4. Describe the feature you'd like to see\n5. Submit the issue",
                    "inline": False
                },
                {
                    "name": "What to Include",
                    "value": "- Clear description of the bug/feature\n- Steps to reproduce (for bugs)\n- Expected vs. actual behavior\n- System information\n- Screenshots if applicable",
                    "inline": False
                }
            ]
        )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="quote", description="Get a random John Lua quote")
    async def quote(self, interaction: discord.Interaction):
        """Returns a random John Lua quote"""
        quotes_file = "data/john_lua_quotes.json"
        
        try:
            data = load_json(quotes_file)
            quotes = data.get("quotes", [])
            
            if not quotes:
                await interaction.response.send_message("No quotes found in the quotes file.", ephemeral=True)
                return
                
            random_quote = random.choice(quotes)
            
            embed = create_embed(
                title="John Lua Says...",
                description=f"*\"{random_quote}\"*",
                color=discord.Color.gold()
            )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.bot.logger.error(f"Error retrieving quote: {e}")
            await interaction.response.send_message("Failed to retrieve a quote.", ephemeral=True)
    
    @app_commands.command(name="help", description="Get help with ScheduleLua commands")
    async def help_command(self, interaction: discord.Interaction):
        """Provides help with bot commands"""
        embed = create_embed(
            title="ScheduleLua Bot Commands",
            description="Here are the available commands:",
            color=discord.Color.blue()
        )
        
        # Info commands
        embed.add_field(
            name="Information",
            value=(
                "/about - Get information about ScheduleLua\n"
                "/docs - Get documentation links\n"
                "/report - Learn how to report bugs or request features\n"
                "/help - Show this help message\n"
                "/chat - Chat with the AI assistant about ScheduleLua\n"
                "/quote - Get a random John Lua quote"
            ),
            inline=False
        )
        
        # Only show admin commands to the owner
        if interaction.user.id == int(os.getenv('OWNER_ID')):
            embed.add_field(
                name="Administration (Owner Only)",
                value=(
                    "/sync - Sync application commands\n"
                    "/reload <cog> - Reload a specific cog\n"
                    "/shutdown - Shut down the bot\n"
                    "/send_rules - Send rules to the rules channel\n"
                    "/add_rule - Add a new rule\n"
                    "/edit_rule - Edit an existing rule\n"
                    "/remove_rule - Remove a rule\n"
                    "/list_rules - List all rules\n"
                    "/autoresponse_add - Add or edit an auto-response\n"
                    "/autoresponse_list - List all auto-responses\n"
                    "/autoresponse_remove - Remove an auto-response\n"
                    "/add_doc - Add a documentation file\n"
                    "/scrape_documentation - Scrape ScheduleLua documentation\n"
                    "/list_docs - List all documentation files\n"
                    "/remove_doc - Remove a documentation file"
                ),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Info(bot)) 