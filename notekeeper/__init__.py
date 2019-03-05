from .notekeeper import NoteKeeper

def setup(bot):
    bot.add_cog(NoteKeeper(bot))