import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from typing import List, Optional

from utils.helpers import load_json, save_json, create_embed

class Rules(commands.Cog):
    """Commands for managing server rules"""
    
    def __init__(self, bot):
        self.bot = bot
        self.rules_file = "data/rules.json"
        self.rules = self.load_rules()
    
    def load_rules(self) -> List[dict]:
        """Load rules from JSON file"""
        data = load_json(self.rules_file)
        if not data:
            # Create default rules if file doesn't exist
            default_rules = [
                {
                    "title": "Be Respectful",
                    "description": "Treat all members with respect. No harassment, hate speech, or excessive profanity."
                },
                {
                    "title": "Stay On Topic",
                    "description": "Keep discussions related to ScheduleLua, Lua scripting, and Schedule 1 modding."
                },
                {
                    "title": "No Spamming",
                    "description": "Avoid excessive posting of the same content or message."
                },
                {
                    "title": "Report Bugs Properly",
                    "description": "Use GitHub Issues to report bugs with proper details and logs."
                },
                {
                    "title": "Share Code Properly",
                    "description": "When sharing code, use code blocks (``` ```). For longer code, use GitHub Gists or Pastebin."
                }
            ]
            save_json(self.rules_file, default_rules)
            return default_rules
        return data
    
    def save_rules(self) -> None:
        """Save rules to JSON file"""
        save_json(self.rules_file, self.rules)
    
    @app_commands.command(name="send_rules", description="Send the server rules to the rules channel")
    @app_commands.default_permissions(administrator=True)
    async def send_rules(self, interaction: discord.Interaction):
        """Send the server rules to the rules channel"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Get the rules channel
        rules_channel_id = int(os.getenv('RULES_CHANNEL_ID'))
        if not rules_channel_id:
            await interaction.response.send_message("Rules channel ID not configured in .env file.", ephemeral=True)
            return
            
        channel = self.bot.get_channel(rules_channel_id)
        if not channel:
            await interaction.response.send_message(f"Could not find channel with ID {rules_channel_id}.", ephemeral=True)
            return
        
        # Create the rules embed
        embed = discord.Embed(
            title="ScheduleLua Community Rules",
            description="Welcome to the ScheduleLua community! Please review and follow these rules to ensure a positive environment for everyone.",
            color=discord.Color.blue()
        )
        
        # Add each rule as a field
        for i, rule in enumerate(self.rules, 1):
            embed.add_field(
                name=f"{i}. {rule['title']}",
                value=rule['description'],
                inline=False
            )
        
        embed.set_footer(text="By participating in this server, you agree to follow these rules.")
        
        # Send the embed
        await interaction.response.send_message("Sending rules to the designated channel...", ephemeral=True)
        message = await channel.send(embed=embed)
        
        # Add reaction for users to acknowledge rules if needed
        await message.add_reaction("✅")
        
        self.bot.logger.info(f"Rules sent to channel {rules_channel_id} by {interaction.user}")
    
    @app_commands.command(name="add_rule", description="Add a new rule or edit an existing one")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        index="Rule number (1-based, use existing number to edit)",
        title="The rule title",
        description="The rule description"
    )
    async def add_rule(
        self, 
        interaction: discord.Interaction, 
        index: int, 
        title: str, 
        description: str
    ):
        """Add or edit a rule"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Check if index is valid
        if index < 1:
            await interaction.response.send_message("Rule index must be 1 or greater.", ephemeral=True)
            return
        
        # If index is beyond the list, pad with empty rules
        while len(self.rules) < index:
            self.rules.append({"title": "New Rule", "description": "No description"})
        
        # Update the rule
        self.rules[index-1] = {"title": title, "description": description}
        
        # Save to file
        self.save_rules()
        
        await interaction.response.send_message(f"Rule {index} has been added/updated.", ephemeral=True)
    
    @app_commands.command(name="edit_rule", description="Edit an existing rule")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        index="Rule number to edit (1-based)",
        title="The new rule title",
        description="The new rule description"
    )
    async def edit_rule(
        self, 
        interaction: discord.Interaction, 
        index: int, 
        title: str, 
        description: str
    ):
        """Edit an existing rule"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Check if index is valid
        if index < 1 or index > len(self.rules):
            await interaction.response.send_message(f"Invalid rule index. Valid range: 1-{len(self.rules)}.", ephemeral=True)
            return
        
        # Get the original rule for display
        original_rule = self.rules[index-1]
        
        # Update the rule
        self.rules[index-1] = {"title": title, "description": description}
        
        # Save to file
        self.save_rules()
        
        # Create an embed to show the changes
        embed = create_embed(
            title=f"Rule {index} Updated",
            description="The rule has been updated successfully.",
            color=discord.Color.green(),
            fields=[
                {
                    "name": "Original Title",
                    "value": original_rule["title"],
                    "inline": True
                },
                {
                    "name": "New Title",
                    "value": title,
                    "inline": True
                },
                {
                    "name": "Original Description",
                    "value": original_rule["description"],
                    "inline": False
                },
                {
                    "name": "New Description",
                    "value": description,
                    "inline": False
                }
            ]
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="remove_rule", description="Remove a rule")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(index="Rule number to remove (1-based)")
    async def remove_rule(self, interaction: discord.Interaction, index: int):
        """Remove a rule"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Check if index is valid
        if index < 1 or index > len(self.rules):
            await interaction.response.send_message(f"Invalid rule index. Valid range: 1-{len(self.rules)}.", ephemeral=True)
            return
        
        # Remove the rule
        removed_rule = self.rules.pop(index-1)
        
        # Save to file
        self.save_rules()
        
        await interaction.response.send_message(f"Rule {index} ({removed_rule['title']}) has been removed.", ephemeral=True)
    
    @app_commands.command(name="list_rules", description="List all rules")
    @app_commands.default_permissions(administrator=True)
    async def list_rules(self, interaction: discord.Interaction):
        """List all rules"""
        if not self.rules:
            await interaction.response.send_message("No rules configured.", ephemeral=True)
            return
        
        # Create an embed with all rules
        embed = create_embed(
            title="Server Rules",
            description=f"Total rules: {len(self.rules)}",
            color=discord.Color.blue()
        )
        
        for i, rule in enumerate(self.rules, 1):
            embed.add_field(
                name=f"{i}. {rule['title']}",
                value=rule['description'],
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    await bot.add_cog(Rules(bot)) 