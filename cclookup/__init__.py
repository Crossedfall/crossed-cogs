from .cclookup import CCLookup


def setup(bot):
    bot.add_cog(CCLookup(bot))
