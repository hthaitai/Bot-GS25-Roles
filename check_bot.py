import discord
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    app_info = await client.application_info()
    perms = discord.Permissions(administrator=True)
    invite_url = discord.utils.oauth_url(app_info.id, permissions=perms)
    
    print("\n" + "="*50)
    print(f"Bot Name: {client.user.name}")
    print(f"Link moi bot: {invite_url}")
    print("="*50)
    
    if len(client.guilds) == 0:
        print("\n[X] Bot CHUA tham gia bat ky server nao!")
        print("-> Vui long copy 'Link moi bot' o tren, dan vao trinh duyet va moi bot vao server cua ban.")
    else:
        print(f"\n[V] Bot dang co mat trong {len(client.guilds)} server:")
        for guild in client.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")
            
    print("\nDang tu dong dong ket noi...")
    await client.close()

client.run(BOT_TOKEN)
