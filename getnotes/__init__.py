from .getnotes import GetNotes

def setup(bot):
    bot.add_cog(GetNotes(bot))