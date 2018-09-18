from .ss13status import SS13Status

def setup(bot):
    bot.add_cog(SS13Status(bot))