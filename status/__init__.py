from .ss13status import SS13Status

async def setup(bot):
    await bot.add_cog(SS13Status(bot))
