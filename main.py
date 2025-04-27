from keep_alive import keep_alive
keep_alive()
import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

user_scores = {}
user_data = {}

button_config = [
    ("最高レート", "rate_input", 0),
    ("最高レート更新(ND)", "rate_update_nd", 5, "once"),
    ("最高レート更新(AD)", "rate_update_ad", 5, "once"),
    ("個人大会で優勝", "tournament_win", 5),
    ("最高レート1700以降10刻み(ND)", "rate_1700_nd", 5),
    ("最高レート1700以降10刻み(AD)", "rate_1700_ad", 5),
    ("10連勝", "win10", 5, "once"),
    ("15連勝", "win15", 5, "once"),
    ("20連勝", "win20", 5, "once"),
    ("二桁連勝相手に勝利", "vs_win_streak", 5),
    ("ランキング一桁相手に勝利", "vs_rank_top10", 5),
    ("瞬間一位達成", "first_place", 10, "once"),
    ("レート1700達成", "rate_1700", 15, "once"),
    ("最終TOP100入り(ND)", "final_top100_nd", 15, "once"),
    ("最終TOP100入り(AD)", "final_top100_ad", 15, "once"),
    ("最終TOP100入り(クイックピック)", "final_top100_qp", 15, "once")
]

class ScoreButton(discord.ui.Button):
    def __init__(self, label, custom_id, style=discord.ButtonStyle.secondary, row=0):
        super().__init__(label=label, custom_id=custom_id, style=style, row=row)

    async def callback(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        if user_id not in user_scores:
            user_scores[user_id] = 0
            user_data[user_id] = {"achievements": set(), "rate": 0, "pressed": set(), "last_action": None}

        if self.custom_id == "rate_input":
            await interaction.response.send_modal(RateInputModal(user_id))
            return

        entry = next((e for e in button_config if e[1] == self.custom_id), None)
        if not entry:
            return

        label, cid, point = entry[:3]
        once = (len(entry) == 4 and entry[3] == "once")
        data = user_data[user_id]

        if once and cid in data["achievements"]:
            await interaction.response.send_message(f"{interaction.user.mention} はすでに「{label}」を達成しています。", ephemeral=True)
            return

        if cid == "win15" and "win10" not in data["achievements"]:
            await interaction.response.send_message(f"{interaction.user.mention}：「10連勝」を先に達成してください。", ephemeral=True)
            return
        if cid == "win20" and "win15" not in data["achievements"]:
            await interaction.response.send_message(f"{interaction.user.mention}：「15連勝」を先に達成してください。", ephemeral=True)
            return

        user_scores[user_id] += point
        data["achievements"].add(cid)
        data["last_action"] = {"cid": cid, "point": point}

        await interaction.response.send_message(
            f"{interaction.user.mention} が「{label}」を選択しました ✅（+{point}点）", ephemeral=False
        )

class RateInputModal(discord.ui.Modal, title="最高レートを入力"):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    rate = discord.ui.TextInput(label="最高レート（半角数字）", style=discord.TextStyle.short, required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            rate_value = int(self.rate.value)
        except ValueError:
            await interaction.response.send_message("❌ 半角数字で入力してください。", ephemeral=True)
            return

        user_data[self.user_id]["rate"] = rate_value
        user_scores[self.user_id] = rate_value
        user_data[self.user_id]["last_action"] = None
        await interaction.response.send_message(f"{interaction.user.mention} の最高レートを {rate_value} に設定しました！", ephemeral=False)

class ScoreButtons(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.add_buttons()

    def add_buttons(self):
        for idx, (label, cid, *_rest) in enumerate(button_config):
            self.add_item(ScoreButton(label=label, custom_id=cid, row=idx // 5))
        self.add_item(ScoreButton(label="集計", custom_id="score_show_total", style=discord.ButtonStyle.green, row=3))
        self.add_item(ScoreButton(label="リセット", custom_id="score_reset", style=discord.ButtonStyle.danger, row=4))
        self.add_item(ScoreButton(label="取消", custom_id="score_undo", style=discord.ButtonStyle.secondary, row=4))

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ ログイン成功: {bot.user}")

@bot.tree.command(name="start", description="得点集計ボットを起動します")
async def start(interaction: discord.Interaction):
    view = ScoreButtons(user_id=str(interaction.user.id))
    await interaction.response.send_message("✅ ボタンから選択してください！", view=view, ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type.name == "component":
        user_id = str(interaction.user.id)
        cid = interaction.data["custom_id"]

        if user_id not in user_scores:
            user_scores[user_id] = 0
            user_data[user_id] = {"achievements": set(), "rate": 0, "pressed": set(), "last_action": None}

        data = user_data[user_id]

        if cid == "score_show_total":
            score = user_scores[user_id]
            await interaction.response.send_message(
                f"{interaction.user.mention} の現在の得点は **{score}点** です。",
                ephemeral=False
            )

        elif cid == "score_reset":
            user_scores[user_id] = 0
            user_data[user_id] = {"achievements": set(), "rate": 0, "pressed": set(), "last_action": None}
            await interaction.response.send_message(
                f"{interaction.user.mention} のスコアと実績をリセットしました。", ephemeral=False
            )

        elif cid == "score_undo":
            last = data.get("last_action")
            if last and last["cid"] in data["achievements"]:
                user_scores[user_id] -= last["point"]
                data["achievements"].discard(last["cid"])
                data["last_action"] = None
                await interaction.response.send_message(f"{interaction.user.mention} の直前の操作を取り消しました。", ephemeral=False)
            else:
                await interaction.response.send_message("取り消す操作がありません。", ephemeral=True)

        else:
            await bot.process_application_commands(interaction)

bot.run(TOKEN)
