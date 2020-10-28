from .verifyckey import VerifyCkey

def setup(bot):
    bot.add_cog(VerifyCkey(bot))