import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import aiohttp
import datetime
import json
from typing import Dict, Any, Optional, List
import logging

from utils.helpers import create_embed, load_json, save_json

# Load configuration from environment variables
DATA_FILE = "data/thunderstore_data.json"
DEFAULT_CHECK_INTERVAL = 30  # minutes

class ThunderstoreUpdates(commands.Cog):
    """Cog for monitoring Thunderstore updates for ScheduleLua"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger("schedulelua_bot.thunderstore")
        self.update_channel_id = int(os.getenv('UPDATES_CHANNEL_ID', 0))
        self.data = self._load_data()
        self.check_interval = int(os.getenv('THUNDERSTORE_CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL))
        
        # Load API configuration from environment variables
        self.api_base_url = os.getenv('THUNDERSTORE_API_URL', 'https://thunderstore.io/api/experimental').rstrip('/')
        self.package_namespace = os.getenv('THUNDERSTORE_NAMESPACE', 'ScheduleLua')
        self.package_name = os.getenv('THUNDERSTORE_PACKAGE_NAME', 'ScheduleLua')
        self.package_full_path = os.getenv('THUNDERSTORE_FULL_PATH', '')
        
        # Ensure we're using experimental endpoints
        if '/experimental' not in self.api_base_url:
            self.api_base_url = self.api_base_url.replace('/api', '/api/experimental')
            self.logger.warning(f"API URL adjusted to ensure experimental endpoints: {self.api_base_url}")
        
        if not self.package_full_path:
            # If full path not specified, construct it from namespace and name
            if self.package_namespace and self.package_name:
                self.package_full_path = f"{self.package_namespace}/{self.package_name}"
            else:
                self.logger.error("Package namespace or name not configured properly.")
                return
        
        # Start the background task if channel ID is configured
        if self.update_channel_id:
            self.check_for_updates.start()
        else:
            self.logger.warning("UPDATES_CHANNEL_ID not configured. Thunderstore update notifications disabled.")
    
    def _load_data(self) -> Dict[str, Any]:
        """Load saved data about the last checked update"""
        data = load_json(DATA_FILE)
        if not data:
            return {"last_version": None, "last_checked": None}
        return data
    
    def _save_data(self) -> None:
        """Save data about the last checked update"""
        save_json(DATA_FILE, self.data)
    
    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.update_channel_id:
            self.check_for_updates.cancel()
    
    @tasks.loop(minutes=DEFAULT_CHECK_INTERVAL)
    async def check_for_updates(self):
        """Periodically check for updates to ScheduleLua on Thunderstore"""
        try:
            self.logger.info("Checking for ScheduleLua updates on Thunderstore...")
            
            # Update check interval from env if needed
            if self.check_interval != int(os.getenv('THUNDERSTORE_CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL)):
                self.check_interval = int(os.getenv('THUNDERSTORE_CHECK_INTERVAL', DEFAULT_CHECK_INTERVAL))
                self.check_for_updates.change_interval(minutes=self.check_interval)
                self.logger.info(f"Update check interval changed to {self.check_interval} minutes")
            
            # --- FIRST API CALL: Get package information ---
            package_url = f"{self.api_base_url}/package/{self.package_namespace}/{self.package_name}/"
            self.logger.info(f"API Call 1/3: experimental_package_read: {package_url}")
            
            async with aiohttp.ClientSession() as session:
                # Get package data
                async with session.get(package_url) as response:
                    if response.status != 200:
                        self.logger.error(f"API Error: Failed to fetch package data: HTTP {response.status}")
                        self.logger.error(f"URL: {package_url}")
                        return
                    
                    try:
                        package_data = await response.json()
                    except json.JSONDecodeError:
                        self.logger.error("API Error: Invalid JSON response from package endpoint")
                        return
                    
                    # Validate required fields
                    if "latest" not in package_data:
                        self.logger.error("API Error: Missing 'latest' field in package data")
                        return
                    
                    latest = package_data.get("latest", {})
                    latest_version = latest.get("version_number")
                    
                    if not latest_version:
                        self.logger.error("API Error: Missing or invalid version number in latest data")
                        return
                    
                    # If we have a new version to process
                    if not self.data["last_version"] or latest_version != self.data["last_version"]:
                        channel = self.bot.get_channel(self.update_channel_id)
                        if not channel:
                            self.logger.error(f"Could not find update channel with ID {self.update_channel_id}")
                            return
                        
                        # --- SECOND API CALL: Get detailed version information ---
                        version_url = f"{self.api_base_url}/package/{self.package_namespace}/{self.package_name}/{latest_version}/"
                        self.logger.info(f"API Call 2/3: experimental_package_version_read: {version_url}")
                        
                        try:
                            async with session.get(version_url) as version_response:
                                if version_response.status != 200:
                                    self.logger.warning(f"API Warning: Failed to fetch version details: HTTP {version_response.status}")
                                    version_data = latest  # Use limited data from package response as fallback
                                else:
                                    try:
                                        version_data = await version_response.json()
                                    except json.JSONDecodeError:
                                        self.logger.warning("API Warning: Invalid JSON from version endpoint, using fallback data")
                                        version_data = latest
                        except Exception as e:
                            self.logger.warning(f"Error in version API call: {e}")
                            version_data = latest
                        
                        # --- THIRD API CALL: Get changelog ---
                        changelog = await self._fetch_changelog(session, latest_version)
                        
                        # Combine all data and send the notification
                        await self._send_update_notification(channel, package_data, version_data, changelog)
                        
                        # Update saved data
                        self.data["last_version"] = latest_version
                        self.data["last_checked"] = datetime.datetime.now().isoformat()
                        self._save_data()
                        
                        self.logger.info(f"New version processed: {latest_version}")
                    else:
                        self.logger.info(f"No new updates. Current version: {latest_version}")
                        self.data["last_checked"] = datetime.datetime.now().isoformat()
                        self._save_data()
        
        except Exception as e:
            self.logger.error(f"Unhandled error in update check: {e}")
    
    @check_for_updates.before_loop
    async def before_check_for_updates(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
    
    async def _fetch_changelog(self, session: aiohttp.ClientSession, version: str) -> Optional[str]:
        """Fetch changelog for a specific version"""
        try:
            # --- THIRD API CALL: Get changelog ---
            changelog_url = f"{self.api_base_url}/package/{self.package_namespace}/{self.package_name}/{version}/changelog/"
            self.logger.info(f"API Call 3/3: experimental_package_version_changelog_read: {changelog_url}")
            
            async with session.get(changelog_url) as response:
                if response.status != 200:
                    self.logger.warning(f"API Warning: Failed to fetch changelog: HTTP {response.status}")
                    return None
                
                try:
                    changelog_data = await response.json()
                    if not isinstance(changelog_data, dict):
                        self.logger.warning("API Warning: Unexpected changelog data format")
                        return None
                    
                    # The changelog API returns object with a "markdown" field containing the changelog
                    if "markdown" in changelog_data:
                        return changelog_data.get("markdown", "")
                    elif "text" in changelog_data:
                        return changelog_data.get("text", "")
                    else:
                        self.logger.warning("API Warning: Changelog data missing expected fields")
                        return None
                        
                except json.JSONDecodeError:
                    self.logger.warning("API Warning: Invalid JSON in changelog response")
                    return None
        except Exception as e:
            self.logger.error(f"Error fetching changelog: {e}")
            return None
    
    def _format_changelog(self, changelog: str, version: str) -> str:
        """Format changelog text for better Discord presentation, extracting only the relevant version"""
        if not changelog:
            return ""
            
        # Try to extract the most relevant part of the changelog
        changelog_lines = changelog.split('\n')
        formatted_sections = []
        current_section = []
        in_section = False
        section_level = 0
        current_version = None
        target_section = None
        
        # Process important sections to highlight
        # We want to preserve hierarchy but format it for Discord
        for line in changelog_lines:
            # Skip empty lines at the start
            if not line.strip() and not formatted_sections and not current_section:
                continue
                
            # Check if this line indicates a version section
            version_markers = [
                f"[{version}]",
                f"[v{version}]",
            ]
            
            is_version_header = any(marker in line for marker in version_markers)
            # Also check for brackets with the version
            if "[" in line and "]" in line and version in line:
                is_version_header = True
                
            # If we find the target version header
            if is_version_header:
                if current_section:
                    # Save previous section if exists
                    formatted_sections.append('\n'.join(current_section))
                current_section = []
                current_section.append(f"**{line.strip('# ')}**")
                current_version = version
                in_section = True
                section_level = 1
                continue
                
            # If we find a different version header after our target version, stop processing
            # Look for version pattern like [0.1.2] or ## 0.1.2
            if current_version == version and (
                (line.startswith('# ') or line.startswith('## ')) and 
                ('[' in line or ']' in line or 
                 any(c.isdigit() for c in line))
            ):
                # Check if this is a new version section
                if any(f"[{v}]" in line or f"## {v}" in line or f"# {v}" in line 
                       for v in [version[:v_len] for v_len in range(len(version), 2, -1)]):
                    continue  # Still part of current version (like a subsection)
                else:
                    # We've reached the next version section, stop
                    break
                
            # Handle headers - preserve hierarchy
            if line.startswith('# '):
                # Main header - make it bold, all caps
                if current_section and current_version != version:
                    formatted_sections.append('\n'.join(current_section))
                    current_section = []
                elif current_version == version:
                    current_section.append(f"**{line.strip('# ').upper()}**")
                section_level = 1
            elif line.startswith('## '):
                # Secondary header - version or major section
                if current_section and section_level > 2 and current_version != version:
                    formatted_sections.append('\n'.join(current_section))
                    current_section = []
                elif current_version == version:
                    current_section.append(f"**{line.strip('# ')}**")
                section_level = 2
            elif line.startswith('### '):
                # Tertiary header - subsection
                if current_version == version:
                    current_section.append(f"__**{line.strip('# ')}**__")
                section_level = 3
            elif line.startswith('#### '):
                # Fourth-level header
                if current_version == version:
                    current_section.append(f"__{line.strip('# ')}__")
                section_level = 4
            # Handle lists
            elif line.strip().startswith(('- ', '* ', '+ ')):
                # Format bullet points consistently
                if current_version == version:
                    current_section.append(f"• {line.strip()[2:]}")
            # Regular lines
            elif line.strip():
                if current_version == version:
                    current_section.append(line)
            # Empty line handling
            elif current_section and current_version == version:
                # Only add one empty line to separate sections
                if current_section[-1]:
                    current_section.append("")
        
        # Save the last section if it's our target version
        if current_section and current_version == version:
            target_section = '\n'.join(current_section)
        
        # If we found our target version section, return it
        if target_section:
            if len(target_section) > 1000:
                return target_section[:997] + "..."
            return target_section
        
        # Fallback: if no specific version section found, try to find by version mentions
        for section in formatted_sections:
            if version in section:
                if len(section) > 1000:
                    return section[:997] + "..."
                return section
        
        # Ultimate fallback: just return first section
        if formatted_sections:
            combined = formatted_sections[0]
            if len(combined) > 1000:
                return combined[:997] + "..."
            return combined
        
        return "No changelog available for this version."
    
    async def _send_update_notification(self, 
                                       channel: discord.TextChannel, 
                                       package_data: Dict[str, Any],
                                       version_data: Dict[str, Any],
                                       changelog: Optional[str]) -> None:
        """Send an update notification to the specified channel"""
        try:
            # Extract data with proper validation and defaults
            version = str(version_data.get("version_number", "Unknown"))
            created_date = version_data.get("date_created", "Unknown")
            
            # Format the date in a more readable format if possible
            try:
                created_datetime = datetime.datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                created_date = created_datetime.strftime("%B %d, %Y")
            except:
                pass  # Keep original format if parsing fails
            
            # Handle numeric fields
            try:
                download_count = int(version_data.get("downloads", 0))
            except (ValueError, TypeError):
                download_count = 0
                
            description = str(version_data.get("description", ""))
            
            # Create a shorter description for the embed
            short_description = description
            if len(short_description) > 250:
                short_description = description[:247] + "..."
                
            # Website URL
            website_url = version_data.get("website_url", "")
            if not website_url:
                website_url = package_data.get("package_url", "")
            
            # Process categories and tags
            tags = []
            community_listings = package_data.get("community_listings", [])
            if isinstance(community_listings, list) and community_listings:
                for listing in community_listings:
                    if not isinstance(listing, dict):
                        continue
                    
                    categories = listing.get("categories", [])
                    if isinstance(categories, list):
                        tags.extend(categories)
            
            # Process dependencies
            dependencies = []
            raw_deps = version_data.get("dependencies", [])
            if isinstance(raw_deps, list):
                dependencies = raw_deps
                
            # Format changelog for Discord, only for the current version
            formatted_changelog = self._format_changelog(changelog, version) if changelog else ""
            
            # Extract key features from changelog if possible
            key_features = []
            if formatted_changelog:  # Use already filtered changelog to extract features
                # Look for "Added" or "Features" sections
                for line in formatted_changelog.split('\n'):
                    if line.strip().startswith(('• ', '- ', '* ')) and len(key_features) < 3:
                        feature = line.strip()[2:].strip()
                        if feature and not any(f.lower() == feature.lower() for f in key_features):
                            key_features.append(feature)
                
                # If no bullet points found, try another approach
                if not key_features:
                    for section in ["__**Added**__", "**Added**", "__**Features**__", "**Features**"]:
                        if section in formatted_changelog:
                            section_start = formatted_changelog.find(section) + len(section)
                            section_end = min(
                                pos for pos in [
                                    formatted_changelog.find("__**", section_start),
                                    formatted_changelog.find("**", section_start),
                                    len(formatted_changelog)
                                ] if pos > section_start
                            )
                            features_text = formatted_changelog[section_start:section_end].strip()
                            for line in features_text.split('\n'):
                                if line.strip().startswith(('• ', '- ', '* ')) and len(key_features) < 3:
                                    feature = line.strip()[2:].strip()
                                    if feature:
                                        key_features.append(feature)
            
            # Download URL
            download_url = version_data.get("download_url", "")
            if not download_url:
                download_url = f"https://thunderstore.io/package/download/{self.package_namespace}/{self.package_name}/{version}/"
            
            # Get icon URL
            icon_url = version_data.get("icon", "")
            
            # Build a rich embed with all the information
            embed = discord.Embed(
                title=f"🚀 ScheduleLua Update v{version}",
                description=short_description or "A new version of ScheduleLua is available!",
                color=discord.Color.brand_green(),
                url="https://thunderstore.io/c/schedule-i/p/ScheduleLua/ScheduleLua/"
            )
            
            # Add version info
            embed.add_field(name="📅 Released", value=created_date, inline=True)
            embed.add_field(name="⬇️ Downloads", value=f"{download_count:,}", inline=True)
            
            # Add tags if available (limit to 3)
            if tags:
                unique_tags = list(set(tags))[:3]
                embed.add_field(name="🏷️ Tags", value=", ".join(unique_tags), inline=True)
            
            # Add key features if available
            if key_features:
                features_text = "\n".join([f"• {feature}" for feature in key_features])
                embed.add_field(name="✨ Key Features", value=features_text, inline=False)
            
            # Add links
            links = [f"[Download]({download_url})"]
            if website_url:
                links.append(f"[Website]({website_url})")
            
            embed.add_field(name="🔗 Links", value=" • ".join(links), inline=False)
            
            # Add changelog if available
            if formatted_changelog:
                # Format and truncate if needed
                if len(formatted_changelog) > 1024:
                    formatted_changelog = formatted_changelog[:1020] + "..."
                
                embed.add_field(name="📋 Changelog", value=formatted_changelog, inline=False)
            
            # Set footer and timestamp
            embed.set_footer(text=f"ScheduleLua • {self.package_namespace}/{self.package_name}")
            embed.timestamp = datetime.datetime.now()
            
            # Set thumbnail
            if icon_url:
                embed.set_thumbnail(url=icon_url)
            
            # Send the notification
            await channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error building notification: {e}")
            # Try to send a simplified notification as fallback
            try:
                simple_embed = discord.Embed(
                    title="ScheduleLua Update Available",
                    description=f"Version {version_data.get('version_number', 'Unknown')} has been released.",
                    color=discord.Color.green()
                )
                await channel.send(embed=simple_embed)
            except:
                self.logger.error("Failed to send even the simplified notification")
    
    @app_commands.command(name="updates_channel", description="Set the channel for ScheduleLua update notifications")
    @app_commands.default_permissions(administrator=True)
    async def set_updates_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set the channel where update notifications should be sent"""
        # Check if user is an admin or the bot owner
        if not interaction.user.guild_permissions.administrator and interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        # Update the channel ID in memory
        self.update_channel_id = channel.id
        
        # Recommend adding to .env file
        await interaction.response.send_message(
            f"Update notifications will now be sent to {channel.mention}.\n"
            f"To make this permanent, add `UPDATES_CHANNEL_ID={channel.id}` to your .env file.",
            ephemeral=True
        )
        
        # Start the background task if it wasn't running
        if not self.check_for_updates.is_running():
            self.check_for_updates.start()
            self.logger.info(f"Started update check task, sending to channel {channel.id}")
    
    @app_commands.command(name="check_updates", description="Manually check for ScheduleLua updates")
    @app_commands.default_permissions(administrator=True)
    async def manual_check(self, interaction: discord.Interaction):
        """Manually trigger a check for ScheduleLua updates"""
        # Check if user is an admin or the bot owner
        if not interaction.user.guild_permissions.administrator and interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
        
        if not self.update_channel_id:
            await interaction.response.send_message(
                "Update channel not configured. Use `/updates_channel` first.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("Checking for ScheduleLua updates...", ephemeral=True)
        
        # Run the check outside of the normal schedule
        try:
            await self.check_for_updates()
            await interaction.followup.send("Update check completed!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error checking for updates: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ThunderstoreUpdates(bot)) 