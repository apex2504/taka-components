from .exceptions import TooManyComponents, SelectOnly
from discord.ext import commands
from enum import IntEnum
from secrets import token_hex


class Utils:
    @staticmethod
    def emoji_to_dict(emoji):
        if not emoji:
            return None

        if isinstance(emoji, str):
            return {
                "name": emoji
            }

        return {
            "id": str(emoji.id),
            "name": emoji.name,
            "animated": emoji.animated
        }


    @staticmethod
    def dict_to_emoji(bt):
        if not bt['emoji'].get('id'):
                return bt['emoji']['name']
        else:
            return ComponentEmoji(
                bt['emoji'].get('id'),
                bt['emoji'].get('name'),
                bt['emoji'].get('animated'),
        )


    @staticmethod
    def create_button(bt):
        if isinstance(bt.get('emoji'), dict):
            emoji = Utils.dict_to_emoji(bt)
        else:
            emoji = bt.get('emoji')

        return Button(
            bt.get('style'),
            bt.get('label'),
            emoji,
            bt.get('custom_id'),
            bt.get('url'),
            bt.get('disabled', False)
        )

    
    @staticmethod
    def create_dropdown(dd):
        return SelectMenu(
            dd.get('custom_id'),
            [Utils.create_select_option(opt) for opt in dd.get('options', [])],
            dd.get('placeholder'),
            dd.get('min_values'),
            dd.get('max_values')
        )


    @staticmethod
    def create_select_option(opt):
        if isinstance(opt.get('emoji'), dict):
            emoji = Utils.dict_to_emoji(opt)
        else:
            emoji = opt.get('emoji')
        return MenuOption(
            opt.get('label'),
            opt.get('value'),
            opt.get('description'),
            emoji,
            opt.get('default', False)
        )


    @staticmethod
    def parse_components(payload_components):
        rows = []

        for action_row in payload_components:
            comps = []

            for component in action_row['components']:
                if component['type'] == 2:
                    comps.append(Utils.create_button(component))
                if component['type'] == 3:
                    comps.append(Utils.create_dropdown(component))

            rows.append(ActionRow(comps))

        return rows


class ComponentEmoji:
    def __init__(self, id_, name, animated):
        self.id = id_
        self.name = name
        self.animated = animated


    async def to_discord_emoji(self, ctx):
        emoji_str = f'<:{self.name}:{self.id}>'
        return await commands.EmojiConverter().convert(ctx, emoji_str)


class Component:
    def __init__(self, custom_id, disabled):
        self.custom_id = custom_id or token_hex(50)
        self.disabled = False if disabled is None else disabled


class MenuOption:
    def __init__(self, label, value, description=None, emoji=None, default=False):
        self.label = label
        self.value = value
        self.description = description
        self.emoji = emoji
        self.default = default


    def __repr__(self):
        return f'<MenuOption label={self.label}, value={self.value}, description={self.description}, default={self.default}>'


    def to_dict(self):
        return {
            'label': self.label,
            'value': self.value,
            'description': self.description,
            'emoji': Utils.emoji_to_dict(self.emoji),
            'default': self.default
        }


class SelectMenu(Component):
    def __init__(self, custom_id=None, options=None, placeholder=None, min_values=None, max_values=None, disabled=None):
        super().__init__(custom_id, disabled)
        self.options = options or []
        self.placeholder = placeholder
        self.min_values = min_values or 1
        self.max_values = max_values or 1


    def __repr__(self):
        return f'<SelectMenu placeholder={self.placeholder}, {len(self.options)} options, disabled={self.disabled}>'


    def to_dict(self):
        return {
            'type': 3,
            'custom_id': self.custom_id,
            'placeholder': self.placeholder,
            'min_values': self.min_values,
            'max_values': self.max_values,
            'options': [opt.to_dict() for opt in self.options],
            'disabled': self.disabled
        }


    def add_option(self, label, value, description=None, emoji=None, default=False):
        self.options.append(
            MenuOption(
                label,
                value,
                description,
                emoji,
                default
            )
        )
        return self


class ButtonType(IntEnum):
    Primary = 1
    Secondary = 2
    Success = 3
    Danger = 4
    Link = 5


class Button(Component):
    def __init__(self, style, label, emoji=None, custom_id=None, url=None, disabled=False):
        super().__init__(custom_id, disabled)
        self.style = style
        self.label = label
        self.emoji = emoji
        self.url = url


    def __repr__(self):
        return f'<Button label={self.label}, style={self.style}, disabled={self.disabled}>'


    def to_dict(self):
        base_dict = {
            "type": 2,
            "label": self.label,
            "style": self.style,
            "emoji": Utils.emoji_to_dict(self.emoji),
            "disabled": self.disabled
        }

        if self.style is not ButtonType.Link:
            base_dict['custom_id'] = self.custom_id
            return base_dict

        base_dict['url'] = self.url
        return base_dict


class ActionRow:
    def __init__(self, components=None):
        self.components = components or []
        self.buttons = components #backwards compat


    def __repr__(self):
        return f'ActionRow with {len(self.components)} components.'
    

    def add_component(self, component):
        if len(self.components) == 0:
            pass

        elif isinstance(component, SelectMenu):
            raise SelectOnly('A single SelectMenu must be the only component in an ActionRow.')

        elif len(self.components) == 5:
            raise TooManyComponents('ActionRows can only have up to 5 components.')

        self.components.append(component)
        return self


    def to_dict(self):
        return {
            "type": 1,
            "components": [comp.to_dict() for comp in self.components]
        }
