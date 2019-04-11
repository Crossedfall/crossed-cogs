from redbot.core import data_manager
from .breenreacts import BreenReacts

def setup(bot):
    bot.add_cog(BreenReacts(bot))