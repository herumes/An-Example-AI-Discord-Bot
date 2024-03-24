import discord
from discord.ext import commands
from shuttleai import ShuttleAsyncClient
from utils import SHUTTLEAI_API_KEY

class ModelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def models(self, ctx: commands.Context):
        try:
            await ctx.defer(ephemeral=False)

            async with ShuttleAsyncClient(SHUTTLEAI_API_KEY, 120) as shuttle:
                response = await shuttle.get_models()

            models = response.data
            embeds = []

            page_size = 3  # Number of models per page
            total_pages = (len(models) + page_size - 1) // page_size  # Calculate total number of pages

            for page in range(total_pages):
                start_index = page * page_size
                end_index = start_index + page_size
                models_page = models[start_index:end_index]

                embed = discord.Embed(title=f"🚀 ShuttleAI Models [Total: {len(models)}]", url="https://api.shuttleai.app/v1/models", color=0x02b2d31)
                embed.set_footer(text=f"Page {page + 1}/{total_pages}")

                for model in models_page:
                    id = model.id
                    tokens = model.tokens or 0
                    cost = model.cost
                    is_free = not model.premium

                    if int(tokens) >= 1000000:
                        tokens = f"{int(tokens/1000000)}M"
                    elif int(tokens) > 1000:
                        tokens = f"{int(tokens/1000)}K"
                    elif int(tokens) <= 0:
                        tokens = "N/A"

                    emb_model_obj_str = f"- **Cost**: {cost}\n- **Tokens**: {tokens}\n- **Free**: {':white_check_mark:' if is_free else ':x:'}"

                    embed.add_field(name=f'`{id}`', value=emb_model_obj_str, inline=True)

                embeds.append(embed)

            paginator = EmbedPaginator()
            for embed in embeds:
                paginator.add_embed(embed)

            for embed in paginator.pages:
                view = PaginatorView(embeds)

            await ctx.send(embed=embeds[0], view=view)
        except Exception as e:
            await ctx.send("An error occurred while fetching models. Please try again later.")

class PaginatorView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.primary)
    async def previous_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            await button.message.edit(embed=self.embeds[self.current_page])
            await button.response.defer()

    @discord.ui.button(label='Next', style=discord.ButtonStyle.primary)
    async def next_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            await button.message.edit(embed=self.embeds[self.current_page])
            await button.response.defer()

class EmbedPaginator:
    def __init__(self):
        self.embeds = []

    def add_embed(self, embed):
        self.embeds.append(embed)

    @property
    def pages(self):
        return self.embeds

async def setup(bot):
    await bot.add_cog(ModelsCog(bot))