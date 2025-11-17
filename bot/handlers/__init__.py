from . import auth, manager, menu, client

all_routers = [
    auth.router,
    manager.router,
    menu.router,
    client.router,
]
