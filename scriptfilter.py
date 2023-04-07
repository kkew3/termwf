import json
import typing as ty

__all__ = [
    'Item',
    'JsonResponse',
]


# pylint: disable=too-few-public-methods
class Item:
    ARG_AS_TITLE = object()

    def __init__(self, title, subtitile=None, arg=ARG_AS_TITLE):
        """
        :type title: str
        :type subtitile: None | str
        :type arg: None | Item.ARG_AS_TITLE | str | Iterable[str]
        """
        self._resp = {'title': title}
        if subtitile:
            self._resp['subtitle'] = subtitile
        if arg is Item.ARG_AS_TITLE:
            self._resp['arg'] = self._resp['title']
        elif arg:
            if isinstance(arg, str):
                self._resp['arg'] = arg
            else:
                self._resp['arg'] = list(arg)

    def __repr__(self):
        return json.dumps(self._resp)

    __str__ = __repr__


class JsonResponse:
    def __init__(self):
        self._written = False
        self._items = []

    def add_item(self, item: ty.Union[str, Item]):
        if isinstance(item, str):
            item = Item(item)
        self._items.append(item)
        return self

    def add_items(self, items: ty.Iterable[Item]):
        self._items.extend(items)
        return self

    def __repr__(self):
        return json.dumps({'items': [x._resp for x in self._items]})

    __str__ = __repr__

    def write_response(self):
        if not self._written:
            self._written = True
            print(self)
