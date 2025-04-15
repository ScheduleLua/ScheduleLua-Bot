import discord
import json
import os
import requests
from typing import Dict, Any, Optional, List, Union

def load_json(filename: str) -> Dict[str, Any]:
    """Load data from a JSON file"""
    if not os.path.isfile(filename):
        return {}
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(filename: str, data: Dict[str, Any]) -> None:
    """Save data to a JSON file"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)

def create_embed(
    title: str, 
    description: str = None, 
    color: discord.Color = discord.Color.blue(),
    fields: List[Dict[str, str]] = None,
    footer: str = None,
    thumbnail: str = None,
    image: str = None
) -> discord.Embed:
    """Create a Discord embed with the given parameters"""
    embed = discord.Embed(title=title, description=description, color=color)
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get("name", ""),
                value=field.get("value", ""),
                inline=field.get("inline", True)
            )
    
    if footer:
        embed.set_footer(text=footer)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
        
    return embed

def is_owner(ctx) -> bool:
    """Check if the command invoker is the bot owner"""
    return ctx.author.id == int(os.getenv('OWNER_ID'))

def fetch_url_content(url: str) -> str:
    """Fetch content from a URL"""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.text
    except Exception as e:
        raise Exception(f"Error fetching URL: {e}") 