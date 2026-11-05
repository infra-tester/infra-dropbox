from app import create_app
from server import run

application = create_app()


if __name__ == "__main__":
    run(application)
