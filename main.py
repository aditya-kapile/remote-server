import random
from fastmcp import FastMCP

#Create a FastMCP server instance
mcp = FastMCP(name = "demo-remote-mcp-server")


@mcp.tool
def roll_dice(n_dice : int = 1) -> list[int]:
    """Rolls n_dice dice and returns the results as a list of integers."""
    return [random.randint(1, 6) for _ in range(n_dice)]

@mcp.tool
def add_numbers(a : float, b : float) -> float:
    """Adds two numbers together."""
    return a + b


if __name__ == "__main__":
    # mcp.run()   #command to run the server  : for local server
    mcp.run(transport="http", host="0.0.0.0" , port=8000)
