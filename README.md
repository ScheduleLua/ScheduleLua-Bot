# ScheduleLua Discord Bot

A Discord bot for the ScheduleLua community. This bot provides information, moderates discussions, and helps users find resources related to the ScheduleLua Lua modding framework for Schedule 1.

## Features

- **Application Commands**: Implements slash commands using discord.py's application commands system
- **Permission System**: Restricts certain commands to only be usable by the bot owner and moderators
- **Auto-Response System**: Monitors messages for specific keywords and responds with helpful information
- **Rules Management**: Generate and send professional-looking embeds for server rules
- **AI Chatbot**: Gemini-powered AI assistant that understands ScheduleLua documentation
- **Document Embeddings**: Uses vector embeddings to provide context-aware responses
- **Modular Structure**: Organized into cogs for maintainability and scalability

## Setup Instructions

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/schedulelua-bot.git
   cd schedulelua-bot
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure the environment variables by editing the `.env` file:
   ```
   # Discord Bot Configuration
   DISCORD_TOKEN=your_bot_token
   OWNER_ID=your_discord_user_id
   GUILD_ID=your_discord_server_id
   APPLICATION_ID=your_bot_application_id

   # Channel IDs
   RULES_CHANNEL_ID=your_rules_channel_id
   LOG_CHANNEL_ID=your_log_channel_id

   # Auto-response Configuration
   AUTO_RESPONSE_COOLDOWN=60  # Cooldown in seconds
   
   # Gemini API Configuration
   GEMINI_API_KEY=your_gemini_api_key
   ```

4. Run the bot:
   ```
   python main.py
   ```

## Commands

### Public Commands

- `/about` - Get information about ScheduleLua
- `/docs` - Get links to ScheduleLua documentation
- `/report` - Learn how to report bugs or request features
- `/help` - Show available commands
- `/chat` - Chat with the AI assistant about ScheduleLua

### Admin Commands (Owner Only)

- `/sync` - Sync application commands
- `/reload <cog>` - Reload a specific cog
- `/shutdown` - Shut down the bot
- `/send_rules` - Send rules to the rules channel
- `/add_rule` - Add a new rule
- `/edit_rule` - Edit an existing rule
- `/remove_rule` - Remove a rule
- `/list_rules` - List all rules
- `/autoresponse_add` - Add or edit an auto-response
- `/autoresponse_list` - List all auto-responses
- `/autoresponse_remove` - Remove an auto-response
- `/add_document` - Add a document to the AI knowledge base
- `/list_documents` - List all documents in the AI knowledge base
- `/remove_document` - Remove a document from the AI knowledge base
- `/scrape_documentation` - Scrape and add ScheduleLua documentation to the AI knowledge base

## Project Structure

```
schedulelua-bot/
├── main.py              # Main bot file
├── requirements.txt     # Dependencies
├── .env                 # Environment variables
├── bot.log              # Log file
├── README.md            # Documentation
├── cogs/                # Bot command modules
│   ├── admin.py         # Admin commands
│   ├── auto_response.py # Auto-response system
│   ├── gemini.py        # Gemini AI integration
│   ├── info.py          # Information commands
│   └── rules.py         # Rules management
├── utils/               # Utility functions
│   ├── __init__.py
│   └── helpers.py       # Helper functions
├── data/                # Data storage
│   ├── auto_responses.json # Auto-responses
│   ├── rules.json       # Server rules
│   ├── documents.json   # AI knowledge base documents
│   └── embeddings.npy   # Document embeddings
```

## AI Integration

This bot integrates with the Gemini API to provide an intelligent chatbot that can:

1. Answer questions about ScheduleLua based on its documentation
2. Maintain context of conversations with users
3. Provide relevant code examples and troubleshooting tips
4. Reference official documentation when appropriate

The AI system uses document embeddings to find relevant information in its knowledge base and provide accurate, context-aware responses.

## Contributing

If you'd like to contribute to this bot, please fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Contact

For questions or support, please join the Schedule 1 Modding Discord server or open an issue on GitHub. 