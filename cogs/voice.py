import asyncio
import json
import os
import sqlite3
import traceback

import discord
from discord.ext import commands


class voice(commands.Cog):

    def initDB(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS `guild` ( `guildID` INTEGER, `ownerID` INTEGER, `voiceChannelID` INTEGER, `voiceCategoryID` INTEGER )")
        c.execute(
            "CREATE TABLE IF NOT EXISTS `guildSettings` ( `guildID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER, `maxBitrate` INTEGER )")
        c.execute(
            "CREATE TABLE IF NOT EXISTS `userSettings` ( `userID` INTEGER, `channelName` TEXT, `channelLimit` INTEGER, `bitrate` INTEGER, `permissions` TEXT )")
        c.execute(
            "CREATE TABLE IF NOT EXISTS `voiceChannel` ( `userID` INTEGER, `voiceID` INTEGER )")
        conn.commit()
        c.close()
        conn.close()

    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.environ.get('VCB_DB_PATH') or 'voice.db'
        self.admin_role_id = os.environ["ADMIN_ROLE_ID"] or None
        self.booster_role_id = os.environ["BOOSTER_ROLE_ID"] or None
        self.initDB()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = member.guild.id
        c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
        voice = c.fetchone()
        try:
            if voice is None:
                print(f"No voice channel found for GuildID: {guildID}")
            else:
                voiceID = voice[0]
                if after.channel is not None and after.channel.id == voiceID:
                    c.execute(
                        "SELECT * FROM voiceChannel WHERE userID = ?", (member.id,))
                    cooldown = c.fetchone()
                    if cooldown is None:
                        pass
                    else:
                        old_chan = self.bot.get_channel(cooldown[1])
                        if old_chan is None:  # If channel no longer exists but still in database
                            c.execute('DELETE FROM voiceChannel WHERE userID=?', (member.id,))
                        elif before.channel is None:  # If channel already exists but shouldn't yet
                            await old_chan.delete()
                            c.execute('DELETE FROM voiceChannel WHERE userID=?', (member.id,))
                        else:
                            await member.send("Creating channels too quickly you've been put on a 15 second cooldown!")
                            await asyncio.sleep(15)
                            if member.voice is None:  # If member has left voice channel
                                return
                    c.execute(
                        "SELECT voiceCategoryID FROM guild WHERE guildID = ?", (guildID,))
                    voice = c.fetchone()
                    c.execute(
                        "SELECT channelName, channelLimit, bitrate, permissions FROM userSettings WHERE userID = ?", (member.id,))
                    setting = c.fetchone()
                    c.execute(
                        "SELECT channelLimit FROM guildSettings WHERE guildID = ?", (guildID,))
                    guildSetting = c.fetchone()
                    if setting is None:
                        name = f"{member.name}'s channel"
                        if guildSetting is None:
                            limit = 0
                        else:
                            limit = guildSetting[0]
                        bitrate = 64
                        permissions = {}
                    else:
                        if guildSetting is None:
                            name = setting[0]
                            limit = setting[1]
                        elif guildSetting is not None and setting[1] == 0:
                            name = setting[0]
                            limit = guildSetting[0]
                        else:
                            name = setting[0]
                            limit = setting[1]
                        bitrate = setting[2] or 64
                        permissions = json.loads(setting[3]) if setting[3] else {}
                    categoryID = voice[0]
                    mid = member.id
                    category = self.bot.get_channel(categoryID)
                    print(f"Creating channel {name} in {category}")
                    channel2 = await member.guild.create_voice_channel(name, category=category)
                    channelID = channel2.id
                    print(f"Moving {member} to {channel2}")
                    await member.move_to(channel2)
                    #print(f"Setting permissions on {channel2}")
                    #await channel2.set_permissions(self.bot.user, connect=True, read_messages=True)
                    print(f"Set user limit to {limit} on {channel2}")
                    await channel2.edit(name=name, user_limit=limit)
                    if bitrate != 64:
                        print(f"Setting bitrate to {bitrate}kbps on {channel2}")
                        await channel2.edit(bitrate=bitrate * 1000)
                    for userID in permissions:
                        member_temp = member.guild.get_member(int(userID))
                        if member_temp is None:
                            continue
                        print(f"Setting permission to {permissions[userID]} for {member_temp}")
                        await channel2.set_permissions(member_temp, connect=permissions[userID], read_messages=True)
                    print(f"Track voiceChannel {mid},{channelID}")
                    c.execute(
                        "INSERT INTO voiceChannel VALUES (?, ?)", (mid, channelID))
                    conn.commit()

                    def check(a, b, c):
                        return len(channel2.members) == 0
                    await self.bot.wait_for('voice_state_update', check=check)
                    print(f"Deleting Channel {channel2} because everyone left")
                    await channel2.delete()
                    await asyncio.sleep(3)
                    c.execute('DELETE FROM voiceChannel WHERE userID=?', (mid,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            conn.commit()
            conn.close()

    @commands.command()
    async def help(self, ctx):
        embed = discord.Embed(title="Help", description="", color=0x7289da)
        embed.set_author(name="Voice Create", url="https://github.com/t1m0thyj/VoiceCreateBot",
                         icon_url="https://i.imgur.com/Ix8pdWil.png")
        embed.add_field(name=f'**Commands**\n\n**Lock your channel by using the following command:**',
                        value=f'`.voice lock`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Unlock your channel by using the following command:**',
                        value=f'`.voice unlock`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Change your channel name by using the following command:**',
                        value=f'`.voice name <name>`\n\n**Example:** `.voice name EU 5kd+`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Change your channel limit by using the following command:**',
                        value='`.voice limit number`\n\n**Example:** `.voice limit 2`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Give users permission to join by using the following command:**',
                        value='`.voice permit @person`\n\n**Example:** `.voice permit @Sam#9452`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Claim ownership of channel once the owner has left:**',
                        value='`.voice claim`\n\n**Example:** `.voice claim`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Remove permission and the user from your channel using the following command:**',
                        value='`.voice reject @person`\n\n**Example:** `.voice reject @Sam#9452`\n\n------------\n\n', inline='false')
        embed.add_field(name=f'**Change channel bitrate if you are a Nitro Booster using the following command:**',
                        value='`.voice bitrate number`\n\n**Example:** `.voice bitrate 128`\n\n', inline='false')
        embed.set_footer(
            text='Bot developed by Sam#9452. Improved by DarthMinos#1161 and ArtfulAardvark#9968')
        await ctx.channel.send(embed=embed)

    @commands.group()
    async def voice(self, ctx):
        pass

    @voice.command(pass_context=True)
    async def setup(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        guildID = ctx.guild.id
        print(f"User id triggering setup: {ctx.author.id}")
        print(f"Owner id: {ctx.guild.owner.id}")
        print(f"Admin role id: {self.admin_role_id}")
        is_author_admin = self.admin_role_id in [str(role.id) for role in ctx.author.roles]
        print(f"Is user admin: {is_author_admin}")
        aid = ctx.author.id
        if ctx.author.id == ctx.guild.owner.id or is_author_admin:
            def check(m):
                return m.author.id == ctx.author.id
            await ctx.channel.send("**You have 60 seconds to answer each question!**")
            await ctx.channel.send(f"**Enter the name of the category you wish to create the channels in:(e.g Voice Channels)**")
            try:
                category = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await ctx.channel.send('Took too long to answer!')
            else:
                new_cat = None
                for old_cat in ctx.guild.categories:
                    if old_cat.name == category.content:
                        new_cat = old_cat
                if new_cat is None:
                    new_cat = await ctx.guild.create_category_channel(category.content)
                await ctx.channel.send('**Enter the name of the voice channel: (e.g Join To Create)**')
                try:
                    channel = await self.bot.wait_for('message', check=check, timeout=60.0)
                except asyncio.TimeoutError:
                    await ctx.channel.send('Took too long to answer!')
                else:
                    try:
                        new_chan = None
                        for old_chan in new_cat.channels:
                            if old_chan.name == channel.content:
                                new_chan = old_chan
                        if new_chan is None:
                            new_chan = await ctx.guild.create_voice_channel(channel.content, category=new_cat)
                        c.execute(
                            "SELECT * FROM guild WHERE guildID = ? AND ownerID=?", (guildID, aid))
                        voiceGroup = c.fetchone()
                        if voiceGroup is None:
                            c.execute("INSERT INTO guild VALUES (?, ?, ?, ?)",
                                      (guildID, aid, new_chan.id, new_cat.id))
                        else:
                            c.execute("UPDATE guild SET guildID = ?, ownerID = ?, voiceChannelID = ?, voiceCategoryID = ? WHERE guildID = ?", (
                                guildID, aid, new_chan.id, new_cat.id, guildID))
                        await ctx.channel.send("**You are all setup and ready to go!**")
                    except Exception as e:
                        traceback.print_exc()
                        await ctx.channel.send("You didn't enter the names properly.\nUse `.voice setup` again!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
    async def setlimit(self, ctx, num):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        is_author_admin = self.admin_role_id in [str(role.id) for role in ctx.author.roles]
        # removed the specific user permission and checked for admin status instead.
        if ctx.author.id == ctx.guild.owner.id or is_author_admin:
            c.execute("SELECT * FROM guildSettings WHERE guildID = ?",
                      (ctx.guild.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO guildSettings VALUES (?, ?, ?, ?)",
                          (ctx.guild.id, f"{ctx.author.name}'s channel", num, None))
            else:
                c.execute(
                    "UPDATE guildSettings SET channelLimit = ? WHERE guildID = ?", (num, ctx.guild.id))
            await ctx.send("You have changed the default channel limit for your server!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
        conn.commit()
        conn.close()

    @commands.command(pass_context=True)
    async def maxbitrate(self, ctx, num):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        is_author_admin = self.admin_role_id in [str(role.id) for role in ctx.author.roles]
        # removed the specific user permission and checked for admin status instead.
        if ctx.author.id == ctx.guild.owner.id or is_author_admin:
            c.execute("SELECT * FROM guildSettings WHERE guildID = ?",
                      (ctx.guild.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO guildSettings VALUES (?, ?, ?, ?)",
                          (ctx.guild.id, f"{ctx.author.name}'s channel", 0, num))
            else:
                c.execute(
                    "UPDATE guildSettings SET maxBitrate = ? WHERE guildID = ?", (num, ctx.guild.id))
            await ctx.send("You have changed the maximum channel bitrate for your server!")
        else:
            await ctx.channel.send(f"{ctx.author.mention} only the owner or admins of the server can setup the bot!")
        conn.commit()
        conn.close()

    @setup.error
    async def info_error(self, ctx, error):
        print(error)

    @voice.command()
    async def lock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        print(f"{ctx.author} triggered lock")
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='Member')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat locked! 🔒')
        conn.commit()
        conn.close()

    @voice.command()
    async def unlock(self, ctx):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            role = discord.utils.get(ctx.guild.roles, name='Member')
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(role, connect=True, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} Voice chat unlocked! 🔓')
        conn.commit()
        conn.close()

    @voice.command(aliases=["allow"])
    async def permit(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        elif int(member.id) == aid:
            await ctx.channel.send(f"{ctx.author.mention} You can't permit yourself.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.set_permissions(member, connect=True)
            await ctx.channel.send(f'{ctx.author.mention} You have permitted {member.name} to have access to the channel. ✅')
            c.execute(
                "SELECT permissions FROM userSettings WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?)",
                          (aid, f'{ctx.author.name}', 0, None, None, json.dumps({member.id: True})))
            else:
                permissions = json.loads(voiceGroup[0]) if voiceGroup[0] else {}
                permissions[member.id] = True
                c.execute(
                    "UPDATE userSettings SET permissions = ? WHERE userID = ?", (json.dumps(permissions), aid))
        conn.commit()
        conn.close()

    @voice.command(aliases=["deny"])
    async def reject(self, ctx, member: discord.Member):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        guildID = ctx.guild.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        elif int(member.id) == aid:
            await ctx.channel.send(f"{ctx.author.mention} You can't reject yourself.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            for members in channel.members:
                if members.id == member.id:
                    c.execute(
                        "SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildID,))
                    voiceGroup = c.fetchone()
                    channel2 = self.bot.get_channel(voiceGroup[0])
                    await member.move_to(channel2)
            await channel.set_permissions(member, connect=False, read_messages=True)
            await ctx.channel.send(f'{ctx.author.mention} You have rejected {member.name} from accessing the channel. ❌')
            c.execute(
                "SELECT permissions FROM userSettings WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?)",
                          (aid, f'{ctx.author.name}', 0, None, None, json.dumps({member.id: False})))
            else:
                permissions = json.loads(voiceGroup[0]) if voiceGroup[0] else {}
                permissions[member.id] = False
                c.execute(
                    "UPDATE userSettings SET permissions = ? WHERE userID = ?", (json.dumps(permissions), aid))
        conn.commit()
        conn.close()

    @voice.command()
    async def limit(self, ctx, limit):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        elif 0 <= int(limit) < 100:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(user_limit=limit)
            await ctx.channel.send(f'{ctx.author.mention} You have set the channel limit to be ' + '{}!'.format(limit))
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?)",
                          (aid, f'{ctx.author.name}', limit, None, None))
            else:
                c.execute(
                    "UPDATE userSettings SET channelLimit = ? WHERE userID = ?", (limit, aid))
        else:
            await ctx.channel.send(f"{ctx.author.mention} Invalid limit - must be 2-99 or 0 for no limit.")
        conn.commit()
        conn.close()

    @voice.command()
    async def name(self, ctx, *, name=None):
        name = name or f"{ctx.author.name}'s channel"
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            await channel.edit(name=name)
            await ctx.channel.send(f'{ctx.author.mention} You have changed the channel name to ' + '{}!'.format(name))
            c.execute(
                "SELECT channelName FROM userSettings WHERE userID = ?", (aid,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                c.execute(
                    "INSERT INTO userSettings VALUES (?, ?, ?, ?, ?)", (aid, name, 0, None, None))
            else:
                c.execute(
                    "UPDATE userSettings SET channelName = ? WHERE userID = ?", (name, aid))
        conn.commit()
        conn.close()

    @voice.command()
    async def claim(self, ctx):
        x = False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        channel = ctx.author.voice.channel
        if channel == None:
            await ctx.channel.send(f"{ctx.author.mention} you're not in a voice channel.")
        else:
            aid = ctx.author.id
            c.execute(
                "SELECT userID FROM voiceChannel WHERE voiceID = ?", (channel.id,))
            voiceGroup = c.fetchone()
            if voiceGroup is None:
                await ctx.channel.send(f"{ctx.author.mention} You can't own that channel!")
            else:
                for data in channel.members:
                    if data.id == voiceGroup[0]:
                        owner = ctx.guild.get_member(voiceGroup[0])
                        await ctx.channel.send(f"{ctx.author.mention} This channel is already owned by {owner.mention}!")
                        x = True
                if x == False:
                    await ctx.channel.send(f"{ctx.author.mention} You are now the owner of the channel!")
                    c.execute(
                        "UPDATE voiceChannel SET userID = ? WHERE voiceID = ?", (aid, channel.id))
            conn.commit()
            conn.close()

    @voice.command()
    async def bitrate(self, ctx, new_bitrate):
        new_bitrate = int(new_bitrate)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        aid = ctx.author.id
        c.execute("SELECT voiceID FROM voiceChannel WHERE userID = ?", (aid,))
        voiceGroup = c.fetchone()
        is_author_admin = self.admin_role_id in [str(role.id) for role in ctx.author.roles]
        is_author_booster = self.booster_role_id in [str(role.id) for role in ctx.author.roles]
        if voiceGroup is None:
            await ctx.channel.send(f"{ctx.author.mention} You don't own a channel.")
        elif not is_author_admin and not is_author_booster:
            await ctx.channel.send(f"{ctx.author.mention} You need to be a Nitro Booster to use this command.")
        else:
            channelID = voiceGroup[0]
            channel = self.bot.get_channel(channelID)
            old_bitrate = int(channel.bitrate / 1000)
            c.execute("SELECT maxBitrate FROM guildSettings WHERE guildID = ?", (ctx.guild.id,))
            guildSetting = c.fetchone()
            if guildSetting is None or not guildSetting[0]:
                c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (ctx.guild.id,))
                voiceGroup = c.fetchone()
                channel2 = self.bot.get_channel(voiceGroup[0])
                max_bitrate = channel2.bitrate
            else:
                max_bitrate = guildSetting[0]
            if new_bitrate < 8 or new_bitrate > max_bitrate:
                await ctx.channel.send(f"{ctx.author.mention} Invalid bitrate specified (must be between 8 and {max_bitrate}).")
            elif new_bitrate == old_bitrate:
                await ctx.channel.send(f'{ctx.author.mention} Channel bitrate already is {new_bitrate}kbps, nothing to change.')
            else:
                await channel.edit(bitrate=new_bitrate * 1000)
                await ctx.channel.send(f'{ctx.author.mention} You have changed the channel bitrate from {old_bitrate}kbps to {new_bitrate}kbps!')
                c.execute(
                    "SELECT channelName FROM userSettings WHERE userID = ?", (aid,))
                voiceGroup = c.fetchone()
                if voiceGroup is None:
                    c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?)",
                            (aid, f'{ctx.author.name}', 0, new_bitrate, None))
                else:
                    c.execute(
                        "UPDATE userSettings SET bitrate = ? WHERE userID = ?", (new_bitrate, aid))
        conn.commit()
        conn.close()


async def setup(bot):
    await bot.add_cog(voice(bot))
