__all__ = ("ExpenseBot",)


def __getattr__(name: str):
    if name == "ExpenseBot":
        from .bot import ExpenseBot

        return ExpenseBot
    raise AttributeError(name)
