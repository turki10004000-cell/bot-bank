import discord
from discord.ext import commands
import random
import time
import asyncio

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# قاعدة البيانات الشاملة
users_db = {}

# إعدادات المتجر العامة (الأسعار الحالية والحدود)
store_items = {
    "اجهزه": {"min": 20000, "mid": 35000, "max": 50000, "current": 35000},
    "متجر": {"min": 60000, "mid": 105000, "max": 150000, "current": 105000},
    "سياره": {"min": 30000, "mid": 65000, "max": 100000, "current": 65000},
    "بيت": {"min": 40000, "mid": 60000, "max": 80000, "current": 60000},
    "اراضي": {"min": 100000, "mid": 250000, "max": 400000, "current": 250000},
    "مبنى": {"min": 95000, "mid": 117500, "max": 140000, "current": 117500},
    "شركه": {"min": 120000, "mid": 160000, "max": 200000, "current": 160000},
    "ذهب": {"min": 300000, "mid": 350000, "max": 400000, "current": 350000},
    "اسهم": {"min": 500000, "mid": 1000000, "max": 1500000, "current": 1000000}
}

store_last_update = time.time()

def update_store_prices():
    global store_last_update
    if time.time() - store_last_update >= 7200: # كل ساعتين
        for item in store_items.values():
            item["current"] = random.randint(item["min"], item["max"])
        store_last_update = time.time()

def get_store_time_remaining():
    elapsed = time.time() - store_last_update
    rem = max(0, 7200 - elapsed)
    mins = int(rem // 60)
    secs = int(rem % 60)
    return f"{mins:02d}:{secs:02d}"

def get_user(user_id):
    if user_id not in users_db:
        users_db[user_id] = {
            "balance": 1000,
            "loan": 0,
            "spouses": [],
            "shield_until": 0,
            "inventory": {k: 0 for k in store_items.keys()},
            "cooldowns": {}
        }
    return users_db[user_id]

def check_cooldown(user, command_name, duration=300):
    now = time.time()
    last = user["cooldowns"].get(command_name, 0)
    if now - last < duration:
        rem = duration - (now - last)
        mins = int(rem // 60)
        secs = int(rem % 60)
        return False, f"انتظر باقي {mins} دقيقة و {secs} ثانية"
    return True, 0

def set_cooldown(user, command_name):
    user["cooldowns"][command_name] = time.time()

def format_time(remaining):
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return f"{mins} دقيقة و {secs} ثانية"

@bot.event
async def on_ready():
    print(f'✅ بوت البنك {bot.user.name} يعمل الآن بكامل المزايا والشروط!')

# ----------------- واجهات الأزرار (Select Menus / Dropdowns) -----------------

class LoanSelect(discord.ui.Select):
    def __init__(self, requested_amount, user_id):
        self.requested_amount = requested_amount
        self.user_id = user_id
        options = [
            discord.SelectOption(label="5k", description="سحب من رصيدك 5k يوميًا حتى الانتهاء"),
            discord.SelectOption(label="10k", description="سحب من رصيدك 10k يوميًا حتى الانتهاء"),
            discord.SelectOption(label="20k", description="سحب من رصيدك 20k يوميًا حتى الانتهاء"),
            discord.SelectOption(label="50k", description="سحب من رصيدك 50k يوميًا حتى الانتهاء"),
            discord.SelectOption(label="100k", description="سحب من رصيدك 100k يوميًا حتى الانتهاء"),
        ]
        super().__init__(placeholder="اختر نوع القرض", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
            return
        
        val_map = {"5k": 5000, "10k": 10000, "20k": 20000, "50k": 50000, "100k": 100000}
        selected_val = val_map[self.values[0]]
        user = get_user(self.user_id)

        if self.requested_amount > selected_val:
            set_cooldown(user, "rob") # عقوبة 5 دقائق
            await interaction.response.edit_message(content="**تم رفض قرضك يا عفوي**", view=None)
        else:
            user["loan"] = selected_val
            user["balance"] += self.requested_amount
            await interaction.response.edit_message(content=f"**سيتم سحب ({selected_val}$) يوميًا حتى الانتهاء**", view=None)

class LoanView(discord.ui.View):
    def __init__(self, requested_amount, user_id):
        super().__init__(timeout=60)
        self.add_item(LoanSelect(requested_amount, user_id))

class DivorceSelect(discord.ui.Select):
    def __init__(self, husband_id, spouses):
        self.husband_id = husband_id
        options = []
        for spouse_id in spouses:
            spouse_user = discord.utils.get(bot.get_all_members(), id=spouse_id)
            name = spouse_user.name if spouse_user else f"مستخدم {spouse_id}"
            options.append(discord.SelectOption(label=f"({name})", value=str(spouse_id)))
        super().__init__(placeholder="اختر الزوجة للطلاق", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.husband_id:
            await interaction.response.send_message("❌ هذه القائمة ليست لك!", ephemeral=True)
            return
        
        spouse_id = int(self.values[0])
        husband_data = get_user(self.husband_id)
        spouse_data = get_user(spouse_id)
        
        if spouse_id in husband_data["spouses"]:
            husband_data["spouses"].remove(spouse_id)
        if self.husband_id in spouse_data["spouses"]:
            spouse_data["spouses"].remove(self.husband_id)
            
        spouse_user = interaction.guild.get_member(spouse_id)
        spouse_name = spouse_user.name if spouse_user else "زوجة"
        
        await interaction.response.edit_message(content=f"**تم طلاق الزوجة ({spouse_name})**", view=None)

class DivorceView(discord.ui.View):
    def __init__(self, husband_id, spouses):
        super().__init__(timeout=60)
        self.add_item(DivorceSelect(husband_id, spouses))

class StoreDetailsSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=k, value=k) for k in store_items.keys()]
        super().__init__(placeholder="رؤية تفاصيل المنتجات…", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_key = self.values[0]
        item = store_items[item_key]
        desc = f"السعر الاعلى\n{item['max']}$\nالسعر المتوسط\n{item['mid']}$\nالسعر الادنى\n{item['min']}$\nالسعر الحالي\n{item['current']}$"
        embed = discord.Embed(title=f"تفاصيل منتج: {item_key}", description=desc, color=0x000000)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class StoreDetailsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(StoreDetailsSelect())

class BuySelect(discord.ui.Select):
    def __init__(self, qty=1):
        self.qty = qty
        options = [discord.SelectOption(label=k, value=k) for k in store_items.keys()]
        super().__init__(placeholder="قم بشراء منتج", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_key = self.values[0]
        item = store_items[item_key]
        total_cost = item["current"] * self.qty
        user = get_user(interaction.user.id)

        if user["balance"] < total_cost:
            await interaction.response.edit_message(content="**لا تملك المبلغ المطلوب**", view=None)
        else:
            user["balance"] -= total_cost
            user["inventory"][item_key] += self.qty
            await interaction.response.edit_message(content="**تم شراء المنتج**", view=None)

class BuyView(discord.ui.View):
    def __init__(self, qty=1):
        super().__init__(timeout=60)
        self.add_item(BuySelect(qty))

class SellSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=k, value=k) for k in store_items.keys()]
        super().__init__(placeholder="لبيع منتجات…", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_key = self.values[0]
        item = store_items[item_key]
        user = get_user(interaction.user.id)

        if user["inventory"][item_key] <= 0:
            await interaction.response.edit_message(content="**لا تملك المنتج**", view=None)
        else:
            user["inventory"][item_key] -= 1
            user["balance"] += item["current"]
            await interaction.response.edit_message(content="**تم بيع المنتج**", view=None)

class SellView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(SellSelect())

# ----------------- الأوامر -----------------

@bot.command(name="البنك", aliases=["اوامر", "بنك"])
async def bank_help(ctx):
    embed = discord.Embed(
        title="الاوامر الخاصه بالبوت",
        description="**بخشيش**\n**تحويل**\n**توب**\n**حراميه**\n**حظ**\n**راتب**\n**رهان**\n**قرض**\n**سداد**\n**فلوس**\n**نهب**\n**استثمار**\n**تداول**\n**قمار**\n**حمايه**\n**نرد**\n**زواج**\n**زواجي**\n**زواجات**\n**طلاق**\n**خلع**\n**متجر**\n**شراء**\n**بيع**\n**ممتلكات**\n**وقت**",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="بخشيش")
async def bakhsheesh(ctx):
    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, "bakhsheesh")
    if not ok:
        await ctx.send(msg)
        return

    chance = random.randint(1, 100)
    if chance <= 55:
        amount = random.randint(1000, 2000)
    elif chance <= 90:
        amount = random.randint(300, 999)
    else:
        amount = random.randint(2001, 2500)

    user["balance"] += amount
    set_cooldown(user, "bakhsheesh")

    embed = discord.Embed(
        description=f"**ما نقص من مال صدقة**\nالمبلغ : {amount}$\nرصيدك الحالي : {user['balance']}$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="تحويل")
async def transfer(ctx, member: discord.Member = None, amount: int = 0):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    if not member or amount <= 0:
        await ctx.send("❌ الاستخدام: تحويل @الشخص المبلغ أو الرد على رسالته.")
        return

    if amount < 1000:
        await ctx.send("❌ لا يقدر يحول اقل من 1000")
        return

    sender = get_user(ctx.author.id)
    if sender["balance"] < amount:
        await ctx.send("**بس يا الغني انت ما معك المبلغ**")
        return

    receiver = get_user(member.id)
    fee = int(amount * 0.10)
    final_amount = amount - fee

    sender["balance"] -= amount
    receiver["balance"] += final_amount

    embed = discord.Embed(
        description=f"**اشعار تحويل**\nمن : {ctx.author.mention}\nالى : {member.mention}\nتم خصم عمولة تحويل **10%**\nالمبلغ المحول : {amount}$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="توب")
async def top(ctx):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    desc = "قائمة اغنى اشخاص بالسيرفر :\n"
    for idx, (uid, data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(uid)
        name = member.mention if member else f"مستخدم {uid}"
        desc += f"#{idx} {name} 💵 {data['balance']}$\n"

    embed = discord.Embed(description=desc, color=0x000000)
    await ctx.send(embed=embed)

@bot.command(name="حراميه")
async def thieves(ctx):
    sorted_users = sorted(users_db.items(), key=lambda x: x[1].get('stolen_total', 0), reverse=True)[:10]
    desc = "قائمة حراميه السيرفر :\n"
    for idx, (uid, data) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(uid)
        name = member.mention if member else f"مستخدم {uid}"
        desc += f"#{idx} {name} 🦹‍♂️ {data.get('stolen_total', 0)}$\n"

    embed = discord.Embed(description=desc, color=0x000000)
    await ctx.send(embed=embed)

@bot.command(name="حظ")
async def haz(ctx):
    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, "haz")
    if not ok:
        await ctx.send(msg)
        return

    chance = random.randint(1, 100)
    if chance <= 15:
        amount = random.randint(500, 1000)
    elif chance <= 45:
        amount = random.randint(1001, 2000)
    elif chance <= 70:
        amount = random.randint(2001, 3000)
    elif chance <= 85:
        amount = random.randint(3001, 4000)
    else:
        amount = random.randint(4001, 5000)

    user["balance"] += amount
    set_cooldown(user, "haz")

    embed = discord.Embed(
        description=f"**حظك هالوقت**\nالمبلغ : {amount}$\nرصيدك الحالي : {user['balance']}$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="راتب")
async def rateb(ctx):
    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, "rateb")
    if not ok:
        await ctx.send(msg)
        return

    jobs = ["مهندس", "دكتور", "سواق", "مبرمج", "محامي", "شرطي", "معلم"]
    job = random.choice(jobs)
    amount = random.randint(3000, 5000)

    user["balance"] += amount
    set_cooldown(user, "rateb")

    embed = discord.Embed(
        description=f"**اشعار ايداع راتب**\nالوظيفه : {job}\nالراتب : {amount}$\nرصيدك الحالي : {user['balance']}$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="رهان")
async def rahan(ctx, member: discord.Member = None, amount: int = 0):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, "rahan")
    if not ok:
        await ctx.send(msg)
        return

    if not member or amount < 5000:
        await ctx.send("❌ الاستخدام: رهان @الشخص المبلغ (أقل مبلغ للرهان 5000)")
        return

    u1 = user
    u2 = get_user(member.id)

    if u1["balance"] < amount or u2["balance"] < amount:
        await ctx.send("❌ أحد الطرفين لا يملك المبلغ المطلوب للرهان!")
        return

    n1, n2 = random.randint(1, 99), random.randint(1, 99)
    while n1 == n2:
        n2 = random.randint(1, 99)

    if n1 > n2:
        u1["balance"] += amount
        u2["balance"] -= amount
        winner = ctx.author.mention
    else:
        u2["balance"] += amount
        u1["balance"] -= amount
        winner = member.mention

    set_cooldown(user, "rahan")
    await ctx.send(f"🎲 نتيجة الرهان:\n{ctx.author.mention}: {n1}\n{member.mention}: {n2}\n🏆 الفائز: {winner} بمبلغ {amount}$")

@bot.command(name="قرض")
async def loan(ctx, amount: int = 0):
    if amount < 10000 or amount > 500000:
        await ctx.send("❌ القرض يجب أن يكون بين 10k و 500k.")
        return

    view = LoanView(amount, ctx.author.id)
    embed = discord.Embed(
        title="اختر نوع القرض",
        description="يرجى اختيار نوع القرض المناسب أدناه:",
        color=0x000000
    )
    await ctx.send(embed=embed, view=view)

@bot.command(name="سداد")
async def sadad(ctx, member: discord.Member = None):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    target_id = member.id if member else ctx.author.id
    user = get_user(target_id)

    if user["loan"] == 0:
        await ctx.send("❌ لا تملك قرض")
        return

    payer = get_user(ctx.author.id)
    if payer["balance"] < user["loan"]:
        await ctx.send("**ما معك يا الفقير**")
        return

    payer["balance"] -= user["loan"]
    user["loan"] = 0
    await ctx.send("**تم تسديد قرضك**")

@bot.command(name="فلوس")
async def money(ctx, member: discord.Member = None):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    target = member or ctx.author
    user = get_user(target.id)

    embed = discord.Embed(
        description=f"**رصيد البنك**\nحساب : {target.mention}\nالرصيد : {user['balance']}$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="نهب")
async def rob(ctx, member: discord.Member = None):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    if member == bot.user:
        await ctx.send("كيف تسرق بوت يغبي")
        return

    if not member:
        await ctx.send("❌ يرجى منشنة الشخص أو الرد على رسالته لسرقته.")
        return

    thief = get_user(ctx.author.id)
    victim = get_user(member.id)
    now = time.time()

    ok, msg = check_cooldown(thief, "rob")
    if not ok:
        await ctx.send(f"⌛ بس يا حرامي تعال بعد `{msg.replace('انتظر باقي ', '')}`")
        return

    if victim["shield_until"] > now:
        rem_shield = victim["shield_until"] - now
        await ctx.send(f"⌛ الحماية تنتهي بعد `{format_time(rem_shield)}`")
        return

    if now - victim.get("last_robbed_time", 0) < 300:
        rem = 300 - (now - victim.get("last_robbed_time", 0))
        await ctx.send(f"المسكين منزرف تعال بعد {format_time(rem)}")
        return

    if victim["balance"] < 5000:
        await ctx.send("❌ الضحية لا تملك فوق 5000 للسرقة.")
        return

    chance = random.randint(1, 100)
    if chance <= 70:
        percentage = random.uniform(0.01, 0.03)
    else:
        percentage = random.uniform(0.04, 0.05)

    stolen_amount = int(victim["balance"] * percentage)
    if stolen_amount < 1:
        stolen_amount = 1

    victim["balance"] -= stolen_amount
    thief["balance"] += stolen_amount
    set_cooldown(thief, "rob")
    victim["last_robbed_time"] = now
    thief["stolen_total"] = thief.get("stolen_total", 0) + stolen_amount

    await ctx.send(f"**ازبم تم نهب {stolen_amount}$ بنجاح**")

# ----------------- استثمار، تداول، قمار -----------------
async def play_game(ctx, amount, game_name, cmd_key):
    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, cmd_key)
    if not ok:
        await ctx.send(msg)
        return

    if amount is None or amount < 1000:
        await ctx.send("**اقل مبلغ للعب هو 1000$**")
        return

    if user["balance"] < amount:
        await ctx.send("**لا تملك المبلغ المطلوب**")
        return

    is_win = random.choice([True, False])
    percentage = random.randint(10, 50)
    prev_balance = user["balance"]
    set_cooldown(user, cmd_key)

    if is_win:
        profit = int(amount * (percentage / 100))
        user["balance"] += profit
        await ctx.send(f"**{game_name} رابح بنسبة {percentage}%\nمبلغ الربح  :  {profit}$\nرصيدك السابق : {prev_balance}$\nرصيدك الحالي : {user['balance']}$**")
    else:
        loss = int(amount * (percentage / 100))
        user["balance"] -= loss
        if user["balance"] < 0: user["balance"] = 0
        await ctx.send(f"**{game_name} خاسر بنسبة {percentage}%😜\nمبلغ الخسارة  : {loss}$\nرصيدك السابق : {prev_balance}$\nرصيدك الحالي : {user['balance']}$**")

@bot.command(name="استثمار")
async def invest(ctx, amount: int = 0):
    await play_game(ctx, amount, "استثمار", "invest")

@bot.command(name="تداول")
async def trade(ctx, amount: int = 0):
    await play_game(ctx, amount, "تداول", "trade")

@bot.command(name="قمار")
async def gamble(ctx, amount: int = 0):
    await play_game(ctx, amount, "قمار", "gamble")

# ----------------- الحماية -----------------
@bot.command(name="حمايه")
async def shield(ctx, hours: int = 0):
    if hours not in [1, 2, 3, 4, 5]:
        await ctx.send("**حط عدد ساعات الحماية**")
        return

    user = get_user(ctx.author.id)
    user["shield_until"] = time.time() + (hours * 3600)
    
    if hours == 1:
        await ctx.send("تم تفعيل حماية لمدة ساعة ⏳")
    else:
        await ctx.send(f"تم تفعيل حماية لمدة {hours} ساعات ⏳")

# ----------------- نرد -----------------
@bot.command(name="نرد")
async def dice(ctx, amount: int = 0):
    user = get_user(ctx.author.id)
    ok, msg = check_cooldown(user, "dice")
    if not ok:
        await ctx.send(msg)
        return

    if amount < 1000:
        await ctx.send("**اقل مبلغ للعب هو 1000$**")
        return

    if user["balance"] < amount:
        await ctx.send("**لا تملك المبلغ المطلوب**")
        return

    set_cooldown(user, "dice")
    user_num = random.randint(1, 99)
    bot_num = random.randint(1, 99)
    while user_num == bot_num:
        bot_num = random.randint(1, 99)

    if user_num > bot_num:
        user["balance"] += amount
        await ctx.send(f"**فزت بالنرد 🥳\nانت اخترت : {user_num}\nانا اخترت : {bot_num}\nمبلغ الربح  : {amount}$\nرصيدك : {user['balance']}$**")
    else:
        user["balance"] -= amount
        if user["balance"] < 0: user["balance"] = 0
        await ctx.send(f"**خسرت بالنرد\nانت اخترت : {user_num}\nانا اخترت : {bot_num}\nمبلغ الخساره  : {amount}$\nرصيدك : {user['balance']}$**")

# ----------------- الزواج والطلاق والخلع -----------------
@bot.command(name="زواج")
async def marry(ctx, member: discord.Member = None, amount: int = 0):
    if member is None and ctx.message.reference:
        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        member = ref_msg.author

    if member == bot.user:
        await ctx.send("كيف تبي تتزوج بوت يمتوحد")
        return

    if not member or amount < 10:
        await ctx.send("منشن فتاة احلامك وحط المهر")
        return

    if amount < 10000:
        await ctx.send("**اقل مبلغ للزواج هو 10,000**")
        return

    proposer = get_user(ctx.author.id)
    target = get_user(member.id)

    if len(proposer["spouses"]) >= 4:
        await ctx.send("الشرع حلل اربع بس!")
        return

    if len(target["spouses"]) >= 1:
        await ctx.send("متزوجه الله يعوضك")
        return

    if proposer["balance"] < amount:
        await ctx.send("❌ لا تملك المهر المطلوب")
        return

    msg = await ctx.send(f"**عقد زواج**\nعقد زواج من {ctx.author.mention} ل فتاة احلامه {member.mention}\nالمهر : {amount}$")
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    def check(reaction, user):
        return user.id == member.id and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == msg.id

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == "❌":
            await msg.edit(content="**تم رفض الزوج**")
        else:
            proposer["balance"] -= amount
            target["balance"] += amount
            proposer["spouses"].append(member.id)
            target["spouses"].append(ctx.author.id)
            await msg.edit(content=f"**تم عقد الزواج💍**")
    except asyncio.TimeoutError:
        await msg.edit(content="انتهى وقت الرد وتم إلغاء الزواج.")

@bot.command(name="زواجي")
async def my_marriage(ctx):
    user = get_user(ctx.author.id)
    if not user["spouses"]:
        await ctx.send("عزابي مو متزوج")
        return

    spouse_id = user["spouses"][0]
    spouse_member = ctx.guild.get_member(spouse_id)
    spouse_name = spouse_member.mention if spouse_member else "زوجة"

    embed = discord.Embed(
        description=f"**عقد الزواج 💍**\nالزوج : {ctx.author.mention}\nالزوجة : {spouse_name}\nالمهر : 10000$",
        color=0x000000
    )
    await ctx.send(embed=embed)

@bot.command(name="زواجات")
async def marriages_top(ctx):
    sorted_users = sorted(users_db.items(), key=lambda x: len(x[1]['spouses']), reverse=True)[:10]
    desc = "قائمة اغلى زواجات بالسيرفر :\n"
    for idx, (uid, data) in enumerate(sorted_users, 1):
        if not data['spouses']: continue
        member = ctx.guild.get_member(uid)
        spouse_member = ctx.guild.get_member(data['spouses'][0])
        name1 = member.mention if member else f"مستخدم {uid}"
        name2 = spouse_member.mention if spouse_member else "زوجة"
        desc += f"#{idx} {name1} 💍 {name2} 10000$\n"

    embed = discord.Embed(description=desc, color=0x000000)
    await ctx.send(embed=embed)

@bot.command(name="طلاق")
async def divorce(ctx):
    user = get_user(ctx.author.id)
    if not user["spouses"]:
        await ctx.send("عزابي انت بتطلق من")
        return

    view = DivorceView(ctx.author.id, user["spouses"])
    embed = discord.Embed(
        title="اختر الزوجة للطلاق",
        description="يرجى اختيار الزوجة المراد طلاقها أدناه:",
        color=0x000000
    )
    await ctx.send(embed=embed, view=view)

@bot.command(name="خلع")
async def khula(ctx):
    user = get_user(ctx.author.id)
    if not user["spouses"]:
        await ctx.send("عزابي بتخلع من؟")
        return

    spouse_id = user["spouses"][0]
    spouse_member = ctx.guild.get_member(spouse_id)
    spouse_name = spouse_member.mention if spouse_member else "زوجها"

    await ctx.send(f"**تم خلع {spouse_name} من قبل {ctx.author.mention} بالتوفيق**")
    user["spouses"].clear()

# ----------------- المتجر والشراء والبيع والممتلكات ووقت -----------------
update_store_prices()

@bot.command(name="متجر")
async def store(ctx):
    update_store_prices()
    timer = get_store_time_remaining()
    desc = f"**المتجر**\nسيتم التحديث خلال : {timer}\n\n"
    for k, v in store_items.items():
        desc += f"{k} : {v['current']}$\n"

    embed = discord.Embed(description=desc, color=0x000000)
    view = StoreDetailsView()
    await ctx.send(embed=embed, view=view)

@bot.command(name="شراء")
async def buy(ctx, qty: int = 1):
    update_store_prices()
    view = BuyView(qty)
    embed = discord.Embed(description="**⏳ قم بالاختيار للشراء من المتجر**", color=0x000000)
    await ctx.send(embed=embed, view=view)

@bot.command(name="بيع")
async def sell(ctx):
    update_store_prices()
    view = SellView()
    embed = discord.Embed(description="**لبيع منتجات…**", color=0x000000)
    await ctx.send(embed=embed, view=view)

@bot.command(name="ممتلكات")
async def inventory(ctx, member: discord.Member = None):
    target = member or ctx.author
    user = get_user(target.id)
    desc = "**الممتلاكات**\n"
    for k, v in user["inventory"].items():
        desc += f"{k}\n{v}\n"

    embed = discord.Embed(description=desc, color=0x000000)
    await ctx.send(embed=embed)

@bot.command(name="وقت")
async def status_time(ctx):
    user = get_user(ctx.author.id)
    now = time.time()
    cmds = ["bakhsheesh", "haz", "rateb", "rob", "rahan", "invest", "trade", "gamble", "dice"]
    
    desc = ""
    for c in cmds:
        last = user["cooldowns"].get(c, 0)
        if now - last >= 300:
            status = "🟢 جاهز للعب"
        else:
            status = "🔴 غير جاهز للعب"
        desc += f"{c} : {status}\n"

    embed = discord.Embed(title="حالة الأوقات", description=desc, color=0x000000)
    await ctx.send(embed=embed)

# ----------------- أمر السلاش /help -----------------
@bot.tree.command(name="help", description="نظام البنك والتحكم بالإعدادات")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message("⚙️ لوحة تحكم نظام البنك والنسب (قيد التشغيل)", ephemeral=True)

bot.run("MTUzNjUzNzIwMjU3MjUyOTY2NA.G2Dodu.MqFBLu2MDH3Ib8ObhUk4HofyQHvIOMDYVB2dek")
