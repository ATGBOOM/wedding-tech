const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');

// Create a new client instance with better configuration
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: false, // Set to false to see what's happening in the browser
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu'
        ]
    },
    webVersionCache: {
        type: 'remote',
        remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html',
    }
});

// Add more detailed event logging
client.on('loading_screen', (percent, message) => {
    console.log('LOADING:', percent, message);
});

client.on('change_state', state => {
    console.log('STATE CHANGED:', state);
});

// Generate QR code for authentication
client.on('qr', (qr) => {
    console.log('Scan this QR code with your WhatsApp mobile app:');
    qrcode.generate(qr, { small: true });
});

// Client is ready
client.on('ready', () => {
    console.log('WhatsApp client is ready!');
    console.log('\n=== WhatsApp Reader POC ===\n');
});

// Authentication successful
client.on('authenticated', () => {
    console.log('Authentication successful!');
});

// Authentication failed
client.on('auth_failure', (msg) => {
    console.error('Authentication failed:', msg);
});

// Disconnected
client.on('disconnected', (reason) => {
    console.log('Client was disconnected:', reason);
});

// Listen to all incoming messages
// client.on('message', async (message) => {
//     console.log('\n--- New Message ---');
//     console.log('From:', message.from);
//     console.log('Body:', message.body);
//     console.log('Timestamp:', new Date(message.timestamp * 1000).toLocaleString());

//     // Get contact info
//     const contact = await message.getContact();
//     console.log('Contact Name:', contact.pushname || contact.name || 'Unknown');

//     // Check if it's from a group
//     const chat = await message.getChat();
//     if (chat.isGroup) {
//         console.log('Group:', chat.name);
//     }
// });

// Function to read messages from a specific chat
async function readChatMessages(chatId, limit = 50) {
    try {
        const chat = await client.getChatById(chatId);
        const messages = await chat.fetchMessages({ limit: limit });

        console.log(`\n=== Messages from ${chat.name || chatId} ===\n`);

        messages.forEach((msg) => {
            const timestamp = new Date(msg.timestamp * 1000).toLocaleString();
            console.log(`[${timestamp}] ${msg.author || msg.from}: ${msg.body}`);
        });

        return messages;
    } catch (error) {
        console.error('Error reading chat:', error);
    }
}

// Helper function to add timeout to any promise
function withTimeout(promise, timeoutMs, errorMsg) {
    return Promise.race([
        promise,
        new Promise((_, reject) =>
            setTimeout(() => reject(new Error(errorMsg)), timeoutMs)
        )
    ]);
}

// Function to get all chats with timeout (can be slow with many chats)
async function getAllChats(timeoutSeconds = 60) {
    try {
        console.log("Fetching all chats (this may take a while if you have many chats)...");
        console.log(`Timeout set to ${timeoutSeconds} seconds`);
        const startTime = Date.now();

        const chats = await withTimeout(
            client.getChats(),
            timeoutSeconds * 1000,
            `getChats() timed out after ${timeoutSeconds} seconds. This might indicate a connection issue.`
        );

        const duration = ((Date.now() - startTime) / 1000).toFixed(2);
        console.log(`✓ Fetched ${chats.length} chats in ${duration}s`);
        console.log('\n=== All Chats ===\n');

        chats.forEach((chat, index) => {
            console.log(`${index + 1}. ${chat.name || chat.id._serialized}`);
            console.log(`   ID: ${chat.id._serialized}`);
            console.log(`   Unread: ${chat.unreadCount}`);
            console.log(`   Is Group: ${chat.isGroup}`);
            console.log('');
        });

        return chats;
    } catch (error) {
        console.error('Error getting chats:', error.message);
        console.error('\nPossible issues:');
        console.error('1. WhatsApp Web interface not fully loaded');
        console.error('2. Network connectivity issues');
        console.error('3. WhatsApp account might be restricted');
        console.error('4. Browser/Puppeteer crash');
        console.error('\nCheck the browser window for more details (headless: false)');
        throw error;
    }
}

// Faster alternative: Get only recent chats with unread messages
async function getRecentChats(limit = 20) {
    try {
        console.log(`Fetching ${limit} most recent chats...`);
        const startTime = Date.now();

        const chats = await client.getChats();

        // Sort by last message timestamp and take the most recent
        const recentChats = chats
            .sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
            .slice(0, limit);

        const duration = ((Date.now() - startTime) / 1000).toFixed(2);
        console.log(`✓ Fetched chats in ${duration}s`);
        console.log(`\n=== ${limit} Most Recent Chats ===\n`);

        recentChats.forEach((chat, index) => {
            const lastMessage = chat.lastMessage ?
                new Date(chat.lastMessage.timestamp * 1000).toLocaleString() :
                'No messages';
            console.log(`${index + 1}. ${chat.name || chat.id._serialized}`);
            console.log(`   ID: ${chat.id._serialized}`);
            console.log(`   Last message: ${lastMessage}`);
            console.log(`   Unread: ${chat.unreadCount}`);
            console.log(`   Is Group: ${chat.isGroup}`);
            console.log('');
        });

        return recentChats;
    } catch (error) {
        console.error('Error getting chats:', error);
    }
}

// Even faster: Search for a specific chat by name
async function searchChatByName(searchTerm) {
    try {
        console.log(`Searching for chats matching: "${searchTerm}"...`);
        const chats = await client.getChats();

        const matchingChats = chats.filter(chat =>
            (chat.name && chat.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
            chat.id._serialized.includes(searchTerm)
        );

        console.log(`\n=== Found ${matchingChats.length} matching chat(s) ===\n`);

        matchingChats.forEach((chat, index) => {
            console.log(`${index + 1}. ${chat.name || chat.id._serialized}`);
            console.log(`   ID: ${chat.id._serialized}`);
            console.log('');
        });

        return matchingChats;
    } catch (error) {
        console.error('Error searching chats:', error);
    }
}

// Example: After client is ready, you can call these functions
client.on('ready', async () => {
    console.log('Client is ready!\n');

    try {
        // Add a small delay to ensure WhatsApp Web is fully loaded
        console.log('Waiting 5 seconds for WhatsApp Web to fully load...');
        await new Promise(resolve => setTimeout(resolve, 5000));

        // OPTION 1: Get only recent chats (FASTER - Recommended)
        await getRecentChats(20);

        // OPTION 2: Get ALL chats (SLOWER - can take 30s+ with many chats)
        // await getAllChats(120); // 120 second timeout

        // OPTION 3: Search for specific chat by name (FAST if you know the name)
        // await searchChatByName('John');

        // OPTION 4: Read messages from a specific chat (fastest if you know the ID)
        // const chatId = '1234567890@c.us'; // Individual chat
        // const chatId = '1234567890-1234567890@g.us'; // Group chat
        // await readChatMessages(chatId, 50);
    } catch (error) {
        console.error('Error in ready handler:', error.message);
    }
});

// Initialize the client
console.log('Initializing WhatsApp Web client...');
client.initialize();

// Handle process termination
process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    await client.destroy();
    process.exit(0);
});
