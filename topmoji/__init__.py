from .topmoji import Topmoji

async def setup(bot):
    await bot.add_cog(Topmoji(bot))
