import discord
from .components import Utils
from aiohttp import ClientSession, FormData
from json import dumps

class InteractionsHandler:
    def __init__(self, bot):
        self.bot = bot


    def _build_component_message(self, partial_msg, channel_id):
        c = self.bot.get_channel(channel_id)
        return ComponentMessage(state=self.bot._connection, channel=c, data=partial_msg)


    def build_files(self, data, files):
        form = FormData()
        form.add_field('payload_json', dumps(data, separators=(',', ':'), ensure_ascii=True))
        for i, f in enumerate(files):
            form.add_field(
                f'file{i}',
                f.fp,
                filename = f.filename,
                content_type = 'application/octet-stream',
            )

        return form


    def build_msg(self, content, components, embeds=[], reply_to=None, mention_author=None, tts=None, ephemeral=None, allowed_mentions=None):
        allowed_mentions = ComponentsHandler._get_am(self.bot, {'allowed_mentions': allowed_mentions})

        data = {
            "content": content,
            "components": [comp.to_dict() for comp in components] if isinstance(components, list) else [],
            "tts": tts,
            "flags": 64 if ephemeral else None,
        }

        if embeds is None:
            data["embeds"] = []
        
        else:
            if isinstance(embeds, list):
                data["embeds"] = [emb.to_dict() for emb in embeds]
            else:
                data["embeds"] = [embeds.to_dict()]

        if reply_to:
            data["message_reference"] = {
                "message_id": str(reply_to.id),
                "channel_id": str(reply_to.channel.id),
                "guild_id": str(reply_to.guild.id)
            }
            if mention_author is None:
                mention_author = True
            allowed_mentions['replied_user'] = mention_author

        data['allowed_mentions'] = allowed_mentions

        return data


    async def respond(self, interaction_id, interaction_token, content, components, embeds,
    reply_to, mention_author, tts, ephemeral, files):
        to_send = {
            "type": 4,
            "data": self.build_msg(
                content,
                components,
                embeds,
                reply_to,
                tts,
                mention_author,
                ephemeral,
            )
        }

        if files:
            form = self.build_files(to_send, files)
            await self.bot.http.request(discord.http.Route('POST', f'/interactions/{interaction_id}/{interaction_token}/callback'), data=form, files=files)
            for f in files:
                f.close()

        else:
            await self.bot.http.request(discord.http.Route('POST', f'/interactions/{interaction_id}/{interaction_token}/callback'), json=to_send)


    async def follow_up(self, channel_id, interaction_id, interaction_token, content, components, embeds, tts, ephemeral):
        to_send = self.build_msg(
            content,
            components,
            embeds,
            tts = tts,
            ephemeral = ephemeral
        )

        partial_msg = await self.bot.http.request(
            discord.http.Route('POST', f'/webhooks/{self.bot.user.id}/{interaction_token}'),
            json = to_send
        )

        return self._build_component_message(partial_msg, channel_id)


    async def send(self, channel, content, components, embeds, reply_to, mention_author, tts, files):
        to_send = self.build_msg(
            content,
            components,
            embeds,
            reply_to,
            mention_author,
            tts,
            None
        )

        if files:
            form = self.build_files(to_send, files)
            partial_msg = await self.bot.http.request(discord.http.Route('POST', f'/channels/{channel.id}/messages'), data=form, files=files)
            for f in files:
                f.close()

        else:
            partial_msg = await self.bot.http.request(discord.http.Route('POST', f'/channels/{channel.id}/messages'), json=to_send)

        return self._build_component_message(partial_msg, channel.id)


    async def defer(self, interaction_id, interaction_token, ephemeral, edit_original):
        to_send = {
            "type": 5 if not edit_original else 6,
            "data": {
                "flags": 64 if ephemeral else None
            }
        }

        await self.bot.http.request(
            discord.http.Route('POST', f'/interactions/{interaction_id}/{interaction_token}/callback'),
            json = to_send
        )


    async def edit_response(self, channel_id, interaction_token, content, components, embeds, files):
        to_send = self.build_msg(
                content,
                components,
                embeds,
        )

        if files is not None:
            if not isinstance(files, list):
                files = [files]

        if files:
            form = self.build_files(to_send, files)
            partial_msg = await self.bot.http.request(discord.http.Route('PATCH', f'/webhooks/{self.bot.user.id}/{interaction_token}/messages/@original'), data=form, files=files)
            for f in files:
                f.close()

        else:
            partial_msg = await self.bot.http.request(discord.http.Route('PATCH', f'/webhooks/{self.bot.user.id}/{interaction_token}/messages/@original'), json=to_send)

        return self._build_component_message(partial_msg, channel_id)


    async def delete_response(self, interaction_token):
        await self.bot.http.request(
            discord.http.Route('DELETE', f'/webhooks/{self.bot.user.id}/{interaction_token}/messages/@original'),
        )


    async def edit_original(self, interaction_id, interaction_token, content, embeds, components, mention_author):
        to_send = {
            "type": 7,
            "data": self.build_msg(
                content,
                components,
                embeds
            )
        }

        await self.bot.http.request(
            discord.http.Route('POST', f'/interactions/{interaction_id}/{interaction_token}/callback'),
            json = to_send
        )


    async def edit_message(self, channel_id, message_id, content, embeds, components):
        to_send = self.build_msg(
            content,
            components,
            embeds
        )

        await self.bot.http.request(
            discord.http.Route('PATCH', f'/channels/{channel_id}/messages/{message_id}'),
            json = to_send
        )


    async def delete_message(self, channel_id, message_id):
        await self.bot.http.request(
            discord.http.Route('DELETE', f'/channels/{channel_id}/messages/{message_id}')
        )


class PartialMessage:
    def __init__(self, msg_id, flags):
        self.id = msg_id
        self.ephemeral = True if flags == 64 else False


class MessageReference(discord.MessageReference):
    def __init__(self, *, message_id, channel_id, guild_id=None, fail_if_not_exists=True):
        super().__init__(message_id=message_id, channel_id=channel_id, guild_id=guild_id, fail_if_not_exists=fail_if_not_exists)

    @classmethod
    def with_state(cls, state, data):
        self = cls.__new__(cls)
        self.message_id = discord.utils._get_as_snowflake(data, 'message_id')
        self.channel_id = int(data['channel_id']) if data.get('channel_id') else 0 #dpy why
        self.guild_id = discord.utils._get_as_snowflake(data, 'guild_id')
        self.fail_if_not_exists = data.get('fail_if_not_exists', True)
        self._state = state
        self.resolved = None
        return self



class ComponentMessage(discord.Message):
    def __init__(self, *, state, channel, data):
        super().__init__(state=state, channel=channel, data=data)
        self.components = Utils.parse_components(data.get('components'))

    def _handle_components(self, value):
        self.components = Utils.parse_components(value)

    async def edit(self, **kwargs):
        """Usage of this is exactly the same as discord.py's `Message.edit()`
        except `embed` has been switched out for `embeds` and a `components` param is supported."""

        try:
            components = kwargs['components']
        except KeyError:
            pass
        else:
            if components is not None and components != []:
                kwargs['components'] = [comp.to_dict() for comp in kwargs['components']]

        try:
            content = kwargs['content']
        except KeyError:
            pass
        else:
            if content is not None:
                kwargs['content'] = str(content)

        try:
            embeds = kwargs['embeds']
        except KeyError:
            pass
        else:
            if embeds is not None:
                kwargs['embeds'] = [embed.to_dict() for embed in embeds] if isinstance(kwargs['embeds'], list) else [kwargs['embeds'].to_dict()]

        try:
            suppress = kwargs.pop('suppress')
        except KeyError:
            pass
        else:
             flags = discord.MessageFlags._from_value(self.flags.value)
             flags.suppress_embeds = suppress
             kwargs['flags'] = flags.value

        delete_after = kwargs.pop('delete_after', None)

        try:
            allowed_mentions = kwargs.pop('allowed_mentions')
        except KeyError:
            pass
        else:
            if allowed_mentions is not None:
                if self._state.allowed_mentions is not None:
                    allowed_mentions = self._state.allowed_mentions.merge(allowed_mentions).to_dict()
                else:
                    allowed_mentions = allowed_mentions.to_dict()
                kwargs['allowed_mentions'] = allowed_mentions

        if kwargs:
            data = await self._state.http.edit_message(self.channel.id, self.id, **kwargs)
            self._update(data)

        if delete_after is not None:
            await self.delete(delay=delete_after)



class InteractionResponse:
    def __init__(self, bot, message, member, member_id, guild, guild_id, channel,
    channel_id, interaction_id, interaction_token, custom_id, values, component_type):
        self._bot = bot
        self.message = message
        self.member = member
        self.member_id = member_id
        self.guild = guild
        self.guild_id = guild_id
        self.channel = channel
        self.channel_id = channel_id
        self.mention = f'<@{self.member_id}>'
        self.interaction_id = interaction_id
        self.interaction_token = interaction_token
        self.custom_id = custom_id
        self.values = values
        self.component_type = component_type
        self._deferred = False
        self._responded = False


    async def respond(self, content=None, embeds=[], reply_to=None, mention_author=False, tts=False, ephemeral=False, files=None, **kwargs):

        if embeds == []:
            if kwargs.get('embed'):
                embeds.append(kwargs['embed'])
        
        if files:
            if not isinstance(files, list):
                files = [files]

        if not self._responded:
            if not self._deferred:
                components = kwargs.get('components', [])
                await InteractionsHandler(self._bot).respond(
                    self.interaction_id,
                    self.interaction_token,
                    content,
                    components,
                    embeds,
                    reply_to,
                    mention_author,
                    tts,
                    ephemeral,
                    files
                )

            else:
                components = kwargs.get('components', [])
                await InteractionsHandler(self._bot).edit_response(
                    self.channel_id,
                    self.interaction_token,
                    content,
                    components,
                    embeds,
                    files
                )

            self._responded = True
            return InteractionMessage(content, embeds, components, ephemeral, self, files, self.interaction_id, self.interaction_token)

        components = kwargs.get('components', [])
        await InteractionsHandler(self._bot).follow_up(
            self.channel_id,
            self.interaction_id,
            self.interaction_token,
            content,
            components,
            embeds,
            tts,
            ephemeral
        )

        return InteractionMessage(content, embeds, components, ephemeral, self, files, self.interaction_id, self.interaction_token)


    async def defer(self, ephemeral=False, edit_original=False):
        self._deferred = True
        await InteractionsHandler(self._bot).defer(
            self.interaction_id,
            self.interaction_token,
            ephemeral,
            edit_original
        )


    async def edit_original(self, **kwargs):
        mention_author = kwargs.get('mention_author', True)
        content = kwargs.get('content', getattr(self.message, 'content', None))
        embs = kwargs.get('embed', [])
        if embs == []:
            embs = kwargs.get('embeds', self.message.embeds)

        if embs is None:
            embs = []

        components = kwargs.get('components', getattr(self.message, 'components', []))

        if self._deferred:
            raise TypeError('edit_original should only be used if the interaction response has not been deferred.')

        await InteractionsHandler(self._bot).edit_original(
            self.interaction_id,
            self.interaction_token,
            content,
            embs,
            components,
            mention_author
        )

        self.message.content = content
        self.message.embeds = embs if isinstance(embs, list) else [embs]
        self.message.components = components

        self._responded = True


    async def _edit_response(self, content, embeds, components, response_message, files):
        await InteractionsHandler(self._bot).edit_response(
            self.channel_id,
            self.interaction_token,
            content,
            components,
            embeds,
            files
        )
        response_message.content = content or response_message.content
        response_message.embeds = embeds
        response_message.components = components or response_message.components
        response_message.files = files


    async def _delete_response(self):
        await InteractionsHandler(self._bot).delete_response(
            self.interaction_token
        )


class InteractionMessage:
    def __init__(self, content, embeds, components, ephemeral, interaction, discord_files, interaction_id, interaction_token):
        self.content = content
        self.embeds = embeds
        self.components = components
        self.ephemeral = ephemeral
        self.interaction = interaction
        self.discord_files = discord_files
        self._interaction_id = interaction_id
        self._interaction_token = interaction_token

    
    async def delete(self):
        if self.ephemeral:
            raise RuntimeError('Cannot delete an ephemeral message.')

        await self.interaction._delete_response()

    async def edit(self, content=None, embeds=None, components=None, files=None):
        if content is None:
            content = self.content
        if embeds is None:
            embeds = self.embeds
        if files is None:
            files = self.discord_files

        await self.interaction._edit_response(
            content,
            embeds,
            components,
            self,
            files
        )


class ComponentsHandler:
    def __init__(self, bot):
        self.bot = bot
        self.handler = InteractionsHandler(self.bot)
    

    @staticmethod
    def _get_am(bot, kwargs):
        if bot._connection.allowed_mentions:
            allowed_mentions = bot._connection.allowed_mentions.to_dict()
        else:
            allowed_mentions = {}
        
        if kwargs.get('allowed_mentions'):
            if kwargs['allowed_mentions'] is not None:
                if bot._connection.allowed_mentions is not None:
                    allowed_mentions = bot._connection.allowed_mentions.merge(allowed_mentions).to_dict()
                else:
                    allowed_mentions = allowed_mentions.to_dict()
            else:
                allowed_mentions = []
        
        return allowed_mentions


    async def send(self, channel, content=None, components=None, embeds=[], reply_to=None, mention_author=False, tts=False, files=None, **kwargs):
        if embeds == []:
            if kwargs.get('embed'):
                embeds.append(kwargs['embed'])

        if files is not None:
            if not isinstance(files, list):
                files = [files]

        return await self.handler.send(
            channel,
            content,
            components,
            embeds,
            reply_to,
            mention_author,
            tts,
            files
        )