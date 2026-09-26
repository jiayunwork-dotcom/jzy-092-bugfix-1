"""服务入口：固定端口 8080。"""

from app.server import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
