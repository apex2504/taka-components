import discord
from .components import Utils
from .handler import InteractionResponse, ComponentsHandler, ComponentMessage, PartialMessage, MessageReference


class InitialiseComponentInteractionBase:
    def __init__(self, bot):
        discord.message.MessageReference = MessageReference #otherwise messages with replies will raise a KeyError
        self.bot = bot
        self.bot.osr = self.on_socket_response
        self.bot.add_listener(self.bot.osr, 'on_socket_response')
        self.bot.handler = ComponentsHandler(self.bot)


    async def on_socket_response(self, payload):
        if payload['t'] != 'INTERACTION_CREATE':
            return

        if not payload.get('d'):
            return

        elif not payload['d'].get('message', {}).get('components') and not payload['d'].get('data', {}).get('custom_id'):
            return
         

        d = payload['d']
        msg_dict = payload['d'].get('message')

        member_id = int(d['member']['user']['id'])
        guild_id = int(d['guild_id'])
        guild = self.bot.get_guild(guild_id) or await self.bot.fetch_guild(guild_id)
        member = discord.Member(data=d['member'], guild=guild, state=self.bot._connection)
        interaction_id = int(d['id'])
        interaction_token = d['token']
        custom_id = d['data']['custom_id']
        component_type = d['data']['component_type']
        channel_id = msg_dict.get('channel_id')
        channel_id = int(channel_id) if channel_id else None
        channel = self.bot.get_channel(channel_id) if channel_id else None

        if len(msg_dict) == 2:
            message = PartialMessage(
                int(msg_dict['id']),
                msg_dict['flags']
            )

        else:
            message = ComponentMessage(state=self.bot._connection, channel=channel, data=msg_dict)

        resp = InteractionResponse(
                self.bot,
                message,
                member,
                member_id,
                guild,
                guild_id,
                channel,
                channel_id,
                interaction_id,
                interaction_token,
                custom_id,
                None,
                component_type,
            )

        if component_type == 2:
            self.bot.dispatch('button_press', resp)
        elif component_type == 3:
            resp.values = d['data']['values']
            self.bot.dispatch('selection', resp)
