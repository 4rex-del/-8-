import discord
from discord.ext import commands
from discord import app_commands
import json, os, datetime

import myserver from server_on

GUILD_ID = 1411573311787241534
CHANNEL_ID = 1411575566976417952
ROLE_LOG_CHANNEL_ID = 1414236550572675105
PAYMENT_LOG_CHANNEL_ID = 1412071745137020958
OWNER_ID = 1400471054295502849

ROLES_SHOP = {
    1411575321798512751: 10,
    1411586539544252537: 10,
    1412437426873434163: 10,
    1412438157772722317: 39,
    1411586465896464506: 59,
    1412436371175374940: 89,
    1412062520826662974: 100
}

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = "purchases.json"
PAYMENT_FILE = "payments.json"
BALANCE_FILE = "balance.json"

for file in [DATA_FILE, PAYMENT_FILE, BALANCE_FILE]:
    if not os.path.exists(file):
        with open(file, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

def load_json(file):
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_balance(user_id):
    data = load_json(BALANCE_FILE)
    return data.get(str(user_id), 0)

def add_balance(user_id, amount):
    data = load_json(BALANCE_FILE)
    data[str(user_id)] = data.get(str(user_id), 0) + amount
    save_json(BALANCE_FILE, data)

def deduct_balance(user_id, amount):
    data = load_json(BALANCE_FILE)
    if data.get(str(user_id), 0) >= amount:
        data[str(user_id)] -= amount
        save_json(BALANCE_FILE, data)
        return True
    return False

# ------------------- Confirm Buy -------------------
class ConfirmBuyView(discord.ui.View):
    def __init__(self, role_id):
        super().__init__(timeout=60)
        self.role_id = role_id
        self.price = ROLES_SHOP[role_id]

    @discord.ui.button(label="✅ ยืนยัน", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        balance = get_balance(user.id)
        role = interaction.guild.get_role(self.role_id)

        if balance < self.price:
            embed = discord.Embed(
                title="❌ ยอดเงินไม่พอ",
                description=f"ยอดเงินของคุณ: {balance} บาท\nราคายศ: {self.price} บาท\nกรุณาเติมเงินก่อน",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        deduct_balance(user.id, self.price)
        await user.add_roles(role)

        purchases = load_json(DATA_FILE)
        if str(user.id) not in purchases:
            purchases[str(user.id)] = []
        purchases[str(user.id)].append({
            "role": role.name,
            "price": self.price,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_json(DATA_FILE, purchases)

        log_channel = bot.get_channel(ROLE_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = discord.Embed(title="🛒 การซื้อยศใหม่", color=discord.Color.orange())
            embed_log.add_field(name="ผู้ซื้อ", value=user.mention, inline=False)
            embed_log.add_field(name="ยศ", value=role.name, inline=True)
            embed_log.add_field(name="ราคา", value=f"{self.price} บาท", inline=True)
            embed_log.add_field(name="เวลา", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed_log.set_thumbnail(url=user.display_avatar.url)
            await log_channel.send(embed=embed_log)

        embed = discord.Embed(
            title="✅ ซื้อยศเรียบร้อย",
            description=f"คุณซื้อยศ {role.name} เรียบร้อยแล้ว\nยอดเงินคงเหลือ: {get_balance(user.id)} บาท",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ ยกเลิก", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚫 ยกเลิกการซื้อ",
            description="คุณยกเลิกการซื้อยศแล้ว",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------- TopUp -------------------
class TopUpModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🧧 ส่งลิ้งซองทรูมันนี่")
        self.link = discord.ui.TextInput(label="ใส่ลิ้งซองทรูมันนี่", style=discord.TextStyle.short)
        self.add_item(self.link)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        link = self.link.value
        payments = load_json(PAYMENT_FILE)
        if str(user.id) not in payments:
            payments[str(user.id)] = []
        payments[str(user.id)].append({
            "link": link,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_json(PAYMENT_FILE, payments)

        log_channel = bot.get_channel(PAYMENT_LOG_CHANNEL_ID)
        if log_channel:
            embed_log = discord.Embed(title="💰 ผู้ใช้ส่งลิ้งเติมเงิน", color=discord.Color.green())
            embed_log.add_field(name="ผู้ส่ง", value=user.mention, inline=False)
            embed_log.add_field(name="ลิ้ง", value=link, inline=False)
            embed_log.add_field(name="เวลา", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
            embed_log.set_thumbnail(url=user.display_avatar.url)
            await log_channel.send(embed=embed_log)

        embed = discord.Embed(
            title="✅ ส่งลิ้งเรียบร้อย",
            description="รอเจ้าของบอทตรวจสอบและเพิ่มเงินให้",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------- History (เอายศคืน) -------------------
class HistoryView(discord.ui.View):
    def __init__(self, user_data, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user
        for entry in user_data:
            self.add_item(discord.ui.Button(
                label=f"❌ เอายศ {entry['role']} คืน",
                style=discord.ButtonStyle.danger,
                custom_id=f"remove_{entry['role']}_{datetime.datetime.now().timestamp()}"
            ))

    @discord.ui.button(label="❌ คืนทั้งหมด", style=discord.ButtonStyle.danger)
    async def remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        purchases = load_json(DATA_FILE)
        roles = [r["role"] for r in purchases.get(str(interaction.user.id), [])]
        for role_name in roles:
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if role:
                await interaction.user.remove_roles(role)
        purchases[str(interaction.user.id)] = []
        save_json(DATA_FILE, purchases)
        embed = discord.Embed(
            title="✅ คืนยศทั้งหมดเรียบร้อย",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------- Main Shop -------------------
class MainShopView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        options = []
        for role_id, price in ROLES_SHOP.items():
            role = guild.get_role(role_id)
            if role:
                options.append(discord.SelectOption(
                    label=role.name,
                    description=f"ราคา {price} บาท",
                    value=str(role_id)
                ))
        if options:
            self.select_menu = discord.ui.Select(
                placeholder="เลือกยศ",
                options=options,
                custom_id=f"role_select_{datetime.datetime.now().timestamp()}"
            )
            self.select_menu.callback = self.select_callback
            self.add_item(self.select_menu)

        self.add_item(discord.ui.Button(
            label="🧧 เติมเงิน",
            style=discord.ButtonStyle.green,
            custom_id=f"topup_btn_{datetime.datetime.now().timestamp()}",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="💵 เช็คยอดเงิน",
            style=discord.ButtonStyle.primary,
            custom_id=f"balance_btn_{datetime.datetime.now().timestamp()}",
            row=1
        ))
        self.add_item(discord.ui.Button(
            label="📑 บันทึกการซื้อยศ",
            style=discord.ButtonStyle.secondary,
            custom_id=f"history_btn_{datetime.datetime.now().timestamp()}",
            row=2
        ))

    async def select_callback(self, interaction: discord.Interaction):
        role_id = int(interaction.data['values'][0])
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"🎖️ ยืนยันซื้อยศ {interaction.guild.get_role(role_id).name}",
                description=f"ราคายศ: {ROLES_SHOP[role_id]} บาท\nยอดเงินของคุณ: {get_balance(interaction.user.id)} บาท",
                color=discord.Color.blue()
            ),
            view=ConfirmBuyView(role_id),
            ephemeral=True
        )

@bot.event
async def on_interaction(interaction: discord.Interaction):
    custom_id = interaction.data.get('custom_id', '')
    if custom_id.startswith("topup_btn"):
        await interaction.response.send_modal(TopUpModal())
    elif custom_id.startswith("balance_btn"):
        embed = discord.Embed(
            title="💵 ยอดเงินของคุณ",
            description=f"คุณมี {get_balance(interaction.user.id)} บาท",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif custom_id.startswith("history_btn"):
        purchases = load_json(DATA_FILE)
        user_data = purchases.get(str(interaction.user.id), [])
        if not user_data:
            embed = discord.Embed(
                title="❌ ไม่มีประวัติการซื้อยศ",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(
            title=f"📑 ประวัติการซื้อของ {interaction.user.name}",
            description="\n".join([f"🎖️ {r['role']} - 💵 {r['price']} บาท - 🕒 {r['time']}" for r in user_data]),
            color=discord.Color.purple()
        )
        view = HistoryView(user_data, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ------------------- Add Money Command -------------------
@bot.tree.command(name="addmoney", description="เพิ่มเงินให้ผู้ใช้")
@app_commands.describe(user="เลือกผู้ใช้ที่จะเพิ่มเงิน", amount="จำนวนเงินที่จะเพิ่ม")
async def addmoney(interaction: discord.Interaction, user: discord.Member, amount: int):
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ คุณไม่มีสิทธิ์ใช้คำสั่งนี้", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("❌ จำนวนเงินต้องมากกว่า 0", ephemeral=True)
        return

    add_balance(user.id, amount)

    log_channel = bot.get_channel(PAYMENT_LOG_CHANNEL_ID)
    if log_channel:
        embed_log = discord.Embed(title="💵 เติมเงินให้ผู้ใช้", color=discord.Color.gold())
        embed_log.add_field(name="ผู้ใช้", value=user.mention, inline=False)
        embed_log.add_field(name="จำนวน", value=f"{amount} บาท", inline=True)
        embed_log.add_field(name="ผู้เติม", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="เวลา", value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), inline=False)
        embed_log.set_thumbnail(url=user.display_avatar.url)
        await log_channel.send(embed=embed_log)

    embed = discord.Embed(
        title="✅ เพิ่มเงินสำเร็จ",
        description=f"ได้เพิ่ม {amount} บาท ให้กับ {user.mention}\nยอดเงินปัจจุบัน: {get_balance(user.id)} บาท",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ------------------- Bot Ready -------------------
@bot.event
async def on_ready():
    streaming = discord.Streaming(
        name="พร้อมใช้งาน💜",
        url="https://discord.gg/v2NyEFpjrC"
    )
    await bot.change_presence(activity=streaming)

    await bot.tree.sync()
    print(f"✅ บอทออนไลน์: {bot.user}")

    guild = bot.get_guild(GUILD_ID)
    channel = bot.get_channel(CHANNEL_ID)
    if not guild or not channel:
        print("❌ ไม่พบ Guild หรือ Channel")
        return

    embed = discord.Embed(
        title="💎 • ซื้อยศผ่านบอท •",
        description="`🧧 ส่งลิ้งซองทรูมันนี่เพื่อเติมเงิน`\n`🛒 ซื้อยศได้ตลอด 24 ชั่วโมง`\n`💙ขอบคุณที่มาอุดหนุนร้านเรา💙`",
        color=discord.Color.blue()
    )
    embed.set_image(url="https://media.discordapp.net/attachments/1414140348468559922/1414160989804302456/1240_20250907150943.png")

    await channel.send(embed=embed, view=MainShopView(guild))

server_on()

bot.os.getenv("TOKEN")



