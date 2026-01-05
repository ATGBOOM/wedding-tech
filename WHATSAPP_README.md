# WhatsApp Reader POC

A proof of concept for reading WhatsApp messages using whatsapp-web.js.

## Setup

1. Dependencies are already installed. If you need to reinstall:
   ```bash
   npm install
   ```

## Running the POC

1. Start the WhatsApp reader:
   ```bash
   node whatsapp-reader.js
   ```

2. A QR code will appear in your terminal. Scan it with your WhatsApp mobile app:
   - Open WhatsApp on your phone
   - Go to Settings → Linked Devices
   - Tap "Link a Device"
   - Scan the QR code

3. Once authenticated, the script will:
   - List all your chats
   - Listen for new incoming messages in real-time
   - Display message details (sender, content, timestamp)

## Features

### Current Functionality

- **Authentication**: QR code-based authentication (saved locally for future sessions)
- **Real-time Message Listening**: Captures all incoming messages
- **List All Chats**: Shows all your WhatsApp conversations
- **Read Chat Messages**: Fetch message history from specific chats

### Available Functions

#### `getAllChats()`
Lists all your WhatsApp chats with:
- Chat name
- Chat ID
- Unread message count
- Whether it's a group or individual chat

#### `readChatMessages(chatId, limit)`
Fetches messages from a specific chat:
- `chatId`: The chat identifier (e.g., '1234567890@c.us' for individuals, '1234567890-1234567890@g.us' for groups)
- `limit`: Number of messages to fetch (default: 50)

## Usage Examples

### Get a Specific Chat's Messages

1. Run the script and note the chat ID from the list
2. Uncomment and modify these lines in the code:
   ```javascript
   const chatId = 'PASTE_CHAT_ID_HERE';
   await readChatMessages(chatId, 50);
   ```

### Send a Message (Add this functionality)

```javascript
async function sendMessage(chatId, message) {
    const chat = await client.getChatById(chatId);
    await chat.sendMessage(message);
}
```

## Important Notes

- **Session Persistence**: Authentication is saved locally in `.wwebjs_auth/` folder
- **First Run**: You'll need to scan the QR code on first run
- **Subsequent Runs**: The client will use saved authentication
- **Terms of Service**: This uses an unofficial API and may violate WhatsApp's ToS
- **Rate Limits**: Be mindful of WhatsApp's rate limits to avoid account restrictions

## Troubleshooting

### QR Code Not Appearing
- Make sure your terminal supports QR code display
- Check that Puppeteer is properly installed

### Authentication Fails
- Delete the `.wwebjs_auth/` folder and try again
- Ensure your WhatsApp account is not banned from using WhatsApp Web

### Messages Not Showing
- Check that the client is fully ready (wait for "Client is ready!" message)
- Verify the chat ID is correct

## Next Steps

To extend this POC:
1. Add message filtering (by date, sender, keywords)
2. Export messages to JSON/CSV
3. Add media download functionality
4. Create a REST API wrapper
5. Add database storage for messages
