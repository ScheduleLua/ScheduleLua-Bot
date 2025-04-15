import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import time
from typing import Dict, List, Optional
import asyncio
import re

from utils.helpers import load_json, save_json, create_embed, is_owner

class AutoResponse(commands.Cog):
    """Handles automatic responses to specific keywords or phrases"""
    
    def __init__(self, bot):
        self.bot = bot
        self.responses_file = "data/auto_responses.json"
        self.responses = self.load_responses()
        self.cooldowns = {}
        self.cooldown_time = int(os.getenv('AUTO_RESPONSE_COOLDOWN', 60))
    
    def load_responses(self) -> Dict[str, Dict]:
        """Load auto responses from JSON file"""
        data = load_json(self.responses_file)
        if not data:
            # Create default responses if file doesn't exist
            default_responses = {
                "install": {
                    "triggers": ["how to install", "installation", "setup guide"],
                    "response": "To install ScheduleLua, check out our installation guide: https://ifbars.github.io/ScheduleLua-Docs/guide/installation.html",
                    "embed": True
                },
                "getting_started": {
                    "triggers": ["getting started", "how to use", "first script"],
                    "response": "To get started with ScheduleLua, follow our Getting Started guide: https://ifbars.github.io/ScheduleLua-Docs/guide/getting-started.html",
                    "embed": True
                }
            }
            save_json(self.responses_file, default_responses)
            return default_responses
        return data
    
    def save_responses(self) -> None:
        """Save auto responses to JSON file"""
        save_json(self.responses_file, self.responses)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Process messages for auto-responses"""
        # Skip bot messages and commands
        if message.author.bot or message.content.startswith('!'):
            return
            
        # Check if the channel has been triggered recently
        current_time = time.time()
        if message.channel.id in self.cooldowns:
            if current_time - self.cooldowns[message.channel.id] < self.cooldown_time:
                return
        
        message_content = message.content.lower()
        
        # Check each response for triggers
        for key, data in self.responses.items():
            for trigger in data.get("triggers", []):
                if re.search(r'\b' + re.escape(trigger.lower()) + r'\b', message_content):
                    # Found a trigger
                    self.cooldowns[message.channel.id] = current_time
                    
                    if data.get("embed", False):
                        # Create an embed response
                        embed = create_embed(
                            title="ScheduleLua Help",
                            description=data["response"],
                            color=discord.Color.blue()
                        )
                        await message.channel.send(embed=embed)
                    else:
                        # Send a regular message response
                        await message.channel.send(data["response"])
                    
                    self.bot.logger.info(f"Auto-response triggered: {key}")
                    return  # Only trigger one response
    
    @app_commands.command(name="autoresponse_add", description="Add or edit an auto-response")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        name="A unique name for this auto-response",
        trigger="The trigger phrase (separate multiple with |)",
        response="The response message",
        use_embed="Whether to send the response as an embed"
    )
    async def add_response(
        self, 
        interaction: discord.Interaction, 
        name: str, 
        trigger: str, 
        response: str, 
        use_embed: bool = True
    ):
        """Add or edit an auto-response"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        # Create or update the response
        triggers = [t.strip() for t in trigger.split('|')]
        self.responses[name] = {
            "triggers": triggers,
            "response": response,
            "embed": use_embed
        }
        
        # Save to file
        self.save_responses()
        
        await interaction.response.send_message(
            f"Auto-response `{name}` has been added/updated with {len(triggers)} triggers.",
            ephemeral=True
        )
    
    @app_commands.command(name="autoresponse_list", description="List all auto-responses")
    @app_commands.default_permissions(administrator=True)
    async def list_responses(self, interaction: discord.Interaction):
        """List all auto-responses"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        if not self.responses:
            await interaction.response.send_message("No auto-responses configured.", ephemeral=True)
            return
            
        # Create an embed with all responses
        embed = create_embed(
            title="Auto-Responses",
            description=f"Total auto-responses: {len(self.responses)}",
            color=discord.Color.blue()
        )
        
        for name, data in self.responses.items():
            embed.add_field(
                name=name,
                value=f"Triggers: {', '.join(data['triggers'])}\nEmbed: {data['embed']}",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="autoresponse_remove", description="Remove an auto-response")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(name="The name of the auto-response to remove")
    async def remove_response(self, interaction: discord.Interaction, name: str):
        """Remove an auto-response"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        if name not in self.responses:
            await interaction.response.send_message(f"Auto-response `{name}` not found.", ephemeral=True)
            return
            
        # Remove the response
        del self.responses[name]
        
        # Save to file
        self.save_responses()
        
        await interaction.response.send_message(f"Auto-response `{name}` has been removed.", ephemeral=True)

async def setup(bot):
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    await bot.add_cog(AutoResponse(bot)) 