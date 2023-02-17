# taka-components

### Pretty much none of this is in use anymore. It has been rewritten and integrated into Taka's core library. Don't use it.

[This code remains here on GitHub both for posterity and for me to look back on in the future and laugh at myself. Maybe I'll remove it, maybe I won't. But the code was never the important part.](https://youtu.be/BxV14h0kFs0?t=609)

Extremely basic discord.py message components handler made for Taka. Slash commands are not supported at all despite the name interactions.

I don't actually intend on providing support on GitHub or even documentation for this and I don't expect you to use it in your projects.

This was made entirely because at the time there weren't any discord.py component libs that I liked using.

This lib includes the bare minimum to use all component types in your messages.

You can't install this via pip because I haven't bothered to set that up. If you want to use it, then clone this and copy the `interactions` folder to your bot's main directory.

Despite everything above, if you still want to use this and need help you can join https://support.taka.moe and ask me directly.

An extremely basic example of a bot supporting buttons would be something like the following;

```py
import discord
import interactions
from discord.ext import commands


bot = commands.Bot(command_prefix='!')
interactions.InitialiseComponentInteractionBase(bot)


@bot.event()
async def on_ready():
    print('online')


@bot.command(name='example')
async def button_example_command(ctx):
    ar = interactions.create_action_row() #create an ActionRow which is essentially a container for components
    ar.add_component(interactions.create_button(label='Button', style=interactions.ButtonType.Primary)) #add a Button to the ActionRow

    m = await bot.handler.send(
        channel = ctx.channel,
        content = 'Click the button!',
        components = [ar]
    )

    i = await bot.wait_for('button_press', check=lambda b: b.message.id==m.id and b.member.id==ctx.author.id)
    await i.respond('Well done, you clicked it!')
 
 
 bot.run('token')
```
