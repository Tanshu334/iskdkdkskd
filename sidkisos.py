import discord
import datetime
import asyncio
import sqlite3
from discord.ext import commands
from discord.ext.commands.errors import MissingPermissions
from discord.ext.commands.errors import MemberNotFound
from discord.ext.commands.errors import CommandNotFound
from discord.ext.commands.errors import MissingRequiredArgument

print("The current discord version is:")
print(discord.__version__)

warnings = {}
bot = commands.Bot(command_prefix=">", intents=discord.Intents.all())
token = "MTExNjAzNjc2Nzg4NDI1NTI4Mw.GgXl4I.rZRjjWPUp_AcleEM2VmAdHTa8un2y8EgJlADV8"


@bot.event
async def on_guild_join(guild):
    welcome_message = f"Hey there, i'm {bot.user.name}, a moderation bot.And i'm developed by very tuff cat#4499! Please type '>commands' to begin!"

    # Find a channel to send the welcome message
    channel = guild.system_channel or guild.text_channels[0]  # Use the first available text channel if no system channel

    await channel.send(welcome_message)	
    
conn = sqlite3.connect('bot_database.db')
c = conn.cursor()

# Create the table to store channel IDs if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS channels
             (guild_id INTEGER PRIMARY KEY, welcome_channel_id INTEGER, goodbye_channel_id INTEGER)''')

@bot.command()
async def welcome(ctx, channel: discord.TextChannel):
    guild_id = ctx.guild.id
    welcome_channel_id = channel.id
    
    # Store the welcome channel ID in the database
    c.execute("INSERT OR REPLACE INTO channels (guild_id, welcome_channel_id) VALUES (?, ?)", (guild_id, welcome_channel_id))
    conn.commit()
    
    await ctx.send(f"Welcome channel has been set to {channel.mention}!")

@bot.command()
async def goodbye(ctx, channel: discord.TextChannel):
    guild_id = ctx.guild.id
    goodbye_channel_id = channel.id
    
    # Store the goodbye channel ID in the database
    c.execute("INSERT OR REPLACE INTO channels (guild_id, goodbye_channel_id) VALUES (?, ?)", (guild_id, goodbye_channel_id))
    conn.commit()
    
    await ctx.send(f"Goodbye channel has been set to {channel.mention}!")

# Retrieve the stored channel IDs
def get_channel_ids(guild_id):
    c.execute("SELECT welcome_channel_id, goodbye_channel_id FROM channels WHERE guild_id = ?", (guild_id,))
    result = c.fetchone()
    if result:
        return result
    return None

# Example usage to retrieve the welcome channel ID
@bot.event
async def on_member_join(member):
    guild = member.guild
    guild_id = member.guild.id
    channel_ids = get_channel_ids(guild_id)
    if channel_ids:
        welcome_channel_id, _ = channel_ids
        if welcome_channel_id:
            welcome_channel = bot.get_channel(welcome_channel_id)
            if welcome_channel:
                await welcome_channel.send(f"Hey {member.mention}, welcome to {guild.name}! Hope you have a great time here.")

# Example usage to retrieve the goodbye channel ID
@bot.event
async def on_member_remove(member):
    guild_id = member.guild.id
    channel_ids = get_channel_ids(guild_id)
    if channel_ids:
        _, goodbye_channel_id = channel_ids
        if goodbye_channel_id:
            goodbye_channel = bot.get_channel(goodbye_channel_id)
            if goodbye_channel:
                await goodbye_channel.send(f"{member.name}#{member.discriminator} has left the server! We'll miss you!")

@bot.event
async def on_ready():
    print(f"Successfully logged into {bot.user.name}!")

@bot.event
async def on_disconnect():
    conn.close()
    
@bot.command(brief="Kick a member from the server", help=f"{bot.command_prefix}kick <member> [reason]")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
        if reason is None:
            reason = "No Reason Provided!"
    
        await ctx.guild.kick(member, reason=f"{reason}")
        embed = discord.Embed(title="Success", description=f"User {member.mention} has been kicked! Reason: {reason}", color=discord.Color.green())
        await ctx.send(embed=embed)

@bot.command(brief="Create a role with custom permissions", help=f"{bot.command_prefix}createrole <member> <role_name> [+perm1] [+perm2] [-perm3] ...")
@commands.has_permissions(manage_roles=True)
async def createrole(ctx, member: discord.Member, role_name, *perms):
    permissions = discord.Permissions()
    perm_strings = []
    
    for perm in perms:
        if perm.startswith("+"):
            perm = perm[1:]
            permission = getattr(discord.Permissions, perm, None)
            if permission:
                permissions.update(**{perm: True})
                perm_strings.append(f"+{perm}")

    role = await ctx.guild.create_role(name=role_name, permissions=permissions)
    await member.add_roles(role)
    embed = discord.Embed(title="Success", description=f"Role `{role.name}` created and assigned to {member.mention} with the following permissions: {' '.join(perm_strings)}", color=discord.Color.green())
    await ctx.send(embed=embed)
        
@bot.command(brief="Ban a member from the server", help=f"{bot.command_prefix}ban <member> [reason]")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "No Reason Provided!"
    
    await ctx.guild.ban(member, reason=f"{reason}")
    embed = discord.Embed(title="Success", description=f"User {member.mention} has been banned! Reason: {reason}", color=discord.Color.green())
    await ctx.send(embed=embed)
    
@bot.command(brief="Unban a user from the server", help=f"{bot.command_prefix}unban <user_id>")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        embed = discord.Embed(title="Success", description=f"{user.name}#{user.discriminator} has been unbanned!", color=discord.Color.green())
        await ctx.send(embed=embed)
    except discord.NotFound:
        embed = discord.Embed(title="Error", description="User not found. Please provide a valid user ID.")
        await ctx.send("User not found. Please provide a valid user ID.")


@bot.command(brief="Warn a member", help=f"{bot.command_prefix}warn <member> <reason>")
@commands.has_permissions(kick_members=True, ban_members=True)
async def warn(ctx, member: discord.Member, *, reason=None):
    if reason is None:
        reason = "No Reason Provided!"

    if member.id not in warnings:
        warnings[member.id] = 1
    else:
        warnings[member.id] += 1

    warning_count = warnings[member.id]
    if not warning_count >= 3:
        await ctx.send(f"{member.mention} has been warned, This is their {warning_count} warning.")
    if warning_count == 3:
        await ctx.guild.kick(member)
        await ctx.send(f"{member.mention} has been kicked, This is their 3rd warning.")
    if warning_count >= 5:
        await ctx.guild.ban(member)
        await ctx.send(f"{member.mention} has been permanently banned.")


@bot.command(brief="Remove a warning from a member", help=f"{bot.command_prefix}unwarn <member>")
@commands.has_permissions(kick_members=True, ban_members=True)
async def unwarn(ctx, member: discord.Member):
    if member.id in warnings:
        warnings[member.id] -= 1
        warning_count = warnings[member.id]
        await ctx.send(f"Cleared {member.mention}'s warnings.")
    else:
        await ctx.send(f"{member.mention} has no warnings.")

def format_duration(duration):
    days = duration.days
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    duration_string = ""
    if days > 0:
        duration_string += f"{days}d "
    if hours > 0:
        duration_string += f"{hours}h "
    if minutes > 0:
        duration_string += f"{minutes}m "
    if seconds > 0:
        duration_string += f"{seconds}s"

    return duration_string.strip()

@bot.command(brief="Mute a member for a specified duration", help=f"{bot.command_prefix}tempmute <member> <duration>")
@commands.has_permissions(manage_roles=True)
async def tempmute(ctx, member: discord.Member, duration):
    duration_dict = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    duration_unit = duration[-1]
    duration_value = int(duration[:-1]) * duration_dict[duration_unit]

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False)

    await member.add_roles(mute_role)
    await ctx.send(f"{member.mention} has been muted for {format_duration(datetime.timedelta(seconds=duration_value))}.")

    await asyncio.sleep(duration_value)
    await member.remove_roles(mute_role)

@bot.command(brief="Mute a member for a specified duration", help=f"{bot.command_prefix}mute <member> <duration>")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    
    if not muted_role:
        # Create muted role if it doesn't exist
        muted_role = await ctx.guild.create_role(name='Muted')
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False)

    await member.add_roles(muted_role)
    await ctx.send(f'{member.mention} has been muted.')

@bot.command(brief="Unmute a member", help=f"{bot.command_prefix}unmute <member>")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name='Muted')
    
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f'{member.mention} has been unmuted.')
    else:
        await ctx.send(f'{member.mention} is not muted.')
        
@bot.command(brief="Set new prefix", help=f"{bot.command_prefix}prefix <new prefix>")
@commands.has_permissions(manage_guild=True)
async def prefix(ctx, new_prefix=None):
    if new_prefix is None:
        await ctx.send(f"The current prefix is `{bot.command_prefix}`")
    else:
        bot.command_prefix = new_prefix
        await ctx.send(f"Prefix updated to `{new_prefix}`")

@bot.command(brief="Delete a specified number of messages", help=f"{bot.command_prefix}purge <amount>")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount+1)  # Add 1 to include the command message
    await ctx.send(f"Deleted {amount} messages.")
    await asyncio.sleep(1)
    await ctx.channel.purge(limit=1)
    
@bot.command(brief="Says anything with the bot.", help=f"{bot.command_prefix}say <message>")
async def say(ctx, *, text):
    await ctx.message.delete()
    await ctx.send(text)

@bot.command(brief="Says anything with the bot to a target person in private message.", help=f"{bot.command_prefix}dm <target> <message>")
async def dm(ctx, member: discord.Member, *, text):
    await ctx.message.delete()
    await member.send(f"{text}")

@bot.command(brief="Shows The Commands")
async def commands(ctx):
    embed = discord.Embed(title="Commands:", color=discord.Color.random())

    for command in bot.commands:
        embed.add_field(name=command.name, value=command.brief, inline=False)

    await ctx.send(embed=embed)

#error handler
@bot.event 
async def on_command_error(ctx, error):
	if isinstance(error, CommandNotFound):
		embed = discord.Embed(title="Error", description=f"{error}! Please type '{bot.command_prefix}commands' to get a list of all the valid commands.", color=discord.Color.red())
		await ctx.send(embed=embed)
	elif isinstance(error, MissingRequiredArgument):
		command = ctx.command
		embed = discord.Embed(title="Usage:", description=command.help, color=discord.Color.random())
		await ctx.send(embed=embed)
	elif isinstance(error, MissingPermissions):
		missing_permissions = error.missing_perms
		embed = discord.Embed(title="Error", description=f"You don't have the following permission(s) to use this command: {missing_permissions}")
		await ctx.send(embed=embed)
		

bot.run(token)
