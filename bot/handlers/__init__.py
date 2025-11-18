from . import auth, manager, menu, client, admin

all_routers = (
    auth.router,
    manager.router,
    admin.router,
    menu.router,
    client.router,
)

