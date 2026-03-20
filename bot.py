import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

# ============================================================
# CẤU HÌNH - Điền vào đây
# ============================================================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Đọc từ file .env
XIN_ROLE_CHANNEL_ID = 1484568010122461457   # #xin-role
DUYET_CHANNEL_ID    = 1484555558257299496   # #duyet-role (log)

ROLE_GS25_ID    = 1484531566712590447
ROLE_KHACH_ID   = 1375500505442422857
ROLE_DUYET_IDS  = [905286901756465242, 1423262413830099055] # Vua và Thái Tử
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# ──────────────────────────────────────────────
# View: Nút Duyệt / Từ chối trong ticket
# ──────────────────────────────────────────────
class ApproveRejectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="✅ Duyệt - Cấp Role", style=discord.ButtonStyle.success, custom_id="approve_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission = interaction.user.guild_permissions.manage_roles or any(role.id in ROLE_DUYET_IDS for role in interaction.user.roles)
        if not has_permission:
            await interaction.response.send_message("❌ Bạn không có quyền duyệt ticket này!", ephemeral=True)
            return

        user = interaction.guild.get_member(self.user_id)
        if not user:
            await interaction.response.send_message("❌ Không tìm thấy người dùng!", ephemeral=True)
            return

        role_gs25 = interaction.guild.get_role(ROLE_GS25_ID)
        role_khach = interaction.guild.get_role(ROLE_KHACH_ID)
        
        if not role_gs25:
            await interaction.response.send_message("❌ Lỗi: Không tìm thấy role GS25!", ephemeral=True)
            return

        # Cấp role GS25 và xóa role Khách
        await user.add_roles(role_gs25)
        if role_khach and role_khach in user.roles:
            try:
                await user.remove_roles(role_khach)
            except discord.errors.Forbidden:
                pass # Bỏ qua nếu không có quyền xóa role khách
            
        await interaction.response.send_message(f"✅ Đã tự động cấp role **GS25** và xóa role **Khách** cho {user.mention}!")

        # Gửi DM
        try:
            await user.send(f"🎉 Chúc mừng! Bạn đã được cấp role **GS25** trong server!")
        except Exception:
            pass

        # Log
        log_channel = interaction.guild.get_channel(DUYET_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="✅ Role đã được duyệt tự động", color=0x57F287)
            embed.add_field(name="Người dùng", value=user.mention, inline=True)
            embed.add_field(name="Role Đã Cấp", value="GS25", inline=True)
            embed.add_field(name="Duyệt bởi", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed)

        # Disable nút cũ
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)
        
        await asyncio.sleep(3)
        await interaction.channel.delete(reason="Ticket approved - GS25 (1-step)")

    @discord.ui.button(label="❌ Từ chối", style=discord.ButtonStyle.danger, custom_id="reject_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_permission = interaction.user.guild_permissions.manage_roles or any(role.id in ROLE_DUYET_IDS for role in interaction.user.roles)
        if not has_permission:
            await interaction.response.send_message("❌ Bạn không có quyền duyệt ticket này!", ephemeral=True)
            return

        user = interaction.guild.get_member(self.user_id)

        await interaction.response.send_message(
            f"❌ Đơn xin role của {user.mention if user else 'người dùng'} đã bị **từ chối**."
        )

        # Gửi DM
        if user:
            try:
                await user.send("❌ Xin lỗi, đơn xin role của bạn đã bị từ chối.")
            except Exception:
                pass

        # Log
        log_channel = interaction.guild.get_channel(DUYET_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="❌ Đơn bị từ chối", color=0xED4245)
            embed.add_field(name="Người dùng", value=user.mention if user else "Unknown", inline=True)
            embed.add_field(name="Từ chối bởi", value=interaction.user.mention, inline=True)
            await log_channel.send(embed=embed)

        # Disable nút
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

        await asyncio.sleep(3)
        await interaction.channel.delete(reason="Ticket rejected")


# ──────────────────────────────────────────────
# View: Nút 📩 Xin Role (trong #xin-role)
# ──────────────────────────────────────────────
class XinRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 Xin Role", style=discord.ButtonStyle.primary, custom_id="xin_role_btn")
    async def xin_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        # Kiểm tra ticket đã tồn tại chưa
        for ch in guild.text_channels:
            if ch.name == f"ticket-{user.name.lower().replace(' ', '-')}":
                await interaction.response.send_message(
                    f"❌ Bạn đã có ticket đang mở: {ch.mention}", ephemeral=True
                )
                return

        # Tạo kênh ticket riêng
        category = interaction.channel.category
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True),
        }
        
        # Thêm quyền cho các role duyệt
        for role_id in ROLE_DUYET_IDS:
            duyet_role = guild.get_role(role_id)
            if duyet_role:
                overwrites[duyet_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{user.name.lower().replace(' ', '-')}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket xin role của {user.name}"
        )

        embed = discord.Embed(
            title="🎫 Yêu cầu xin Role",
            description=f"Xin chào {user.mention}!\n\nAdmin sẽ xem xét đơn của bạn sớm nhất có thể.\nVui lòng chờ và không đóng ticket này.",
            color=0x5865F2
        )
        embed.add_field(name="👤 Người dùng", value=user.mention, inline=True)
        embed.add_field(name="🆔 ID", value=f"`{user.id}`", inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.set_footer(text="GS25 Bot • Hệ thống xin role")

        await ticket_channel.send(
            content=f"{user.mention} • Chờ admin xét duyệt 👇",
            embed=embed,
            view=ApproveRejectView(user.id)
        )

        await interaction.response.send_message(
            f"✅ Ticket đã được tạo: {ticket_channel.mention}", ephemeral=True
        )


# ──────────────────────────────────────────────
# Bot Events
# ──────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user} đã online!")

    # Đăng ký persistent views
    bot.add_view(XinRoleView())
    bot.add_view(ApproveRejectView(user_id=0))

    # Gửi panel vào #xin-role (chỉ gửi 1 lần)
    channel = bot.get_channel(XIN_ROLE_CHANNEL_ID)
    if channel:
        async for msg in channel.history(limit=20):
            if msg.author == bot.user and msg.components:
                print("⚡ Panel đã tồn tại, bỏ qua.")
                return

        embed = discord.Embed(
            title="🎫 Xin cấp Role",
            description="Bấm nút bên dưới để gửi đơn xin role!\nAdmin sẽ xem xét và phản hồi sớm nhất có thể. ✅",
            color=0x5865F2
        )
        embed.set_footer(text="GS25 Bot • Hệ thống xin role")
        await channel.send(embed=embed, view=XinRoleView())
        print("✅ Panel đã được gửi vào #xin-role!")


keep_alive()
bot.run(BOT_TOKEN)
