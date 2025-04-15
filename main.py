import os
import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("schedulelua_bot")

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID'))
APPLICATION_ID = int(os.getenv('APPLICATION_ID'))
GUILD_ID = int(os.getenv('GUILD_ID')) if os.getenv('GUILD_ID') else None

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Enable message content intent for auto-responses
intents.members = True  # Enable member tracking

# Create bot instance
class ScheduleLuaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',  # Fallback prefix, mainly using slash commands
            intents=intents,
            application_id=APPLICATION_ID,
            owner_id=OWNER_ID
        )
        self.logger = logger
        
    async def setup_hook(self):
        """Setup hook runs when the bot is starting up"""
        await self.load_cogs()
        
        # Sync commands with Discord
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            self.logger.info(f"Synced commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            self.logger.info("Synced global commands")
    
    async def load_cogs(self):
        """Load all cogs from the cogs directory"""
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    self.logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    self.logger.error(f"Failed to load cog {filename}: {e}")
    
    async def on_ready(self):
        """Event triggered when the bot is ready"""
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, 
                name="ScheduleLua | /help"
            )
        )
        self.logger.info("Bot is ready!")

# Run the bot
def main():
    bot = ScheduleLuaBot()
    bot.run(TOKEN, log_handler=None)  # Disable default logging handler

if __name__ == "__main__":
    main() 