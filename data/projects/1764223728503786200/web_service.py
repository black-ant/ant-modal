import modal

app = modal.App("web-service")

@app.function()
@modal.web_endpoint(method="GET")
def api_hello(name: str = "World"):
    return {"message": f"Hello, {name}!"}
