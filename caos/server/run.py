from caos.http import app
from caos.config import Settings


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=Settings.from_env().port)
