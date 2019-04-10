from redbot.core import data_manager
from .projectbreen import ProjectBreen

def setup(bot):
    bot.add_cog(ProjectBreen(bot))