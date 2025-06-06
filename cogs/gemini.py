import os
import json
import discord
from discord import app_commands
from discord.ext import commands
from typing import Dict, List, Optional, Tuple
import numpy as np
import google.genai as genai
from google.genai import types
import asyncio
import re
import time
import glob
import pathlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from utils.helpers import create_embed, load_json, save_json, fetch_url_content


class GeminiChatbot(commands.Cog):
    """AI chatbot integration using Gemini API"""
    
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            self.bot.logger.error("GEMINI_API_KEY not found in environment variables")
            return
            
        # Initialize Gemini client
        self.client = genai.Client(api_key=self.api_key)
        
        # Model names
        self.generation_model = "gemini-2.0-flash"
        
        # Conversation history per user
        self.conversations = {}
        
        # Documentation path
        self.docs_folder = "data/docs"
        os.makedirs(self.docs_folder, exist_ok=True)
        
        # Get documentation URLs from environment variables
        self.readme_url = os.getenv('SCHEDULELUA_README_URL', 'https://raw.githubusercontent.com/ScheduleLua/ScheduleLua-Framework/refs/heads/main/README.md')
        self.docs_base_url = os.getenv('SCHEDULELUA_DOCS_URL', 'https://schedulelua.github.io/ScheduleLua-Docs/')
        
        # Set up the system instruction for ScheduleLua context
        self.system_instruction = """
        You are ScheduleLuaBot, a helpful AI assistant specialized in ScheduleLua, a Lua modding framework for Schedule 1.
        You help users with questions about ScheduleLua's installation, usage, scripting, and troubleshooting.
        
        When responding:
        1. Provide accurate information about ScheduleLua based on documentation
        2. Share code examples when appropriate, using proper formatting
        3. Link to relevant documentation when available
        4. Be friendly and supportive to users of all experience levels
        5. If you're unsure about something, acknowledge it and suggest checking the official documentation
        
        ScheduleLua documentation: https://schedulelua.github.io/ScheduleLua-Docs/
        
        IMPORTANT TOPICS YOU KNOW ABOUT:
        - Mod system architecture and concepts
        - Mod functions and their usage
        - Mod deployment and distribution
        
        SCHEDULEUA MOD SYSTEM:
        ScheduleLua supports two types of script loading:
        1. Individual Scripts: Simple .lua files placed in the Scripts folder
        2. Lua Mods: Structured folders containing manifest.json and multiple Lua files
        
        Lua Mods work similar to FiveM resources, with a folder structure:
        - manifest.json: Contains mod metadata (name, author, version, dependencies)
        - init.lua: Main entry point script (configurable in manifest)
        - Additional .lua files: Referenced in the manifest
        
        Mods can interact with each other through:
        - ExportFunction(): Making functions available to other mods
        - ImportFunction(): Using functions from other mods
        - GetMod(): Accessing information about other loaded mods
        
        The mod system handles dependencies, load order, and proper initialization.
        
        IMPORTANT: When referencing documentation, ALWAYS link to the public GitHub Pages site 
        (https://schedulelua.github.io/ScheduleLua-Docs/) rather than mentioning any local markdown files 
        or internal file structures. Users should always be directed to the official online documentation.
        """
        
        self.bot.logger.info("Gemini integration initialized")
    
    def find_relevant_docs(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """Find relevant documentation files based on a search query"""
        docs = []
        
        # Get all markdown files in the docs folder
        md_files = glob.glob(f"{self.docs_folder}/**/*.md", recursive=True)
        
        # Calculate relevance score for each file based on keyword matches
        query_keywords = set(re.findall(r'\w+', query.lower()))
        scored_docs = []
        
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract filename as title
                title = os.path.basename(file_path).replace('.md', '')
                
                # Count keyword matches
                doc_text = content.lower()
                match_count = sum(1 for keyword in query_keywords if keyword in doc_text)
                
                if match_count > 0:
                    scored_docs.append({
                        'title': title,
                        'content': content,
                        'path': file_path,
                        'score': match_count
                    })
            except Exception as e:
                self.bot.logger.error(f"Error reading file {file_path}: {e}")
        
        # Sort by score and take top_k
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs[:top_k]
    
    @app_commands.command(name="chat", description="Chat with the AI assistant about ScheduleLua")
    @app_commands.describe(question="Your question or message about ScheduleLua")
    async def chat_command(self, interaction: discord.Interaction, question: str):
        """Chat with the AI assistant"""
        await interaction.response.defer(thinking=True)
        
        user_id = str(interaction.user.id)
        
        try:
            # Find relevant documents
            relevant_docs = self.find_relevant_docs(question)
            context = ""
            
            if relevant_docs:
                context = "Information from ScheduleLua documentation:\n\n"
                for i, doc in enumerate(relevant_docs):
                    context += f"Document {i+1}: {doc['title']}\n"
                    context += f"{doc['content']}\n\n"
            
            # Initialize conversation if it doesn't exist
            if user_id not in self.conversations:
                self.start_conversation(user_id)
            
            # Add context to the prompt if available
            prompt = question
            if context:
                prompt = f"{context}\nUser question: {question}\nPlease answer based on the provided documentation. IMPORTANT: Do NOT mention these context documents or any local files in your response - only reference the public documentation website (https://schedulelua.github.io/ScheduleLua-Docs/):"
            
            # Update system instruction to require brief responses
            compact_system_instruction = self.system_instruction + """
            IMPORTANT: You MUST keep your responses under 2000 characters to fit within a single Discord message.
            Be concise and to the point. Omit unnecessary information and focus on answering the question directly.
            If you need to include code examples, keep them short and focused on the essential parts.
            
            CRITICAL: Never mention or reference any local markdown (.md) files in your responses.
            Always direct users to the official documentation website at https://schedulelua.github.io/ScheduleLua-Docs/
            instead of referencing internal files like 'installation.md' or any file paths.
            """
            
            # Send the message to the model with system instruction
            response = self.client.models.generate_content(
                model=self.generation_model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=compact_system_instruction,
                    max_output_tokens=800  # Limit output tokens (approx. 1600-2000 chars)
                )
            )
            
            # Format and send the response
            content = response.text
            
            # Ensure content fits within Discord's message limit (2000 chars)
            if len(content) > 1950:  # Leave some margin for safety
                content = content[:1947] + "..."
            
            await interaction.followup.send(content)
                
        except Exception as e:
            self.bot.logger.error(f"Error in chat command: {e}")
            await interaction.followup.send(f"Error: {str(e)}")
    
    def start_conversation(self, user_id: str) -> None:
        """Start a new conversation for a user"""
        self.conversations[user_id] = []
    
    @app_commands.command(name="add_doc", description="Add a documentation file to the knowledge base")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        title="Document title (will be used as filename)",
        content="Markdown content of the documentation"
    )
    async def add_document(
        self, 
        interaction: discord.Interaction, 
        title: str, 
        content: str
    ):
        """Add a documentation file to the docs folder"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        await interaction.response.defer(thinking=True)
        
        try:
            # Sanitize the title for use as a filename
            filename = re.sub(r'[^\w\-\.]', '_', title.lower().replace(' ', '_')) + '.md'
            file_path = os.path.join(self.docs_folder, filename)
            
            # Save the content to a file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            await interaction.followup.send(f"Documentation file '{title}' added successfully.", ephemeral=True)
            
        except Exception as e:
            self.bot.logger.error(f"Error adding documentation file: {e}")
            await interaction.followup.send(f"Error adding documentation file: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="scrape_documentation", description="Scrape ScheduleLua documentation and save as markdown files")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(single_page_url="Optional: URL of a single page to scrape (for testing)")
    async def scrape_documentation(self, interaction: discord.Interaction, single_page_url: str = None):
        """Scrape ScheduleLua documentation and save as markdown files using URLs from environment variables"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        await interaction.response.defer(thinking=True)
        
        doc_pages = []
        
        # Single page mode for testing
        if single_page_url:
            self.bot.logger.info(f"Single page mode - testing with URL: {single_page_url}")
            await interaction.followup.send(f"Testing scraper with single page: {single_page_url}", ephemeral=True)
            doc_pages = [single_page_url]
        else:
            # Log the base URL for debugging
            self.bot.logger.info(f"Starting documentation crawl from base URL: {self.docs_base_url}")
            await interaction.followup.send(f"Scanning documentation site for pages from: {self.docs_base_url}", ephemeral=True)
            
            # Temporarily removed allowed_prefixes to see if that's blocking pages
            doc_pages = self.crawl_docs(
                self.docs_base_url,
                allowed_prefixes=None,  # Removed filter
                max_pages=50  # Prevent runaway crawling
            )
        
        # Log the found pages for debugging
        self.bot.logger.info(f"Found {len(doc_pages)} pages to crawl")
        if len(doc_pages) > 0:
            self.bot.logger.info(f"Sample pages: {doc_pages[:3]}")
        else:
            self.bot.logger.warning("No documentation pages were found during crawling!")
            
        added_count = 0
        errors_count = 0
        
        # First, fetch and save the README from the main repo
        try:
            readme_content = fetch_url_content(self.readme_url)
            file_path = os.path.join(self.docs_folder, "readme.md")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            added_count += 1
            self.bot.logger.info(f"Successfully saved README to {file_path}")
        except Exception as e:
            self.bot.logger.error(f"Error scraping README: {e}")
            errors_count += 1
        
        # Then process the regular documentation pages
        for page_url in doc_pages:
            try:
                self.bot.logger.info(f"Processing documentation page: {page_url}")
                content = fetch_url_content(page_url)
                
                if not content or len(content) < 50:
                    self.bot.logger.warning(f"Skipping page with insufficient content: {page_url}")
                    continue
                
                # Extract title
                title_match = re.search(r"<title>(.*?)</title>", content)
                title = title_match.group(1) if title_match else os.path.basename(page_url)
                self.bot.logger.info(f"Extracted title: {title}")
                
                # Simple HTML to markdown conversion
                # Extract main content
                main_content_match = re.search(r'<main.*?>(.*?)</main>', content, re.DOTALL)
                if main_content_match:
                    main_content = main_content_match.group(1)
                    self.bot.logger.info(f"Found <main> content section for {page_url}")
                else:
                    main_content = content
                    self.bot.logger.warning(f"No <main> section found for {page_url}, using full content")
                
                # Convert headings
                main_content = re.sub(r'<h1.*?>(.*?)</h1>', r'# \1', main_content)
                main_content = re.sub(r'<h2.*?>(.*?)</h2>', r'## \1', main_content)
                main_content = re.sub(r'<h3.*?>(.*?)</h3>', r'### \1', main_content)
                main_content = re.sub(r'<a.*?href="(.*?)".*?>(.*?)</a>', r'[\2](\1)', main_content)
                main_content = re.sub(r'<li.*?>(.*?)</li>', r'* \1', main_content)
                main_content = re.sub(r'<pre.*?><code.*?>(.*?)</code></pre>', r'```\n\1\n```', main_content)
                main_content = re.sub(r'<[^>]*>', ' ', main_content)
                main_content = re.sub(r'\s+', ' ', main_content).strip()
                
                # Add title
                markdown_content = f"# {title}\n\n{main_content}"
                filename = re.sub(r'[^\w\-\.]', '_', title.lower().replace(' ', '_')) + '.md'
                file_path = os.path.join(self.docs_folder, filename)
                
                # Save to file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                added_count += 1
                self.bot.logger.info(f"Successfully saved {title} to {file_path}")
                await asyncio.sleep(5)  # Rate limiting
            except Exception as e:
                self.bot.logger.error(f"Error scraping {page_url}: {e}")
                errors_count += 1
        
        await interaction.followup.send(
            f"Documentation scraping complete. Added {added_count} files. Encountered {errors_count} errors.",
            ephemeral=True
        )
    
    def crawl_docs(self, base_url, allowed_prefixes=None, max_pages=100):
        """
        Crawl the documentation site starting from base_url and return all unique internal routes.
        allowed_prefixes: list of URL path prefixes to restrict crawling (e.g., ['guide/', 'api/'])
        """
        visited = set()
        to_visit = set([base_url])
        found_pages = set()

        self.bot.logger.info(f"Starting crawler with base_url: {base_url}")
        
        # Validate base URL by attempting to fetch it
        try:
            resp = requests.get(base_url, timeout=10)
            resp.raise_for_status()
            self.bot.logger.info(f"Successfully connected to base URL: {base_url}")
            self.bot.logger.info(f"Base URL returned HTTP {resp.status_code} with content length: {len(resp.text)} bytes")
        except Exception as e:
            self.bot.logger.error(f"Could not connect to base URL: {base_url}")
            self.bot.logger.error(f"Error: {str(e)}")
            return list(found_pages)
            
        self.bot.logger.info(f"Allowed prefixes: {allowed_prefixes}")

        while to_visit and len(found_pages) < max_pages:
            url = to_visit.pop()
            if url in visited:
                continue
                
            visited.add(url)
            self.bot.logger.info(f"Crawling URL: {url}")
            
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                html = resp.text
                self.bot.logger.info(f"Successfully fetched page: {url}")
            except Exception as e:
                self.bot.logger.error(f"Error fetching {url}: {e}")
                continue

            try:
                soup = BeautifulSoup(html, "html.parser")
                links = soup.find_all("a", href=True)
                self.bot.logger.info(f"Found {len(links)} links on page {url}")
                
                # Debug: Print all links found on the page
                link_urls = [a.get("href") for a in links]
                self.bot.logger.info(f"All links found on {url}: {link_urls[:10]}...")
                if len(link_urls) > 10:
                    self.bot.logger.info(f"...and {len(link_urls) - 10} more")
                
                for a in links:
                    href = a["href"]
                    
                    # Ignore empty links
                    if not href.strip():
                        continue
                        
                    # Ignore javascript links
                    if href.startswith("javascript:"):
                        continue
                        
                    # Handle URL types
                    if href.startswith("http"):
                        # Absolute URL
                        if not href.startswith(base_url):
                            self.bot.logger.info(f"Skipping external URL: {href}")
                            continue
                        next_url = href
                    elif href.startswith("/"):
                        # Site-relative URL
                        next_url = urljoin(base_url, href)
                    else:
                        # Page-relative URL
                        next_url = urljoin(url, href)

                    # Remove fragments and queries
                    next_url = next_url.split("#")[0].split("?")[0]

                    # Only crawl under allowed prefixes if specified
                    if allowed_prefixes:
                        rel_path = urlparse(next_url).path.lstrip("/")
                        if not any(rel_path.startswith(p) for p in allowed_prefixes):
                            self.bot.logger.info(f"Skipping URL with non-matching prefix: {next_url}, rel_path: {rel_path}")
                            continue

                    # Modified: Be more lenient with URL extensions - accept most web document types
                    # and don't check extensions if URL ends with /
                    if not next_url.endswith("/"):
                        valid_extensions = [".html", ".htm", ".php", ".asp", ".aspx", ".jsp", ".md", ""]
                        if not any(next_url.endswith(ext) for ext in valid_extensions):
                            self.bot.logger.info(f"Skipping URL with invalid extension: {next_url}")
                            continue

                    # Add to crawl queue if not visited
                    if next_url not in visited and next_url.startswith(base_url):
                        to_visit.add(next_url)
                        found_pages.add(next_url)
                        self.bot.logger.info(f"Added to crawl queue: {next_url}")
            except Exception as e:
                self.bot.logger.error(f"Error parsing page {url}: {e}")
                
        self.bot.logger.info(f"Crawling complete. Found {len(found_pages)} pages.")
        return sorted(found_pages)
    
    @app_commands.command(name="list_docs", description="List all documentation files in the knowledge base")
    @app_commands.default_permissions(administrator=True)
    async def list_documents(self, interaction: discord.Interaction):
        """List all documentation files"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        # Get all markdown files in the docs folder
        md_files = glob.glob(f"{self.docs_folder}/**/*.md", recursive=True)
        
        if not md_files:
            await interaction.response.send_message("No documentation files found.", ephemeral=True)
            return
            
        # Create an embed with all documents
        embed = create_embed(
            title="Documentation Files",
            description=f"Total files: {len(md_files)}",
            color=discord.Color.blue()
        )
        
        for i, file_path in enumerate(md_files):
            # Get relative path
            rel_path = os.path.relpath(file_path, self.docs_folder)
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Read first line to get title
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    title = first_line.replace('# ', '') if first_line.startswith('# ') else os.path.basename(file_path)
            except:
                title = os.path.basename(file_path)
            
            embed.add_field(
                name=f"{i+1}. {title}",
                value=f"Path: {rel_path}\nSize: {file_size} bytes",
                inline=False
            )
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="remove_doc", description="Remove a documentation file from the knowledge base")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(filename="The filename to remove (see /list_docs)")
    async def remove_document(self, interaction: discord.Interaction, filename: str):
        """Remove a documentation file"""
        # Check if user is authorized
        if interaction.user.id != int(os.getenv('OWNER_ID')):
            await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
            return
            
        file_path = os.path.join(self.docs_folder, filename)
        
        if not os.path.exists(file_path):
            await interaction.response.send_message(f"File '{filename}' not found.", ephemeral=True)
            return
            
        try:
            os.remove(file_path)
            await interaction.response.send_message(f"File '{filename}' removed successfully.", ephemeral=True)
        except Exception as e:
            self.bot.logger.error(f"Error removing file {file_path}: {e}")
            await interaction.response.send_message(f"Error removing file: {str(e)}", ephemeral=True)

async def setup(bot):
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)
    os.makedirs("data/docs", exist_ok=True)
    await bot.add_cog(GeminiChatbot(bot)) 